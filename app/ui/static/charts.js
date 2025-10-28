// --- Chart Setup ---
const chartContainer = document.getElementById('chart-container');
const chart = LightweightCharts.createChart(chartContainer, {
    width: chartContainer.clientWidth,
    height: chartContainer.clientHeight,
    layout: {
        backgroundColor: '#131722',
        textColor: '#d1d4dc',
    },
    grid: {
        vertLines: { color: '#2a2e39' },
        horzLines: { color: '#2a2e39' },
    },
    timeScale: {
        timeVisible: true,
        secondsVisible: false,
    },
});

// --- Series ---
const candleSeries = chart.addCandlestickSeries({
    upColor: '#26a69a',
    downColor: '#ef5350',
    borderDownColor: '#ef5350',
    borderUpColor: '#26a69a',
    wickDownColor: '#ef5350',
    wickUpColor: '#26a69a',
});

// --- DOM Elements ---
const portfolioStatus = document.getElementById('portfolio-status');
const runBacktestBtn = document.getElementById('run-backtest-btn');
const fastEmaInput = document.getElementById('fast-ema');
const slowEmaInput = document.getElementById('slow-ema');
const atrPeriodInput = document.getElementById('atr-period');


// --- Initial Data Loading ---
async function loadInitialData() {
    // 1. Load historical OHLCV data
    const ohlcvResponse = await fetch('/api/ohlcv');
    const ohlcvData = await ohlcvResponse.json();
    candleSeries.setData(ohlcvData);

    // 2. Load historical trade signals (optional, for visualizing a complete backtest at once)
    const tradesResponse = await fetch('/api/trades');
    const tradeData = await tradesResponse.json();
    candleSeries.setMarkers(tradeData);

    console.log("Initial data loaded.");
}


// --- WebSocket Logic for Real-Time Simulation ---
function runBacktestSimulation() {
    // Clear previous markers and reset status
    candleSeries.setMarkers([]);
    portfolioStatus.innerText = 'Portfolio Value: $10000.00';
    runBacktestBtn.disabled = true;
    runBacktestBtn.innerText = 'Running...';

    // Get strategy parameters from UI inputs
    const fastEma = fastEmaInput.value;
    const slowEma = slowEmaInput.value;
    const atrPeriod = atrPeriodInput.value;

    const queryParams = new URLSearchParams({
        symbol: "BTCUSDT",
        interval: "1h",
        start_date: "2023-01-01",
        end_date: "2023-12-31",
        fast_ema: fastEma,
        slow_ema: slowEma,
        atr_period: atrPeriod
    });

    const wsUrl = `ws://${window.location.host}/ws/run_backtest?${queryParams.toString()}`;
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
        console.log("WebSocket connection established with params:", queryParams.toString());
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        switch (data.type) {
            case 'update':
                candleSeries.update(data.kline);
                portfolioStatus.innerText = `Portfolio Value: $${data.portfolio_value.toFixed(2)}`;
                if (data.trade) {
                    const trade = data.trade;
                    candleSeries.setMarkers([...candleSeries.markers(), {
                        time: Math.floor(new Date(trade.timestamp).getTime() / 1000),
                        position: trade.type === 'SELL' ? 'aboveBar' : 'belowBar',
                        color: trade.type === 'SELL' ? '#e91e63' : '#2196F3',
                        shape: trade.type === 'SELL' ? 'arrowDown' : 'arrowUp',
                        text: `${trade.type} @ ${trade.price.toFixed(2)}`
                    }]);
                }
                break;
            case 'finished':
                console.log("Backtest simulation finished.");
                socket.close();
                break;
            case 'error':
                console.error("Error from backend:", data.message);
                alert(`An error occurred: ${data.message}`);
                socket.close();
                break;
        }
    };

    socket.onclose = () => {
        console.log("WebSocket connection closed.");
        runBacktestBtn.disabled = false;
        runBacktestBtn.innerText = 'Run Backtest';
    };

    socket.onerror = (error) => {
        console.error("WebSocket error:", error);
        alert("A WebSocket error occurred. Check the console for details.");
    };
}


// --- Event Listeners ---
runBacktestBtn.addEventListener('click', runBacktestSimulation);

window.addEventListener('resize', () => {
    chart.resize(chartContainer.clientWidth, chartContainer.clientHeight);
});

document.addEventListener('DOMContentLoaded', loadInitialData);
