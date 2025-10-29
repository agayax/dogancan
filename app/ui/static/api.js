// A simple API wrapper to keep API calls separate from chart logic

/**
 * Fetches historical OHLCV data from the server's API.
 * @param {string} symbol The trading symbol, e.g., 'BTCUSDT'.
 * @param {string} interval The chart interval, e.g., '1h'.
 * @returns {Promise<Array>} A promise that resolves to an array of candle data.
 */
async function fetchOHLCV(symbol, interval) {
    try {
        const response = await fetch(`/api/ohlcv/${symbol}/${interval}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        // The server might return an error object
        if (data.error) {
            throw new Error(data.error);
        }
        return data;
    } catch (error) {
        console.error("Failed to fetch OHLCV data:", error);
        // Return an empty array so the chart doesn't break
        return [];
    }
}
