async function showPairEvidenceById(examId, studentAId, studentBId) {
    const data = await api.getPairEvidence(examId, studentAId, studentBId);
    _renderCrossEvidence(data);
}

function _renderCrossEvidence(data) {
    const panel = document.getElementById('pair-evidence-panel');
    const title = document.getElementById('pair-evidence-title');
    const content = document.getElementById('pair-evidence-content');

    title.textContent = `${data.student_a.name} & ${data.student_b.name} — 三路交叉证据`;

    let html = '<div class="evidence-sections">';

    // === Section 1: Answer Path ===
    const ans = data.answer_path;
    html += `
    <div class="evidence-section">
        <h4 class="section-header answer-header">答案路径</h4>
        <div class="metrics-row">
            <div class="metric-card">
                <div class="value risk-high">${ans.summary.both_wrong_same_count}</div>
                <div class="label">相同错误选项</div>
            </div>
            <div class="metric-card">
                <div class="value">${ans.summary.same_answer_count}</div>
                <div class="label">答案一致数</div>
            </div>
            <div class="metric-card">
                <div class="value">${ans.summary.total_questions}</div>
                <div class="label">总题数</div>
            </div>
        </div>
        <div class="evidence-grid">`;
    for (const a of ans.answers) {
        let cls = 'different';
        let label = `Q${a.question_number}`;
        if (a.both_wrong_same) {
            cls = 'both-wrong-same';
            label += `:${a.student_a_option}`;
        } else if (a.student_a_correct && a.student_b_correct) {
            cls = 'both-correct';
        }
        html += `<div class="evidence-cell ${cls}" title="A选:${a.student_a_option} B选:${a.student_b_option} 正确:${a.correct_option}">${label}</div>`;
    }
    html += '</div></div>';

    // === Section 2: Operation Path ===
    const opA = data.operation_path.student_a;
    const opB = data.operation_path.student_b;
    html += `
    <div class="evidence-section">
        <h4 class="section-header behavior-header">操作路径</h4>
        <table class="compare-table">
            <thead><tr><th>指标</th><th>${data.student_a.name}</th><th>${data.student_b.name}</th></tr></thead>
            <tbody>
                <tr>
                    <td>切屏次数</td>
                    <td class="${_flagVal(opA?.tab_count, 5)}">${opA?.tab_count ?? '-'}</td>
                    <td class="${_flagVal(opB?.tab_count, 5)}">${opB?.tab_count ?? '-'}</td>
                </tr>
                <tr>
                    <td>离开总时长</td>
                    <td class="${_flagVal(opA?.total_away_seconds, 30)}">${opA?.total_away_seconds ? opA.total_away_seconds.toFixed(1) + 's' : '-'}</td>
                    <td class="${_flagVal(opB?.total_away_seconds, 30)}">${opB?.total_away_seconds ? opB.total_away_seconds.toFixed(1) + 's' : '-'}</td>
                </tr>
                <tr>
                    <td>节奏模式</td>
                    <td class="${opA?.rhythm_pattern !== 'normal' ? 'risk-high' : ''}">${opA ? patternLabel(opA.rhythm_pattern) : '-'}</td>
                    <td class="${opB?.rhythm_pattern !== 'normal' ? 'risk-high' : ''}">${opB ? patternLabel(opB.rhythm_pattern) : '-'}</td>
                </tr>
                <tr>
                    <td>前10题均时</td>
                    <td class="${_flagVal(10 - (opA?.first10_mean ?? 10), 2)}">${opA?.first10_mean != null ? opA.first10_mean.toFixed(1) + 's' : '-'}</td>
                    <td class="${_flagVal(10 - (opB?.first10_mean ?? 10), 2)}">${opB?.first10_mean != null ? opB.first10_mean.toFixed(1) + 's' : '-'}</td>
                </tr>
                <tr>
                    <td>后10题均时</td>
                    <td>${opA?.last10_mean != null ? opA.last10_mean.toFixed(1) + 's' : '-'}</td>
                    <td>${opB?.last10_mean != null ? opB.last10_mean.toFixed(1) + 's' : '-'}</td>
                </tr>
                <tr>
                    <td>鼠标异常Z值</td>
                    <td class="${_flagVal(opA?.mouse_z, 1.5)}">${opA?.mouse_z ?? '-'}</td>
                    <td class="${_flagVal(opB?.mouse_z, 1.5)}">${opB?.mouse_z ?? '-'}</td>
                </tr>
                <tr>
                    <td>行为综合分</td>
                    <td class="${_flagVal(opA?.behavior_score, 0.5)}">${opA?.behavior_score?.toFixed(3) ?? '-'}</td>
                    <td class="${_flagVal(opB?.behavior_score, 0.5)}">${opB?.behavior_score?.toFixed(3) ?? '-'}</td>
                </tr>
            </tbody>
        </table>`;

    // Mini rhythm comparison chart
    if (opA?.per_question_times?.length && opB?.per_question_times?.length) {
        html += '<div id="pair-rhythm-chart" class="chart-sm" style="margin-top:12px;"></div>';
    }
    html += '</div>';

    // === Section 3: Time Path ===
    const zA = data.time_path.student_a;
    const zB = data.time_path.student_b;
    html += `
    <div class="evidence-section">
        <h4 class="section-header time-header">时间路径</h4>
        <table class="compare-table">
            <thead><tr><th>指标</th><th>${data.student_a.name}</th><th>${data.student_b.name}</th></tr></thead>
            <tbody>
                <tr>
                    <td>时间风险分</td>
                    <td class="${_flagVal(zA?.time_risk_score, 0.4)}">${zA?.time_risk_score?.toFixed(3) ?? '-'}</td>
                    <td class="${_flagVal(zB?.time_risk_score, 0.4)}">${zB?.time_risk_score?.toFixed(3) ?? '-'}</td>
                </tr>
                <tr>
                    <td>秒选难题次数</td>
                    <td class="${_flagVal(zA?.indicators?.instant_hard, 2)}">${zA?.indicators?.instant_hard ?? '-'}</td>
                    <td class="${_flagVal(zB?.indicators?.instant_hard, 2)}">${zB?.indicators?.instant_hard ?? '-'}</td>
                </tr>
                <tr>
                    <td>犹豫简单题次数</td>
                    <td class="${_flagVal(zA?.indicators?.slow_easy, 2)}">${zA?.indicators?.slow_easy ?? '-'}</td>
                    <td class="${_flagVal(zB?.indicators?.slow_easy ?? 0, 2)}">${zB?.indicators?.slow_easy ?? '-'}</td>
                </tr>
                <tr>
                    <td>持续快速比例</td>
                    <td class="${_flagVal(zA?.indicators?.consistent_fast, 0.3)}">${zA?.indicators?.consistent_fast?.toFixed(3) ?? '-'}</td>
                    <td class="${_flagVal(zB?.indicators?.consistent_fast, 0.3)}">${zB?.indicators?.consistent_fast?.toFixed(3) ?? '-'}</td>
                </tr>
                <tr>
                    <td>异常标记数</td>
                    <td class="${_flagVal(zA?.flag_count, 3)}">${zA?.flag_count ?? 0}</td>
                    <td class="${_flagVal(zB?.flag_count, 3)}">${zB?.flag_count ?? 0}</td>
                </tr>
            </tbody>
        </table>
    </div>`;

    html += '</div>';
    content.innerHTML = html;
    panel.style.display = 'block';

    // Render mini rhythm comparison chart if data available
    if (opA?.per_question_times?.length && opB?.per_question_times?.length) {
        setTimeout(() => _renderPairRhythmChart(opA, opB, data.student_a.name, data.student_b.name), 100);
    }
}

function _flagVal(val, threshold) {
    if (val == null) return '';
    return val >= threshold ? 'risk-high' : '';
}

function _renderPairRhythmChart(opA, opB, nameA, nameB) {
    const dom = document.getElementById('pair-rhythm-chart');
    if (!dom) return;
    const chart = echarts.init(dom);

    const qLabels = opA.per_question_times.map(q => 'Q' + q.question);
    const timesA = opA.per_question_times.map(q => q.time);
    const timesB = opB.per_question_times.map(q => q.time);

    chart.setOption({
        tooltip: { trigger: 'axis' },
        legend: { data: [nameA, nameB], bottom: 0 },
        grid: { left: 50, right: 20, top: 20, bottom: 40 },
        xAxis: { type: 'category', data: qLabels, axisLabel: { fontSize: 9, interval: 4 } },
        yAxis: { type: 'value', name: '秒' },
        series: [
            { name: nameA, type: 'line', data: timesA, smooth: true, lineStyle: { width: 1.5 }, symbol: 'none' },
            { name: nameB, type: 'line', data: timesB, smooth: true, lineStyle: { width: 1.5 }, symbol: 'none' }
        ]
    });
}
