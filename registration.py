import os
from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
from dotenv import load_dotenv

load_dotenv()

router = Router()
import psycopg2
from psycopg2.extras import DictCursor
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

def is_user_registered(user_id, role):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cursor:
            query = """
                SELECT COUNT(*)
                FROM registrations
                WHERE telegram_id = %s AND role = %s
            """
            cursor.execute(query, (user_id, role))
            count = cursor.fetchone()["count"]
            return count > 0
    finally:
        conn.close()

def get_registration_requests():
    """
    Возвращает список заявок на регистрацию, статус которых — 'pending'.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cursor:
            query = """
                SELECT telegram_id, role, class, full_name, status, registration_date
                FROM registrations
                WHERE status = 'pending'
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            return rows
    finally:
        conn.close()

@router.message(Command("view_registration"))
async def view_registration(message: types.Message):
    """
    Обработчик для вывода списка заявок на регистрацию с инлайн-кнопками для действий.
    """
    requests = get_registration_requests()  # Считываем заявки из базы
    if not requests:
        await message.answer("Нет доступных заявок на регистрацию.")
        return

    for row in requests:
        # Формируем текст для каждой заявки
        text = (
            f"Telegram ID: {row['telegram_id']}\n"
            f"Роль: {row['role']}\n"
            f"Класс: {row.get('class', 'Не указан')}\n"
            f"Имя: {row.get('full_name', 'Не указано')}\n"
            f"Статус: {row['status']}\n"
            f"Дата регистрации: {row['registration_date']}"
        )
        # Создаем инлайн-кнопки для принятия и отклонения заявки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Принять", callback_data=f"approve:{row['telegram_id']}"),
                InlineKeyboardButton(text="Отклонить", callback_data=f"reject:{row['telegram_id']}")
            ]
        ])
        await message.answer(text, reply_markup=keyboard)

@router.callback_query(lambda c: c.data and c.data.startswith("approve:"))
async def approve_registration(callback: types.CallbackQuery):
    """
    Обработчик для принятия заявки.
    """
    telegram_id = callback.data.split(":")[1]  # Получаем Telegram ID из callback_data

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Обновляем статус заявки на "approved"
            query = """
                UPDATE registrations
                SET status = 'approved'
                WHERE telegram_id = %s AND status = 'pending'
            """
            cursor.execute(query, (telegram_id,))
            conn.commit()
        await callback.message.edit_text(f"Заявка пользователя с Telegram ID {telegram_id} была одобрена.")
    finally:
        conn.close()


@router.callback_query(lambda c: c.data and c.data.startswith("reject:"))
async def reject_registration(callback: types.CallbackQuery):
    """
    Обработчик для отклонения заявки.
    """
    telegram_id = callback.data.split(":")[1]  # Получаем Telegram ID из callback_data

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Обновляем статус заявки на "rejected"
            query = """
                UPDATE registrations
                SET status = 'rejected'
                WHERE telegram_id = %s AND status = 'pending'
            """
            cursor.execute(query, (telegram_id,))
            conn.commit()
        await callback.message.edit_text(f"Заявка пользователя с Telegram ID {telegram_id} была отклонена.")
    finally:
        conn.close()

def save_registration(user_id, role, full_name, chosen_class, status):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            query = """
                INSERT INTO registrations (telegram_id, role, full_name, class, status)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (user_id, role, full_name, chosen_class, status))
            conn.commit()
    finally:
        conn.close()

class Registration(StatesGroup):
    choosing_role = State()
    choosing_class = State()
    entering_name = State()

def role_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text="Куратор", callback_data="register_role:curator"),
            InlineKeyboardButton(text="Родитель", callback_data="register_role:parent")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def class_keyboard():
    rows = []
    for grade in range(1, 12):
        row = []
        for letter in ["A", "B", "C", "D"]:
            class_name = f"{grade}{letter}"
            row.append(InlineKeyboardButton(text=class_name, callback_data=f"register_class:{class_name}"))
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)



@router.message(Command("register"))
async def cmd_register(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    # Проверяем, зарегистрирован ли пользователь как куратор или родитель
    if is_user_registered(user_id, "curator") or is_user_registered(user_id, "parent"):
        await message.answer(
            "Вы уже зарегистрированы. Если вы куратор, вы всё ещё можете зарегистрироваться как родитель.")
        return
    await message.answer("Желаете зарегистрироваться? Выберите вашу роль:", reply_markup=role_keyboard())
    await state.set_state(Registration.choosing_role)


@router.callback_query(lambda c: c.data and c.data.startswith("register_role:"))
async def callback_choose_role(callback: types.CallbackQuery, state: FSMContext):
    role = callback.data.split(":")[1]
    user_id = str(callback.from_user.id)

    # Проверка: Если пользователь пытается зарегистрироваться повторно как куратор
    if role == "curator" and is_user_registered(user_id, "curator"):
        await callback.message.edit_text("Вы уже зарегистрированы как куратор.")
        await state.clear()
        return

    await state.update_data(role=role)
    await callback.message.edit_text("Выберите ваш класс:", reply_markup=class_keyboard())
    await state.set_state(Registration.choosing_class)


@router.callback_query(lambda c: c.data and c.data.startswith("register_class:"))
async def callback_choose_class(callback: types.CallbackQuery, state: FSMContext):
    chosen_class = callback.data.split(":")[1]
    user_id = str(callback.from_user.id)
    data = await state.get_data()
    role = data.get("role")

    # Проверяем, если пользователь уже зарегистрирован как родитель в выбранном классе
    if role == "parent" and is_user_registered(user_id, role):
        await callback.message.edit_text(f"Вы уже зарегистрированы как родитель в классе {chosen_class}.")
        await state.clear()
        return

    await state.update_data(chosen_class=chosen_class)

    if role == "curator":
        save_registration(user_id, role, None, chosen_class, status="approved")
        await callback.message.edit_text(f"Вы выбрали класс {chosen_class} в качестве куратора. Регистрация завершена.")
        await state.clear()
    elif role == "parent":
        await callback.message.edit_text(f"Вы выбрали класс {chosen_class}. Введите, пожалуйста, ваше ФИО:")
        await state.set_state(Registration.entering_name)


@router.message(Registration.entering_name)
async def handle_parent_name(message: types.Message, state: FSMContext):
    full_name = message.text.strip()
    data = await state.get_data()
    user_id = str(message.from_user.id)
    chosen_class = data.get("chosen_class")
    role = data.get("role")

    # Проверяем, зарегистрирован ли пользователь в роли родителя
    if is_user_registered(user_id, role):
        await message.answer(f"Вы уже зарегистрированы как родитель в классе {chosen_class}.")
        await state.clear()
        return

    save_registration(user_id, role, full_name, chosen_class, status="pending")
    await message.answer("Ваша заявка на регистрацию отправлена куратору.")
    await state.clear()