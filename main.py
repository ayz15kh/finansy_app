
import asyncio
import aiosqlite
from datetime import datetime
import json
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import WebAppInfo
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import config


bot = Bot(token=config.API_TOKEN)
dp = Dispatcher()

DB_NAME = config.DB


# =======================
# FSM
# =======================

class Form(StatesGroup):
    expense = State()
    income = State()
    goal = State()
    deposit = State()
    calc = State()
    portfolio = State()


# =======================
# DB
# =======================

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0,
            currency TEXT DEFAULT '₽',
            notifications INTEGER DEFAULT 1
        )
        """)

        await db.execute("""CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            amount REAL,
            category TEXT
        )""")

        await db.execute("""CREATE TABLE IF NOT EXISTS income (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            amount REAL,
            source TEXT
        )""")

        await db.execute("""CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            name TEXT,
            target REAL,
            saved REAL DEFAULT 0
        )""")

        await db.execute("""CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            name TEXT
        )""")

        await db.commit()

@dp.message(F.web_app_data)
async def web_app_handler(message: Message):
    data = json.loads(message.web_app_data.data)

    amount = float(data["amount"])
    category = data["category"]

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO expenses (user_id, amount, category) VALUES (?, ?, ?)",
            (message.from_user.id, amount, category)
        )
        await db.commit()

    await message.answer(f"✅ Добавлено из WebApp: {amount} ₽ — {category}")
# =======================
# UI
# =======================

def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="🌐 Открыть приложение",web_app=WebAppInfo(url=config.WEBAPP_URL))
    kb.button(text="💰 Бюджет", callback_data="budget")
    kb.button(text="🎯 Цели", callback_data="goals")
    kb.button(text="📈 Инвестиции", callback_data="invest")
    kb.button(text="📊 Портфели", callback_data="portfolio")
    kb.button(text="🧠 Обучение", callback_data="learn")
    kb.button(text="⚙️ Настройки", callback_data="settings")
    kb.adjust(2)
    return kb.as_markup()


# =======================
# START
# =======================

@dp.message(CommandStart())
async def start(message: Message):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (id) VALUES (?)",
            (message.from_user.id,)
        )
        await db.commit()

    await message.answer("🏠 Главное меню", reply_markup=main_menu())


# =======================
# БЮДЖЕТ
# =======================

@dp.callback_query(F.data == "budget")
async def budget(callback: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Доход", callback_data="income")
    kb.button(text="➖ Расход", callback_data="expense")
    kb.button(text="💳 Баланс", callback_data="balance")
    kb.button(text="📊 Аналитика", callback_data="analytics")
    kb.button(text="⬅️ Назад", callback_data="back")
    kb.adjust(1)

    await callback.message.edit_text("💰 Бюджет", reply_markup=kb.as_markup())


# ДОХОД
@dp.callback_query(F.data == "income")
async def income(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Form.income)
    await callback.message.answer("Введи доход: 10000 зарплата")


@dp.message(Form.income)
async def save_income(message: Message, state: FSMContext):
    amount, source = message.text.split(maxsplit=1)

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO income (user_id, amount, source) VALUES (?, ?, ?)",
            (message.from_user.id, float(amount), source)
        )
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE id=?",
            (float(amount), message.from_user.id)
        )
        await db.commit()

    await message.answer("💰 Доход добавлен")
    await state.clear()


# РАСХОД
@dp.callback_query(F.data == "expense")
async def expense(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Form.expense)
    await callback.message.answer("Введи расход: 500 еда")


@dp.message(Form.expense)
async def save_expense(message: Message, state: FSMContext):
    amount, category = message.text.split(maxsplit=1)

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO expenses (user_id, amount, category) VALUES (?, ?, ?)",
            (message.from_user.id, float(amount), category)
        )
        await db.execute(
            "UPDATE users SET balance = balance - ? WHERE id=?",
            (float(amount), message.from_user.id)
        )
        await db.commit()

    await message.answer("➖ Расход добавлен")
    await state.clear()


# БАЛАНС
@dp.callback_query(F.data == "balance")
async def balance(callback: CallbackQuery):
    async with aiosqlite.connect(DB_NAME) as db:
        row = await (await db.execute(
            "SELECT balance FROM users WHERE id=?",
            (callback.from_user.id,)
        )).fetchone()

    await callback.message.answer(f"💳 Баланс: {row[0]} ₽")


# АНАЛИТИКА
@dp.callback_query(F.data == "analytics")
async def analytics(callback: CallbackQuery):
    async with aiosqlite.connect(DB_NAME) as db:
        rows = await (await db.execute(
            "SELECT category, SUM(amount) FROM expenses WHERE user_id=? GROUP BY category",
            (callback.from_user.id,)
        )).fetchall()

    text = "📊 Расходы:\n"
    for r in rows:
        text += f"{r[0]} — {r[1]}₽\n"

    await callback.message.answer(text)


# =======================
# ЦЕЛИ
# =======================

@dp.callback_query(F.data == "goals")
async def goals(callback: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Создать", callback_data="create_goal")
    kb.button(text="📋 Список", callback_data="list_goals")
    kb.button(text="💸 Пополнить", callback_data="deposit")
    kb.button(text="🧮 Калькулятор", callback_data="calc")
    kb.button(text="⬅️ Назад", callback_data="back")
    kb.adjust(1)

    await callback.message.edit_text("🎯 Цели", reply_markup=kb.as_markup())


@dp.callback_query(F.data == "create_goal")
async def create_goal(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Form.goal)
    await callback.message.answer("Название и сумма: Айфон 100000")


@dp.message(Form.goal)
async def save_goal(message: Message, state: FSMContext):
    name, target = message.text.rsplit(" ", 1)

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO goals (user_id, name, target) VALUES (?, ?, ?)",
            (message.from_user.id, name, float(target))
        )
        await db.commit()

    await message.answer("🎯 Цель создана")
    await state.clear()


@dp.callback_query(F.data == "list_goals")
async def list_goals(callback: CallbackQuery):
    async with aiosqlite.connect(DB_NAME) as db:
        rows = await (await db.execute(
            "SELECT id, name, target, saved FROM goals WHERE user_id=?",
            (callback.from_user.id,)
        )).fetchall()

    text = ""
    for r in rows:
        text += f"{r[0]}. {r[1]} — {r[3]}/{r[2]}₽\n"

    await callback.message.answer(text or "Нет целей")


@dp.callback_query(F.data == "calc")
async def calc(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Form.calc)
    await callback.message.answer(
        "🧮 Введи:\n"
        "ЦЕЛЬ ВЗНОС_В_МЕС\n\n"
        "Пример:\n100000 5000"
    )


@dp.message(Form.calc)
async def calculate(message: Message, state: FSMContext):
    try:
        total, monthly = map(float, message.text.split())

        if monthly <= 0:
            await message.answer("❌ Взнос должен быть > 0")
            return

        months = total / monthly
        years = months / 12

        await message.answer(
            f"⏳ Результат:\n\n"
            f"Месяцев: {months:.1f}\n"
            f"Лет: {years:.1f}"
        )

        await state.clear()

    except:
        await message.answer("❌ Ошибка. Введи: 100000 5000")

# =======================
# ИНВЕСТИЦИИ
# =======================

@dp.callback_query(F.data == "invest")
async def invest(callback: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="🌍 Рынок", callback_data="market")
    kb.button(text="💎 Криптовалюты", callback_data="crypto")
    kb.button(text="📊 Акции", callback_data="stocks")
    kb.button(text="📦 ETF", callback_data="etf")
    kb.button(text="⬅️ Назад", callback_data="back")
    kb.adjust(1)

    await callback.message.edit_text("📈 Инвестиции", reply_markup=kb.as_markup())


@dp.callback_query(F.data == "market")
async def market(callback: CallbackQuery):
    await callback.message.answer(
        "🌍 Рынок сегодня:\n\n"
        "S&P 500: +1.2%\n"
        "NASDAQ: +0.8%\n"
        "Dow Jones: +0.5%\n\n"
        "📊 Тренд: рост"
    )


@dp.callback_query(F.data == "crypto")
async def crypto(callback: CallbackQuery):
    await callback.message.answer(
        "💎 Криптовалюты:\n\n"
        "Bitcoin: $67,000 (+2%)\n"
        "Ethereum: $3,200 (+1.5%)\n"
        "Solana: $150 (+4%)\n"
    )


@dp.callback_query(F.data == "stocks")
async def stocks(callback: CallbackQuery):
    await callback.message.answer(
        "📊 Акции:\n\n"
        "Apple: +1.3%\n"
        "Tesla: +2.1%\n"
        "Amazon: +0.7%\n"
    )


@dp.callback_query(F.data == "etf")
async def etf(callback: CallbackQuery):
    await callback.message.answer(
        "📦 ETF:\n\n"
        "SPY: +1.2%\n"
        "QQQ: +0.9%\n"
        "VTI: +1.0%\n"
    )


# =======================
# ПОРТФЕЛИ
# =======================

@dp.callback_query(F.data == "portfolio")
async def portfolio(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Form.portfolio)
    await callback.message.answer("Название портфеля")


@dp.message(Form.portfolio)
async def save_portfolio(message: Message, state: FSMContext):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO portfolio (user_id, name) VALUES (?, ?)",
            (message.from_user.id, message.text)
        )
        await db.commit()

    await message.answer("📊 Портфель создан")
    await state.clear()


# =======================
# ОБУЧЕНИЕ
# =======================

@dp.callback_query(F.data == "learn")
async def learn(callback: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Бюджет", callback_data="learn_budget")
    kb.button(text="📈 Инвестиции", callback_data="learn_invest")
    kb.button(text="🧠 Советы", callback_data="learn_tips")
    kb.button(text="⬅️ Назад", callback_data="back")
    kb.adjust(1)

    await callback.message.edit_text("🧠 Обучение", reply_markup=kb.as_markup())


@dp.callback_query(F.data == "learn_budget")
async def learn_budget(callback: CallbackQuery):
    await callback.message.answer(
        "💰 Основы бюджета:\n\n"
        "1. Трать меньше, чем зарабатываешь\n"
        "2. Делай учет расходов\n"
        "3. Откладывай минимум 10%\n"
        "4. Избегай импульсивных покупок"
    )


@dp.callback_query(F.data == "learn_invest")
async def learn_invest(callback: CallbackQuery):
    await callback.message.answer(
        "📈 Инвестиции:\n\n"
        "• Начни с ETF\n"
        "• Диверсифицируй портфель\n"
        "• Не инвестируй последние деньги\n"
        "• Думай на долгий срок"
    )


@dp.callback_query(F.data == "learn_tips")
async def learn_tips(callback: CallbackQuery):
    await callback.message.answer(
        "🧠 Финансовые советы:\n\n"
        "💡 Веди учет расходов\n"
        "💡 Не бери кредиты без необходимости\n"
        "💡 Создай финансовую подушку (3-6 мес)\n"
        "💡 Инвестируй регулярно\n"
        "💡 Не трать деньги на статус\n"
        "💡 Покупай активы, не пассивы\n"
        "💡 Учись финансовой грамотности\n"
        "💡 Избегай долгов\n"
    )


# =======================
# НАСТРОЙКИ
# =======================
@dp.callback_query(F.data == "settings")
async def settings(callback: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="💱 Валюта", callback_data="currency")
    kb.button(text="🔔 Уведомления", callback_data="notifications")
    kb.button(text="👤 Профиль", callback_data="profile")
    kb.button(text="🧹 Сброс данных", callback_data="reset")
    kb.button(text="⬅️ Назад", callback_data="back")
    kb.adjust(1)

    await callback.message.edit_text("⚙️ Настройки", reply_markup=kb.as_markup())



@dp.callback_query(F.data == "currency")
async def currency(callback: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="₽ Рубль", callback_data="set_rub")
    kb.button(text="$ Доллар", callback_data="set_usd")
    kb.button(text="€ Евро", callback_data="set_eur")
    kb.button(text="⬅️ Назад", callback_data="settings")
    kb.adjust(1)

    await callback.message.edit_text("💱 Выбери валюту", reply_markup=kb.as_markup())


async def set_currency(user_id, cur):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET currency=? WHERE id=?", (cur, user_id))
        await db.commit()


@dp.callback_query(F.data == "set_rub")
async def set_rub(callback: CallbackQuery):
    await set_currency(callback.from_user.id, "₽")
    await callback.message.answer("✅ Валюта: ₽")


@dp.callback_query(F.data == "set_usd")
async def set_usd(callback: CallbackQuery):
    await set_currency(callback.from_user.id, "$")
    await callback.message.answer("✅ Валюта: $")


@dp.callback_query(F.data == "set_eur")
async def set_eur(callback: CallbackQuery):
    await set_currency(callback.from_user.id, "€")
    await callback.message.answer("✅ Валюта: €")







@dp.callback_query(F.data == "notifications")
async def notifications(callback: CallbackQuery):
    async with aiosqlite.connect(DB_NAME) as db:
        row = await (await db.execute(
            "SELECT notifications FROM users WHERE id=?",
            (callback.from_user.id,)
        )).fetchone()

    status = "ВКЛ" if row[0] else "ВЫКЛ"

    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Переключить", callback_data="toggle_notifications")
    kb.button(text="⬅️ Назад", callback_data="settings")
    kb.adjust(1)

    await callback.message.edit_text(
        f"🔔 Уведомления: {status}",
        reply_markup=kb.as_markup()
    )


@dp.callback_query(F.data == "toggle_notifications")
async def toggle_notifications(callback: CallbackQuery):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        UPDATE users
        SET notifications = NOT notifications
        WHERE id=?
        """, (callback.from_user.id,))
        await db.commit()

    await callback.message.answer("✅ Настройки обновлены")





