import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_squared_error
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[2]))

class ModelTrainer:
    """
    Trains specialized XGBoost persona models (e.g., Aggressive, Cautious)
    on filtered datasets to achieve different objectives.
    """
    def __init__(self, features_path="data/derived/model_features.parquet", model_output_dir="models/"):
        self.features_path = Path(features_path)
        if not self.features_path.exists():
            raise FileNotFoundError("Features file not found. Run the feature engineering job first.")

        self.df = pd.read_parquet(self.features_path)
        self.model_output_dir = Path(model_output_dir)
        self.model_output_dir.mkdir(parents=True, exist_ok=True)

    def train_persona(self, persona_config):
        """
        Trains a single persona model based on a configuration dictionary.
        """
        persona_name = persona_config['name']
        print(f"--- Starting training for Persona: {persona_name} ---")

        # 1. Filter data based on persona's regime
        persona_df = self.df.query(persona_config['data_filter']).copy()
        print(f"Filtered data for {persona_name}: {len(persona_df)} records remaining.")

        if persona_df.empty:
            print(f"Warning: No data available for persona '{persona_name}' after filtering. Skipping.")
            return

        # 2. Define Features and Target
        features = [col for col in self.df.columns if col not in ['target', 'timestamp', 'volatility', 'avg_volatility', 'z_score_50', 'mean_reversion_signal', 'volatility_regime']]
        target = 'target'

        X = persona_df[features]
        y = persona_df[target]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

        # 3. Train Model
        print(f"Training {persona_config['model_type']} for {persona_name}...")
        model_params = persona_config['model_params']

        if persona_config['model_type'] == 'classifier':
            model = xgb.XGBClassifier(**model_params)
        else: # regressor
            model = xgb.XGBRegressor(**model_params)

        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )

        # 4. Evaluate
        preds = model.predict(X_test)
        if persona_config['model_type'] == 'classifier':
            metric = accuracy_score(y_test, preds)
            print(f"Evaluation complete. Test Accuracy: {metric:.4f}")
        else:
            metric = mean_squared_error(y_test, preds, squared=False)
            print(f"Evaluation complete. Test RMSE: {metric:.6f}")

        # 5. Save Model
        model_path = self.model_output_dir / persona_config['output_filename']
        model.save_model(model_path)
        print(f"Persona model '{persona_name}' saved to {model_path}\n")


if __name__ == '__main__':
    # Define the configurations for each AI Persona

    # Persona 1: "Agresif" (Grendel) - High volatility, profit maximization
    grendel_config = {
        "name": "Agent_Grendel",
        "model_type": "regressor",
        "data_filter": "volatility_regime == 1",
        "output_filename": "ade_grendel_v1.bin",
        "model_params": {
            'objective': 'reg:squarederror',
            'n_estimators': 1000,
            'learning_rate': 0.05,
            'early_stopping_rounds': 50,
            'eval_metric': 'rmse'
        }
    }

    # Persona 2: "Tedbirli" (Beowulf) - Mean reversion, risk minimization (predicting win/loss)
    beowulf_config = {
        "name": "Agent_Beowulf",
        "model_type": "classifier",
        "data_filter": "mean_reversion_signal != 0",
        "output_filename": "ade_beowulf_v1.bin",
        "model_params": {
            'objective': 'binary:logistic',
            'n_estimators': 500,
            'learning_rate': 0.01,
            'early_stopping_rounds': 50,
            'eval_metric': 'logloss'
        }
    }

    try:
        trainer = ModelTrainer()
        trainer.train_persona(grendel_config)
        trainer.train_persona(beowulf_config)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please run the 'generate-features' job first.")
