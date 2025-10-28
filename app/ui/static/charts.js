// --- Chart Setup ---
const chartContainer = document.getElementById('chart-container');
const subChartContainer = document.getElementById('sub-chart-container');

const chart = LightweightCharts.createChart(chartContainer, { width: chartContainer.clientWidth, height: chartContainer.clientHeight, layout: { backgroundColor: '#131722', textColor: '#d1d4dc' }, grid: { vertLines: { color: '#2a2e39' }, horzLines: { color: '#2a2e39' } }, timeScale: { timeVisible: true, secondsVisible: false } });
const subChart = LightweightCharts.createChart(subChartContainer, { width: subChartContainer.clientWidth, height: subChartContainer.clientHeight, layout: { backgroundColor: '#131722', textColor: '#d1d4dc' }, grid: { vertLines: { color: '#2a2e39' }, horzLines: { color: '#2a2e39' } }, timeScale: { timeVisible: true, secondsVisible: false } });

const candleSeries = chart.addCandlestickSeries({ upColor: '#26a69a', downColor: '#ef5350', borderDownColor: '#ef5350', borderUpColor: '#26a69a', wickDownColor: '#ef5350', wickUpColor: '#26a69a' });
const subChartSeries = subChart.addHistogramSeries({ color: '#2962FF', base: 0 });

// --- Time Scale Sync ---
chart.timeScale().subscribeVisibleTimeRangeChange(timeRange => { subChart.timeScale().setVisibleRange(timeRange); });
subChart.timeScale().subscribeVisibleTimeRangeChange(timeRange => { chart.timeScale().setVisibleRange(timeRange); });

// --- DOM Elements ---
const macroSelect = document.getElementById('macro-data-select');
const runBacktestBtn = document.getElementById('run-backtest-btn'); // Assuming this exists

// --- Data Loading ---
async function loadInitialData() {
    const ohlcvResponse = await fetch('/api/ohlcv');
    const ohlcvData = await ohlcvResponse.json();
    candleSeries.setData(ohlcvData);
    // You might want to pre-load a default macro view, e.g., sentiment
    await loadMacroData('sentiment');
}

async function loadMacroData(dataType) {
    let url = '';
    subChartSeries.setData([]);
    if (dataType === 'none') return;

    switch (dataType) {
        case 'sentiment': url = '/api/sentiment'; break;
        case 'onchain_btc_active': url = '/api/onchain?metric=btc_active_addresses'; break;
        case 'onchain_eth_gas': url = '/api/onchain?metric=eth_avg_gas_gwei'; break;
    }
    const response = await fetch(url);
    const data = await response.json();
    subChartSeries.setData(data);
}

// --- Event Listeners ---
macroSelect.addEventListener('change', (event) => loadMacroData(event.target.value));

// ... (Resize logic)
window.addEventListener('resize', () => {
    chart.resize(chartContainer.clientWidth, chartContainer.clientHeight);
    subChart.resize(subChartContainer.clientWidth, subChartContainer.clientHeight);
});

// ... (WebSocket and Backtest logic from previous sprints remains here)
// Make sure to adapt it if necessary

document.addEventListener('DOMContentLoaded', loadInitialData);
