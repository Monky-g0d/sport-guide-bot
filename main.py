from __future__ import annotations
import asyncio
import os
from dataclasses import dataclass
from typing import Dict, Tuple

from aiogram.client.default import DefaultBotProperties
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# --- Настройки окружения ---
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = "@Lirkach0k"

# --- Инициализация базы ---
def init_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_user(user_id: int, username: str | None):
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    c = conn.cursor()
    c.execute("""
        INSERT INTO users (user_id, username)
        VALUES (%s, %s)
        ON CONFLICT (user_id) DO NOTHING
    """, (user_id, username))
    conn.commit()
    conn.close()

def count_users() -> int:
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total = c.fetchone()["count"]
    conn.close()
    return total

# --- Проверка подписки ---
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

# --- Клавиатуры ---
def main_menu_kb() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="💪 Индивидуальное ведение", callback_data="personal")
    kb.button(text="📚 Гайды", callback_data="guides_menu")
    kb.button(text="ℹ️ Советы", callback_data="tips")
    kb.adjust(1)
    return kb


# --- Обработчики команд ---
async def cmd_start(message: Message, bot: Bot):
    user_id = message.from_user.id
    username = message.from_user.username
    add_user(user_id, username)

    if await check_subscription(bot, message.from_user.id):
        await message.answer("Привет! Выбери программу или гайд 👇", reply_markup=main_menu_kb().as_markup())
    else:
        await message.answer("❗ Для доступа к боту нужно подписаться на канал:", reply_markup=subscription_kb())

async def cb_check_sub(call: CallbackQuery, bot: Bot):
    if await check_subscription(bot, call.from_user.id):
        await call.message.edit_text("✅ Подписка найдена! Теперь выбирай:", reply_markup=main_menu_kb().as_markup())
    else:
        await call.answer("Ты всё ещё не подписан!", show_alert=True)

async def cmd_stats(message: Message):
    total = count_users()
    await message.answer(f"📊 Всего пользователей: <b>{total}</b>")


async def cb_back_main(call: CallbackQuery):
    await call.message.edit_text("Главное меню:", reply_markup=main_menu_kb().as_markup())
    await call.answer()


# --- Раздел "Индивидуальное ведение" ---
def personal_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back:main")]
    ])
    return kb

async def cb_personal(call: CallbackQuery):
    await call.message.edit_text(
        "💪 Индивидуальное ведение\n\n"
        "Хочешь персональные тренировки, питание и сопровождение?\n"
        "Пиши мне в личку 👇\n\n"
        "👉 <a href='https://t.me/R1t3ziz'>@R1t3ziz</a>",
        parse_mode="HTML",
        reply_markup=personal_kb()
    )
    await call.answer()


# --- Раздел "Гайды" ---
PDF_MASS_PATH = "mass_guild.pdf"
PDF_RECOMP_PATH = "recomp_guide.pdf"
PDF_SPORTPIT_PATH = "sportpit.pdf"
DOCX_GASTRO_PATH = "Gayd_po_ZHKT.docx"
VIDEO_WARMUP_PATH = "Obshesustavnaya_razminka.mp4"

def guides_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📘 Массоноборный гайд", callback_data="guide_mass")],
        [InlineKeyboardButton(text="⚖️ Гайд на рекомпозицию", callback_data="guide_recomp")],
        [InlineKeyboardButton(text="🍽️ Спортпит", callback_data="guide_sportpit")],
        [InlineKeyboardButton(text="🫀 Гайд по ЖКТ", callback_data="guide_gastro")],
        [InlineKeyboardButton(text="🎥 Разминка (видео)", callback_data="guide_warmup_video")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back:main")]
    ])

async def cb_guides_menu(call: CallbackQuery):
    await call.message.edit_text("📚 Выбери нужный гайд:", reply_markup=guides_kb())
    await call.answer()

async def send_file_or_text(call: CallbackQuery, path: str, file_type: str, caption: str = None):
    if os.path.exists(path):
        if file_type == "pdf" or file_type == "docx":
            await call.message.answer_document(FSInputFile(path), caption=caption)
        elif file_type == "video":
            await call.message.answer_video(FSInputFile(path), caption=caption)
    else:
        await call.message.answer("❗ Файл ещё в разработке 😢")
    await call.answer()

async def cb_guide_mass(call: CallbackQuery): await send_file_or_text(call, PDF_MASS_PATH, "pdf")
async def cb_guide_recomp(call: CallbackQuery): await send_file_or_text(call, PDF_RECOMP_PATH, "pdf")
async def cb_guide_sportpit(call: CallbackQuery): await send_file_or_text(call, PDF_SPORTPIT_PATH, "pdf")
async def cb_guide_gastro(call: CallbackQuery): await send_file_or_text(call, DOCX_GASTRO_PATH, "docx")
async def cb_guide_warmup_video(call: CallbackQuery): await send_file_or_text(call, VIDEO_WARMUP_PATH, "video")

# --- Регистрация ---
def setup_router(dp: Dispatcher):
    dp.message.register(cmd_start, CommandStart())
    dp.callback_query.register(cb_check_sub, F.data == "check_sub")
    dp.message.register(cmd_stats, Command("stats"))
    dp.callback_query.register(cb_back_main, F.data == "back:main")
    dp.callback_query.register(cb_guides_menu, F.data == "guides_menu")
    dp.callback_query.register(cb_guide_mass, F.data == "guide_mass")
    dp.callback_query.register(cb_guide_recomp, F.data == "guide_recomp")
    dp.callback_query.register(cb_guide_sportpit, F.data == "guide_sportpit")
    dp.callback_query.register(cb_guide_gastro, F.data == "guide_gastro")
    dp.callback_query.register(cb_personal, F.data == "personal")
    dp.callback_query.register(cb_guide_warmup_video, F.data == "guide_warmup_video")

# --- Запуск ---
async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не найден в .env")
    init_db()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    setup_router(dp)
    print("✅ Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("❌ Бот остановлен")

