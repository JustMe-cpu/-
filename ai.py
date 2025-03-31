import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from registration import is_user_registered

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "deepseek/deepseek-r1-distill-qwen-32b:free"

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

def load_context(filename="answers.txt"):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def save_pending_question(question, user_id, filename="pending_questions.txt"):
    entry = {"user_id": user_id, "question": question}
    with open(filename, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def check_user_access(user_id):
    if is_user_registered(user_id, "curator"):
        return True
    if is_user_registered(user_id, "parent") or is_user_registered(user_id, "student"):
        return True
    return False

def generate_response(prompt, user_id):
    if not check_user_access(user_id):
        return "Доступ разрешён только для родителей и учеников, зарегистрируйтесь."
    if "вопрос для куратора" in prompt.lower():
        save_pending_question(prompt, user_id)
        return "Ваш вопрос сохранён для проверки куратором, пожалуйста, ожидайте ответа."
    context_text = load_context()
    full_prompt = ("Используй информацию из ниже приведённого документа как контекст:\n\n" +
                   context_text + "\n\nНа основе этой информации ответь на вопрос ниже:\n" + prompt)
    system_prompt = ("Ты дружелюбный помощник, отвечающий строго на русском языке. " +
                     "Отвечай максимально точно, кратко и чётко, соблюдая корректность речи, " +
                     "основываясь на актуальных знаниях и предоставленном документе.")
    messages = [{"role": "system", "content": system_prompt},
                {"role": "user", "content": full_prompt}]
    try:
        completion = client.chat.completions.create(extra_body={}, model=MODEL, messages=messages)
        response = completion.choices[0].message.content
        return response
    except Exception as e:
        print(f"Ошибка при генерации ответа: {e}")
        return "Извините, произошла ошибка при обработке вашего запроса."

def refine_question(question: str) -> str:
    system_prompt = ("Ты помощник, который уточняет и переформулирует вопросы. Сделай их лаконичными и понятными, удаляя некорректные детали или ненормативную лексику. Если вопрос некорректен или слишком короткий, верни пустую строку.")
    messages = [{"role": "system", "content": system_prompt},
                {"role": "user", "content": question}]
    try:
        completion = client.chat.completions.create(model=MODEL, messages=messages, extra_body={})
        refined = completion.choices[0].message.content.strip()
        if len(refined) < 10:
            return ""
        return refined
    except Exception as e:
        print(f"Ошибка во второй нейросети: {e}")
        return ""

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

def remove_pending_question(question, filename="pending_questions.txt"):
    if not os.path.exists(filename):
        return
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()
    new_lines = [line for line in lines if question not in line]
    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

def save_qa_pair(question, answer, filename="answers.txt"):
    entry = f"Вопрос: {question}\nОтвет: {answer}\n\n"
    with open(filename, "a", encoding="utf-8") as f:
        f.write(entry)

def handle_questions():
    pending_questions = get_pending_questions()
    if not pending_questions:
        print("Нет ожидающих вопросов.")
        return
    for question_entry in pending_questions:
        original_question = question_entry["question"]
        refined_question = refine_question(original_question)
        if not refined_question:
            print(f"Некорректный вопрос удалён: {original_question}")
            remove_pending_question(original_question)
            continue
        print(f"Вопрос: {refined_question}")
        answer = input("Введите ответ: ").strip()
        save_qa_pair(refined_question, answer)
        remove_pending_question(original_question)
    print("Все вопросы обработаны.")