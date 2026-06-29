import asyncio
import csv
import os

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import ADMIN_ID, BOT_TOKEN

USERS_FILE = "users.csv"

router = Router()


# ── FSM ───────────────────────────────────────────────────────────────────────
class BroadcastState(StatesGroup):
    waiting_for_content = State()


# ── CSV-утилиты ───────────────────────────────────────────────────────────────
def load_users() -> list[int]:
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, newline="", encoding="utf-8") as f:
        return [int(row[0]) for row in csv.reader(f) if row]


def save_user(user_id: int) -> bool:
    if user_id in load_users():
        return False
    with open(USERS_FILE, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([user_id])
    return True


# ── Клавиатуры ────────────────────────────────────────────────────────────────
def admin_keyboard() -> InlineKeyboardMarkup:
    """Главная панель администратора."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
            InlineKeyboardButton(text="📨 Рассылка",   callback_data="broadcast"),
        ],
        [
            InlineKeyboardButton(text="🔄 Обновить",   callback_data="refresh"),
        ],
        [
            InlineKeyboardButton(text="◀️ Назад",      callback_data="back"),
            InlineKeyboardButton(text="❌ Закрыть",     callback_data="cancel_panel"),
        ],
    ])


def broadcast_keyboard() -> InlineKeyboardMarkup:
    """Кнопки во время ожидания контента рассылки."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="◀️ Назад",  callback_data="back"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_broadcast"),
        ],
    ])


# ── Панель ────────────────────────────────────────────────────────────────────
async def show_admin_panel(message: Message) -> None:
    count = len(load_users())
    await message.answer(
        f"🔧 <b>Панель администратора</b>\n\n"
        f"👥 Пользователей в базе: <b>{count}</b>",
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# КОМАНДЫ
# ─────────────────────────────────────────────────────────────────────────────

@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    if message.from_user is None:
        return
    is_new = save_user(message.from_user.id)
    text   = "Добро пожаловать! Вы зарегистрированы. ✅" if is_new else "С возвращением! 👋"
    await message.answer(text)


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if message.from_user is None or message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        return
    await show_admin_panel(message)


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    if message.from_user is None or message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        return
    count = len(load_users())
    await message.answer(f"👥 Пользователей в базе: <b>{count}</b>", parse_mode="HTML")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext) -> None:
    if message.from_user is None or message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        return
    await message.answer(
        "📤 Отправьте контент для рассылки:\n"
        "• текст\n• фото (с подписью или без)\n• видео (с подписью или без)",
        reply_markup=broadcast_keyboard(),
    )
    await state.set_state(BroadcastState.waiting_for_content)


@router.message(Command("cancel"), BroadcastState.waiting_for_content)
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Рассылка отменена.")
    await show_admin_panel(message)


# ─────────────────────────────────────────────────────────────────────────────
# CALLBACK-КНОПКИ
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "stats")
async def cb_stats(call: CallbackQuery) -> None:
    if call.from_user.id != ADMIN_ID:
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    if not isinstance(call.message, Message):
        return
    count = len(load_users())
    await call.answer(f"👥 Пользователей: {count}")
    await call.message.edit_text(
        f"🔧 <b>Панель администратора</b>\n\n"
        f"👥 Пользователей в базе: <b>{count}</b>",
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )


@router.callback_query(F.data == "refresh")
async def cb_refresh(call: CallbackQuery) -> None:
    if call.from_user.id != ADMIN_ID:
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    if not isinstance(call.message, Message):
        return
    count = len(load_users())
    await call.answer("Обновлено ✅")
    await call.message.edit_text(
        f"🔧 <b>Панель администратора</b>\n\n"
        f"👥 Пользователей в базе: <b>{count}</b>",
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )


@router.callback_query(F.data == "broadcast")
async def cb_broadcast(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user.id != ADMIN_ID:
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    if not isinstance(call.message, Message):
        return
    await call.answer()
    await call.message.edit_text(
        "📤 Отправьте контент для рассылки:\n"
        "• текст\n• фото (с подписью или без)\n• видео (с подписью или без)",
        reply_markup=broadcast_keyboard(),
    )
    await state.set_state(BroadcastState.waiting_for_content)


# ── Кнопка «Назад» — возвращает в главную панель ─────────────────────────────
@router.callback_query(F.data == "back")
async def cb_back(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user.id != ADMIN_ID:
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    if not isinstance(call.message, Message):
        return
    await state.clear()   # сбрасываем FSM если был активен
    await call.answer()
    count = len(load_users())
    await call.message.edit_text(
        f"🔧 <b>Панель администратора</b>\n\n"
        f"👥 Пользователей в базе: <b>{count}</b>",
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )


# ── Кнопка «Закрыть» — удаляет сообщение с панелью ──────────────────────────
@router.callback_query(F.data == "cancel_panel")
async def cb_cancel_panel(call: CallbackQuery) -> None:
    if call.from_user.id != ADMIN_ID:
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    if not isinstance(call.message, Message):
        return
    await call.answer("Панель закрыта.")
    await call.message.delete()


# ── Кнопка «Отмена» в режиме рассылки ────────────────────────────────────────
@router.callback_query(F.data == "cancel_broadcast")
async def cb_cancel_broadcast(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user.id != ADMIN_ID:
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    if not isinstance(call.message, Message):
        return
    await state.clear()
    await call.answer("Рассылка отменена.")
    count = len(load_users())
    await call.message.edit_text(
        f"🔧 <b>Панель администратора</b>\n\n"
        f"👥 Пользователей в базе: <b>{count}</b>",
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# FSM: получаем контент и рассылаем
# ─────────────────────────────────────────────────────────────────────────────

@router.message(BroadcastState.waiting_for_content)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot) -> None:
    if message.photo:
        content_type = "photo"
        file_id      = message.photo[-1].file_id
        caption      = message.caption or ""
    elif message.video:
        content_type = "video"
        file_id      = message.video.file_id
        caption      = message.caption or ""
    elif message.text:
        content_type = "text"
        file_id      = ""
        caption      = message.text
    else:
        await message.answer(
            "⚠️ Поддерживаются только текст, фото и видео. Попробуйте ещё раз:",
            reply_markup=broadcast_keyboard(),
        )
        return

    await state.clear()

    users = load_users()
    if not users:
        await message.answer("База пользователей пуста.")
        return

    status_msg = await message.answer(f"⏳ Отправляю {len(users)} пользователям...")

    sent, failed = 0, 0
    for user_id in users:
        try:
            if content_type == "photo":
                await bot.send_photo(user_id, photo=file_id, caption=caption)
            elif content_type == "video":
                await bot.send_video(user_id, video=file_id, caption=caption)
            else:
                await bot.send_message(user_id, caption)
            sent += 1
        except Exception as e:
            print(f"[broadcast] Ошибка для {user_id}: {e}")
            failed += 1

    await status_msg.edit_text(
        f"📨 <b>Рассылка завершена</b>\n\n"
        f"✅ Отправлено: <b>{sent}</b>\n"
        f"❌ Ошибок:     <b>{failed}</b>",
        parse_mode="HTML",
    )
    await show_admin_panel(message)


# ── Запуск ────────────────────────────────────────────────────────────────────
async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    dp  = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    print("Бот запущен. Нажмите Ctrl+C для остановки.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())