import os
import psycopg2
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT
)
cursor = conn.cursor()

def create_tables():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS PendingQuestions (
        id SERIAL PRIMARY KEY,
        user_id TEXT NOT NULL,
        question TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    # Здесь можно создать и другие таблицы, если нужно
    conn.commit()

create_tables()

def add_pending_question(user_id, question):
    try:
        now = datetime.now(timezone.utc)
        cursor.execute(
            "INSERT INTO PendingQuestions (user_id, question, timestamp) VALUES (%s, %s, %s)",
            (user_id, question, now)
        )
        conn.commit()
        print(f"Вопрос сохранён: {question}")
    except Exception as e:
        print("Ошибка при добавлении вопроса:", e)

def get_all_pending_questions():
    cursor.execute("SELECT id, user_id, question, timestamp FROM PendingQuestions")
    return cursor.fetchall()

def delete_pending_question(question_id):
    try:
        cursor.execute("DELETE FROM PendingQuestions WHERE id = %s", (question_id,))
        conn.commit()
        return True
    except Exception as e:
        print("Ошибка при удалении вопроса:", e)
        return False
