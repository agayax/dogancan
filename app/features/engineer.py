import pandas as pd
import numpy as np
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[2]))
from app.data.storage import DataStorage

class FeatureEngineer:
    """
    Combines all data sources (OHLCV, on-chain, sentiment) into a single
    feature set for model training.
    """
    def __init__(self, ohlcv_path="data/ohlcv", onchain_path="data/derived/onchain_daily.parquet", sentiment_path="data/derived/sentiment_feed.parquet", output_path="data/derived/model_features.parquet"):
        self.ohlcv_path = ohlcv_path
        self.onchain_path = onchain_path
        self.sentiment_path = sentiment_path
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage = DataStorage()

    def create_features(self, symbol='BTCUSDT', interval='1h'):
        print(f"Starting feature engineering for {symbol}...")

        # 1. Load all data sources
        ohlcv_df = self.storage.read_ohlcv(symbol, interval)
        if ohlcv_df.empty:
            raise ValueError("OHLCV data is empty. Run data updates first.")

        onchain_df = pd.read_parquet(self.onchain_path) if Path(self.onchain_path).exists() else pd.DataFrame()
        sentiment_df = pd.read_parquet(self.sentiment_path) if Path(self.sentiment_path).exists() else pd.DataFrame()

        # 2. Resample and merge data
        # Resample sentiment to hourly to match OHLCV
        if not sentiment_df.empty:
            sentiment_df = sentiment_df.set_index('timestamp')['sentiment_score'].resample('h').mean().to_frame()

        # Resample on-chain daily data to hourly
        if not onchain_df.empty:
            onchain_df = onchain_df.set_index('timestamp').resample('h').ffill()

        # Merge
        df = ohlcv_df.join(sentiment_df, how='left').join(onchain_df, how='left')
        df.fillna(method='ffill', inplace=True)

        # 3. Create Technical Indicators (Features)
        df['RSI'] = self._rsi(df['close'], 14)
        df['SMA_50'] = df['close'].rolling(window=50).mean()
        df['SMA_200'] = df['close'].rolling(window=200).mean()
        df['returns'] = df['close'].pct_change()

        # 4. Create Target Variable
        # Predict the return of the next hour
        df['target_return_1h'] = df['returns'].shift(-1)

        # 5. Drop NaNs and save
        df.dropna(inplace=True)
        df.to_parquet(self.output_path)

        print(f"Feature engineering complete. {len(df)} records saved to {self.output_path}")

    def _rsi(self, series, period):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

if __name__ == '__main__':
    # This requires data to be present.
    # Run the data update jobs in the orchestrator first.
    try:
        engineer = FeatureEngineer()
        engineer.create_features()
    except ValueError as e:
        print(f"Error: {e}")
        print("Please run 'poetry run python app/jobs/jules_runner.py update-data' and other update jobs first.")
