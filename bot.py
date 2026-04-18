# ADVANCED Telegram Bot: Waguri Kaoruko (aiogram 3.x)
# Production-ready, fault-tolerant, structured

import asyncio
import json
import logging
import random
import time
from threading import Thread
from typing import Dict

from aiohttp import ClientSession, ClientTimeout
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from flask import Flask

# ================= CONFIG =================
TOKEN = "8737614623:AAG988AgZyD9X1g11W2DOP4zLmW4eBHZD-4"
OWNER_ID = 7799004635
DB_FILE = "db.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ================= KEEP ALIVE =================
app = Flask(__name__)

@app.route('/')
def home():
    return "alive"


def run_web():
    app.run(host='0.0.0.0', port=8080)


def keep_alive():
    Thread(target=run_web, daemon=True).start()

# ================= DATABASE =================
class Database:
    def __init__(self, file: str):
        self.file = file
        self.data = self.load()

    def load(self) -> Dict:
        try:
            with open(self.file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {"users": {}, "admins": []}

    def save(self):
        try:
            with open(self.file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"DB SAVE ERROR: {e}")

    def get_user(self, user_id: int):
        uid = str(user_id)
        if uid not in self.data["users"]:
            self.data["users"][uid] = {
                "exp": 0,
                "cake": 0,
                "warns": 0,
                "last_cake": 0,
                "last_date": 0
            }
        return self.data["users"][uid]

    def is_admin(self, user_id: int):
        return user_id == OWNER_ID or user_id in self.data.get("admins", [])


DB = Database(DB_FILE)

# ================= BOT CORE =================
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()

# ================= UI =================
def main_menu(user_id):
    buttons = [
        [InlineKeyboardButton(text="🎭 РП", callback_data="rp")],
        [InlineKeyboardButton(text="🍰 Тортик", callback_data="cake")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🏆 Топ", callback_data="top")],
        [InlineKeyboardButton(text="❤️ Свидание", callback_data="date")],
        [InlineKeyboardButton(text="👑 Любимчики", callback_data="admins")],
    ]
    if DB.is_admin(user_id):
        buttons.append([InlineKeyboardButton(text="🛡 Админка", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ================= START =================
@router.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "<b>Вагури Каоруко здесь... 💕</b>\n"
        "Я не просто бот. Я твоя вайфу с системой прогрессии.\n\n"
        "🎭 RP\n🍰 Рост\n🏆 Топы\n🛡 Модерация",
        reply_markup=main_menu(message.from_user.id)
    )

# ================= PROFILE =================
def calc_level(exp):
    return int(exp ** 0.5)

@router.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):
    user = DB.get_user(callback.from_user.id)

    level = calc_level(user['exp'])
    role = "👑 Owner" if callback.from_user.id == OWNER_ID else ("🛡 Admin" if DB.is_admin(callback.from_user.id) else "🌸 User")

    text = (
        f"👤 <b>{callback.from_user.full_name}</b>\n"
        f"{role}\n\n"
        f"⭐ LVL: {level}\n"
        f"✨ EXP: {user['exp']}\n"
        f"🍰 Тортик: {user['cake']} см\n"
        f"⚠ Варны: {user['warns']}"
    )

    await callback.message.edit_text(text, reply_markup=main_menu(callback.from_user.id))

# ================= CAKE =================
@router.callback_query(F.data == "cake")
async def cake(callback: CallbackQuery):
    user = DB.get_user(callback.from_user.id)
    now = time.time()

    if now - user['last_cake'] < 3600:
        await callback.answer("⏳ Подожди...", show_alert=True)
        return

    grow = random.randint(0, 15)
    user['cake'] = max(0, user['cake'] + grow)
    user['last_cake'] = now

    DB.save()

    await callback.message.answer(f"🍰 +{grow} см")

# ================= DATE =================
@router.callback_query(F.data == "date")
async def date(callback: CallbackQuery):
    user = DB.get_user(callback.from_user.id)
    now = time.time()

    if now - user['last_date'] < 14400:
        await callback.answer("⏳ 4 часа кулдаун", show_alert=True)
        return

    change = random.choice([25, -5])
    user['exp'] += change
    user['last_date'] = now

    DB.save()

    await callback.message.answer(f"❤️ EXP: {change}")

# ================= TOP =================
def build_top(key):
    users = sorted(DB.data['users'].items(), key=lambda x: x[1][key], reverse=True)[:10]
    text = ""
    for i, (uid, data) in enumerate(users, 1):
        text += f"{i}. {uid} — {data[key]}\n"
    return text

@router.callback_query(F.data == "top")
async def top(callback: CallbackQuery):
    text = (
        "🏆 <b>Топы</b>\n\n"
        "🍰 Тортики:\n" + build_top("cake") + "\n"
        "✨ EXP:\n" + build_top("exp")
    )
    await callback.message.edit_text(text)

# ================= RP =================
RP_ACTIONS = ["hug","kiss","bite","pat","slap","cuddle","lick","poke","wink","smile",
              "dance","cry","laugh","blush","sleep","wave","highfive","facepalm","shrug","yeet"]

async def fetch_gif(action):
    try:
        timeout = ClientTimeout(total=5)
        async with ClientSession(timeout=timeout) as session:
            async with session.get(f"https://api.waifu.pics/sfw/{action}") as r:
                return (await r.json()).get("url")
    except Exception as e:
        logging.error(f"GIF ERROR: {e}")
        return None

@router.message()
async def rp(message: Message):
    if not message.reply_to_message or not message.text:
        return

    cmd = message.text.lower()
    if cmd not in RP_ACTIONS:
        return

    gif = await fetch_gif(cmd)
    if not gif:
        return

    user = DB.get_user(message.from_user.id)
    user['exp'] += 2
    DB.save()

    await message.answer_animation(gif)

# ================= ADMIN =================
@router.message()
async def admin(message: Message):
    if not DB.is_admin(message.from_user.id):
        return

    if not message.reply_to_message:
        return

    target = message.reply_to_message.from_user.id
    text = message.text.lower()

    if "варн" in text:
        DB.get_user(target)['warns'] += 1
        DB.save()
        await message.answer("⚠ Варн выдан")

    if "+админ" in text and message.from_user.id == OWNER_ID:
        if target not in DB.data['admins']:
            DB.data['admins'].append(target)
            DB.save()
            await message.answer("🛡 Новый админ")

# ================= RUN =================
async def main():
    keep_alive()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.critical(f"CRASH: {e}")
