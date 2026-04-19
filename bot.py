import asyncio, random, aiohttp, time, os, json, logging
from threading import Thread
from datetime import timedelta
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ChatPermissions
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import hlink

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("TOKEN")
OWNER_ID = 7799004635 
DB_FILE = "waguruko_final_db.json"

logging.basicConfig(level=logging.INFO)

app = Flask('')
@app.route('/')
def home(): return "Waguruko Final System: Active"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- DATABASE ---
class Database:
    def __init__(self, path):
        self.path = path
        self.data = self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return {"users": {}, "admins": [OWNER_ID]}

    def save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def get_user(self, uid, name="Странник"):
        uid = str(uid)
        if uid not in self.data["users"]:
            self.data["users"][uid] = {"name": name, "exp": 0, "softness": 0, "last_cake": 0, "warns": 0}
        else:
            # Обновляем имя, если оно изменилось
            self.data["users"][uid]["name"] = name
        self.save()
        return self.data["users"][uid]

db = Database(DB_FILE)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- КЛАВИАТУРА ---
def main_kb(uid):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🎭 РП Список", callback_data="rp_list"), 
                InlineKeyboardButton(text="🍰 Скушать тортик", callback_data="eat_cake"))
    builder.row(InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
                InlineKeyboardButton(text="☁️ Топ Мягкости", callback_data="top_soft"))
    builder.row(InlineKeyboardButton(text="👑 Любимчики", callback_data="admins_list"))
    if int(uid) in db.data["admins"]:
        builder.row(InlineKeyboardButton(text="🛡 Мод-Панель", callback_data="mod_help"))
    builder.row(InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu"))
    return builder.as_markup()

# --- ОБРАБОТЧИКИ КНОПОК ---

@dp.callback_query(F.data == "admins_list")
async def view_admins(call: CallbackQuery):
    txt = "<b>👑 Любимчики Вагури:</b>\n\n"
    for admin_id in db.data["admins"]:
        admin_info = db.data["users"].get(str(admin_id))
        name = admin_info["name"] if admin_info else f"User_{admin_id}"
        # Делаем имя ссылкой на профиль (через tg://user?id=...)
        txt += f"• <a href='tg://user?id={admin_id}'>{name}</a> (<code>{admin_id}</code>)\n"
    
    await call.message.edit_text(txt, parse_mode="HTML", reply_markup=main_kb(call.from_user.id))

@dp.callback_query(F.data == "eat_cake")
async def cake_logic(call: CallbackQuery):
    uid = str(call.from_user.id)
    u = db.get_user(uid, call.from_user.first_name)
    now = time.time()
    if now - u["last_cake"] < 3600:
        return await call.answer("⏳ Щечки еще не проголодались!", show_alert=True)
    growth = random.randint(0, 20)
    u["softness"] += growth
    u["last_cake"] = now
    db.save()
    await call.message.edit_text(f"🍰 <b>Ням!</b>\nМягкость щечек увеличилась на <b>{growth} ед.</b>\nВсего: <b>{u['softness']} ед.</b> ✨", 
                                 parse_mode="HTML", reply_markup=main_kb(uid))

# --- ПРИВЕТСТВИЕ И ОБРАБОТКА ИМЕН ---

@dp.message(F.new_chat_members)
async def welcome_new_member(m: types.Message):
    for member in m.new_chat_members:
        if member.is_bot: continue
        db.get_user(member.id, member.first_name)
        await m.answer(f"<b>Добро пожаловать, {member.mention_html()}!</b> 🌸\nЯ — Вагури Каоруко. Нажми кнопку, чтобы познакомиться!", 
                       parse_mode="HTML", reply_markup=main_kb(member.id))

# --- РП И МОДЕРАЦИЯ ---
RP_MAP = {"обнять": "hug", "поцеловать": "kiss", "кусь": "bite", "гладить": "pat", "уебать": "slap", "тык": "poke"}

@dp.message(F.reply_to_message)
async def reply_handler(m: types.Message):
    txt = m.text.lower().strip()
    target = m.reply_to_message.from_user
    uid = m.from_user.id
    
    # Обновляем данные обоих участников в базе при любом взаимодействии
    db.get_user(uid, m.from_user.first_name)
    db.get_user(target.id, target.first_name)
    
    is_admin = uid in db.data["admins"]

    if is_admin:
        if txt == "+админ" and uid == OWNER_ID:
            if target.id not in db.data["admins"]: db.data["admins"].append(target.id); db.save()
            return await m.answer(f"💎 {target.first_name} теперь Админ!")
        if txt == "-админ" and uid == OWNER_ID:
            if target.id in db.data["admins"]: db.data["admins"].remove(target.id); db.save()
            return await m.answer(f"❌ {target.first_name} разжалован.")
        if txt == "мут":
            await m.chat.restrict(target.id, permissions=ChatPermissions(can_send_messages=False), until_date=timedelta(minutes=15))
            return await m.answer(f"🔇 {target.first_name} в муте.")

    if txt in RP_MAP:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(f"https://api.waifu.pics/sfw/{RP_MAP[txt]}") as r:
                data = await r.json()
                await m.answer_animation(data["url"], caption=f"🌸 {m.from_user.mention_html()} {txt} {target.mention_html()}!", parse_mode="HTML")
                db.get_user(uid)["exp"] += 5; db.save()

# --- СИСТЕМНОЕ ---
@dp.message(Command("start"))
async def start_cmd(m: types.Message):
    db.get_user(m.from_user.id, m.from_user.first_name)
    await m.answer("🌸 Я Вагури! Позови меня по имени, чтобы открыть меню.", reply_markup=main_kb(m.from_user.id))

@dp.message(lambda m: any(n in m.text.lower() for n in ["вагури", "каоруко"]))
async def name_trigger(m: types.Message):
    if m.text.startswith("/") or m.new_chat_members: return
    db.get_user(m.from_user.id, m.from_user.first_name)
    await m.answer(f"Слушаю, {m.from_user.first_name}! Чем займемся?", reply_markup=main_kb(m.from_user.id))

@dp.callback_query(F.data == "close_menu")
async def close_menu(call: CallbackQuery): await call.message.delete()

# Остальные кнопки (профиль, топ и т.д.) оставить из прошлой версии
@dp.callback_query(F.data == "profile")
async def profile_call(call: CallbackQuery):
    u = db.get_user(call.from_user.id, call.from_user.first_name)
    role = "👑 Создатель" if call.from_user.id == OWNER_ID else ("🛡 Админ" if call.from_user.id in db.data["admins"] else "👤 Участник")
    await call.message.edit_text(f"<b>『 🌸 Профиль 』</b>\n\n👤 Имя: {u['name']}\n🎖 Статус: {role}\n💠 EXP: {u['exp']}\n☁️ Мягкость: {u['softness']} ед.", 
                                 parse_mode="HTML", reply_markup=main_kb(call.from_user.id))

async def main():
    keep_alive()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())