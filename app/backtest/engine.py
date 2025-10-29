import pandas as pd
import numpy as np
from pathlib import Path
import sys
import yaml
import time
import random
sys.path.append(str(Path(__file__).resolve().parents[2]))
from app.services.llm import LLMService

class PortfolioBacktestEngine:
    """
    Enhanced portfolio backtest engine with Chaos Engineering and event-based
    stress testing capabilities.
    """
    def __init__(self, data_dict, strategy, initial_capital=100000.0, rebalance_freq='W-FRI'):
        self.data_dict = data_dict
        # ... (same initializations)
        self.master_df = pd.concat(data_dict, names=['symbol', 'timestamp']).sort_index()

    def run(self, chaos_params=None, scenario_path=None):
        print(f"Running Portfolio Backtest... (Chaos Mode: {bool(chaos_params)})")

        # --- Scenario Loading ---
        events = self._load_scenario(scenario_path)

        all_timestamps = self.master_df.index.get_level_values('timestamp').unique()
        # ... (rebalance_dates calculation)

        for timestamp in all_timestamps:
            # --- Chaos: API Outage / Data Gap ---
            if chaos_params and random.random() < chaos_params.get('data_gap_chance', 0):
                print(f"CHAOS: Simulating data gap at {timestamp}")
                time.sleep(0.01) # Simulate the passing of time
                continue

            # --- Chaos: Latency Spike ---
            if chaos_params and random.random() < chaos_params.get('latency_chance', 0):
                latency = random.uniform(0.5, 2.0)
                print(f"CHAOS: Simulating latency spike of {latency:.2f}s at {timestamp}")
                time.sleep(latency)

            # --- Event-based Stress ---
            active_event = self._get_active_event(timestamp, events)
            slippage_mult = active_event['effects']['slippage_multiplier'] if active_event else 1.0

            # ... (portfolio value calculation)

            # --- Rebalancing Logic (with Chaos) ---
            if timestamp in rebalance_dates:
                # ... (target portfolio generation)

                # ... (rebalancing logic for buys and sells, now passing slippage_mult)
                # self._execute_buy(..., slippage_multiplier=slippage_mult, chaos_params=chaos_params)

        self.results = pd.DataFrame(self.portfolio_history).set_index('timestamp')
        return self.results

    def _execute_buy(self, timestamp, symbol, units, slippage_multiplier=1.0, chaos_params=None):
        # --- Chaos: Order Rejection ---
        if chaos_params and random.random() < chaos_params.get('rejection_chance', 0):
            print(f"CHAOS: Simulating order rejection for BUY {symbol}")
            return

        price = self.master_df.loc[(symbol, timestamp), 'close']

        # --- Chaos: Slippage Spike ---
        base_slippage = 0.001
        current_slippage = base_slippage * slippage_multiplier
        buy_price = price * (1 + current_slippage)

        # ... (rest of the buy logic)

    def _execute_sell(self, timestamp, symbol, units, slippage_multiplier=1.0, chaos_params=None):
        # ... (similar chaos injections for sell orders)
        pass

    def _load_scenario(self, scenario_path):
        if not scenario_path or not Path(scenario_path).exists():
            return []
        with open(scenario_path, 'r') as f:
            events = yaml.safe_load(f)
        # Convert timestamps to datetime objects
        for event in events:
            event['timestamp'] = pd.to_datetime(event['timestamp'])
        return events

    def _get_active_event(self, timestamp, events):
        for event in events:
            if event['timestamp'] <= timestamp < (event['timestamp'] + pd.Timedelta(minutes=event['duration_minutes'])):
                return event
        return None

    def _calculate_metrics(self, results_df, initial_capital):
        if results_df.empty:
            return {'Sharpe Ratio': 0, 'Max Drawdown (%)': -100}

        returns = results_df['portfolio_value'].pct_change().dropna()
        sharpe = (returns.mean() / returns.std()) * np.sqrt(365) if returns.std() != 0 else 0

        rolling_max = results_df['portfolio_value'].cummax()
        drawdown = (results_df['portfolio_value'] - rolling_max) / rolling_max
        max_drawdown = drawdown.min() * 100

        return {'Sharpe Ratio': sharpe, 'Max Drawdown (%)': max_drawdown}

    def generate_resilience_report(self, standard_results, chaos_results, report_filename):
        print("Generating Resilience Report...")

        std_metrics = self._calculate_metrics(standard_results, self.initial_capital)
        chaos_metrics = self._calculate_metrics(chaos_results, self.initial_capital)

        resilience_score = chaos_metrics['Sharpe Ratio'] / std_metrics['Sharpe Ratio'] if std_metrics['Sharpe Ratio'] > 0 else 0

        report = {
            "Resilience Score": f"{resilience_score:.2f} (Target > 0.8)",
            "Standard Run": std_metrics,
            "Chaos Run": chaos_metrics
        }

        report_path = Path('reports') / report_filename
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=4)

        print(f"Resilience report saved to {report_path}")
        print(json.dumps(report, indent=4))
        return resilience_score

# ... (Old BacktestEngine can remain)
