import pandas as pd
import xgboost as xgb
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[2]))
from app.features.engineer import FeatureEngineer

class ADEStrategy:
    """
    An AI Decision Engine (ADE) strategy that uses a trained XGBoost model.
    It can be configured to represent different personas (e.g., Grendel, Beowulf)
    by loading different model files.
    """
    def __init__(self, model_path, threshold=0.55):
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Trained model not found at {self.model_path}")

        self.model = xgb.Booster()
        self.model.load_model(self.model_path)
        print(f"ADE Strategy instance created. Loaded model from {self.model_path}")

        self.feature_engineer = FeatureEngineer()
        self.threshold = threshold

    def generate_signals(self, data):
        """
        Generates a target portfolio based on the model's prediction.

        :param data: A dictionary where keys are symbols and values are dataframes.
        :return: A dictionary representing the target portfolio, e.g., {'BTCUSDT': 1.0}.
        """
        symbol = list(data.keys())[0]
        df = data[symbol].copy()

        if df.empty:
            return {}

        # 1. On-the-fly Feature Engineering
        features_df = self.feature_engineer._generate_technical_indicators(df)
        features_df.dropna(inplace=True)

        if features_df.empty:
            return {}

        # 2. Prediction
        feature_names = self.model.feature_names
        dmatrix = xgb.DMatrix(features_df[feature_names].tail(1))
        prediction = self.model.predict(dmatrix)[0]

        # 3. Signal to Target Portfolio
        # This is a simple binary decision based on the threshold
        target_weight = 1.0 if prediction > self.threshold else 0.0

        return {symbol: target_weight}

if __name__ == '__main__':
    print("ADEStrategy class defined. This module is intended to be imported.")
