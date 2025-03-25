import os
import asyncio
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from database import (
    add_pending_question,
    delete_pending_question
)
from ai import generate_response

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

last_user_query = {}


# Хэндлер на команду /start
@dp.message(commands=["start"])
async def handle_start(message: Message):
    await message.answer(
        f"Привет, {message.from_user.first_name}! Я бот для школьного администрирования. "
        "Вы можете задавать вопросы или отправить заявку на регистрацию с помощью команды /register."
    )


# Хэндлер на команду /register
@dp.message(commands=["register"])
async def handle_register(message: Message):
    user_id = str(message.from_user.id)
    user_name = message.from_user.first_name
    application_text = f"Заявка на регистрацию:\nПользователь: {user_name}\nID: {user_id}"

    # Отправка заявки куратору через inline-кнопки
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="Принять", callback_data=f"accept_{user_id}"),
        InlineKeyboardButton(text="Отклонить", callback_data=f"reject_{user_id}")
    )
    curator_chat_id = os.getenv("CURATOR_CHAT_ID")  # ID чата куратора из переменных окружения
    await bot.send_message(curator_chat_id, application_text, reply_markup=keyboard)
    await message.answer("Ваша заявка отправлена куратору. Ожидайте подтверждения.")


# Хэндлер для обработки ответов от куратора
@dp.callback_query(F.data.startswith("accept_"))
async def handle_accept(callback_query: types.CallbackQuery):
    user_id = callback_query.data.split("_")[1]
    await bot.send_message(user_id, "Вашу заявку на регистрацию приняли. Добро пожаловать!")
    await callback_query.answer("Вы приняли заявку.")


@dp.callback_query(F.data.startswith("reject_"))
async def handle_reject(callback_query: types.CallbackQuery):
    user_id = callback_query.data.split("_")[1]
    await bot.send_message(user_id, "К сожалению, вашу заявку на регистрацию отклонили.")
    await callback_query.answer("Вы отклонили заявку.")


# Основной обработчик текстовых сообщений
@dp.message(F.text)
async def handle_message(message: Message):
    user_input = message.text.strip()
    user_id = str(message.from_user.id)
    lower_text = user_input.lower()

    # Обработка удаления вопросов
    if ("удали мой вопрос" in lower_text or
            "отмени вопрос" in lower_text or
            "отмени запрос" in lower_text):
        pending = get_pending_question_by_user(user_id)
        if pending:
            question_text, timestamp = pending
            if datetime.now(timezone.utc) - timestamp <= timedelta(minutes=10):
                if delete_pending_question(user_id, question_text):
                    await message.answer("Ваш вопрос успешно удалён.")
                else:
                    await message.answer("Не удалось удалить вопрос. Попробуйте позже.")
            else:
                await message.answer("Удалять вопрос можно только в течение 10 минут после отправки.")
        else:
            await message.answer("Нет сохранённых вопросов для удаления.")
        return

    # Проверка на похожие вопросы
    if is_similar_pending_question(user_id, user_input):
        await message.answer(
            "Вы уже задавали вопрос с подобной сутью. Пожалуйста, дождитесь ответа на предыдущий запрос."
        )
        return

    # Сохранение последнего запроса для возможной отмены
    last_user_query[user_id] = (user_input, datetime.now(timezone.utc))

    # Генерация ответа через AI
    response = generate_response(user_input, user_id, add_pending_question)
    await message.answer(response)


# Основная функция запуска
async def main():
    print("Бот успешно запущен и готов к работе!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