@dp.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):
    async with aiosqlite.connect(DB_NAME) as db:
        row = await (await db.execute(
            "SELECT balance, currency FROM users WHERE id=?",
            (callback.from_user.id,)
        )).fetchone()

    balance, currency = row

    await callback.message.answer(
        f"👤 Профиль\n\n"
        f"💳 Баланс: {balance} {currency}\n"
        f"🆔 ID: {callback.from_user.id}"
    )






@dp.callback_query(F.data == "reset")
async def reset(callback: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="❗ ДА, удалить", callback_data="confirm_reset")
    kb.button(text="⬅️ Назад", callback_data="settings")
    kb.adjust(1)

    await callback.message.edit_text(
        "⚠️ Удалить ВСЕ данные?",
        reply_markup=kb.as_markup()
    )


@dp.callback_query(F.data == "confirm_reset")
async def confirm_reset(callback: CallbackQuery):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM expenses WHERE user_id=?", (callback.from_user.id,))
        await db.execute("DELETE FROM income WHERE user_id=?", (callback.from_user.id,))
        await db.execute("DELETE FROM goals WHERE user_id=?", (callback.from_user.id,))
        await db.execute("UPDATE users SET balance=0 WHERE id=?", (callback.from_user.id,))
        await db.commit()

    await callback.message.answer("🧹 Данные очищены")





# =======================
# НАЗАД
# =======================

@dp.callback_query(F.data == "back")
async def back(callback: CallbackQuery):
    await callback.message.edit_text("🏠 Главное меню", reply_markup=main_menu())


# =======================
# RUN
# =======================

async def main():
    await init_db()
    print("Bot started...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
