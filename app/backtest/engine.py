import pandas as pd
import numpy as np
from pathlib import Path

# Adjust imports for LLM service
import sys
sys.path.append(str(Path(__file__).resolve().parents[2]))
from app.services.llm import LLMService


class BacktestEngine:
    """
    A bar-by-bar backtesting engine, enhanced with XAI and LLM-powered reporting.
    """
    def __init__(self, data_df, strategy, initial_capital=10000.0, commission_rate=0.001, slippage_rate=0.0005):
        self.data_df = data_df
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.results = pd.DataFrame()
        self.llm_service = LLMService()

        self.cash = initial_capital
        self.position_size = 0.0
        self.trades = []
        self.portfolio_history = []

    def run(self):
        print("Running backtest with XAI logging...")
        signals_df = self.strategy.generate_signals(self.data_df)

        if signals_df.empty:
            print("No data to backtest after generating signals. Aborting.")
            return pd.DataFrame()

        for timestamp, row in signals_df.iterrows():
            current_price = row['close']
            signal = row['signal']
            reason = row['reason'] # Capture the reason

            current_portfolio_value = self.cash + (self.position_size * current_price)
            self.portfolio_history.append((timestamp, current_portfolio_value))

            if signal == 1 and self.position_size == 0:
                self._execute_buy(timestamp, current_price, reason)
            elif signal == -1 and self.position_size > 0:
                self._execute_sell(timestamp, current_price, reason)

        self.results = pd.DataFrame(self.portfolio_history, columns=['timestamp', 'portfolio_value']).set_index('timestamp')
        print("Backtest finished.")
        return self.results

    def _execute_buy(self, timestamp, price, reason):
        buy_price = price * (1 + self.slippage_rate)
        units_to_buy = self.cash / buy_price
        cost = units_to_buy * buy_price
        commission = cost * self.commission_rate
        total_cost = cost + commission
        if total_cost > self.cash: return
        self.cash -= total_cost
        self.position_size += units_to_buy
        self.trades.append({'timestamp': timestamp, 'type': 'BUY', 'price': buy_price, 'units': units_to_buy, 'cost': total_cost, 'reason': reason})

    def _execute_sell(self, timestamp, price, reason):
        sell_price = price * (1 - self.slippage_rate)
        proceeds = self.position_size * sell_price
        commission = proceeds * self.commission_rate
        total_proceeds = proceeds - commission
        self.cash += total_proceeds
        sold_units = self.position_size
        self.position_size = 0.0
        self.trades.append({'timestamp': timestamp, 'type': 'SELL', 'price': sell_price, 'units': sold_units, 'proceeds': total_proceeds, 'reason': reason})

    def generate_report(self, report_filename='backtest_report.txt'):
        if self.results.empty:
            print("No results to generate a report for.")
            return

        print("Generating enhanced performance report...")
        final_value = self.results['portfolio_value'].iloc[-1]
        total_return = (final_value / self.initial_capital) - 1
        returns = self.results['portfolio_value'].pct_change().dropna()
        sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(365) if returns.std() != 0 else 0
        rolling_max = self.results['portfolio_value'].cummax()
        drawdown = (self.results['portfolio_value'] - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        metrics = {
            'Initial Capital': [self.initial_capital], 'Final Portfolio Value': [final_value],
            'Total Return (%)': [total_return * 100], 'Max Drawdown (%)': [max_drawdown * 100],
            'Sharpe Ratio (Annualized)': [sharpe_ratio], 'Total Trades': [len(self.trades)],
        }

        metrics_df = pd.DataFrame(metrics).T
        metrics_df.columns = ['Value']

        # --- LLM Integration ---
        llm_summary = self.llm_service.summarize_backtest(metrics)

        # --- Save Combined Report ---
        report_path = Path('reports') / report_filename
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, 'w') as f:
            f.write("--- Performance Metrics ---\n")
            f.write(metrics_df.to_string())
            f.write("\n\n--------------------------\n\n")
            f.write(llm_summary)

        print(f"Enhanced report saved to {report_path}")
        print("\n--- Performance Metrics ---")
        print(metrics_df)
        print("\n--- LLM Summary ---")
        print(llm_summary)

if __name__ == '__main__':
    from app.strategy.ema_atr import EmaAtrStrategy
    from app.data.storage import DataStorage

    storage = DataStorage()
    try:
        data = storage.read_ohlcv("BTCUSDT", "1h", "2023-01-01", "2023-12-31")
        if data.empty: raise FileNotFoundError
    except Exception:
        print("Could not load real data, creating dummy data for example.")
        close_prices = 100 + np.random.randn(1000).cumsum()
        data = pd.DataFrame({'open': close_prices, 'high': close_prices, 'low': close_prices, 'close': close_prices, 'volume': 1000}, index=pd.to_datetime(pd.date_range(start='2023-01-01', periods=1000)))

    strategy = EmaAtrStrategy(fast_ema_period=10, slow_ema_period=30)
    engine = BacktestEngine(data, strategy)
    results = engine.run()

    if not results.empty:
        engine.generate_report(report_filename='ema_atr_btc_1h_report_enhanced.txt')
    else:
        print("\nBacktest produced no results.")
