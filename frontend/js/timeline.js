let timelineChart = null;
let behaviorData = null;

function initTimeline() {
    const dom = document.getElementById('timeline-chart');
    if (!dom) return;
    timelineChart = echarts.init(dom);
    window.addEventListener('resize', () => timelineChart && timelineChart.resize());
}

async function loadBehaviorData(examId) {
    behaviorData = await api.getBehavior(examId);

    const select = document.getElementById('behavior-student-select');
    select.innerHTML = '<option value="">选择考生...</option>';
    for (const s of behaviorData) {
        const label = s.rhythm_pattern !== 'normal' ? ` [${patternLabel(s.rhythm_pattern)}]` : '';
        const opt = document.createElement('option');
        opt.value = s.student_id;
        opt.textContent = `${s.name} (行为分: ${s.behavior_score.toFixed(3)})${label}`;
        select.appendChild(opt);
    }
}

function patternLabel(p) {
    const m = {
        'lookup_then_answer': '先查后答',
        'likely_lookup': '疑似先查',
        'shared_midway': '中途获取答案',
        'abrupt_change': '节奏突变',
        'normal': '正常'
    };
    return m[p] || p;
}

function renderBehaviorForStudent(studentId) {
    if (!behaviorData) return;
    const student = behaviorData.find(s => s.student_id === parseInt(studentId));
    if (!student) return;

    renderMetrics(student);
    renderTimeline(student);
}

function renderMetrics(student) {
    const container = document.getElementById('behavior-metrics');
    const patternClass = student.rhythm_pattern !== 'normal' ? 'risk-high' : '';
    container.innerHTML = `
        <div class="metric-card">
            <div class="value">${student.tab_count}</div>
            <div class="label">切屏次数</div>
        </div>
        <div class="metric-card">
            <div class="value">${student.total_away_seconds.toFixed(1)}s</div>
            <div class="label">离开总时长</div>
        </div>
        <div class="metric-card">
            <div class="value ${patternClass}">${patternLabel(student.rhythm_pattern)}</div>
            <div class="label">节奏模式</div>
        </div>
        <div class="metric-card">
            <div class="value">${student.first10_mean !== null ? student.first10_mean.toFixed(1) + 's' : '-'}</div>
            <div class="label">前10题均时</div>
        </div>
        <div class="metric-card">
            <div class="value">${student.last10_mean !== null ? student.last10_mean.toFixed(1) + 's' : '-'}</div>
            <div class="label">后10题均时</div>
        </div>
        <div class="metric-card">
            <div class="value">${student.mouse_score.toFixed(3)}</div>
            <div class="label">鼠标异常(Z=${student.mouse_z})</div>
        </div>
    `;
}

function renderTimeline(student) {
    if (!timelineChart) initTimeline();

    const timeline = student.timeline;
    const perQ = student.per_question_times || [];

    if (!timeline || timeline.length === 0) {
        timelineChart.clear();
        return;
    }

    // === Build answer rhythm bar chart (per question time) ===
    const questionNums = perQ.map(q => 'Q' + q.question);
    const questionTimes = perQ.map(q => q.time);

    // Color bars: first 10 green, last 10 orange, middle gray
    // Highlight the rhythm change
    const barColors = perQ.map((q, i) => {
        if (i < 10) return '#4caf50';
        if (i >= perQ.length - 10) return '#ff9800';
        return '#90a4ae';
    });

    // === Build tab switch gantt-style bars ===
    const minTime = timeline.length > 0 ? Math.min(...timeline.map(t => t.timestamp)) : 0;
    const tabBars = [];
    for (const event of timeline) {
        if (event.event_type === 'tab_switch' && event.duration) {
            const startMin = (event.timestamp - minTime) / 60;
            tabBars.push({
                start: startMin,
                duration: event.duration,
                durationMin: event.duration / 60
            });
        }
    }

    const option = {
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' }
        },
        grid: [
            { left: 60, right: 30, top: 40, height: '45%' },
            { left: 60, right: 30, top: '65%', height: '25%' }
        ],
        xAxis: [
            {
                type: 'category',
                data: questionNums,
                gridIndex: 0,
                axisLabel: { fontSize: 9, interval: 4 },
                name: '题号'
            },
            {
                type: 'value',
                gridIndex: 1,
                name: '考试时间(分钟)',
                nameLocation: 'center',
                nameGap: 25,
                max: Math.max(50, ...tabBars.map(t => t.start + t.durationMin)) + 2
            }
        ],
        yAxis: [
            {
                type: 'value',
                gridIndex: 0,
                name: '答题用时(秒)',
                nameLocation: 'center',
                nameGap: 35
            },
            {
                type: 'category',
                gridIndex: 1,
                data: ['切屏'],
                axisLine: { show: false },
                axisTick: { show: false }
            }
        ],
        series: [
            {
                name: '答题用时',
                type: 'bar',
                xAxisIndex: 0,
                yAxisIndex: 0,
                data: questionTimes.map((t, i) => ({
                    value: t,
                    itemStyle: { color: barColors[i] }
                })),
                markLine: {
                    silent: true,
                    symbol: 'none',
                    lineStyle: { type: 'dashed', color: '#f44336' },
                    data: [
                        { xAxis: 9, label: { formatter: '←前10题', position: 'start', fontSize: 10 } },
                        { xAxis: perQ.length - 11, label: { formatter: '后10题→', position: 'end', fontSize: 10 } }
                    ]
                }
            },
            {
                name: '切屏',
                type: 'custom',
                xAxisIndex: 1,
                yAxisIndex: 1,
                renderItem: function(params, api) {
                    const bar = tabBars[params.dataIndex];
                    if (!bar) return;
                    const startCoord = api.coord([bar.start, 0]);
                    const endCoord = api.coord([bar.start + bar.durationMin, 0]);
                    const height = 20;
                    return {
                        type: 'rect',
                        shape: {
                            x: startCoord[0],
                            y: startCoord[1] - height / 2,
                            width: endCoord[0] - startCoord[0],
                            height: height
                        },
                        style: {
                            fill: '#ef5350',
                            opacity: 0.8
                        }
                    };
                },
                data: tabBars.map((t, i) => [t.start, 0]),
                tooltip: {
                    formatter: function(params) {
                        const bar = tabBars[params.dataIndex];
                        return `切屏 @ ${bar.start.toFixed(1)}分<br/>持续: <strong>${bar.duration.toFixed(1)}秒</strong>`;
                    }
                }
            }
        ]
    };

    timelineChart.setOption(option, true);
}
