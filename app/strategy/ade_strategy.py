import pandas as pd
import xgboost as xgb
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[2]))
from app.features.engineer import FeatureEngineer # Reuse for on-the-fly feature calculation

class ADEStrategy:
    """
    An AI Decision Engine (ADE) strategy that uses a trained XGBoost model
    to make trading decisions.
    """
    def __init__(self, model_path="models/ade_xgb_v1.bin", prediction_threshold=0.0005):
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Trained model not found at {self.model_path}")

        self.model = xgb.Booster()
        self.model.load_model(self.model_path)
        print(f"ADE Strategy loaded model from {self.model_path}")

        self.feature_engineer = FeatureEngineer()
        self.prediction_threshold = prediction_threshold

    def generate_signals(self, ohlcv_df, sentiment_df=None, onchain_df=None):
        """
        Generates a trading signal based on the model's prediction.

        :param ohlcv_df: DataFrame of the latest OHLCV data.
        :param sentiment_df: DataFrame of recent sentiment data.
        :param onchain_df: DataFrame of recent on-chain data.
        :return: A signal (1 for buy, -1 for sell, 0 for hold) and a reason dictionary.
        """
        # --- On-the-fly Feature Engineering ---
        # This part needs to mirror the logic in FeatureEngineer but for a single, live data point.
        # For simplicity in this implementation, we'll assume ohlcv_df contains enough history
        # to calculate indicators. A more robust implementation would manage a history buffer here.

        df = ohlcv_df.copy()

        # Add technical indicators
        df['RSI'] = self.feature_engineer._rsi(df['close'], 14)
        df['SMA_50'] = df['close'].rolling(window=50).mean()
        df['SMA_200'] = df['close'].rolling(window=200).mean()
        df['returns'] = df['close'].pct_change()

        # Add sentiment/onchain if available (simplified for this example)
        if sentiment_df is not None and not sentiment_df.empty:
            df['sentiment_score'] = sentiment_df['sentiment_score'].iloc[-1]
        else:
            df['sentiment_score'] = 0

        if onchain_df is not None and not onchain_df.empty:
            df['btc_active_addresses'] = onchain_df['btc_active_addresses'].iloc[-1]
        else:
            df['btc_active_addresses'] = 0

        df.dropna(inplace=True)

        if df.empty:
            return 0, {}

        # --- Prediction ---
        last_features = df.tail(1)
        feature_names = self.model.feature_names

        # Ensure correct column order
        dmatrix = xgb.DMatrix(last_features[feature_names])
        prediction = self.model.predict(dmatrix)[0]

        # --- Signal Generation ---
        signal = 0
        if prediction > self.prediction_threshold:
            signal = 1  # Buy signal
        elif prediction < -self.prediction_threshold:
            signal = -1 # Sell signal

        reason = {
            'model_prediction': float(prediction),
            'prediction_threshold': self.prediction_threshold,
            'signal_generated': signal
        }

        # This is a simplified signal generation. For portfolio strategies,
        # this would return target weights instead.
        return signal, reason
