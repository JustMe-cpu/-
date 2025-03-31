import os
import json
from dotenv import load_dotenv
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from openai import OpenAI

# Загружаем переменные среды
load_dotenv()

API_KEY2 = os.getenv("OPENROUTER_API_KEY2")
BASE_URL = "https://openrouter.ai/api/v1"
MODEL2 = "deepseek/deepseek-r1-distill-qwen-32b:free"

# Инициализация клиента для работы с нейросетью
client = OpenAI(base_url=BASE_URL, api_key=API_KEY2)

router = Router()

class CuratorProcessing(StatesGroup):
    awaiting_answer = State()

# Функция для уточнения вопроса через нейросеть
def refine_question(question: str) -> str:
    system_prompt = (
        "Ты помощник, который уточняет и переформулирует вопросы. "
        "Сделай их лаконичными и понятными, удаляя некорректные детали или ненормативную лексику. "
        "Если вопрос некорректен или слишком короткий, верни пустую строку."
    )
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": question}]
    try:
        completion = client.chat.completions.create(model=MODEL2, messages=messages, extra_body={})
        refined = completion.choices[0].message.content.strip()
        if len(refined) < 10:
            return ""
        return refined
    except Exception as e:
        print(f"Ошибка в нейросети: {e}")
        return ""

# Чтение ожидающих вопросов
def get_pending_questions(filename="pending_questions.txt"):
    if not os.path.exists(filename):
        return []
    pending = []
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            try:
                pending.append(json.loads(line.strip()))
            except Exception:
                continue
    return pending

# Удаление обработанного вопроса
def remove_pending_question(question: str, filename="pending_questions.txt"):
    if not os.path.exists(filename):
        return
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()
    new_lines = [line for line in lines if question not in line]
    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

# Сохранение пары "Вопрос – Ответ"
def save_qa_pair(question: str, answer: str, filename="answers.txt"):
    entry = f"Вопрос: {question}\nОтвет: {answer}\n\n"
    with open(filename, "a", encoding="utf-8") as f:
        f.write(entry)

# Проверка на ненормативную лексику
def contains_profanity(text: str) -> bool:
    banned_words = ["хуй", "пизда", "ебать", "бляд", "сука", "пидор", "говно"]
    lower_text = text.lower()
    for word in banned_words:
        if word in lower_text:
            return True
    return False

# Обработчик команды "/ai2"
@router.message(Command("ai2"))
async def cmd_ii2(message: types.Message, state: FSMContext):
    await message.answer("Привет, куратор! Начинаем обработку вопросов.Вопрос:\n{refined}\n\n")
    await state.set_state(CuratorProcessing.awaiting_answer)
    await ask_next_pending(message, state)

# Функция для обработки следующего вопроса
async def ask_next_pending(message: types.Message, state: FSMContext):
    pending = get_pending_questions()
    if not pending:
        await message.answer("Все вопросы обработаны.")
        await state.clear()
        return
    next_entry = pending[0]
    original_question = next_entry["question"]
    refined = refine_question(original_question)
    if not refined or contains_profanity(refined):
        remove_pending_question(original_question)
        await message.answer("Некорректный или неприемлемый вопрос удалён. Переходим к следующему.")
        await ask_next_pending(message, state)
        return
    await state.update_data(current_question=refined, original_question=original_question)
    await message.answer(f"Вопрос:\n{refined}\n\nВведите ответ:")

# Обработчик ответа куратора
@router.message(CuratorProcessing.awaiting_answer)
async def curator_answer_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    current_question = data.get("current_question")
    original_question = data.get("original_question")
    if not current_question:
        await message.answer("Ошибка: вопрос не найден.")
        await state.clear()
        return
    answer = message.text.strip()
    save_qa_pair(current_question, answer)
    remove_pending_question(original_question)
    await message.answer("Ответ сохранён. Переходим к следующему вопросу.")
    await ask_next_pending(message, state)