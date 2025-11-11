import pandas as pd
import duckdb
from pathlib import Path

class DataStorage:
    """Handles saving and reading of OHLCV data using Parquet and DuckDB."""
    def __init__(self, base_path="data/ohlcv"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def write_ohlcv(self, df: pd.DataFrame, symbol: str, interval: str):
        """Writes OHLCV DataFrame to a partitioned Parquet file."""
        if 'timestamp' in df.columns:
            df = df.set_index('timestamp')

        partition_path = self.base_path / f"symbol={symbol}" / f"interval={interval}"
        partition_path.mkdir(parents=True, exist_ok=True)

        output_file = partition_path / "data.parquet"
        df.to_parquet(output_file)
        print(f"Data for {symbol}/{interval} saved to {output_file}")

    def read_ohlcv(self, symbol: str, interval: str) -> pd.DataFrame:
        """Reads OHLCV data for a specific symbol and interval."""
        partition_path = self.base_path / f"symbol={symbol}" / f"interval={interval}"
        data_file = partition_path / "data.parquet"

        if not data_file.exists():
            print(f"No data found for {symbol}/{interval} at {data_file}")
            return pd.DataFrame()

        df = pd.read_parquet(data_file)
        if not isinstance(df.index, pd.DatetimeIndex):
            df = df.set_index('timestamp')

        return df
