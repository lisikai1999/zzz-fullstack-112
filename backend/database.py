import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'exam.db')


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        duration_minutes INTEGER NOT NULL,
        question_count INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER NOT NULL REFERENCES exams(id),
        question_number INTEGER NOT NULL,
        correct_option TEXT NOT NULL,
        difficulty REAL DEFAULT 0.5,
        UNIQUE(exam_id, question_number)
    );

    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER NOT NULL REFERENCES exams(id),
        name TEXT NOT NULL,
        student_code TEXT NOT NULL,
        UNIQUE(exam_id, student_code)
    );

    CREATE TABLE IF NOT EXISTS answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL REFERENCES students(id),
        question_id INTEGER NOT NULL REFERENCES questions(id),
        selected_option TEXT,
        is_correct INTEGER NOT NULL DEFAULT 0,
        time_spent_seconds REAL,
        answered_at TIMESTAMP,
        UNIQUE(student_id, question_id)
    );

    CREATE TABLE IF NOT EXISTS operation_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL REFERENCES students(id),
        event_type TEXT NOT NULL,
        timestamp REAL NOT NULL,
        duration_seconds REAL,
        metadata TEXT
    );

    CREATE TABLE IF NOT EXISTS analysis_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER NOT NULL REFERENCES exams(id),
        computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        result_type TEXT NOT NULL,
        result_json TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()


if __name__ == '__main__':
    init_db()
    print("Database initialized.")
