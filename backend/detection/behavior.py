import json
import math
import numpy as np
from database import get_conn


def compute_behavior_scores(exam_id):
    conn = get_conn()
    students = conn.execute(
        "SELECT id, name, student_code FROM students WHERE exam_id=? ORDER BY id",
        (exam_id,)
    ).fetchall()

    # First pass: collect all mouse angle means for baseline computation
    raw_results = []
    all_mouse_angles = []
    for student in students:
        score = _analyze_student(conn, student['id'])
        score['student_id'] = student['id']
        score['name'] = student['name']
        raw_results.append(score)
        if score['_mouse_mean_angle'] is not None:
            all_mouse_angles.append(score['_mouse_mean_angle'])

    # Second pass: compute mouse score relative to cohort baseline
    if len(all_mouse_angles) >= 5:
        baseline_mean = float(np.mean(all_mouse_angles))
        baseline_std = float(np.std(all_mouse_angles))
    else:
        baseline_mean = 45.0
        baseline_std = 15.0

    for r in raw_results:
        angle = r['_mouse_mean_angle']
        if angle is not None and baseline_std > 1.0:
            z_smooth = (baseline_mean - angle) / baseline_std
            if z_smooth > 2.5:
                r['mouse_score'] = 0.9
            elif z_smooth > 1.8:
                r['mouse_score'] = 0.7
            elif z_smooth > 1.2:
                r['mouse_score'] = 0.45
            elif z_smooth > 0.5:
                r['mouse_score'] = 0.2
            else:
                r['mouse_score'] = 0.05
            r['mouse_z'] = round(z_smooth, 3)
        else:
            r['mouse_score'] = 0.0
            r['mouse_z'] = 0.0

        r['behavior_score'] = round(
            r['tab_score'] * 0.4 + r['rhythm_score'] * 0.35 + r['mouse_score'] * 0.25, 3
        )
        r['mouse_score'] = round(r['mouse_score'], 3)
        r['mouse_baseline_mean'] = round(baseline_mean, 2)
        r['mouse_baseline_std'] = round(baseline_std, 2)
        del r['_mouse_mean_angle']

    conn.close()
    raw_results.sort(key=lambda x: -x['behavior_score'])
    return raw_results


