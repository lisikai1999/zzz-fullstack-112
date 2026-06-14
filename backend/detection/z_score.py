import numpy as np
from database import get_conn


def compute_z_scores(exam_id):
    conn = get_conn()

    questions = conn.execute(
        "SELECT id, question_number, correct_option, difficulty FROM questions WHERE exam_id=? ORDER BY question_number",
        (exam_id,)
    ).fetchall()

    students = conn.execute(
        "SELECT id, name FROM students WHERE exam_id=? ORDER BY id",
        (exam_id,)
    ).fetchall()

    student_ids = [s['id'] for s in students]
    student_names = {s['id']: s['name'] for s in students}

    # Build time matrix: (students x questions)
    time_matrix = np.full((len(student_ids), len(questions)), np.nan)

    for i, sid in enumerate(student_ids):
        rows = conn.execute(
            "SELECT question_id, time_spent_seconds FROM answers WHERE student_id=?",
            (sid,)
        ).fetchall()
        qid_to_idx = {q['id']: j for j, q in enumerate(questions)}
        for r in rows:
            if r['time_spent_seconds'] is not None and r['question_id'] in qid_to_idx:
                time_matrix[i, qid_to_idx[r['question_id']]] = r['time_spent_seconds']

    # Compute per-question stats
    results = {}
    for i, sid in enumerate(student_ids):
        results[sid] = {
            'student_id': sid,
            'name': student_names[sid],
            'flags': [],
            'z_scores': [],
            'indicators': {
                'instant_hard': 0,
                'slow_easy': 0,
                'consistent_fast': 0,
                'extreme_variance': 0.0,
            }
        }

    for j, q in enumerate(questions):
        col = time_matrix[:, j]
        valid = col[~np.isnan(col)]
        if len(valid) < 5:
            continue
        mu = np.mean(valid)
        sigma = np.std(valid)
        if sigma < 1.0:
            continue

        for i, sid in enumerate(student_ids):
            if np.isnan(time_matrix[i, j]):
                continue
            t = time_matrix[i, j]
            z = (t - mu) / sigma

            results[sid]['z_scores'].append({
                'question_number': q['question_number'],
                'z_score': round(float(z), 3),
                'time_spent': round(float(t), 2),
                'mean_time': round(float(mu), 2),
                'std_time': round(float(sigma), 2),
                'difficulty': q['difficulty']
            })

            if z < -2.0 and q['difficulty'] > 0.5:
                results[sid]['flags'].append({
                    'type': 'instant_hard',
                    'question': q['question_number'],
                    'z': round(float(z), 3),
                    'time_spent': round(float(t), 2)
                })
                results[sid]['indicators']['instant_hard'] += 1

            if z > 2.0 and q['difficulty'] < 0.35:
                results[sid]['flags'].append({
                    'type': 'slow_easy',
                    'question': q['question_number'],
                    'z': round(float(z), 3),
                    'time_spent': round(float(t), 2)
                })
                results[sid]['indicators']['slow_easy'] += 1

    # Compute summary indicators
    for sid, data in results.items():
        all_z = [x['z_score'] for x in data['z_scores']]
        if len(all_z) > 0:
            data['indicators']['consistent_fast'] = round(
                sum(1 for z in all_z if z < -1) / len(all_z), 3
            )
            data['indicators']['extreme_variance'] = round(float(np.std(all_z)), 3)

        # Composite time risk
        risk = (
            data['indicators']['instant_hard'] * 0.12 +
            data['indicators']['slow_easy'] * 0.08 +
            data['indicators']['consistent_fast'] * 0.45 +
            min(1.0, data['indicators']['extreme_variance'] / 3.0) * 0.35
        )
        data['time_risk_score'] = round(min(1.0, risk), 3)

    conn.close()

    result_list = sorted(results.values(), key=lambda x: -x['time_risk_score'])
    return result_list
