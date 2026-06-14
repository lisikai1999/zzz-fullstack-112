import numpy as np
from database import get_conn


def compute_k_index(exam_id):
    conn = get_conn()

    questions = conn.execute(
        "SELECT id, question_number, correct_option, difficulty FROM questions WHERE exam_id=? ORDER BY question_number",
        (exam_id,)
    ).fetchall()

    students = conn.execute(
        "SELECT id, name, student_code FROM students WHERE exam_id=? ORDER BY id",
        (exam_id,)
    ).fetchall()

    if not questions or not students:
        return {'pairs': [], 'matrix': []}

    student_ids = [s['id'] for s in students]
    question_ids = [q['id'] for q in questions]
    correct_options = {q['id']: q['correct_option'] for q in questions}
    num_options = 4

    # Build answer matrix: (num_students x num_questions), value = selected option index (0-3), -1 if null
    option_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
    answer_matrix = np.full((len(student_ids), len(question_ids)), -1, dtype=np.int8)
    correct_vector = np.array([option_map[correct_options[qid]] for qid in question_ids], dtype=np.int8)

    for idx, sid in enumerate(student_ids):
        rows = conn.execute(
            "SELECT question_id, selected_option FROM answers WHERE student_id=? ORDER BY question_id",
            (sid,)
        ).fetchall()
        for r in rows:
            qidx = question_ids.index(r['question_id'])
            if r['selected_option'] and r['selected_option'] in option_map:
                answer_matrix[idx, qidx] = option_map[r['selected_option']]

    # Filter out easy questions (accuracy >= 0.8)
    accuracy = np.array([
        np.mean(answer_matrix[:, j] == correct_vector[j]) for j in range(len(question_ids))
    ])
    non_trivial_mask = accuracy < 0.80
    filtered_matrix = answer_matrix[:, non_trivial_mask]
    filtered_correct = correct_vector[non_trivial_mask]

    # For each pair, compute K-index
    n_students = len(student_ids)
    pairs = []

    for i in range(n_students):
        for j in range(i + 1, n_students):
            ans_i = filtered_matrix[i]
            ans_j = filtered_matrix[j]

            both_wrong = (ans_i != filtered_correct) & (ans_j != filtered_correct) & (ans_i >= 0) & (ans_j >= 0)
            total_both_wrong = int(np.sum(both_wrong))

            if total_both_wrong == 0:
                continue

            same_wrong = both_wrong & (ans_i == ans_j)
            shared_wrong_count = int(np.sum(same_wrong))

            expected = total_both_wrong / (num_options - 1)
            k_index = shared_wrong_count / max(expected, 0.001)

            if k_index > 1.5 and shared_wrong_count >= 3:
                # Get details of shared wrong answers
                shared_questions = []
                non_trivial_indices = np.where(non_trivial_mask)[0]
                same_wrong_positions = np.where(same_wrong)[0]
                for pos in same_wrong_positions:
                    orig_idx = non_trivial_indices[pos]
                    qnum = questions[orig_idx]['question_number']
                    opt = ['A', 'B', 'C', 'D'][ans_i[pos]]
                    shared_questions.append({'question': qnum, 'selected': opt})

                pairs.append({
                    'student_a_id': student_ids[i],
                    'student_b_id': student_ids[j],
                    'student_a_name': students[i]['name'],
                    'student_b_name': students[j]['name'],
                    'k_index': round(k_index, 3),
                    'shared_wrong': shared_wrong_count,
                    'total_both_wrong': total_both_wrong,
                    'expected_by_chance': round(expected, 2),
                    'shared_questions': shared_questions
                })

    pairs.sort(key=lambda x: -x['k_index'])

    # Build heatmap matrix (all pairs, not just flagged)
    heatmap = []
    for i in range(n_students):
        for j in range(i + 1, n_students):
            ans_i = filtered_matrix[i]
            ans_j = filtered_matrix[j]
            both_wrong = (ans_i != filtered_correct) & (ans_j != filtered_correct) & (ans_i >= 0) & (ans_j >= 0)
            total_both_wrong = int(np.sum(both_wrong))
            if total_both_wrong == 0:
                k = 0
            else:
                same_wrong = both_wrong & (ans_i == ans_j)
                k = int(np.sum(same_wrong)) / max(total_both_wrong / (num_options - 1), 0.001)
            heatmap.append([i, j, round(k, 3)])

    conn.close()
    return {
        'pairs': pairs,
        'matrix': heatmap,
        'student_names': [s['name'] for s in students],
        'non_trivial_count': int(np.sum(non_trivial_mask)),
        'total_questions': len(question_ids)
    }


def get_pair_evidence(exam_id, student_a_id, student_b_id):
    conn = get_conn()
    questions = conn.execute(
        "SELECT id, question_number, correct_option FROM questions WHERE exam_id=? ORDER BY question_number",
        (exam_id,)
    ).fetchall()

    evidence = []
    for q in questions:
        ans_a = conn.execute(
            "SELECT selected_option, time_spent_seconds FROM answers WHERE student_id=? AND question_id=?",
            (student_a_id, q['id'])
        ).fetchone()
        ans_b = conn.execute(
            "SELECT selected_option, time_spent_seconds FROM answers WHERE student_id=? AND question_id=?",
            (student_b_id, q['id'])
        ).fetchone()

        if ans_a and ans_b:
            a_correct = ans_a['selected_option'] == q['correct_option']
            b_correct = ans_b['selected_option'] == q['correct_option']
            evidence.append({
                'question_number': q['question_number'],
                'correct_option': q['correct_option'],
                'student_a_option': ans_a['selected_option'],
                'student_b_option': ans_b['selected_option'],
                'student_a_correct': a_correct,
                'student_b_correct': b_correct,
                'same_answer': ans_a['selected_option'] == ans_b['selected_option'],
                'both_wrong_same': (not a_correct and not b_correct and ans_a['selected_option'] == ans_b['selected_option']),
                'student_a_time': ans_a['time_spent_seconds'],
                'student_b_time': ans_b['time_spent_seconds']
            })

    conn.close()
    return evidence
