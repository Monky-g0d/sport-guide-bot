from __future__ import annotations
import asyncio
import os
import json
from dataclasses import dataclass
from typing import Dict, Tuple
from aiogram.client.default import DefaultBotProperties
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart

from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = "@Lirkach0k"

# Проверка подписки
async def check_subscription(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False

def subscription_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подписаться", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
        [InlineKeyboardButton(text="🔄 Проверить подписку", callback_data="check_sub")]
    ])


USERS_FILE = "users.json"

def load_users() -> set[int]:
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_users(users: set[int]):
    with open(USERS_FILE, "w") as f:
        json.dump(list(users), f)

# Загружаем пользователей при старте
USERS = load_users()

# --- Данные программ ---
@dataclass(frozen=True)
class Exercise:
    name: str
    sets: int
    reps: str
    note: str = ""

@dataclass(frozen=True)
class WorkoutDay:
    title: str
    exercises: Tuple[Exercise, ...]

@dataclass(frozen=True)
class Program:
    key: str
    title: str
    description: str
    split: Tuple[WorkoutDay, ...]
    weekly_days: int

FULL_BODY_3 = Program(
    key="full_body_3",
    title="Full Body (3 дня)",
    description="Целиком тело 3 раза в неделю. Фокус на базу + аксессуары.",
    weekly_days=3,
    split=(
        WorkoutDay(
            title="День A (Сила)",
            exercises=(
                Exercise("Жим ногами", 5, "5"),
                Exercise("Жим штанги лёжа", 5, "5"),
                Exercise("Тяга верхнего блока", 4, "6-8"),
                Exercise("Отведение гантелей", 3, "8-10"),
                Exercise("Подъем штанги на бицепс", 3, "12-15"),
            ),
        ),
        WorkoutDay(
            title="День B (Гипертрофия)",
            exercises=(
                Exercise("Становая тяга", 3, "3-5"),
                Exercise("Жим стоя", 4, "6-8"),
                Exercise("Подтягивания", 4, "8-10"),
                Exercise("Выпады", 3, "10-12"),
                Exercise("Подъём гантелей на бицепс", 3, "10-12"),
            ),
        ),
        WorkoutDay(
            title="День C (Общий)",
            exercises=(
                Exercise("Фронтальные приседы", 4, "5-6"),
                Exercise("Жим гантелей на наклонной", 4, "8-10"),
                Exercise("Тяга горизонтального блока", 4, "8-10"),
                Exercise("Разведения на дельты", 3, "12-15"),
                Exercise("Планка", 3, "40-60 сек"),
            ),
        ),
    ),
)

PROGRAMS: Dict[str, Program] = {FULL_BODY_3.key: FULL_BODY_3}

def render_day(day: WorkoutDay) -> str:
    lines = [f"📌 <b>{day.title}</b>"]
    for idx, ex in enumerate(day.exercises, start=1):
        note = f" — {ex.note}" if ex.note else ""
        lines.append(f"{idx}. {ex.name}: {ex.sets}×{ex.reps}{note}")
    return "\n".join(lines)

def render_program(program: Program) -> str:
    header = f"🏋️‍♂️ <b>{program.title}</b>\n{program.description}\nДней в неделю: <b>{program.weekly_days}</b>\n— — —"
    days = "\n\n".join(render_day(d) for d in program.split)
    return f"{header}\n\n{days}"

# --- Клавиатуры ---
def main_menu_kb() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="📚 Программы", callback_data="programs")
    kb.button(text="📘 Гайды", callback_data="guides_menu")
    kb.button(text="ℹ️ Советы", callback_data="tips")
    kb.adjust(1)
    return kb

def programs_kb() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    for p in PROGRAMS.values():
        kb.button(text=p.title, callback_data=f"prog:{p.key}")
    kb.button(text="⬅️ Назад", callback_data="back:main")
    kb.adjust(1)
    return kb

def program_nav_kb(pkey: str) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="📄 Вся программа", callback_data=f"prog_show:{pkey}")
    prog = PROGRAMS[pkey]
    for i, day in enumerate(prog.split):
        kb.button(text=f"🗓️ День {i+1}: {day.title}", callback_data=f"day:{pkey}:{i}")
    kb.button(text="⬅️ Назад", callback_data="programs")
    kb.adjust(1)
    return kb

# --- Обработчики ---
async def cmd_start(message: Message, bot: Bot):
    user_id = message.from_user.id

    # Добавляем пользователя, если его нет
    if user_id not in USERS:
        USERS.add(user_id)
        save_users(USERS)
        print(f"Новый пользователь: {message.from_user.username or user_id} (всего {len(USERS)})")
    if await check_subscription(bot, message.from_user.id):
        await message.answer(
            "Привет! Выбери программу или гайд 👇",
            reply_markup=main_menu_kb().as_markup()
        )
    else:
        await message.answer(
            "❗ Для доступа к боту нужно подписаться на канал:",
            reply_markup=subscription_kb()
        )

async def cb_check_sub(call: CallbackQuery, bot: Bot):
    if await check_subscription(bot, call.from_user.id):
        await call.message.edit_text(
            "✅ Подписка найдена! Теперь выбирай:",
            reply_markup=main_menu_kb().as_markup()
        )
    else:
        await call.answer("Ты всё ещё не подписан!", show_alert=True)


