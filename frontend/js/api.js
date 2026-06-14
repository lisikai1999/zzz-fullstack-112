const API_BASE = 'http://localhost:5000/api';

const api = {
    async getExams() {
        const res = await fetch(`${API_BASE}/exams`);
        return res.json();
    },

    async getStudents(examId) {
        const res = await fetch(`${API_BASE}/exams/${examId}/students`);
        return res.json();
    },

    async getKIndex(examId) {
        const res = await fetch(`${API_BASE}/exams/${examId}/analysis/k-index`);
        return res.json();
    },

    async getBehavior(examId) {
        const res = await fetch(`${API_BASE}/exams/${examId}/analysis/behavior`);
        return res.json();
    },

    async getZScore(examId) {
        const res = await fetch(`${API_BASE}/exams/${examId}/analysis/z-score`);
        return res.json();
    },

    async getRiskScores(examId) {
        const res = await fetch(`${API_BASE}/exams/${examId}/analysis/risk-scores`);
        return res.json();
    },

    async getPairEvidence(examId, studentA, studentB) {
        const res = await fetch(`${API_BASE}/pairs/${examId}/${studentA}/${studentB}/evidence`);
        return res.json();
    },

    async getStudentEvidence(studentId) {
        const res = await fetch(`${API_BASE}/students/${studentId}/evidence`);
        return res.json();
    }
};
