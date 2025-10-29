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
    def __init__(self,
                 ohlcv_path="data/ohlcv",
                 onchain_path="data/derived/onchain_daily.parquet",
                 sentiment_path="data/derived/sentiment_feed.parquet",
                 output_path="data/derived/model_features.parquet"):
        self.ohlcv_path = ohlcv_path
        self.onchain_path = onchain_path
        self.sentiment_path = sentiment_path
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage = DataStorage()

    def create_features(self, symbol='BTCUSDT', interval='1h'):
        print(f"Starting feature engineering for {symbol}...")

        # 1. Load and prepare historical data
        df = self._load_and_prepare_historical_data(symbol, interval)

        # 2. Create historical features
        df = self._generate_technical_indicators(df)

        # 3. Create target for historical data
        df['target_return_1h'] = df['close'].pct_change().shift(-1)
        # Target for classification: 1 if the next hour's return is positive, else 0
        df['target'] = (df['target_return_1h'] > 0).astype(int)
        df.drop(columns=['target_return_1h'], inplace=True)

        # 4. Save final dataset
        df.dropna(inplace=True)
        df.to_parquet(self.output_path)
        print(f"Feature engineering complete. {len(df)} records saved to {self.output_path}")

    def _load_and_prepare_historical_data(self, symbol, interval):
        ohlcv_df = self.storage.read_ohlcv(symbol, interval)
        if ohlcv_df.empty:
            raise ValueError("OHLCV data is empty. Run data updates first.")

        onchain_df = pd.read_parquet(self.onchain_path) if Path(self.onchain_path).exists() else pd.DataFrame()
        sentiment_df = pd.read_parquet(self.sentiment_path) if Path(self.sentiment_path).exists() else pd.DataFrame()

        if not sentiment_df.empty:
            sentiment_df = sentiment_df.set_index('timestamp')['sentiment_score'].resample('h').mean().to_frame()
        if not onchain_df.empty:
            onchain_df = onchain_df.set_index('timestamp').resample('h').ffill()

        df = ohlcv_df.join(sentiment_df, how='left').join(onchain_df, how='left')
        return df.fillna(method='ffill')

    def _generate_technical_indicators(self, df):
        # Standard Indicators
        df['RSI'] = self._rsi(df['close'], 14)
        df['SMA_50'] = df['close'].rolling(window=50).mean()
        df['SMA_200'] = df['close'].rolling(window=200).mean()
        df['returns'] = df['close'].pct_change()

        # --- NEW: Features for Persona-Based Models ---

        # 1. Volatility Regime (for 'Aggressive' persona)
        # Using 20-period rolling standard deviation of returns
        df['volatility'] = df['returns'].rolling(window=20).std()
        df['avg_volatility'] = df['volatility'].rolling(window=200).mean()
        df['volatility_regime'] = (df['volatility'] > df['avg_volatility']).astype(int) # 1 for high, 0 for low

        # 2. Mean Reversion Signal (for 'Cautious' persona)
        # Using distance from a moving average (e.g., SMA 50) in terms of standard deviations
        rolling_std = df['close'].rolling(window=50).std()
        df['z_score_50'] = (df['close'] - df['SMA_50']) / rolling_std

        # Signal: 1 for potential buy (oversold), -1 for potential sell (overbought)
        df['mean_reversion_signal'] = 0
        df.loc[df['z_score_50'] < -1.5, 'mean_reversion_signal'] = 1  # Oversold condition
        df.loc[df['z_score_50'] > 1.5, 'mean_reversion_signal'] = -1 # Overbought condition

        return df

    def _rsi(self, series, period):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

if __name__ == '__main__':
    try:
        engineer = FeatureEngineer()
        engineer.create_features()
    except ValueError as e:
        print(f"Error: {e}")
        print("Please run 'poetry run python app/jobs/jules_runner.py update-data' and other update jobs first.")
