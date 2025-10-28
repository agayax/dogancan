import os
from binance.client import Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class BinanceFetcher:
    """
    A class to fetch data from the Binance REST API.
    """

    def __init__(self):
        """
        Initializes the BinanceFetcher with API credentials from environment variables.
        """
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")

        if not api_key or not api_secret:
            raise ValueError("Binance API key and secret must be set in the .env file.")

        self.client = Client(api_key, api_secret)

    def get_klines(self, symbol, interval, limit=500):
        """
        Fetches k-line (candlestick) data for a given symbol and interval.

        :param symbol: The trading symbol (e.g., 'BTCUSDT').
        :param interval: The interval for k-lines (e.g., Client.KLINE_INTERVAL_1HOUR).
        :param limit: The number of k-lines to fetch (max 1000).
        :return: A list of k-line data.
        """
        try:
            klines = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
            return klines
        except Exception as e:
            print(f"An error occurred while fetching klines for {symbol}: {e}")
            return None

if __name__ == "__main__":
    fetcher = BinanceFetcher()

    # Example usage: Fetch 1-hour k-lines for BTCUSDT
    btc_klines = fetcher.get_klines("BTCUSDT", Client.KLINE_INTERVAL_1HOUR, limit=10)

    if btc_klines:
        print(f"Successfully fetched {len(btc_klines)} k-lines for BTCUSDT.")
        for kline in btc_klines:
            print(kline)
