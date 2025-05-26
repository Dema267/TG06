import asyncio
import random
import logging
import sqlite3
from typing import Optional

import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from config import TOKEN

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Кнопки меню
button_registr = KeyboardButton(text="Регистрация в телеграм боте")
button_exchange_rates = KeyboardButton(text="Курс валют")
button_tips = KeyboardButton(text="Советы по экономии")
button_finances = KeyboardButton(text="Личные финансы")
button_report = KeyboardButton(text="Отчет по расходам")

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [button_registr, button_exchange_rates],
        [button_tips, button_finances],
        [button_report],
    ],
    resize_keyboard=True,
)

# База данных
def get_db_connection():
    conn = sqlite3.connect("user.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                telegram_id INTEGER UNIQUE,
                name TEXT,
                category1 TEXT,
                category2 TEXT,
                category3 TEXT,
                expenses1 REAL,
                expenses2 REAL,
                expenses3 REAL
            )
            """
        )

init_db()

# Состояния
class FinancesForm(StatesGroup):
    category1 = State()
    expenses1 = State()
    category2 = State()
    expenses2 = State()
    category3 = State()
    expenses3 = State()

# Хендлеры
@dp.message(CommandStart())
async def send_start(message: Message):
    await message.answer(
        "Привет! Я ваш личный финансовый помощник. Выберите одну из опций в меню:",
        reply_markup=keyboard,
    )

@dp.message(F.text == "Регистрация в телеграм боте")
async def registration(message: Message):
    telegram_id = message.from_user.id
    name = message.from_user.full_name

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()

        if user:
            await message.answer("Вы уже зарегистрированы!")
        else:
            cursor.execute(
                "INSERT INTO users (telegram_id, name) VALUES (?, ?)",
                (telegram_id, name),
            )
            await message.answer("Вы успешно зарегистрированы!")

@dp.message(F.text == "Курс валют")
async def exchange_rates(message: Message):
    url = "https://v6.exchangerate-api.com/v6/7f97251f0ead2e4e4a32bd3e/latest/USD"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    await message.answer("Не удалось получить данные о курсе валют!")
                    return

                data = await response.json()
                usd_to_rub = data["conversion_rates"]["RUB"]
                eur_to_usd = data["conversion_rates"]["EUR"]
                euro_to_rub = eur_to_usd * usd_to_rub

                await message.answer(
                    f"1 USD - {usd_to_rub:.2f} RUB\n"
                    f"1 EUR - {euro_to_rub:.2f} RUB"
                )
    except Exception as e:
        logging.error(f"Error fetching exchange rates: {e}")
        await message.answer("Произошла ошибка при получении курса валют")

@dp.message(F.text == "Советы по экономии")
async def send_tips(message: Message):
    tips = [
        "Совет 1: Ведите бюджет и следите за своими расходами.",
        "Совет 2: Откладывайте часть доходов на сбережения.",
        "Совет 3: Покупайте товары по скидкам и распродажам.",
        "Совет 4: Используйте кэшбэк-сервисы для возврата части средств.",
        "Совет 5: Анализируйте подписки и отказывайтесь от ненужных.",
    ]
    await message.answer(random.choice(tips))

@dp.message(F.text == "Личные финансы")
async def finances_start(message: Message, state: FSMContext):
    await state.set_state(FinancesForm.category1)
    await message.reply("Введите первую категорию расходов:")

@dp.message(FinancesForm.category1)
async def process_category1(message: Message, state: FSMContext):
    await state.update_data(category1=message.text)
    await state.set_state(FinancesForm.expenses1)
    await message.reply("Введите расходы для категории 1:")

@dp.message(FinancesForm.expenses1)
async def process_expenses1(message: Message, state: FSMContext):
    try:
        expenses = float(message.text)
        await state.update_data(expenses1=expenses)
        await state.set_state(FinancesForm.category2)
        await message.reply("Введите вторую категорию расходов:")
    except ValueError:
        await message.reply("Пожалуйста, введите число!")

@dp.message(FinancesForm.category2)
async def process_category2(message: Message, state: FSMContext):
    await state.update_data(category2=message.text)
    await state.set_state(FinancesForm.expenses2)
    await message.reply("Введите расходы для категории 2:")

@dp.message(FinancesForm.expenses2)
async def process_expenses2(message: Message, state: FSMContext):
    try:
        expenses = float(message.text)
        await state.update_data(expenses2=expenses)
        await state.set_state(FinancesForm.category3)
        await message.reply("Введите третью категорию расходов:")
    except ValueError:
        await message.reply("Пожалуйста, введите число!")

@dp.message(FinancesForm.category3)
async def process_category3(message: Message, state: FSMContext):
    await state.update_data(category3=message.text)
    await state.set_state(FinancesForm.expenses3)
    await message.reply("Введите расходы для категории 3:")

@dp.message(FinancesForm.expenses3)
async def process_expenses3(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        telegram_id = message.from_user.id
        expenses = float(message.text)

        with get_db_connection() as conn:
            conn.execute(
                """
                UPDATE users 
                SET 
                    category1 = ?, expenses1 = ?,
                    category2 = ?, expenses2 = ?,
                    category3 = ?, expenses3 = ? 
                WHERE telegram_id = ?
                """,
                (
                    data["category1"], data["expenses1"],
                    data["category2"], data["expenses2"],
                    data["category3"], expenses,
                    telegram_id,
                ),
            )

        await state.clear()
        await message.answer("Категории и расходы сохранены!")
    except ValueError:
        await message.reply("Пожалуйста, введите число!")
    except Exception as e:
        logging.error(f"Error saving finances: {e}")
        await message.answer("Произошла ошибка при сохранении данных")

@dp.message(F.text == "Отчет по расходам")
async def report_expenses(message: Message):
    telegram_id = message.from_user.id

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()

        if not user:
            await message.answer("Сначала зарегистрируйтесь с помощью кнопки регистрации.")
            return

        if not all([user["category1"], user["expenses1"],
                    user["category2"], user["expenses2"],
                    user["category3"], user["expenses3"]]):
            await message.answer("Сначала заполните данные о расходах.")
            return

        total = user["expenses1"] + user["expenses2"] + user["expenses3"]

        await message.answer(
            f"🧾 Отчет по расходам:\n\n"
            f"{user['category1']}: {user['expenses1']} руб\n"
            f"{user['category2']}: {user['expenses2']} руб\n"
            f"{user['category3']}: {user['expenses3']} руб\n\n"
            f"💰 Общие расходы: {total} руб"
        )

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
