import pandas as pd
import numpy as np
from pathlib import Path

class BacktestEngine:
    """
    A simple bar-by-bar backtesting engine with performance reporting.
    """
    def __init__(self, data_df, strategy, initial_capital=10000.0, commission_rate=0.001, slippage_rate=0.0005):
        """
        Initializes the backtesting engine.
        """
        self.data_df = data_df
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.results = pd.DataFrame()

        # Portfolio state variables
        self.cash = initial_capital
        self.position_size = 0.0
        self.portfolio_value = initial_capital

        # History and logging
        self.trades = []
        self.portfolio_history = []

    def run(self):
        """
        Executes the backtest.
        """
        print("Running backtest...")
        signals_df = self.strategy.generate_signals(self.data_df)

        if signals_df.empty:
            print("No data to backtest after generating signals. Aborting.")
            return pd.DataFrame()

        for timestamp, row in signals_df.iterrows():
            current_price = row['close']
            signal = row['signal']
            current_portfolio_value = self.cash + (self.position_size * current_price)
            self.portfolio_history.append((timestamp, current_portfolio_value))

            if signal == 1 and self.position_size == 0:
                self._execute_buy(timestamp, current_price)
            elif signal == -1 and self.position_size > 0:
                self._execute_sell(timestamp, current_price)

        self.results = pd.DataFrame(self.portfolio_history, columns=['timestamp', 'portfolio_value']).set_index('timestamp')
        print("Backtest finished.")
        return self.results

    def _execute_buy(self, timestamp, price):
        buy_price = price * (1 + self.slippage_rate)
        units_to_buy = self.cash / buy_price
        cost = units_to_buy * buy_price
        commission = cost * self.commission_rate
        total_cost = cost + commission
        if total_cost > self.cash: return
        self.cash -= total_cost
        self.position_size += units_to_buy
        self.trades.append({'timestamp': timestamp, 'type': 'BUY', 'price': buy_price, 'units': units_to_buy, 'cost': total_cost})

    def _execute_sell(self, timestamp, price):
        sell_price = price * (1 - self.slippage_rate)
        proceeds = self.position_size * sell_price
        commission = proceeds * self.commission_rate
        total_proceeds = proceeds - commission
        self.cash += total_proceeds
        sold_units = self.position_size
        self.position_size = 0.0
        self.trades.append({'timestamp': timestamp, 'type': 'SELL', 'price': sell_price, 'units': sold_units, 'proceeds': total_proceeds})

    def generate_report(self, report_filename='backtest_report.csv'):
        """
        Calculates performance metrics and saves them to a CSV file.
        """
        if self.results.empty:
            print("No results to generate a report for.")
            return

        print("Generating performance report...")

        # Calculate Metrics
        final_value = self.results['portfolio_value'].iloc[-1]
        total_return = (final_value / self.initial_capital) - 1

        # Max Drawdown
        rolling_max = self.results['portfolio_value'].cummax()
        drawdown = (self.results['portfolio_value'] - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        # Sharpe Ratio (annualized, assuming daily data for simplicity)
        # For crypto, 365 days is more appropriate than 252
        returns = self.results['portfolio_value'].pct_change().dropna()
        sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(365) if returns.std() != 0 else 0

        metrics = {
            'Initial Capital': [self.initial_capital],
            'Final Portfolio Value': [final_value],
            'Total Return (%)': [total_return * 100],
            'Max Drawdown (%)': [max_drawdown * 100],
            'Sharpe Ratio (Annualized)': [sharpe_ratio],
            'Total Trades': [len(self.trades)],
        }

        metrics_df = pd.DataFrame(metrics).T
        metrics_df.columns = ['Value']

        # Save report
        report_path = Path('reports') / report_filename
        report_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_df.to_csv(report_path)

        print(f"Report saved to {report_path}")
        print("\n--- Performance Metrics ---")
        print(metrics_df)
        print("--------------------------")

if __name__ == '__main__':
    from ..strategy.ema_atr import EmaAtrStrategy
    from ..data.storage import DataStorage

    storage = DataStorage()
    try:
        data = storage.read_ohlcv("BTCUSDT", "1h", "2023-01-01", "2023-12-31")
        if data.empty: raise FileNotFoundError
    except Exception:
        print("Could not load real data, creating dummy data for example.")
        close_prices = 100 + np.random.randn(1000).cumsum()
        data = pd.DataFrame({
            'open': close_prices - 1, 'high': close_prices + 1,
            'low': close_prices - 1, 'close': close_prices, 'volume': 1000
        }, index=pd.to_datetime(pd.date_range(start='2023-01-01', periods=1000)))

    strategy = EmaAtrStrategy(fast_ema_period=10, slow_ema_period=30)
    engine = BacktestEngine(data, strategy)
    results = engine.run()

    if not results.empty:
        engine.generate_report(report_filename='ema_atr_btc_1h_report.csv')
    else:
        print("\nBacktest produced no results.")
