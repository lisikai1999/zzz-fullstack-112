from detection.k_index import compute_k_index
from detection.behavior import compute_behavior_scores
from detection.z_score import compute_z_scores


def compute_risk_scores(exam_id):
    k_data = compute_k_index(exam_id)
    behavior_data = compute_behavior_scores(exam_id)
    z_data = compute_z_scores(exam_id)

    # Index by student_id
    behavior_map = {b['student_id']: b for b in behavior_data}
    z_map = {z['student_id']: z for z in z_data}

    # Get max K-index per student
    k_max = {}
    for pair in k_data['pairs']:
        a = pair['student_a_id']
        b = pair['student_b_id']
        k_max[a] = max(k_max.get(a, 0), pair['k_index'])
        k_max[b] = max(k_max.get(b, 0), pair['k_index'])

    # All student IDs from behavior data (most complete)
    all_students = []
    for b in behavior_data:
        sid = b['student_id']
        k_val = k_max.get(sid, 0)
        k_normalized = min(1.0, k_val / 3.0)

        b_score = b['behavior_score']
        z_score_risk = z_map.get(sid, {}).get('time_risk_score', 0)

        base_risk = k_normalized * 0.4 + b_score * 0.3 + z_score_risk * 0.3

        flagged_paths = sum(1 for x in [k_normalized, b_score, z_score_risk] if x > 0.5)
        if flagged_paths >= 3:
            multiplier = 1.3
        elif flagged_paths >= 2:
            multiplier = 1.15
        else:
            multiplier = 1.0

        final_risk = min(1.0, base_risk * multiplier)

        if final_risk >= 0.7:
            level = 'high'
        elif final_risk >= 0.4:
            level = 'medium'
        else:
            level = 'low'

        all_students.append({
            'student_id': sid,
            'name': b['name'],
            'k_index_max': round(k_val, 3),
            'k_normalized': round(k_normalized, 3),
            'behavior_score': round(b_score, 3),
            'z_score_risk': round(z_score_risk, 3),
            'final_risk': round(final_risk, 3),
            'risk_level': level,
            'flagged_paths': flagged_paths
        })

    all_students.sort(key=lambda x: -x['final_risk'])

    return {
        'students': all_students,
        'suspect_pairs': k_data['pairs'][:10],
        'summary': {
            'high': sum(1 for s in all_students if s['risk_level'] == 'high'),
            'medium': sum(1 for s in all_students if s['risk_level'] == 'medium'),
            'low': sum(1 for s in all_students if s['risk_level'] == 'low'),
        }
    }
