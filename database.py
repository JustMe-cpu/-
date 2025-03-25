import os
import psycopg2
from datetime import datetime, timezone
from dotenv import load_dotenv
import json

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
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        cluster_id INTEGER
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
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        cluster_id INTEGER
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS QuestionClusters (
        id SERIAL PRIMARY KEY,
        representative_question TEXT NOT NULL,
        questions JSONB NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
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
    cursor.execute("SELECT id, user_id, question, timestamp, cluster_id FROM PendingQuestions")
    return cursor.fetchall()

def delete_pending_question(question_id):
    try:
        cursor.execute("DELETE FROM PendingQuestions WHERE id = %s", (question_id,))
        conn.commit()
        return True
    except Exception as e:
        print("Ошибка при удалении вопроса:", e)
        return False

def exists_pending_question(user_id, question):
    try:
        cursor.execute("SELECT id FROM PendingQuestions WHERE user_id = %s AND question = %s", (user_id, question))
        return cursor.fetchone() is not None
    except Exception as e:
        print("Ошибка при проверке существования вопроса:", e)
        return False

def mark_question_answered(question_id, answer, query_text):
    try:
        now = datetime.now(timezone.utc)
        cursor.execute(
            "INSERT INTO AnsweredQuestions (query, answer, timestamp) VALUES (%s, %s, %s)",
            (query_text, answer, now)
        )
        delete_pending_question(question_id)
        conn.commit()
    except Exception as e:
        print("Ошибка при сохранении ответа:", e)

def search_answered_question(query, similarity_threshold=0.85):
    cursor.execute("SELECT answer FROM AnsweredQuestions WHERE query ILIKE %s", (f"%{query}%",))
    return cursor.fetchone()

def add_question_cluster(representative, questions_list):
    try:
        now = datetime.now(timezone.utc)
        questions_json = json.dumps(questions_list, ensure_ascii=False)
        cursor.execute(
            "INSERT INTO QuestionClusters (representative_question, questions, timestamp) VALUES (%s, %s, %s)",
            (representative, questions_json, now)
        )
        conn.commit()
    except Exception as e:
        print("Ошибка при добавлении кластеров вопросов:", e)
