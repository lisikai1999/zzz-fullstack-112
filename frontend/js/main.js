let currentExamId = null;

document.addEventListener('DOMContentLoaded', async () => {
    // Load exams
    const exams = await api.getExams();
    const select = document.getElementById('exam-select');
    for (const exam of exams) {
        const opt = document.createElement('option');
        opt.value = exam.id;
        opt.textContent = `${exam.name} (${exam.student_count}人)`;
        select.appendChild(opt);
    }

    if (exams.length > 0) {
        select.value = exams[0].id;
        loadExam(exams[0].id);
    }

    select.addEventListener('change', () => {
        if (select.value) loadExam(parseInt(select.value));
    });

    // Tab navigation
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById(tab.dataset.tab).classList.add('active');

            // Resize charts on tab switch
            setTimeout(() => {
                if (heatmapChart) heatmapChart.resize();
                if (timelineChart) timelineChart.resize();
                if (radarChart) radarChart.resize();
            }, 50);
        });
    });

    // Behavior student selector
    document.getElementById('behavior-student-select').addEventListener('change', (e) => {
        if (e.target.value) renderBehaviorForStudent(e.target.value);
    });

    // Z-score student selector
    document.getElementById('zscore-student-select').addEventListener('change', (e) => {
        if (e.target.value) renderRadarForStudent(e.target.value);
    });
});

async function loadExam(examId) {
    currentExamId = examId;
    await Promise.all([
        loadDashboard(examId),
        renderHeatmap(examId),
        loadBehaviorData(examId),
        loadZScoreData(examId)
    ]);
}

async function loadDashboard(examId) {
    const data = await api.getRiskScores(examId);

    // Risk pie
    renderRiskPie(data.summary);

    // Top suspects
    renderTopSuspects(data.students.slice(0, 8));

    // Risk table
    renderRiskTable(data.students);
}

function renderRiskPie(summary) {
    const dom = document.getElementById('risk-pie');
    const chart = echarts.init(dom);

    const option = {
        tooltip: { trigger: 'item' },
        series: [{
            type: 'pie',
            radius: ['40%', '70%'],
            data: [
                { value: summary.high, name: '高风险', itemStyle: { color: '#d32f2f' } },
                { value: summary.medium, name: '中风险', itemStyle: { color: '#f57c00' } },
                { value: summary.low, name: '低风险', itemStyle: { color: '#388e3c' } }
            ],
            label: { formatter: '{b}: {c}人' }
        }]
    };

    chart.setOption(option);
    window.addEventListener('resize', () => chart.resize());
}

function renderTopSuspects(students) {
    const container = document.getElementById('top-suspects');
    container.innerHTML = '';

    for (const s of students) {
        const div = document.createElement('div');
        div.className = 'suspect-item';
        div.innerHTML = `
            <span class="suspect-name">${s.name}</span>
            <span class="suspect-score risk-${s.risk_level}">${(s.final_risk * 100).toFixed(1)}%</span>
        `;
        container.appendChild(div);
    }
}

function renderRiskTable(students) {
    const tbody = document.querySelector('#risk-table tbody');
    tbody.innerHTML = '';

    for (const s of students) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${s.name}</strong></td>
            <td>${s.k_index_max.toFixed(3)}</td>
            <td>${s.behavior_score.toFixed(3)}</td>
            <td>${s.z_score_risk.toFixed(3)}</td>
            <td><strong>${(s.final_risk * 100).toFixed(1)}%</strong></td>
            <td class="risk-${s.risk_level}">${levelLabel(s.risk_level)}</td>
        `;
        tbody.appendChild(tr);
    }
}

function levelLabel(level) {
    const labels = { high: '高', medium: '中', low: '低' };
    return labels[level] || level;
}
