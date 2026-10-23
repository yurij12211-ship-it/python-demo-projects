"""
Telegram-бот запису клієнтів (демо для барбершопу / салону / студії).

Клієнт: обирає послугу → дату → вільний час → лишає ім'я і телефон.
Адміністратор: отримує заявку в особисті повідомлення, /today показує записи на сьогодні.
Зайняті слоти зберігаються в SQLite, двічі записати один час неможливо.

Запуск:  pip install aiogram==3.*
         BOT_TOKEN=... ADMIN_ID=... python bot.py
"""
import asyncio
import os
import sqlite3
from datetime import date, timedelta

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, KeyboardButton, Message,
                           ReplyKeyboardMarkup, ReplyKeyboardRemove)

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
SERVICES = {"cut": ("Стрижка", 400), "beard": ("Борода", 250), "combo": ("Стрижка + борода", 600)}
SLOTS = ["10:00", "11:00", "12:00", "14:00", "15:00", "16:00", "17:00", "18:00"]

db = sqlite3.connect("bookings.db")
db.execute("""CREATE TABLE IF NOT EXISTS bookings(
    day TEXT, slot TEXT, service TEXT, name TEXT, phone TEXT, user_id INTEGER,
    PRIMARY KEY(day, slot))""")
router = Router()


class Booking(StatesGroup):
    name = State()
    phone = State()


def kb(rows):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=d)] for t, d in rows])


def free_slots(day: str) -> list[str]:
    taken = {r[0] for r in db.execute("SELECT slot FROM bookings WHERE day=?", (day,))}
    return [s for s in SLOTS if s not in taken]


@router.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("Це демо-бот запису для барбершопу чи салону. Спробуйте записатися: обирайте послугу, дату і час.\n\nОберіть послугу:",
                   reply_markup=kb([(f"{n} · {p} грн", f"svc:{k}") for k, (n, p) in SERVICES.items()]))


@router.callback_query(F.data.startswith("svc:"))
async def pick_day(c: CallbackQuery, state: FSMContext):
    await state.update_data(service=c.data[4:])
    days = [date.today() + timedelta(days=i) for i in range(5)]
    await c.message.edit_text("Оберіть дату:", reply_markup=kb([(d.strftime("%d.%m (%a)"), f"day:{d}") for d in days]))


@router.callback_query(F.data.startswith("day:"))
async def pick_slot(c: CallbackQuery, state: FSMContext):
    day = c.data[4:]
    slots = free_slots(day)
    if not slots:
        return await c.answer("На цей день вільних місць немає", show_alert=True)
    await state.update_data(day=day)
    await c.message.edit_text("Вільний час:", reply_markup=kb([(s, f"slot:{s}") for s in slots]))


@router.callback_query(F.data.startswith("slot:"))
async def ask_name(c: CallbackQuery, state: FSMContext):
    await state.update_data(slot=c.data[5:])
    await state.set_state(Booking.name)
    await c.message.edit_text("Як до вас звертатися?")


@router.message(Booking.name)
async def ask_phone(m: Message, state: FSMContext):
    await state.update_data(name=m.text.strip()[:50])
    await state.set_state(Booking.phone)
    await m.answer("Надішліть номер телефону:", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Надіслати номер", request_contact=True)]], resize_keyboard=True))


@router.message(Booking.phone)
async def confirm(m: Message, state: FSMContext, bot: Bot):
    phone = m.contact.phone_number if m.contact else (m.text or "").strip()
    d = await state.get_data()
    name, price = SERVICES[d["service"]]
    try:
        with db:
            db.execute("INSERT INTO bookings VALUES(?,?,?,?,?,?)",
                       (d["day"], d["slot"], name, d["name"], phone, m.from_user.id))
    except sqlite3.IntegrityError:
        await state.clear()
        return await m.answer("Цей час щойно зайняли, оберіть інший: /start", reply_markup=ReplyKeyboardRemove())
    await state.clear()
    await m.answer(f"✅ Ви записані!\n{name}, {d['day']} о {d['slot']}\nДо зустрічі!", reply_markup=ReplyKeyboardRemove())
    if ADMIN_ID:
        await bot.send_message(ADMIN_ID, f"🆕 Новий запис\n{name} · {price} грн\n{d['day']} {d['slot']}\n{d['name']}, {phone}")


@router.message(Command("today"), F.from_user.id == ADMIN_ID)
async def today(m: Message):
    rows = db.execute("SELECT slot, service, name, phone FROM bookings WHERE day=? ORDER BY slot",
                      (str(date.today()),)).fetchall()
    await m.answer("\n".join(f"{s} · {sv} · {n} · {p}" for s, sv, n, p in rows) or "Сьогодні записів немає")


async def main():
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(Bot(BOT_TOKEN))


if __name__ == "__main__":
    asyncio.run(main())
