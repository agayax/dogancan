import optuna
import pandas as pd
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.data.storage import DataStorage
from app.strategy.ema_atr import EmaAtrStrategy
from app.backtest.engine import BacktestEngine

class Optimizer:
    """
    Finds the best hyperparameters for a strategy using Optuna.
    """
    def __init__(self, symbol, interval, start_date, end_date):
        self.symbol = symbol
        self.interval = interval
        self.start_date = start_date
        self.end_date = end_date

        # Load data once
        print("Loading data for optimization...")
        storage = DataStorage()
        self.data_df = storage.read_ohlcv(symbol, interval, start_date, end_date)
        if self.data_df.empty:
            raise ValueError("No data available for the given optimization parameters.")

    def _objective(self, trial):
        """
        The objective function for Optuna to optimize.
        """
        # Suggest hyperparameters to test
        fast_ema = trial.suggest_int('fast_ema_period', 5, 50)
        slow_ema = trial.suggest_int('slow_ema_period', 10, 100)
        atr_period = trial.suggest_int('atr_period', 7, 21)

        # Ensure slow_ema is greater than fast_ema
        if fast_ema >= slow_ema:
            return -1.0 # Return a poor score to prune this trial

        # Run backtest with the suggested parameters
        strategy = EmaAtrStrategy(
            fast_ema_period=fast_ema,
            slow_ema_period=slow_ema,
            atr_period=atr_period
        )

        # Use a simplified backtest run that just returns metrics
        engine = BacktestEngine(self.data_df, strategy)
        results = engine.run()

        if results.empty:
            return -1.0

        # Calculate Sharpe Ratio to use as the optimization target
        returns = results['portfolio_value'].pct_change().dropna()
        if returns.std() == 0:
            return -1.0

        sharpe_ratio = (returns.mean() / returns.std()) * (365**0.5) # Annualized
        return sharpe_ratio

    def run_optimization(self, n_trials=100):
        """
        Starts the Optuna optimization study.
        """
        print(f"Starting optimization for {self.symbol} with {n_trials} trials...")
        study = optuna.create_study(direction='maximize')
        study.optimize(self._objective, n_trials=n_trials)

        print("\n--- Optimization Finished ---")
        print(f"Best trial:")
        trial = study.best_trial
        print(f"  Value (Sharpe Ratio): {trial.value:.4f}")
        print("  Params: ")
        for key, value in trial.params.items():
            print(f"    {key}: {value}")

        return trial.params, trial.value

# --- Example Usage ---
def main():
    optimizer = Optimizer(
        symbol="BTCUSDT",
        interval="1h",
        start_date="2023-01-01",
        end_date="2023-12-31"
    )

    best_params, best_value = optimizer.run_optimization(n_trials=50) # Use fewer trials for a quick example

    # Save the best parameters to a file or report
    report = {
        'run_timestamp': datetime.now().isoformat(),
        'symbol': 'BTCUSDT',
        'interval': '1h',
        'period': '2023-01-01 to 2023-12-31',
        'best_sharpe_ratio': best_value,
        'best_params': best_params
    }

    Path('reports').mkdir(exist_ok=True)
    report_path = Path('reports') / 'optimization_report.txt'
    with open(report_path, 'w') as f:
        for key, value in report.items():
            f.write(f"{key}: {value}\n")
    print(f"\nOptimization report saved to {report_path}")

if __name__ == "__main__":
    main()
