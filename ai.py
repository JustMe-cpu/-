from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "deepseek/deepseek-r1-distill-qwen-32b:free"

client = OpenAI(
    base_url=BASE_URL,
    api_key=API_KEY,
)

def generate_response(prompt, user_id, add_pending_question_func):
    messages = [
        {
            "role": "system",
            "content": (
                "Ты дружелюбный, поддерживающий помощник для школьного администрирования. "
                "Если у тебя есть точные данные, давай подробный, развернутый ответ, который поможет пользователю. "
                "Если информации недостаточно или точного ответа нет, строго отвечай: "
                "'Извините, данных по этому вопросу недостаточно. Ваш вопрос сохранён для проверки куратором, пожалуйста, ожидайте ответа.' "
                "Не придумывай информацию и не давай ответы, если ты не уверен, или у тебя их нет. "
                "Также помни: если ты не можешь дать ответ по причине незнания, то тоже сохраняй запрос, предупреждая об этом."
            )
        },
        {"role": "user", "content": prompt}
    ]
    try:
        completion = client.chat.completions.create(
            extra_body={},
            model=MODEL,
            messages=messages
        )
        response = completion.choices[0].message.content
        if "Ваш вопрос сохранён для проверки куратором" in response:
            add_pending_question_func(user_id, prompt)
        return response
    except Exception as e:
        print(f"Ошибка при генерации ответа: {e}")
        return "Извините, произошла ошибка при обработке вашего запроса."
