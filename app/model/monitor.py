import pandas as pd
import json
from pathlib import Path
from scipy.stats import ks_2samp

class DriftMonitor:
    """
    Monitors for data drift by comparing the statistical properties of live data
    against the training data.
    """
    def __init__(self, features_path="data/derived/model_features.parquet", baseline_stats_path="models/baseline_stats.json"):
        self.features_path = Path(features_path)
        self.baseline_stats_path = Path(baseline_stats_path)
        self.baseline_stats = None

    def generate_baseline_stats(self):
        """
        Calculates descriptive statistics for the training feature set and saves them.
        This should be run after a new model is trained.
        """
        if not self.features_path.exists():
            raise FileNotFoundError("Features file not found. Cannot generate baseline stats.")

        print("Generating baseline statistics from training data...")
        df = pd.read_parquet(self.features_path)
        features = [col for col in df.columns if col not in ['target_return_1h', 'timestamp']]

        stats = {}
        for feature in features:
            stats[feature] = {
                'mean': df[feature].mean(),
                'std': df[feature].std(),
            }

        with open(self.baseline_stats_path, 'w') as f:
            json.dump(stats, f, indent=4)
        print(f"Baseline stats saved to {self.baseline_stats_path}")

    def check_for_drift(self, live_features_df, p_value_threshold=0.05):
        """
        Compares a DataFrame of live features against the baseline statistics.
        Uses the Kolmogorov-Smirnov test to check if distributions have shifted.

        :param live_features_df: A DataFrame of the most recent features from live trading.
        :param p_value_threshold: The significance level for the KS test.
        :return: A dictionary of features that have drifted, or an empty dict if no drift.
        """
        if self.baseline_stats is None:
            if not self.baseline_stats_path.exists():
                raise FileNotFoundError("Baseline stats file not found. Generate it first.")
            with open(self.baseline_stats_path, 'r') as f:
                self.baseline_stats = json.load(f)

        print("Checking for model drift...")
        drifted_features = {}

        training_df = pd.read_parquet(self.features_path)

        for feature in self.baseline_stats.keys():
            if feature in live_features_df.columns:
                stat, p_value = ks_2samp(training_df[feature], live_features_df[feature])

                if p_value < p_value_threshold:
                    drifted_features[feature] = {
                        'p_value': p_value,
                        'live_mean': live_features_df[feature].mean(),
                        'baseline_mean': self.baseline_stats[feature]['mean']
                    }

        if drifted_features:
            print(f"!!! DRIFT DETECTED in features: {list(drifted_features.keys())}")
        else:
            print("No significant model drift detected.")

        return drifted_features

if __name__ == '__main__':
    # 1. Generate baseline stats (should be done after training)
    monitor = DriftMonitor()
    # monitor.generate_baseline_stats()

    # 2. Simulate checking for drift with some live data
    # Create a dummy "live" DataFrame. Let's make the RSI drift significantly.
    dummy_live_data = {
        'RSI': np.random.normal(loc=70, scale=5, size=100), # Training RSI is usually around 50
        'SMA_50': np.random.normal(loc=100, scale=10, size=100),
        # ... other features
    }
    live_df = pd.DataFrame(dummy_live_data)

    try:
        drift_report = monitor.check_for_drift(live_df)
        if drift_report:
            print("\nDrift Report:")
            print(json.dumps(drift_report, indent=4))
    except FileNotFoundError as e:
        print(e)