def _analyze_student(conn, student_id):
    logs = conn.execute(
        "SELECT event_type, timestamp, duration_seconds, metadata FROM operation_logs WHERE student_id=? ORDER BY timestamp",
        (student_id,)
    ).fetchall()

    answers = conn.execute(
        "SELECT a.time_spent_seconds, q.question_number, a.answered_at FROM answers a "
        "JOIN questions q ON a.question_id = q.id "
        "WHERE a.student_id=? ORDER BY q.question_number",
        (student_id,)
    ).fetchall()

    # --- Tab Switch Score ---
    tab_switches = [l for l in logs if l['event_type'] == 'tab_switch']
    tab_count = len(tab_switches)
    total_away = sum(l['duration_seconds'] or 0 for l in tab_switches)
    tab_score = min(1.0, (tab_count / 5) * 0.5 + (total_away / 60) * 0.5)

    # --- Rhythm Score: precise first-10/last-10 pattern matching ---
    times = [a['time_spent_seconds'] for a in answers if a['time_spent_seconds'] is not None]
    rhythm_score = 0.0
    rhythm_pattern = 'normal'
    first10_mean = None
    last10_mean = None
    per_question_times = []

    if len(times) >= 20:
        first10 = times[:10]
        last10 = times[-10:]
        middle = times[10:-10] if len(times) > 20 else []
        first10_mean = float(np.mean(first10))
        last10_mean = float(np.mean(last10))
        overall_mean = float(np.mean(times))

        # Pattern: "先查后答" — first 10 questions answered in <8s avg, last 10 > 35s avg
        first10_fast = sum(1 for t in first10 if t < 8)
        last10_slow = sum(1 for t in last10 if t > 30)

        if first10_mean < 8 and last10_mean > 35 and first10_fast >= 7:
            rhythm_score = 0.95
            rhythm_pattern = 'lookup_then_answer'
        elif first10_mean < 12 and last10_mean > 30 and first10_fast >= 5:
            rhythm_score = 0.75
            rhythm_pattern = 'likely_lookup'
        elif last10_mean < 8 and first10_mean > 35:
            rhythm_score = 0.65
            rhythm_pattern = 'shared_midway'
        else:
            # Fallback: check for abrupt rhythm change at any point
            max_ratio = 0
            for split in range(8, len(times) - 8):
                seg_a = np.mean(times[:split])
                seg_b = np.mean(times[split:])
                if seg_b > 1:
                    ratio = seg_a / seg_b
                    if ratio < 1:
                        ratio = 1 / ratio
                    max_ratio = max(max_ratio, ratio)
            if max_ratio > 4:
                rhythm_score = 0.6
                rhythm_pattern = 'abrupt_change'
            else:
                cv = np.std(times) / max(overall_mean, 1)
                rhythm_score = min(0.4, cv / 3.0)
    elif len(times) > 5:
        cv = np.std(times) / max(np.mean(times), 1)
        rhythm_score = min(0.3, cv / 3.0)

    # Build per-question time list for timeline visualization
    for a in answers:
        if a['time_spent_seconds'] is not None:
            per_question_times.append({
                'question': a['question_number'],
                'time': round(a['time_spent_seconds'], 2)
            })

    # --- Mouse Smoothness: compute raw mean angle, scoring deferred to cohort pass ---
    mouse_events = [l for l in logs if l['event_type'] == 'mouse_move']
    mouse_mean_angle = None
    mouse_angle_std = None
    if len(mouse_events) > 20:
        points = []
        for m in mouse_events:
            if m['metadata']:
                data = json.loads(m['metadata'])
                points.append((data['x'], data['y']))

        if len(points) > 20:
            angles = []
            for k in range(2, len(points)):
                angle = _compute_angle(points[k-2], points[k-1], points[k])
                if angle is not None:
                    angles.append(angle)
            if angles:
                mouse_mean_angle = float(np.mean(angles))
                mouse_angle_std = float(np.std(angles))

    # Build timeline data with richer structure
    timeline_events = []
    for l in logs:
        entry = {
            'event_type': l['event_type'],
            'timestamp': l['timestamp'],
            'duration': l['duration_seconds']
        }
        if l['metadata']:
            entry['metadata'] = json.loads(l['metadata'])
        timeline_events.append(entry)

    return {
        'tab_score': round(tab_score, 3),
        'tab_count': tab_count,
        'total_away_seconds': round(total_away, 1),
        'rhythm_score': round(rhythm_score, 3),
        'rhythm_pattern': rhythm_pattern,
        'first10_mean': round(first10_mean, 2) if first10_mean is not None else None,
        'last10_mean': round(last10_mean, 2) if last10_mean is not None else None,
        'per_question_times': per_question_times,
        'mouse_score': 0.0,
        'mouse_z': 0.0,
        '_mouse_mean_angle': mouse_mean_angle,
        'mouse_angle_mean': round(mouse_mean_angle, 2) if mouse_mean_angle is not None else None,
        'mouse_angle_std': round(mouse_angle_std, 2) if mouse_angle_std is not None else None,
        'behavior_score': 0.0,
        'timeline': timeline_events
    }


def _compute_angle(p0, p1, p2):
    v1 = (p1[0] - p0[0], p1[1] - p0[1])
    v2 = (p2[0] - p1[0], p2[1] - p1[1])
    mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
    mag2 = math.sqrt(v2[0]**2 + v2[1]**2)
    if mag1 < 0.001 or mag2 < 0.001:
        return None
    cos_angle = (v1[0]*v2[0] + v1[1]*v2[1]) / (mag1 * mag2)
    cos_angle = max(-1, min(1, cos_angle))
    return math.degrees(math.acos(cos_angle))
