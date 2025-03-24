import os
import asyncio
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from database import (
    add_pending_question,
    delete_pending_question,
    get_pending_question_by_user,
    is_similar_pending_question
)
from ai import generate_response

#смтори Нурэл, сюда ты должен добавить старт, и регистрацию, в целом ничего труного, главное не задень остальные файлы и функции.
#И ещё, регистрацию делай так : кога родитель регается он делает заявку которая отправляется куратору и он либо принимает либо нет.


load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

last_user_query = {}

@dp.message(F.text)
async def handle_message(message: Message):
    user_input = message.text.strip()
    user_id = str(message.from_user.id)
    lower_text = user_input.lower()

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

    if is_similar_pending_question(user_id, user_input):
        await message.answer("Вы уже задавали вопрос с подобной сущностью. Пожалуйста, дождитесь ответа на предыдущий запрос.")
        return

    last_user_query[user_id] = (user_input, datetime.now(timezone.utc))
    response = generate_response(user_input, user_id, add_pending_question)
    await message.answer(response)

async def main():
    print("Бот успешно запущен и готов к работе!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
