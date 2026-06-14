let heatmapChart = null;
let currentKData = null;

function initHeatmap() {
    const dom = document.getElementById('heatmap-chart');
    if (!dom) return;
    heatmapChart = echarts.init(dom);
    window.addEventListener('resize', () => heatmapChart && heatmapChart.resize());
}

async function renderHeatmap(examId) {
    if (!heatmapChart) initHeatmap();

    const data = await api.getKIndex(examId);
    currentKData = data;
    const names = data.student_names;
    const n = names.length;

    // Build symmetric matrix data
    const matrixData = [];
    for (const [i, j, k] of data.matrix) {
        matrixData.push([i, j, k]);
        matrixData.push([j, i, k]);
    }

    const maxK = Math.max(...matrixData.map(d => d[2]), 1);

    const option = {
        tooltip: {
            position: 'top',
            formatter: function(params) {
                const i = params.data[0];
                const j = params.data[1];
                const k = params.data[2];
                return `${names[i]} & ${names[j]}<br/>K-index: <strong>${k.toFixed(3)}</strong>`;
            }
        },
        grid: {
            left: 80,
            right: 20,
            top: 20,
            bottom: 80
        },
        xAxis: {
            type: 'category',
            data: names,
            axisLabel: { rotate: 45, fontSize: 10 },
            splitArea: { show: true }
        },
        yAxis: {
            type: 'category',
            data: names,
            axisLabel: { fontSize: 10 },
            splitArea: { show: true }
        },
        visualMap: {
            min: 0,
            max: Math.min(maxK, 5),
            calculable: true,
            orient: 'horizontal',
            left: 'center',
            bottom: 0,
            inRange: {
                color: ['#f5f5f5', '#fff3e0', '#ffcc02', '#ff6600', '#d32f2f']
            }
        },
        series: [{
            type: 'heatmap',
            data: matrixData,
            label: { show: false },
            emphasis: {
                itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' }
            }
        }]
    };

    heatmapChart.setOption(option);

    heatmapChart.off('click');
    heatmapChart.on('click', function(params) {
        if (params.data && params.data[2] > 0.5) {
            const i = params.data[0];
            const j = params.data[1];
            showPairEvidence(examId, data, i, j);
        }
    });
}

async function showPairEvidence(examId, kData, i, j) {
    const names = kData.student_names;
    const pair = kData.pairs.find(p =>
        (p.student_a_name === names[i] && p.student_b_name === names[j]) ||
        (p.student_a_name === names[j] && p.student_b_name === names[i])
    );

    if (!pair) return;

    const data = await api.getPairEvidence(examId, pair.student_a_id, pair.student_b_id);
    _renderCrossEvidence(data);
}
