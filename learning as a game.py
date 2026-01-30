# ======================
# IMPORTS
# ======================
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date, time

# ======================
# SETTINGS
# ======================
BOT_TOKEN = "8435851436:AAHENY0AGnFImSORLrFl6Mm_kcS8_oyVMDQ"
SPREADSHEET_NAME = "bot"
ADMIN_IDS = [5010534845]  #Telegram ID

# ======================
# GOOGLE SHEETS
# ======================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "credentials.json", scope
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
# STORAGE & CONSTANTS
# ======================
selected_students = {}



GOTFRIED_ITEMS = {
    3: "📖 Волшебная книга заклинаний",
    5: "🧪 Пояс с зельями",
    6: "🎩 Магическая шляпа",
    8: "🪄 Волшебная палочка",
    10: "💎 Древние магические камни"
}


# ======================
# KEYBOARDS
# ======================
def student_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        KeyboardButton("📊 Профиль"),
        KeyboardButton("🏅 Достижения")
    )
    kb.add(
        KeyboardButton("👥 Прогресс группы")
    )
    return kb


def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        KeyboardButton("👤 Выбрать ученика"),
        KeyboardButton("➕ ДЗ (+20 XP)")
    )
    kb.add(
        KeyboardButton("🏅 Выдать достижение"),
        KeyboardButton("📊 Статистика группы")
    )
    return kb

# ======================
# HELPERS — STUDENTS
# ======================
def get_student_row(telegram_id: int):
    records = sheet.get_all_records()
    for i, row in enumerate(records, start=2):
        if row["telegram_id"] == telegram_id:
            return i, row
    return None, None


def add_student(telegram_id: int, name: str):
    sheet.append_row([
        telegram_id,
        name,
        "A1",
        0,
        0,
        "",
        ""
    ])


def add_xp(telegram_id: int, amount: int):
    row_num, student = get_student_row(telegram_id)
    if not student:
        return False, None

    old_xp = int(student["xp"])
    new_xp = old_xp + amount

    sheet.update_cell(row_num, 4, new_xp)

    leveled_up, new_level = check_level_up(old_xp, new_xp)

    return leveled_up, new_level



def update_streak(telegram_id: int):
    row_num, student = get_student_row(telegram_id)
    if not student:
        return

    today = date.today()
    last_activity = student.get("last_activity")

    if not last_activity:
        new_streak = 1
    else:
        last_date = date.fromisoformat(last_activity)
        if last_date == today:
            return
        elif last_date == today - timedelta(days=1):
            new_streak = int(student["streak"]) + 1
        else:
            new_streak = 1

    sheet.update_cell(row_num, 5, new_streak)
    sheet.update_cell(row_num, 6, today.isoformat())

# ======================
# ACHIEVEMENTS
# ======================
def get_achievements(student):
    raw = student.get("achievements", "")
    if not raw:
        return []
    return raw.split(",")


def add_achievement(telegram_id: int, key: str):
    row_num, student = get_student_row(telegram_id)
    if not student:
        return False

    current = get_achievements(student)
    if key in current:
        return False

    current.append(key)
    sheet.update_cell(row_num, 7, ",".join(current))
    return True

# ======================
# GROUPS
# ======================
def get_group_row(group_name: str):
    records = groups_sheet.get_all_records()
    for i, row in enumerate(records, start=2):
        if row["group"] == group_name:
            return i, row
    return None, None


def add_group_xp(group_name: str, amount: int):
    row_num, group = get_group_row(group_name)
    if not group:
        return

    current_xp = int(group["group_xp"])
    groups_sheet.update_cell(row_num, 2, current_xp + amount)


def get_students_by_group(group_name: str):
    records = sheet.get_all_records()
    return [r for r in records if r["group"] == group_name]


def group_stats(group_name: str, days: int = 7):
    students = get_students_by_group(group_name)
    if not students:
        return None

    today = date.today()
    total = len(students)
    active = 0
    total_streak = 0
    dz_count = 0

    for s in students:
        total_streak += int(s.get("streak", 0))
        last = s.get("last_activity")
        if last:
            last_date = date.fromisoformat(last)
            if (today - last_date).days <= days:
                active += 1
                dz_count += 1

    return {
        "total": total,
        "active": active,
        "dz_count": dz_count,
        "avg_streak": round(total_streak / total, 1)
    }

