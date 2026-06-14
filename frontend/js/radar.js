let radarChart = null;
let zScoreData = null;

function initRadar() {
    const dom = document.getElementById('radar-chart');
    if (!dom) return;
    radarChart = echarts.init(dom);
    window.addEventListener('resize', () => radarChart && radarChart.resize());
}

async function loadZScoreData(examId) {
    zScoreData = await api.getZScore(examId);

    const select = document.getElementById('zscore-student-select');
    select.innerHTML = '<option value="">选择考生...</option>';
    for (const s of zScoreData) {
        const opt = document.createElement('option');
        opt.value = s.student_id;
        opt.textContent = `${s.name} (时间风险: ${s.time_risk_score.toFixed(3)})`;
        select.appendChild(opt);
    }
}

function renderRadarForStudent(studentId) {
    if (!zScoreData) return;
    const student = zScoreData.find(s => s.student_id === parseInt(studentId));
    if (!student) return;

    if (!radarChart) initRadar();

    const indicators = student.indicators;

    // Compute class averages
    const avgIndicators = {
        instant_hard: 0,
        slow_easy: 0,
        consistent_fast: 0,
        extreme_variance: 0
    };
    for (const s of zScoreData) {
        avgIndicators.instant_hard += s.indicators.instant_hard;
        avgIndicators.slow_easy += s.indicators.slow_easy;
        avgIndicators.consistent_fast += s.indicators.consistent_fast;
        avgIndicators.extreme_variance += s.indicators.extreme_variance;
    }
    const n = zScoreData.length;
    avgIndicators.instant_hard /= n;
    avgIndicators.slow_easy /= n;
    avgIndicators.consistent_fast /= n;
    avgIndicators.extreme_variance /= n;

    const maxVals = [
        Math.max(5, indicators.instant_hard, avgIndicators.instant_hard * 2),
        Math.max(5, indicators.slow_easy, avgIndicators.slow_easy * 2),
        Math.max(1, indicators.consistent_fast, avgIndicators.consistent_fast * 2),
        Math.max(2, indicators.extreme_variance, avgIndicators.extreme_variance * 2),
        1
    ];

    const option = {
        tooltip: {},
        legend: { data: [student.name, '班级平均'], bottom: 0 },
        radar: {
            indicator: [
                { name: '秒选难题', max: maxVals[0] },
                { name: '犹豫简单题', max: maxVals[1] },
                { name: '持续快速', max: maxVals[2] },
                { name: '时间波动', max: maxVals[3] },
                { name: '综合风险', max: maxVals[4] }
            ],
            shape: 'polygon',
            splitNumber: 4
        },
        series: [{
            type: 'radar',
            data: [
                {
                    name: student.name,
                    value: [
                        indicators.instant_hard,
                        indicators.slow_easy,
                        indicators.consistent_fast,
                        indicators.extreme_variance,
                        student.time_risk_score
                    ],
                    itemStyle: { color: '#e53935' },
                    areaStyle: { opacity: 0.3 }
                },
                {
                    name: '班级平均',
                    value: [
                        avgIndicators.instant_hard,
                        avgIndicators.slow_easy,
                        avgIndicators.consistent_fast,
                        avgIndicators.extreme_variance,
                        zScoreData.reduce((s, x) => s + x.time_risk_score, 0) / n
                    ],
                    itemStyle: { color: '#90a4ae' },
                    areaStyle: { opacity: 0.1 },
                    lineStyle: { type: 'dashed' }
                }
            ]
        }]
    };

    radarChart.setOption(option, true);

    renderFlagsTable(student);
}

function renderFlagsTable(student) {
    const tbody = document.querySelector('#flags-table tbody');
    tbody.innerHTML = '';

    const flags = student.flags || [];
    if (flags.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#999;">无异常标记</td></tr>';
        return;
    }

    const typeLabels = {
        'instant_hard': '秒选难题',
        'slow_easy': '犹豫简单题'
    };

    for (const flag of flags) {
        const zEntry = student.z_scores.find(z => z.question_number === flag.question);
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>Q${flag.question}</td>
            <td>${zEntry ? zEntry.difficulty.toFixed(3) : '-'}</td>
            <td>${flag.time_spent.toFixed(1)}</td>
            <td>${zEntry ? zEntry.mean_time.toFixed(1) : '-'}</td>
            <td class="${Math.abs(flag.z) > 2 ? 'risk-high' : ''}">${flag.z.toFixed(3)}</td>
            <td>${typeLabels[flag.type] || flag.type}</td>
        `;
        tbody.appendChild(tr);
    }
}
