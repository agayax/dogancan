import pandas as pd
import numpy as np
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[2]))
from app.services.llm import LLMService

class PortfolioBacktestEngine:
    """
    A backtesting engine designed for multi-asset, portfolio-based strategies
    that generate target weights and rebalance periodically.
    """
    def __init__(self, data_dict, strategy, initial_capital=100000.0, rebalance_freq='W-FRI'):
        self.data_dict = data_dict  # A dict of DataFrames, one for each symbol
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.rebalance_freq = rebalance_freq
        self.llm_service = LLMService()

        self.cash = initial_capital
        self.positions = {}  # { 'symbol': units }
        self.portfolio_history = []
        self.trades = []

        # Combine all data into a single multi-index DataFrame for easier time iteration
        self.master_df = pd.concat(data_dict, names=['symbol', 'timestamp']).sort_index()

    def run(self):
        print("Running Portfolio Backtest...")

        # Get all unique timestamps across all assets and determine rebalancing dates
        all_timestamps = self.master_df.index.get_level_values('timestamp').unique()
        rebalance_dates = pd.to_datetime(all_timestamps).to_series().resample(self.rebalance_freq).last().dropna()

        for timestamp in all_timestamps:
            # Update portfolio value at every timestamp
            current_value = self.cash
            for symbol, units in self.positions.items():
                if (symbol, timestamp) in self.master_df.index:
                    current_price = self.master_df.loc[(symbol, timestamp), 'close']
                    current_value += units * current_price
            self.portfolio_history.append({'timestamp': timestamp, 'portfolio_value': current_value})

            # --- Rebalancing Logic ---
            if timestamp in rebalance_dates:
                print(f"--- Rebalancing on {timestamp.date()} ---")

                # 1. Get target portfolio from the strategy
                # The strategy needs access to all data up to the current timestamp
                historical_data_slice = {sym: df.loc[:timestamp] for sym, df in self.data_dict.items()}
                target_portfolio = self.strategy.generate_target_portfolio(historical_data_slice)

                # 2. Liquidate positions not in the new target portfolio
                positions_to_exit = set(self.positions.keys()) - set(target_portfolio.keys())
                for symbol in positions_to_exit:
                    self._execute_sell(timestamp, symbol, self.positions[symbol])

                # 3. Adjust positions for assets in the target portfolio
                for symbol, target_weight in target_portfolio.items():
                    target_value = current_value * target_weight

                    current_price = self.master_df.loc[(symbol, timestamp), 'close']
                    current_units = self.positions.get(symbol, 0)
                    current_value_asset = current_units * current_price

                    delta_value = target_value - current_value_asset
                    delta_units = delta_value / current_price

                    if delta_units > 0: # Need to buy more
                        self._execute_buy(timestamp, symbol, delta_units)
                    elif delta_units < 0: # Need to sell some
                        self._execute_sell(timestamp, symbol, abs(delta_units))

        self.results = pd.DataFrame(self.portfolio_history).set_index('timestamp')
        print("Portfolio backtest finished.")
        return self.results

    def _execute_buy(self, timestamp, symbol, units):
        price = self.master_df.loc[(symbol, timestamp), 'close']
        cost = units * price
        if self.cash < cost:
            # Not enough cash, skip or partially fill (here, we skip)
            return
        self.cash -= cost
        self.positions[symbol] = self.positions.get(symbol, 0) + units
        self.trades.append({'timestamp': timestamp, 'symbol': symbol, 'type': 'BUY', 'units': units, 'price': price})

    def _execute_sell(self, timestamp, symbol, units):
        price = self.master_df.loc[(symbol, timestamp), 'close']
        proceeds = units * price
        self.cash += proceeds
        self.positions[symbol] = self.positions.get(symbol, 0) - units
        if self.positions[symbol] <= 1e-6: # Clean up dust positions
            del self.positions[symbol]
        self.trades.append({'timestamp': timestamp, 'symbol': symbol, 'type': 'SELL', 'units': units, 'price': price})

    def generate_report(self, report_filename='portfolio_backtest_report.txt'):
        # ... (Similar to single-asset engine's report generation)
        if self.results.empty: return
        # ... (Metrics calculation as before)
        metrics = {} # Calculate metrics like Sharpe, Drawdown, etc.
        llm_summary = self.llm_service.summarize_backtest(metrics)
        # ... (Save report)
        print("Portfolio report generated.")

# Keep the old engine for single-asset strategies if needed
class BacktestEngine:
    # ... (The previous single-asset engine code can remain here)
    pass