# ======================
# HANDLERS
# ======================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    telegram_id = message.from_user.id
    name = message.from_user.first_name

    _, student = get_student_row(telegram_id)
    if not student:
        add_student(telegram_id, name)

    welcome_text = (
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

    if telegram_id in ADMIN_IDS:
        await message.answer(welcome_text, reply_markup=admin_menu())
    else:
        await message.answer(welcome_text, reply_markup=student_menu())



def make_progress_bar(current, max_value=100, length=10):
    filled = int((current / max_value) * length)
    filled = min(filled, length)
    return "🟩" * filled + "⬜" * (length - filled)

def get_level(xp: int):
    return xp // 100 + 1


def check_level_up(old_xp: int, new_xp: int):
    old_level = old_xp // 100 + 1
    new_level = new_xp // 100 + 1
    return new_level > old_level, new_level

def give_gotfried_item(telegram_id: int, level: int):
    item = GOTFRIED_ITEMS.get(level)
    if not item:
        return None

    row_num, student = get_student_row(telegram_id)
    if not student:
        return None

    inventory = student.get("achievements", "")
    items = inventory.split(",") if inventory else []

    if item in items:
        return None

    items.append(item)
    sheet.update_cell(row_num, 7, ",".join(items))

    return item




@dp.message_handler(lambda m: m.text == "📊 Профиль")
async def profile(message: types.Message):
    _, student = get_student_row(message.from_user.id)
    if not student:
        return

    xp = int(student["xp"])
    streak = student["streak"]

    level = get_level(xp)
    xp_in_level = xp % 100

    bar = make_progress_bar(xp_in_level, 100)

    await message.answer(
        f"👤 {student['name']}\n"
        f"🏆 Уровень: {level}\n"
        f"XP: {xp_in_level} / 100\n"
        f"{bar}\n"
        f"🔥 Дней без пропусков: {streak}"
    )



@dp.message_handler(lambda m: m.text == "👤 Выбрать ученика")
async def choose_student(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for r in sheet.get_all_records():
        kb.add(KeyboardButton(f"{r['name']} | {r['telegram_id']}"))
    await message.answer("Выбери ученика:", reply_markup=kb)


@dp.message_handler(lambda m: "|" in m.text)
async def select_student(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        _, telegram_id = message.text.split("|")
        selected_students[message.from_user.id] = int(telegram_id.strip())
        await message.answer("Ученик выбран", reply_markup=admin_menu())
    except:
        pass


@dp.message_handler(lambda m: m.text == "➕ ДЗ (+20 XP)")
async def add_homework(message: types.Message):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        return

    student_id = selected_students.get(admin_id)
    if not student_id:
        await message.answer("Сначала выберете ученика")
        return

    leveled_up, new_level = add_xp(student_id, 20)
    update_streak(student_id)

    if leveled_up:
        item = give_gotfried_item(student_id, new_level)

        text = (
            f"🎉 Поздравляем!\n"
            f"Достигнут {new_level} уровень!\n\n"
            f"🧙‍♂️ Готфрид благодарит тебя!"
        )

        if item:
            text += f"\n🎁 Найден предмет: {item}"

        await bot.send_message(student_id, text)

    _, student = get_student_row(student_id)
    add_group_xp(student["group"], 20)

    await message.answer("Учебный шаг зафиксирован. +20 XP")


@dp.message_handler(lambda m: m.text == "🏅 Выдать достижение")
async def give_achievement_menu(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for title in ACHIEVEMENTS.values():
        kb.add(KeyboardButton(title))
    await message.answer("Выберете достижение:", reply_markup=kb)




@dp.message_handler(lambda m: m.text == "🏅 Достижения")
async def student_achievements(message: types.Message):
    _, student = get_student_row(message.from_user.id)
    if not student:
        return

    items_raw = student.get("achievements", "")
    items = items_raw.split(",") if items_raw else []

    text = "🧙‍♂️ Снаряжение Готфрида:\n"

    if not items:
        text += "❌ Пока ничего не найдено"
    else:
        for item in items:
            text += f"• {item}\n"

    await message.answer(text)



@dp.message_handler(lambda m: m.text == "👥 Прогресс группы")
async def group_progress(message: types.Message):
    _, student = get_student_row(message.from_user.id)
    if not student:
        return

    _, group = get_group_row(student["group"])
    xp = int(group["group_xp"])

    filled = min(xp // 50, 10)
    bar = "🟩" * filled + "⬜" * (10 - filled)

    await message.answer(
        f"Группа {student['group']}\n"
        f"{bar}\n"
        f"XP группы: {xp}"
    )


@dp.message_handler(lambda m: m.text == "📊 Статистика группы")
async def admin_stats(message: types.Message):
    admin_id = message.from_user.id
    student_id = selected_students.get(admin_id)
    if not student_id:
        return

    _, student = get_student_row(student_id)
    stats = group_stats(student["group"])

    await message.answer(
        f"Группа {student['group']}\n"
        f"👥 Учеников: {stats['total']}\n"
        f"📘 ДЗ за 7 дней: {stats['dz_count']}\n"
        f"🔥 Средняя серия: {stats['avg_streak']}\n"
        f"⚡ Активных: {stats['active']}"
    )

# ======================
# RUN
# ======================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

print('бот запущен')
