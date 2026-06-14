from flask import Blueprint, jsonify
from detection.k_index import get_pair_evidence
from detection.behavior import compute_behavior_scores
from detection.z_score import compute_z_scores
from database import get_conn

evidence_bp = Blueprint('evidence', __name__)


@evidence_bp.route('/pairs/<int:exam_id>/<int:student_a>/<int:student_b>/evidence')
def pair_evidence(exam_id, student_a, student_b):
    conn = get_conn()
    name_a = conn.execute("SELECT name FROM students WHERE id=?", (student_a,)).fetchone()
    name_b = conn.execute("SELECT name FROM students WHERE id=?", (student_b,)).fetchone()
    conn.close()

    # === Answer Path evidence ===
    answer_evidence = get_pair_evidence(exam_id, student_a, student_b)

    # === Operation Path evidence for both students ===
    behavior_all = compute_behavior_scores(exam_id)
    behavior_a = next((b for b in behavior_all if b['student_id'] == student_a), None)
    behavior_b = next((b for b in behavior_all if b['student_id'] == student_b), None)

    # === Time Path evidence for both students ===
    z_all = compute_z_scores(exam_id)
    z_a = next((z for z in z_all if z['student_id'] == student_a), None)
    z_b = next((z for z in z_all if z['student_id'] == student_b), None)

    # Build cross-evidence summary
    def _behavior_brief(b):
        if not b:
            return None
        return {
            'tab_count': b['tab_count'],
            'total_away_seconds': b['total_away_seconds'],
            'tab_score': b['tab_score'],
            'rhythm_score': b['rhythm_score'],
            'rhythm_pattern': b['rhythm_pattern'],
            'first10_mean': b['first10_mean'],
            'last10_mean': b['last10_mean'],
            'mouse_score': b['mouse_score'],
            'mouse_z': b['mouse_z'],
            'mouse_angle_mean': b['mouse_angle_mean'],
            'behavior_score': b['behavior_score'],
            'per_question_times': b['per_question_times'],
        }

    def _zscore_brief(z):
        if not z:
            return None
        return {
            'time_risk_score': z['time_risk_score'],
            'indicators': z['indicators'],
            'flags': z['flags'][:10],
            'flag_count': len(z['flags']),
        }

    return jsonify({
        'student_a': {'id': student_a, 'name': name_a['name'] if name_a else ''},
        'student_b': {'id': student_b, 'name': name_b['name'] if name_b else ''},
        'answer_path': {
            'answers': answer_evidence,
            'summary': {
                'total_questions': len(answer_evidence),
                'same_answer_count': sum(1 for e in answer_evidence if e['same_answer']),
                'both_wrong_same_count': sum(1 for e in answer_evidence if e['both_wrong_same']),
            }
        },
        'operation_path': {
            'student_a': _behavior_brief(behavior_a),
            'student_b': _behavior_brief(behavior_b),
        },
        'time_path': {
            'student_a': _zscore_brief(z_a),
            'student_b': _zscore_brief(z_b),
        }
    })


@evidence_bp.route('/students/<int:student_id>/evidence')
def student_evidence(student_id):
    conn = get_conn()
    student = conn.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    exam_id = student['exam_id']
    conn.close()

    behavior_all = compute_behavior_scores(exam_id)
    behavior = next((b for b in behavior_all if b['student_id'] == student_id), None)

    z_all = compute_z_scores(exam_id)
    z_data = next((z for z in z_all if z['student_id'] == student_id), None)

    return jsonify({
        'student': {'id': student_id, 'name': student['name'], 'code': student['student_code']},
        'behavior': behavior,
        'z_score': z_data
    })
