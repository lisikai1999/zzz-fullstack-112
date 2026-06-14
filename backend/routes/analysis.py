from flask import Blueprint, jsonify
from detection.k_index import compute_k_index
from detection.behavior import compute_behavior_scores
from detection.z_score import compute_z_scores
from detection.risk_score import compute_risk_scores

analysis_bp = Blueprint('analysis', __name__)


@analysis_bp.route('/exams/<int:exam_id>/analysis/k-index')
def get_k_index(exam_id):
    result = compute_k_index(exam_id)
    return jsonify(result)


@analysis_bp.route('/exams/<int:exam_id>/analysis/behavior')
def get_behavior(exam_id):
    result = compute_behavior_scores(exam_id)
    return jsonify(result)


@analysis_bp.route('/exams/<int:exam_id>/analysis/z-score')
def get_z_score(exam_id):
    result = compute_z_scores(exam_id)
    return jsonify(result)


@analysis_bp.route('/exams/<int:exam_id>/analysis/risk-scores')
def get_risk_scores(exam_id):
    result = compute_risk_scores(exam_id)
    return jsonify(result)
