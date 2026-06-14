import random
import math
import json
import numpy as np
from database import init_db, get_conn

random.seed(42)
np.random.seed(42)

OPTIONS = ['A', 'B', 'C', 'D']
NUM_QUESTIONS = 50
NUM_STUDENTS = 30
EXAM_DURATION_MINUTES = 60

STUDENT_NAMES = [
    "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry",
    "Ivy", "Jack", "Karen", "Leo", "Mia", "Noah", "Olivia", "Peter",
    "Quinn", "Ryan", "Sophia", "Tom", "Uma", "Victor", "Wendy", "Xavier",
    "Yuki", "Zach", "Amy", "Brian", "Chloe", "David"
]

# Cheater roles:
# Pair A (indices 2,3 - Charlie & Diana): answer copying — share 80% wrong answers
# Pair B (indices 6,7 - Grace & Henry): fast-start pattern + many tab switches
# Student 10 (Karen): remote control — smooth mouse trajectory


def generate_questions(conn, exam_id):
    questions = []
    for i in range(1, NUM_QUESTIONS + 1):
        correct = random.choice(OPTIONS)
        difficulty = random.betavariate(2, 3)  # skewed toward easier
        conn.execute(
            "INSERT INTO questions (exam_id, question_number, correct_option, difficulty) VALUES (?, ?, ?, ?)",
            (exam_id, i, correct, round(difficulty, 3))
        )
        questions.append({'number': i, 'correct': correct, 'difficulty': difficulty})
    conn.commit()

    rows = conn.execute(
        "SELECT id, question_number, correct_option, difficulty FROM questions WHERE exam_id=? ORDER BY question_number",
        (exam_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def generate_normal_answer(question, ability):
    p_correct = max(0.1, min(0.95, ability - question['difficulty'] + 0.5))
    if random.random() < p_correct:
        return question['correct_option'], True
    wrong = [o for o in OPTIONS if o != question['correct_option']]
    return random.choice(wrong), False


def generate_time_normal(question):
    base = 20 + question['difficulty'] * 60
    return max(3, np.random.lognormal(math.log(base), 0.5))


def generate_answers_normal(conn, student_id, questions, ability):
    exam_start = 1000000.0
    elapsed = 0
    for q in questions:
        selected, correct = generate_normal_answer(q, ability)
        time_spent = generate_time_normal(q)
        elapsed += time_spent
        conn.execute(
            "INSERT INTO answers (student_id, question_id, selected_option, is_correct, time_spent_seconds, answered_at) VALUES (?, ?, ?, ?, ?, ?)",
            (student_id, q['id'], selected, int(correct), round(time_spent, 2), exam_start + elapsed)
        )
    conn.commit()


def generate_answers_copy_pair(conn, student_a_id, student_b_id, questions, ability_a, ability_b):
    """Pair A: answer copying. Student B copies from A on 80% of wrong answers."""
    exam_start_a = 1000000.0
    exam_start_b = 1000000.0
    elapsed_a = 0
    elapsed_b = 0

    a_answers = []
    for q in questions:
        selected, correct = generate_normal_answer(q, ability_a)
        time_spent = generate_time_normal(q)
        elapsed_a += time_spent
        conn.execute(
            "INSERT INTO answers (student_id, question_id, selected_option, is_correct, time_spent_seconds, answered_at) VALUES (?, ?, ?, ?, ?, ?)",
            (student_a_id, q['id'], selected, int(correct), round(time_spent, 2), exam_start_a + elapsed_a)
        )
        a_answers.append({'selected': selected, 'correct': correct})

    for i, q in enumerate(questions):
        a_sel = a_answers[i]['selected']
        a_correct = a_answers[i]['correct']

        if not a_correct and random.random() < 0.80:
            selected = a_sel
            correct = (selected == q['correct_option'])
        else:
            selected, correct = generate_normal_answer(q, ability_b)

        time_spent = generate_time_normal(q) * random.uniform(0.9, 1.3)
        elapsed_b += time_spent
        conn.execute(
            "INSERT INTO answers (student_id, question_id, selected_option, is_correct, time_spent_seconds, answered_at) VALUES (?, ?, ?, ?, ?, ?)",
            (student_b_id, q['id'], selected, int(correct), round(time_spent, 2), exam_start_b + elapsed_b)
        )
    conn.commit()


def generate_answers_fast_start(conn, student_id, questions, ability):
    """Pair B: first 15 questions answered in <5 seconds, rest normal."""
    exam_start = 1000000.0
    elapsed = 0
    for i, q in enumerate(questions):
        selected, correct = generate_normal_answer(q, ability + 0.1)
        if i < 15:
            time_spent = random.uniform(2, 5)
        else:
            time_spent = generate_time_normal(q) * random.uniform(1.2, 2.0)
        elapsed += time_spent
        conn.execute(
            "INSERT INTO answers (student_id, question_id, selected_option, is_correct, time_spent_seconds, answered_at) VALUES (?, ?, ?, ?, ?, ?)",
            (student_id, q['id'], selected, int(correct), round(time_spent, 2), exam_start + elapsed)
        )
    conn.commit()


def generate_ops_normal(conn, student_id, num_questions):
    """Normal student: 0-2 tab switches, jittery mouse."""
    exam_start = 1000000.0
    tab_count = random.randint(0, 2)
    for _ in range(tab_count):
        t = exam_start + random.uniform(60, 3000)
        dur = random.uniform(1, 5)
        conn.execute(
            "INSERT INTO operation_logs (student_id, event_type, timestamp, duration_seconds, metadata) VALUES (?, ?, ?, ?, ?)",
            (student_id, 'tab_switch', t, round(dur, 2), None)
        )

    # Mouse movements — jittery
    num_moves = random.randint(100, 300)
    x, y = 500.0, 400.0
    for k in range(num_moves):
        t = exam_start + (k * (3000.0 / num_moves)) + random.uniform(-2, 2)
        dx = random.gauss(0, 30)
        dy = random.gauss(0, 30)
        x = max(0, min(1200, x + dx))
        y = max(0, min(800, y + dy))
        conn.execute(
            "INSERT INTO operation_logs (student_id, event_type, timestamp, duration_seconds, metadata) VALUES (?, ?, ?, ?, ?)",
            (student_id, 'mouse_move', t, None, json.dumps({'x': round(x, 1), 'y': round(y, 1)}))
        )
    conn.commit()


def generate_ops_tab_heavy(conn, student_id):
    """Pair B cheater: many tab switches."""
    exam_start = 1000000.0
    tab_count = random.randint(8, 12)
    for _ in range(tab_count):
        t = exam_start + random.uniform(30, 2500)
        dur = random.uniform(10, 35)
        conn.execute(
            "INSERT INTO operation_logs (student_id, event_type, timestamp, duration_seconds, metadata) VALUES (?, ?, ?, ?, ?)",
            (student_id, 'tab_switch', t, round(dur, 2), None)
        )

    # Normal-ish mouse
    num_moves = random.randint(80, 200)
    x, y = 500.0, 400.0
    for k in range(num_moves):
        t = exam_start + (k * (3000.0 / num_moves))
        dx = random.gauss(0, 25)
        dy = random.gauss(0, 25)
        x = max(0, min(1200, x + dx))
        y = max(0, min(800, y + dy))
        conn.execute(
            "INSERT INTO operation_logs (student_id, event_type, timestamp, duration_seconds, metadata) VALUES (?, ?, ?, ?, ?)",
            (student_id, 'mouse_move', t, None, json.dumps({'x': round(x, 1), 'y': round(y, 1)}))
        )
    conn.commit()


def generate_ops_smooth_mouse(conn, student_id):
    """Karen: abnormally smooth mouse (remote control simulation)."""
    exam_start = 1000000.0
    tab_count = random.randint(1, 3)
    for _ in range(tab_count):
        t = exam_start + random.uniform(100, 2800)
        dur = random.uniform(2, 8)
        conn.execute(
            "INSERT INTO operation_logs (student_id, event_type, timestamp, duration_seconds, metadata) VALUES (?, ?, ?, ?, ?)",
            (student_id, 'tab_switch', t, round(dur, 2), None)
        )

    # Smooth, nearly linear mouse movements
    num_moves = 200
    x, y = 100.0, 100.0
    vx, vy = 3.0, 1.5
    for k in range(num_moves):
        t = exam_start + (k * 15.0)
        vx += random.gauss(0, 0.3)
        vy += random.gauss(0, 0.3)
        x = max(0, min(1200, x + vx))
        y = max(0, min(800, y + vy))
        if x <= 0 or x >= 1200:
            vx = -vx
        if y <= 0 or y >= 800:
            vy = -vy
        conn.execute(
            "INSERT INTO operation_logs (student_id, event_type, timestamp, duration_seconds, metadata) VALUES (?, ?, ?, ?, ?)",
            (student_id, 'mouse_move', t, None, json.dumps({'x': round(x, 1), 'y': round(y, 1)}))
        )
    conn.commit()


def seed():
    init_db()
    conn = get_conn()

    # Clear existing data
    for table in ['analysis_results', 'operation_logs', 'answers', 'students', 'questions', 'exams']:
        conn.execute(f"DELETE FROM {table}")
    conn.commit()

    # Create exam
    conn.execute(
        "INSERT INTO exams (name, duration_minutes, question_count) VALUES (?, ?, ?)",
        ("期中考试-数据结构", EXAM_DURATION_MINUTES, NUM_QUESTIONS)
    )
    conn.commit()
    exam_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Create questions
    questions = generate_questions(conn, exam_id)

    # Create students
    student_ids = []
    for i, name in enumerate(STUDENT_NAMES):
        conn.execute(
            "INSERT INTO students (exam_id, name, student_code) VALUES (?, ?, ?)",
            (exam_id, name, f"STU{i+1:03d}")
        )
        sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        student_ids.append(sid)
    conn.commit()

    abilities = [random.uniform(0.3, 0.85) for _ in range(NUM_STUDENTS)]

    # Generate answers
    # Pair A: Charlie(2) & Diana(3) — answer copying
    generate_answers_copy_pair(conn, student_ids[2], student_ids[3], questions, abilities[2], abilities[3])

    # Pair B: Grace(6) & Henry(7) — fast start
    generate_answers_fast_start(conn, student_ids[6], questions, abilities[6])
    generate_answers_fast_start(conn, student_ids[7], questions, abilities[7])

    # Normal students (skip 2,3,6,7)
    for i in range(NUM_STUDENTS):
        if i in (2, 3, 6, 7):
            continue
        generate_answers_normal(conn, student_ids[i], questions, abilities[i])

    # Generate operation logs
    for i in range(NUM_STUDENTS):
        if i in (6, 7):
            generate_ops_tab_heavy(conn, student_ids[i])
        elif i == 10:
            generate_ops_smooth_mouse(conn, student_ids[i])
        else:
            generate_ops_normal(conn, student_ids[i], NUM_QUESTIONS)

    # Update question difficulty based on actual accuracy
    for q in questions:
        row = conn.execute(
            "SELECT AVG(is_correct) as acc FROM answers WHERE question_id=?", (q['id'],)
        ).fetchone()
        accuracy = row['acc'] if row['acc'] is not None else 0.5
        conn.execute(
            "UPDATE questions SET difficulty=? WHERE id=?",
            (round(1 - accuracy, 3), q['id'])
        )
    conn.commit()
    conn.close()

    print(f"Seeded exam '{exam_id}' with {NUM_STUDENTS} students, {NUM_QUESTIONS} questions.")
    print("Cheater Pair A (answer copy): Charlie & Diana")
    print("Cheater Pair B (fast start + tab): Grace & Henry")
    print("Remote control (smooth mouse): Karen")


if __name__ == '__main__':
    seed()
