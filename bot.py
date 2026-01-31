# для сервера

BOT_TOKEN = os.getenv("BOT_TOKEN")







from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from datetime import date, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ======================
# НАСТРОЙКИ
# ======================

BOT_TOKEN = "8435851436:AAHENY0AGnFImSORLrFl6Mm_kcS8_oyVMDQ"
SPREADSHEET_NAME = "bot"
ADMIN_IDS = [5010534845]

# ======================
# GOOGLE SHEETS
# ======================

import os
import json

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

google_creds = json.loads(os.getenv("GOOGLE_CREDENTIALS"))

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    google_creds, scope
)

client = gspread.authorize(creds)


sheet = client.open(SPREADSHEET_NAME).worksheet("Students")
groups_sheet = client.open(SPREADSHEET_NAME).worksheet("Groups")


# ======================
# BOT
# ======================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ======================
# CONSTANTS
# ======================

GOTFRIED_ITEMS = {
    3: "📖 Волшебная книга заклинаний",
    5: "🧪 Пояс с зельями",
    6: "🎩 Магическая шляпа",
    8: "🪄 Волшебная палочка",
    10: "💎 Древние магические камни"
}

LEVELS = {
    1:  {"title": "Новичок", "emoji": "🌱"},
    2:  {"title": "Ученик", "emoji": "📘"},
    3:  {"title": "Посвящённый", "emoji": "📖"},
    4:  {"title": "Младший маг", "emoji": "✨"},
    5:  {"title": "Маг", "emoji": "🧪"},
    6:  {"title": "Старший маг", "emoji": "🎩"},
    7:  {"title": "Чародей", "emoji": "🔥"},
    8:  {"title": "Архимаг", "emoji": "🪄"},
    9:  {"title": "Хранитель магии", "emoji": "🔮"},
    10: {"title": "Легенда Готфрида", "emoji": "💎"},
}


selected_students = {}

# ======================
# HELPERS
# ======================

def get_student_row(tg_id):
    records = sheet.get_all_records()
    for i, row in enumerate(records, start=2):
        if row["telegram_id"] == tg_id:
            return i, row
    return None, None


def add_student(tg_id, name):
    sheet.append_row([tg_id, name, "A1", 0, 0, "", ""])


def get_level(xp):
    return xp // 100 + 1

def get_level_info(level: int):
    return LEVELS.get(level, LEVELS[max(LEVELS)])



def add_xp(tg_id, amount):
    row, student = get_student_row(tg_id)
    if not student:
        return None

    old_xp = int(student["xp"])
    new_xp = old_xp + amount
    sheet.update_cell(row, 4, new_xp)

    return get_level(old_xp), get_level(new_xp)


def update_streak(tg_id):
    row, student = get_student_row(tg_id)
    today = date.today()
    last = student["last_activity"]

    if last:
        last = date.fromisoformat(last)
        if last == today:
            return
        elif last == today - timedelta(days=1):
            streak = int(student["streak"]) + 1
        else:
            streak = 1
    else:
        streak = 1

    sheet.update_cell(row, 5, streak)
    sheet.update_cell(row, 6, today.isoformat())


def give_item(tg_id, level):
    if level not in GOTFRIED_ITEMS:
        return None

    row, student = get_student_row(tg_id)
    items = student["achievements"].split(",") if student["achievements"] else []

    item = GOTFRIED_ITEMS[level]
    if item in items:
        return None

    items.append(item)
    sheet.update_cell(row, 7, ",".join(items))
    return item


# ======================
# KEYBOARDS
# ======================

def student_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📊 Профиль", "🏅 Достижения")
    kb.add("👥 Прогресс группы")
    return kb


def admin_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("👤 Выбрать ученика", "➕ ДЗ (+20 XP)")
    kb.add("📊 Статистика группы")
    return kb


# ======================
# HANDLERS
# ======================

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    tg_id = message.from_user.id
    name = message.from_user.first_name

    _, student = get_student_row(tg_id)
    if not student:
        add_student(tg_id, name)

    text = (
         "🌟 Добро пожаловать в мир магии!\n\n"
        "Ты — хранитель пути великого мага Готфрида 🧙‍♂️\n"
        "Когда-то он был самым могущественным волшебником,\n"
        "но его артефакты были утеряны…\n\n"
        "Теперь тебе предстоит помочь ему вернуть силу 💫\n\n"
        "🔹 Выполняй задания и получай XP\n"
        "🔹 Повышай уровень\n"
        "🔹 Собирай магические предметы\n\n"
        "📜 Артефакты Готфрида:\n"
        "• 📖 Книга заклинаний — 3 уровень\n"
        "• 🧪 Пояс с зельями — 5 уровень\n"
        "• 🎩 Магическая шляпа — 6 уровень\n"
        "• 🪄 Волшебная палочка — 8 уровень\n"
        "• 💎 Древние магические камни — 10 уровень\n\n"
        "✨ Начни путь — выполняй задания и повышай уровень!"
    )

    if tg_id in ADMIN_IDS:
        await message.answer(text, reply_markup=admin_kb())
    else:
        await message.answer(text, reply_markup=student_kb())


@dp.message_handler(lambda m: m.text == "📊 Профиль")
async def profile(message: types.Message):
    _, s = get_student_row(message.from_user.id)

    xp = int(s["xp"])
    level = get_level(xp)
    info = get_level_info(level)

    xp_in_level = xp % 100
    filled = xp_in_level // 10
    bar = "🟩" * filled + "⬜" * (10 - filled)

    await message.answer(
        f"🧙‍♂️ {s['name']}\n\n"
        f"{info['emoji']} Уровень {level} — {info['title']}\n"
        f"✨ XP: {xp_in_level}/100\n"
        f"{bar}"
    )



@dp.message_handler(lambda m: m.text == "🏅 Достижения")
async def achievements(message):
    _, s = get_student_row(message.from_user.id)
    items = s["achievements"].split(",") if s["achievements"] else []

    text = "🎒 Снаряжение Готфрида:\n"
    if not items:
        text += "Пока пусто"
    else:
        for i in items:
            text += f"• {i}\n"

    await message.answer(text)


@dp.message_handler(lambda m: m.text == "➕ ДЗ (+20 XP)")
async def add_hw(message):
    if message.from_user.id not in ADMIN_IDS:
        return

    student_id = selected_students.get(message.from_user.id)
    if not student_id:
        await message.answer("Сначала выбери ученика")
        return

    old, new = add_xp(student_id, 20)
    update_streak(student_id)

    if new > old:
        item = give_item(student_id, new)
        if item:
            await bot.send_message(
                student_id,
                f"🎉 Новый уровень!\nТы получил: {item}"
            )

    await message.answer("✅ +20 XP начислено")


@dp.message_handler(lambda m: m.text == "👤 Выбрать ученика")
async def choose_student(message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for s in sheet.get_all_records():
        kb.add(f"{s['name']} | {s['telegram_id']}")
    await message.answer("Выбери ученика:", reply_markup=kb)


@dp.message_handler(lambda m: "|" in m.text)
async def select_student(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    _, tg_id = message.text.split("|")
    selected_students[message.from_user.id] = int(tg_id.strip())
    await message.answer("Ученик выбран ✅", reply_markup=admin_kb())


# ======================
# START
# ======================
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_ping_server():
    server = HTTPServer(("0.0.0.0", 10000), PingHandler)
    server.serve_forever()

threading.Thread(target=run_ping_server, daemon=True).start()

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