from aiogram.filters import Command

async def cmd_stats(message: Message):
    await message.answer(f"📊 Всего пользователей: <b>{len(USERS)}</b>")


async def cb_programs(call: CallbackQuery):
    await call.message.edit_text("Выбери программу:", reply_markup=programs_kb().as_markup())
    await call.answer()

async def cb_back_main(call: CallbackQuery):
    await call.message.edit_text("Главное меню:", reply_markup=main_menu_kb().as_markup())
    await call.answer()

async def cb_program_pick(call: CallbackQuery):
    pkey = call.data.split(":", 1)[1]
    prog = PROGRAMS[pkey]
    await call.message.edit_text(
        f"{prog.title}\n{prog.description}\nДней/нед: {prog.weekly_days}",
        reply_markup=program_nav_kb(pkey).as_markup(),
    )
    await call.answer()

async def cb_program_show(call: CallbackQuery):
    pkey = call.data.split(":", 1)[1]
    await call.message.edit_text(render_program(PROGRAMS[pkey]), parse_mode="HTML",
                                 reply_markup=program_nav_kb(pkey).as_markup())
    await call.answer()

async def cb_day_show(call: CallbackQuery):
    _, pkey, idx = call.data.split(":", 2)
    prog = PROGRAMS[pkey]
    day = prog.split[int(idx)]
    await call.message.edit_text(render_day(day), parse_mode="HTML",
                                 reply_markup=program_nav_kb(pkey).as_markup())
    await call.answer()

# --- Раздел "Гайды" ---
PDF_MASS_PATH = "mass_guild.pdf"
PDF_RECOMP_PATH = "recomp_guide.pdf"
PDF_SPORTPIT_PATH = "sportpit.pdf"
VIDEO_WARMUP_PATH = "Obshesustavnaya_razminka.mp4"

def guides_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📘 Массоноборный гайд", callback_data="guide_mass")],
        [InlineKeyboardButton(text="⚖️ Гайд на рекомпозицию", callback_data="guide_recomp")],
        [InlineKeyboardButton(text="🍽️ Спортпит", callback_data="guide_sportpit")],
        [InlineKeyboardButton(text="🫀 Гайд по ЖКТ", callback_data="guide_gastro")],
        [InlineKeyboardButton(text="🎥 Разминка (видео)", callback_data="guide_warmup_video")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back:main")]
    ])
    return kb

async def cb_guides_menu(call: CallbackQuery):
    await call.message.edit_text("📚 Выбери нужный гайд:", reply_markup=guides_kb())
    await call.answer()

async def cb_guide_mass(call: CallbackQuery):
    if os.path.exists(PDF_MASS_PATH):
        await call.message.answer_document(FSInputFile(PDF_MASS_PATH))
    else:
        await call.message.answer("В разработке 😢")
    await call.answer()

async def cb_guide_recomp(call: CallbackQuery):
    if os.path.exists(PDF_RECOMP_PATH):
        await call.message.answer_document(FSInputFile(PDF_RECOMP_PATH))
    else:
        await call.message.answer("В разработке 😢")
    await call.answer()

async def cb_guide_sportpit(call: CallbackQuery):
    if os.path.exists(PDF_SPORTPIT_PATH):
        await call.message.answer_document(FSInputFile(PDF_SPORTPIT_PATH))
    else:
        await call.message.answer("В разработке 😢")
    await call.answer()

DOCX_GASTRO_PATH = "Gayd_po_ZHKT.docx"

async def cb_guide_gastro(call: CallbackQuery):
    if os.path.exists(DOCX_GASTRO_PATH):
        await call.message.answer_document(FSInputFile(DOCX_GASTRO_PATH))
    else:
        await call.message.answer("В разработке😢")
    await call.answer()


async def cb_guide_warmup_video(call: CallbackQuery):
    if os.path.exists(VIDEO_WARMUP_PATH):
        await call.message.answer_video(FSInputFile(VIDEO_WARMUP_PATH), caption="🎥 Общесуставная разминка")
    else:
        await call.message.answer("Видео не найдено😢")
    await call.answer()

# --- Регистрация ---
def setup_router(dp: Dispatcher):
    dp.message.register(cmd_start, CommandStart())
    dp.callback_query.register(cb_check_sub, F.data == "check_sub")
    dp.callback_query.register(cb_programs, F.data == "programs")
    dp.message.register(cmd_stats, Command("stats"))
    dp.callback_query.register(cb_back_main, F.data == "back:main")
    dp.callback_query.register(cb_program_pick, F.data.startswith("prog:"))
    dp.callback_query.register(cb_program_show, F.data.startswith("prog_show:"))
    dp.callback_query.register(cb_day_show, F.data.startswith("day:"))
    dp.callback_query.register(cb_guides_menu, F.data == "guides_menu")
    dp.callback_query.register(cb_guide_mass, F.data == "guide_mass")
    dp.callback_query.register(cb_guide_recomp, F.data == "guide_recomp")
    dp.callback_query.register(cb_guide_sportpit, F.data == "guide_sportpit")
    dp.callback_query.register(cb_guide_gastro, F.data == "guide_gastro")
    dp.callback_query.register(cb_guide_warmup_video, F.data == "guide_warmup_video")

# --- Запуск ---
async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не найден")
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    setup_router(dp)
    print("Bot started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped")