from flask import Blueprint, jsonify
from database import get_conn

exams_bp = Blueprint('exams', __name__)


@exams_bp.route('/exams')
def list_exams():
    conn = get_conn()
    exams = conn.execute("SELECT * FROM exams ORDER BY id").fetchall()
    result = []
    for e in exams:
        student_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM students WHERE exam_id=?", (e['id'],)
        ).fetchone()['cnt']
        result.append({
            'id': e['id'],
            'name': e['name'],
            'created_at': e['created_at'],
            'duration_minutes': e['duration_minutes'],
            'question_count': e['question_count'],
            'student_count': student_count
        })
    conn.close()
    return jsonify(result)


@exams_bp.route('/exams/<int:exam_id>')
def get_exam(exam_id):
    conn = get_conn()
    exam = conn.execute("SELECT * FROM exams WHERE id=?", (exam_id,)).fetchone()
    if not exam:
        return jsonify({'error': 'Exam not found'}), 404

    student_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM students WHERE exam_id=?", (exam_id,)
    ).fetchone()['cnt']

    conn.close()
    return jsonify({
        'id': exam['id'],
        'name': exam['name'],
        'created_at': exam['created_at'],
        'duration_minutes': exam['duration_minutes'],
        'question_count': exam['question_count'],
        'student_count': student_count
    })


@exams_bp.route('/exams/<int:exam_id>/students')
def list_students(exam_id):
    conn = get_conn()
    students = conn.execute(
        "SELECT id, name, student_code FROM students WHERE exam_id=? ORDER BY id",
        (exam_id,)
    ).fetchall()
    conn.close()
    return jsonify([dict(s) for s in students])
