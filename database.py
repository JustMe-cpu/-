import os
import psycopg2
from datetime import datetime, timezone
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import numpy as np

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
    CREATE TABLE IF NOT EXISTS Users (
        id SERIAL PRIMARY KEY,
        tg_id BIGINT NOT NULL UNIQUE,
        user_id TEXT NOT NULL UNIQUE,
        role TEXT NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Teachers (
        id SERIAL PRIMARY KEY,
        subject TEXT NOT NULL,
        name TEXT NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS PendingQuestions (
        id SERIAL PRIMARY KEY,
        user_id TEXT NOT NULL,
        question TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Schedule (
        id SERIAL PRIMARY KEY,
        day_of_week TEXT NOT NULL,
        lesson_time TEXT NOT NULL,
        subject TEXT NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Exceptions (
        id SERIAL PRIMARY KEY,
        date DATE NOT NULL,
        detail TEXT NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Homework (
        id SERIAL PRIMARY KEY,
        subject TEXT NOT NULL,
        task TEXT NOT NULL,
        due_date DATE NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Birthdays (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        birthday DATE NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Grades (
        id SERIAL PRIMARY KEY,
        student_name TEXT NOT NULL,
        subject TEXT NOT NULL,
        grade REAL NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Memory (
        id SERIAL PRIMARY KEY,
        key TEXT UNIQUE NOT NULL,
        value TEXT NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Logs (
        id SERIAL PRIMARY KEY,
        user_id TEXT NOT NULL,
        action TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS AnsweredQuestions (
        id SERIAL PRIMARY KEY,
        query TEXT NOT NULL,
        answer TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()

create_tables()

# Загрузка модели эмбеддингов (например, "paraphrase-MiniLM-L6-v2" — легкая и быстрая)
embedding_model = SentenceTransformer('paraphrase-MiniLM-L6-v2')

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

def get_pending_question_by_user(user_id):
    try:
        cursor.execute("""
            SELECT question, timestamp
            FROM PendingQuestions 
            WHERE user_id = %s 
            ORDER BY timestamp DESC 
            LIMIT 1
        """, (user_id,))
        row = cursor.fetchone()
        if row:
            question, ts = row
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return (question, ts)
        else:
            return None
    except Exception as e:
        print("Ошибка при получении последнего вопроса:", e)
        return None

def delete_pending_question(user_id, question):
    try:
        cursor.execute(
            "DELETE FROM PendingQuestions WHERE user_id = %s AND question = %s",
            (user_id, question)
        )
        conn.commit()
        return True
    except Exception as e:
        print("Ошибка при удалении вопроса:", e)
        return False

def exists_pending_question(user_id, question):
    try:
        cursor.execute(
            "SELECT id FROM PendingQuestions WHERE user_id = %s AND question = %s",
            (user_id, question)
        )
        return cursor.fetchone() is not None
    except Exception as e:
        print("Ошибка при проверке существования вопроса:", e)
        return False

def is_similar_pending_question(user_id, new_question, threshold=0.85):
    new_embed = embedding_model.encode([new_question])[0]
    cursor.execute("SELECT question FROM PendingQuestions WHERE user_id = %s", (user_id,))
    rows = cursor.fetchall()
    for row in rows:
        existing_question = row[0]
        existing_embed = embedding_model.encode([existing_question])[0]
        cosine_sim = np.dot(new_embed, existing_embed) / (np.linalg.norm(new_embed) * np.linalg.norm(existing_embed))
        if cosine_sim >= threshold:
            return True
    return False
