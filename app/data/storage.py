import os
import duckdb
import pandas as pd
from pathlib import Path

# Assuming fetcher is in the same directory
from .fetcher import BinanceFetcher
from binance.client import Client

class DataStorage:
    """
    Handles storing and retrieving OHLCV data in partitioned Parquet files.
    Uses DuckDB for efficient querying.
    """
    def __init__(self, base_path='data/ohlcv'):
        """
        Initializes the DataStorage with a base path for the data.

        :param base_path: The root directory to store Parquet files.
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.db_conn = duckdb.connect(database=':memory:', read_only=False)

    def save_ohlcv(self, df, symbol, interval):
        """
        Saves OHLCV DataFrame to a partitioned Parquet file.
        The partitioning is done by symbol and interval.

        :param df: pandas DataFrame with OHLCV data.
        :param symbol: The trading symbol (e.g., 'BTCUSDT').
        :param interval: The data interval (e.g., '1h', '1d').
        """
        if df.empty:
            print(f"DataFrame for {symbol}/{interval} is empty. Nothing to save.")
            return

        partition_path = self.base_path / f"symbol={symbol}" / f"interval={interval}"
        partition_path.mkdir(parents=True, exist_ok=True)

        file_path = partition_path / "data.parquet"

        # Write to Parquet
        df.to_parquet(file_path, engine='pyarrow')
        print(f"Data for {symbol}/{interval} saved to {file_path}")

    def read_ohlcv(self, symbol, interval, start_date=None, end_date=None):
        """
        Reads OHLCV data from Parquet files for a given symbol and interval,
        optionally filtering by a date range.

        :param symbol: The trading symbol to read.
        :param interval: The data interval to read.
        :param start_date: Optional start date (YYYY-MM-DD string).
        :param end_date: Optional end date (YYYY-MM-DD string).
        :return: A pandas DataFrame with the requested data.
        """
        partition_path = self.base_path / f"symbol={symbol}" / f"interval={interval}"

        if not partition_path.exists():
            print(f"No data found for {symbol}/{interval} at {partition_path}")
            return pd.DataFrame()

        # DuckDB can read partitioned Parquet files directly using glob syntax
        glob_path = str(self.base_path / "symbol=*" / "interval=*" / "*.parquet")

        # Build the SQL query
        query = f"SELECT * FROM read_parquet('{str(self.base_path)}/*/*/*.parquet', hive_partitioning=1)"

        conditions = [
            f"symbol = '{symbol}'",
            f"interval = '{interval}'"
        ]

        if start_date:
            conditions.append(f"timestamp >= '{start_date}'")
        if end_date:
            conditions.append(f"timestamp <= '{end_date}'")

        query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY timestamp"

        try:
            result_df = self.db_conn.execute(query).fetchdf()
            result_df['timestamp'] = pd.to_datetime(result_df['timestamp'])
            result_df.set_index('timestamp', inplace=True)
            return result_df
        except Exception as e:
            print(f"An error occurred while querying data for {symbol}/{interval}: {e}")
            return pd.DataFrame()


if __name__ == "__main__":
    # Example usage
    try:
        # 1. Fetch data
        print("Fetching data from Binance...")
        fetcher = BinanceFetcher()
        # Fetch a small amount of recent data for the example
        df_btc = fetcher.get_klines("BTCUSDT", Client.KLINE_INTERVAL_1HOUR, "2024-01-01", "2024-01-31")
        df_eth = fetcher.get_klines("ETHUSDT", Client.KLINE_INTERVAL_1HOUR, "2024-01-01", "2024-01-31")

        # 2. Store data
        print("\nStoring data...")
        storage = DataStorage()
        if not df_btc.empty:
            storage.save_ohlcv(df_btc, "BTCUSDT", "1h")
        if not df_eth.empty:
            storage.save_ohlcv(df_eth, "ETHUSDT", "1h")

        # 3. Read data back
        print("\nReading data back from storage...")
        read_df = storage.read_ohlcv("BTCUSDT", "1h", start_date="2024-01-10", end_date="2024-01-15")

        if not read_df.empty:
            print("Successfully read data for BTCUSDT (1h) for the specified date range:")
            print(read_df.head())
            print("...")
            print(read_df.tail())
        else:
            print("Could not read data or no data available for the specified range.")

    except ValueError as e:
        print(f"ValueError: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during the example run: {e}")
        print("Please ensure your API keys are set in the .env file.")
