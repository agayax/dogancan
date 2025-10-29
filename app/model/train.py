import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from pathlib import Path

class ModelTrainer:
    """
    Trains an XGBoost model on the engineered features to predict future returns.
    """
    def __init__(self, features_path="data/derived/model_features.parquet", model_output_dir="models/"):
        self.features_path = Path(features_path)
        self.model_output_dir = Path(model_output_dir)
        self.model_output_dir.mkdir(parents=True, exist_ok=True)

    def train_model(self):
        """
        Loads features, trains the model, and saves it to a file.
        """
        if not self.features_path.exists():
            raise FileNotFoundError("Features file not found. Run the feature engineering job first.")

        print("Loading features for model training...")
        df = pd.read_parquet(self.features_path)

        # --- Feature and Target Selection ---
        features = [col for col in df.columns if col not in ['target_return_1h', 'timestamp']]
        target = 'target_return_1h'

        X = df[features]
        y = df[target]

        # Split data into training and testing sets
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

        # --- Model Training (XGBoost) ---
        print("Training XGBoost model...")
        model = xgb.XGBRegressor(
            objective='reg:squarederror',
            n_estimators=1000,
            learning_rate=0.05,
            early_stopping_rounds=50,
            eval_metric='rmse'
        )

        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )

        # --- Evaluation ---
        preds = model.predict(X_test)
        rmse = mean_squared_error(y_test, preds, squared=False)
        print(f"Model training complete. Test RMSE: {rmse:.6f}")

        # --- Save Model ---
        model_version = "v1" # This could be dynamic
        model_path = self.model_output_dir / f"ade_xgb_{model_version}.bin"
        model.save_model(model_path)
        print(f"Model saved to {model_path}")

if __name__ == '__main__':
    try:
        trainer = ModelTrainer()
        trainer.train_model()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please run the 'generate-features' job first.")
