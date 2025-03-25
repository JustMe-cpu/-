from openai import OpenAI
from dotenv import load_dotenv
import os
import json

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY2")
BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "deepseek/deepseek-r1-distill-qwen-32b:free"

client = OpenAI(
    base_url=BASE_URL,
    api_key=API_KEY,
)


def cluster_questions(questions):
    prompt_text = (
        "Ты нейросеть, задачей которой является сортировка и кластеризация вопросов по смыслу. "
        "У тебя имеется следующий список вопросов:\n"
        f"{json.dumps(questions, ensure_ascii=False, indent=2)}\n"
        "Пожалуйста, сгруппируй вопросы, имеющие одну и ту же суть. "
        "Для каждой группы выбери один уникальный главный вопрос, который будет представлен вне скобок, "
        "а остальные вопросы с той же сутью выведи в скобках. "
        "Выведи результат в формате JSON, например так: { \"Главный Вопрос\": [\"Вопрос 1\", \"Вопрос 2\", ...], ... }."
    )

    messages = [
        {"role": "system", "content": "Ты нейросеть для сортировки и кластеризации вопросов по смыслу."},
        {"role": "user", "content": prompt_text}
    ]

    completion = client.chat.completions.create(
        extra_body={},
        model=MODEL,
        messages=messages
    )
    return completion.choices[0].message.content


# Если требуется, можно добавить блок для отладки, но он не будет выполняться по умолчанию.
if __name__ == "__main__":
    pass
