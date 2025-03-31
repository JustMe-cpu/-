from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import os
import logging
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from ai import generate_response
from registration import router as registration_router
from ai2 import router as ai2_router


load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(registration_router)
dp.include_router(ai2_router)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIChat(StatesGroup):
    waiting_for_message = State()

def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/start")],
            [KeyboardButton(text="/register")],
            [KeyboardButton(text="/help")],
            [KeyboardButton(text="/info")],
            [KeyboardButton(text="/ai")]
        ],
        resize_keyboard=True
    )

# Обработчик команды /start
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("Привет! Выберите действие, используя кнопки ниже:", reply_markup=main_menu_keyboard())


# Обработчик команды /help
@dp.message(Command("help"))
async def help_handler(message: types.Message):
    await message.answer(
        "Вот команды, которые вы можете использовать:\n"
        "/start - Запуск бота\n"
        "/register - Регистрация\n"
        "/help - Помощь\n"
        "/info - Информация\n"
        "/ai - ИИ-чат\n"
    )

# Обработчик команды /info
@dp.message(Command("info"))
async def info_handler(message: types.Message):
    await message.answer("Я- лучший друг куратора, отвечающий на его вопросы и помогая родителям и ученикам получить ответ")

@dp.message(Command("ai"))
async def cmd_ai(message: types.Message, state: FSMContext):
    await message.answer("Вы вошли в AI-чат. Введите ваш запрос. Для выхода отправьте /stop. И если вам не понравидся ответа на ваш вопрос, то отпраьте ваш вопрос повторно добавивь слова: Вопрос для куратора.")
    await state.set_state(AIChat.waiting_for_message)

@dp.message(Command("stop"))
async def cmd_stop(message: types.Message, state: FSMContext):
    await state.clear()

@dp.message(AIChat.waiting_for_message)
async def ai_chat_handler(message: types.Message, state: FSMContext):
    user_input = message.text.strip()
    user_id = str(message.from_user.id)
    response = generate_response(user_input, user_id)  # Убедитесь, что эта функция определена в вашем коде
    await message.answer(response)

async def main():
    logger.info("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
