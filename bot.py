import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# ============ НАСТРОЙКИ ============
TOKEN = os.getenv("TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",")]
ADMIN_CONTACT = "@pa1_1_1a"

# ============ ДАННЫЕ ============
players = {}

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ============ СОСТОЯНИЯ ============
class Reg(StatesGroup):
    car = State()
    plate = State()
    team = State()

# ============ МЕНЮ ============
def user_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Регистрация"), KeyboardButton(text="💸 Я оплатил")],
            [KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True
    )

def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚙️ Админ-панель")],
            [KeyboardButton(text="📝 Регистрация"), KeyboardButton(text="💸 Я оплатил")],
            [KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True
    )

MENU_BUTTONS = ["📝 Регистрация", "💸 Я оплатил", "ℹ️ Помощь", "⚙️ Админ-панель"]

# ============ РЕГИСТРАЦИЯ ============
@dp.message(Command("reg"))
async def reg_start(message: Message, state: FSMContext):
    if message.from_user.id in players:
        is_admin = message.from_user.id in ADMIN_IDS
        menu = admin_menu() if is_admin else user_menu()
        await message.answer("Ты уже зарегистрирован. Если ошибся — напиши /unreg", reply_markup=menu)
        return
    await message.answer("🚗 Введи марку авто:")
    await state.set_state(Reg.car)

@dp.message(Reg.car)
async def reg_car(message: Message, state: FSMContext):
    if message.text in MENU_BUTTONS:
        await message.answer("Пожалуйста, введи марку авто текстом:")
        return
    await state.update_data(car=message.text)
    await message.answer("🔢 Введи номер авто:")
    await state.set_state(Reg.plate)

@dp.message(Reg.plate)
async def reg_plate(message: Message, state: FSMContext):
    if message.text in MENU_BUTTONS:
        await message.answer("Пожалуйста, введи номер авто текстом:")
        return
    await state.update_data(plate=message.text)
    await message.answer("👥 Введи название команды:")
    await state.set_state(Reg.team)

@dp.message(Reg.team)
async def reg_team(message: Message, state: FSMContext):
    if message.text in MENU_BUTTONS:
        await message.answer("Пожалуйста, введи название команды текстом:")
        return
    data = await state.update_data(team=message.text)
    user = message.from_user
    players[user.id] = {
        "id": user.id,
        "name": user.full_name,
        "username": f"@{user.username}" if user.username else "нет ника",
        "car": data["car"],
        "plate": data["plate"],
        "team": data["team"],
        "confirmed": False,
    }
    await state.clear()
    is_admin = user.id in ADMIN_IDS
    menu = admin_menu() if is_admin else user_menu()
    await message.answer(
        f"✅ Регистрация на квест завершена!\n\n"
        f"🚗 {data['car']} | {data['plate']}\n"
        f"👥 {data['team']}\n\n"
        f"💰 Взнос: 500₽\n"
        f"Оплата наличными или переводом организатору.\n"
        f"После оплаты нажми /pay — админ отметит тебя.\n\n"
        f"⏳ Ждите подтверждения.\n"
        f"Если у вас возникли вопросы — свяжитесь с админом: {ADMIN_CONTACT}",
        reply_markup=menu
    )

@dp.message(Command("unreg"))
async def unreg(message: Message):
    uid = message.from_user.id
    is_admin = uid in ADMIN_IDS
    menu = admin_menu() if is_admin else user_menu()
    if uid in players:
        del players[uid]
        await message.answer("🗑 Регистрация удалена. Можешь зарегистрироваться заново: /reg", reply_markup=menu)
    else:
        await message.answer("Ты и так не зарегистрирован.", reply_markup=menu)

@dp.message(Command("pay"))
async def pay(message: Message):
    is_admin = message.from_user.id in ADMIN_IDS
    menu = admin_menu() if is_admin else user_menu()
    if message.from_user.id not in players:
        await message.answer("Сначала зарегистрируйся: /reg", reply_markup=menu)
        return
    await message.answer(
        "💸 Принято! Жди, пока админ отметит тебя в панели.",
        reply_markup=menu
    )

# ============ АДМИН-ПАНЕЛЬ ============
@dp.message(Command("panel"))
async def panel(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Эта команда только для админа.", reply_markup=user_menu())
        return
    buttons = [
        [InlineKeyboardButton(text="✅ Подтвердить игрока", callback_data="show_confirm")],
        [InlineKeyboardButton(text="❌ Отменить подтверждение", callback_data="show_unconfirm")],
        [InlineKeyboardButton(text="🗑 Удалить игрока", callback_data="show_delete")],
        [InlineKeyboardButton(text="📋 Полный список", callback_data="show_list")],
        [InlineKeyboardButton(text="🗑 Очистить список", callback_data="clear_list")],
    ]
    await message.answer("⚙️ Админ-панель:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data == "show_list")
async def cb_list(callback: CallbackQuery):
    if not players:
        await callback.message.edit_text("Список пуст.")
        return
    text = "📋 <b>Все зарегистрированные:</b>\n\n"
    for p in players.values():
        status = "✅" if p.get("confirmed") else "❌"
        text += f"{status} <b>{p['team']}</b>\n"
        text += f"🚗 {p['car']} | {p['plate']}\n"
        text += f"👤 {p['username']}\n\n"
    await callback.message.edit_text(text, parse_mode="HTML")

# ============ ПОДТВЕРЖДЕНИЕ ============
@dp.callback_query(F.data == "show_confirm")
async def cb_show_confirm(callback: CallbackQuery):
    buttons = []
    for uid, p in players.items():
        if not p.get("confirmed"):
            buttons.append([InlineKeyboardButton(
                text=f"{p['team']} ({p['plate']})",
                callback_data=f"confirm_{uid}"
            )])
    if not buttons:
        await callback.message.edit_text("Все игроки уже подтверждены ✅")
        return
    await callback.message.edit_text(
        "Кто оплатил? Жми на игрока:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@dp.callback_query(F.data.startswith("confirm_"))
async def cb_confirm(callback: CallbackQuery):
    uid = int(callback.data.split("_")[1])
    if uid in players:
        players[uid]["confirmed"] = True
        name = players[uid]["name"]
        await callback.answer(f"✅ {name} подтверждён")
        try:
            await bot.send_message(
                uid,
                "✅ <b>Оплата подтверждена!</b>\n"
                "Ты отмечен как участник квеста. Жди деталей! 🎭",
                parse_mode="HTML"
            )
        except Exception:
            pass
    await cb_show_confirm(callback)

# ============ ОТМЕНА ПОДТВЕРЖДЕНИЯ ============
@dp.callback_query(F.data == "show_unconfirm")
async def cb_show_unconfirm(callback: CallbackQuery):
    buttons = []
    for uid, p in players.items():
        if p.get("confirmed"):
            buttons.append([InlineKeyboardButton(
                text=f"{p['team']} ({p['plate']})",
                callback_data=f"unconfirm_{uid}"
            )])
    if not buttons:
        await callback.message.edit_text("Нет подтверждённых игроков.")
        return
    await callback.message.edit_text(
        "Кого отменить? Жми на игрока:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@dp.callback_query(F.data.startswith("unconfirm_"))
async def cb_unconfirm(callback: CallbackQuery):
    uid = int(callback.data.split("_")[1])
    if uid in players:
        players[uid]["confirmed"] = False
        name = players[uid]["name"]
        await callback.answer(f"❌ {name} снят с подтверждения")
    await cb_show_unconfirm(callback)

# ============ УДАЛЕНИЕ ИГРОКА ============
@dp.callback_query(F.data == "show_delete")
async def cb_show_delete(callback: CallbackQuery):
    buttons = []
    for uid, p in players.items():
        buttons.append([InlineKeyboardButton(
            text=f"{p['team']} ({p['plate']})",
            callback_data=f"delete_{uid}"
        )])
    if not buttons:
        await callback.message.edit_text("Список пуст.")
        return
    await callback.message.edit_text(
        "Кого удалить? Жми на игрока:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@dp.callback_query(F.data.startswith("delete_"))
async def cb_delete(callback: CallbackQuery):
    uid = int(callback.data.split("_")[1])
    if uid in players:
        name = players[uid]["name"]
        del players[uid]
        await callback.answer(f"🗑 {name} удалён")
    await cb_show_delete(callback)

# ============ ОЧИСТКА ============
@dp.callback_query(F.data == "clear_list")
async def cb_clear(callback: CallbackQuery):
    count = len(players)
    players.clear()
    await callback.message.edit_text(f"🗑 Список очищен. Было игроков: {count}. Готово к новому квесту!")

@dp.message(Command("newgame"))
async def newgame(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    count = len(players)
    players.clear()
    await message.answer(f"🗑 Список очищен. Было игроков: {count}. Готово к новому квесту!")

# ============ КНОПКИ МЕНЮ ============
@dp.message(F.text == "📝 Регистрация")
async def btn_reg(message: Message, state: FSMContext):
    await reg_start(message, state)

@dp.message(F.text == "💸 Я оплатил")
async def btn_pay(message: Message):
    await pay(message)

@dp.message(F.text == "⚙️ Админ-панель")
async def btn_panel(message: Message):
    await panel(message)

@dp.message(F.text == "ℹ️ Помощь")
async def btn_help(message: Message):
    await message.answer(
        "📖 <b>Что умеет бот:</b>\n\n"
        "📝 Регистрация — записаться на квест\n"
        "💸 Я оплатил — сообщить об оплате\n"
        "⚙️ Админ-панель — для организатора\n\n"
        "<b>Команды вручную:</b>\n"
        "/reg — зарегистрироваться\n"
        "/unreg — отменить регистрацию\n"
        "/pay — сообщить об оплате\n"
        "/panel — админ-панель (только для админа)",
        parse_mode="HTML"
    )

# ============ СТАРТ ============
@dp.message(CommandStart())
async def start_handler(message: Message):
    is_admin = message.from_user.id in ADMIN_IDS
    menu = admin_menu() if is_admin else user_menu()
    await message.answer(
        f"Привет, {message.from_user.full_name}! 👋\n\n"
        f"Жми на кнопки внизу экрана 👇",
        reply_markup=menu
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
