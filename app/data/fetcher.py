import os
import pandas as pd
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

        # Use testnet=True for paper trading or development
        self.client = Client(api_key, api_secret)

    def get_klines(self, symbol, interval, start_str=None, end_str=None):
        """
        Fetches k-line (candlestick) data for a given symbol and interval and returns it as a pandas DataFrame.

        :param symbol: The trading symbol (e.g., 'BTCUSDT').
        :param interval: The interval for k-lines (e.g., Client.KLINE_INTERVAL_1HOUR).
        :param start_str: The start date string in format 'YYYY-MM-DD' or 'DD MMM YYYY'.
        :param end_str: The end date string in format 'YYYY-MM-DD' or 'DD MMM YYYY'.
        :return: A pandas DataFrame with OHLCV data.
        """
        try:
            klines = self.client.get_historical_klines(symbol, interval, start_str, end_str)

            if not klines:
                return pd.DataFrame()

            # Define column names for the DataFrame
            columns = [
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ]

            df = pd.DataFrame(klines, columns=columns)

            # Convert data types
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'quote_asset_volume',
                            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Set timestamp as index and select relevant columns
            df.set_index('timestamp', inplace=True)
            df = df[['open', 'high', 'low', 'close', 'volume']]

            return df

        except Exception as e:
            print(f"An error occurred while fetching klines for {symbol}: {e}")
            return pd.DataFrame()

if __name__ == "__main__":
    # This requires API keys with permissions for historical data.
    # If you don't have them, this part might fail.
    try:
        fetcher = BinanceFetcher()

        # Example usage: Fetch daily k-lines for BTCUSDT for a specific period
        btc_df = fetcher.get_klines("BTCUSDT", Client.KLINE_INTERVAL_1DAY, "2023-01-01", "2023-12-31")

        if not btc_df.empty:
            print(f"Successfully fetched {len(btc_df)} k-lines for BTCUSDT.")
            print("DataFrame head:")
            print(btc_df.head())
            print("\nDataFrame tail:")
            print(btc_df.tail())
        else:
            print("Could not fetch k-lines for BTCUSDT. The DataFrame is empty.")
            print("Please ensure your API keys are correctly set in the .env file and have the necessary permissions.")

    except ValueError as e:
        print(e)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
