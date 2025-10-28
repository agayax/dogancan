import asyncio
import pandas as pd
from collections import deque

# Adjust import paths to work from the root of the project
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.data.ws import BinanceWebsocketClient
from app.data.fetcher import BinanceFetcher
from app.strategy.ema_atr import EmaAtrStrategy
from app.live.notifier import Notifier

class PaperTradingBroker:
    """
    Simulates a live paper trading session using a WebSocket for live data.
    """
    def __init__(self, symbol, interval, strategy, initial_capital=10000.0, history_size=100):
        self.symbol = symbol
        self.interval = interval
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.history_size = history_size

        # Portfolio state
        self.cash = initial_capital
        self.position_size = 0.0

        # Data and state
        self.ohlcv_history = deque(maxlen=history_size)
        self.notifier = Notifier()
        self.ws_client = BinanceWebsocketClient(self.symbol, self.interval, self._on_new_kline)

    async def _initialize_history(self):
        """
        Fetches historical data to warm up the initial state for the strategy.
        """
        print(f"Initializing historical data for {self.symbol}...")
        fetcher = BinanceFetcher()
        # Fetch a bit more than history_size to ensure indicators are ready
        df = fetcher.get_klines(self.symbol, self.interval, start_str=f"{self.history_size + 50} hours ago UTC")

        if not df.empty:
            # Convert to list of dicts for the deque
            records = df.reset_index().to_dict('records')
            self.ohlcv_history.extend(records)
            print(f"Successfully initialized with {len(self.ohlcv_history)} historical klines.")
        else:
            print("Warning: Could not fetch initial historical data. Starting with an empty history.")

    async def _on_new_kline(self, kline_data):
        """
        Callback function executed on each new kline from the WebSocket.
        """
        # Append new kline and convert to DataFrame for the strategy
        self.ohlcv_history.append(kline_data)
        current_df = pd.DataFrame(list(self.ohlcv_history)).set_index('timestamp')

        # Generate signals
        signals_df = self.strategy.generate_signals(current_df)

        if signals_df.empty:
            return

        last_signal = signals_df['signal'].iloc[-1]
        current_price = signals_df['close'].iloc[-1]

        # --- Trade Execution Logic ---
        if last_signal == 1 and self.position_size == 0:
            # Buy signal and no position
            self._execute_buy(current_price)
        elif last_signal == -1 and self.position_size > 0:
            # Sell signal and in a position
            self._execute_sell(current_price)

    def _execute_buy(self, price):
        """
        Simulates a buy order.
        """
        self.position_size = self.cash / price
        self.cash = 0.0
        print(f"\n--- EXECUTED BUY ---")
        print(f"Price: {price:.2f}, Size: {self.position_size:.6f} {self.symbol}")
        print(f"Portfolio: Cash=${self.cash:.2f}, Position Value=${self.position_size * price:.2f}")

        # Send notification
        message = (
            f"*PAPER TRADE: BUY executed*\n\n"
            f"*Symbol:* {self.symbol}\n"
            f"*Price:* ${price:,.2f}\n"
            f"*Quantity:* {self.position_size:.6f}"
        )
        asyncio.create_task(self.notifier.send_message(message))

    def _execute_sell(self, price):
        """
        Simulates a sell order.
        """
        self.cash = self.position_size * price
        position_value = self.cash
        self.position_size = 0.0
        print(f"\n--- EXECUTED SELL ---")
        print(f"Price: {price:.2f}, Proceeds: ${position_value:.2f}")
        print(f"Portfolio: Cash=${self.cash:.2f}, Position Value=$0.00")

        # Send notification
        message = (
            f"*PAPER TRADE: SELL executed*\n\n"
            f"*Symbol:* {self.symbol}\n"
            f"*Price:* ${price:,.2f}\n"
            f"*Proceeds:* ${position_value:,.2f}"
        )
        asyncio.create_task(self.notifier.send_message(message))

    async def start(self):
        """
        Starts the paper trading session.
        """
        await self._initialize_history()
        await self.ws_client.start()

# --- Main Execution ---
async def main():
    strategy = EmaAtrStrategy(fast_ema_period=12, slow_ema_period=26)
    broker = PaperTradingBroker(symbol="BTCUSDT", interval="1m", strategy=strategy)

    try:
        await broker.start()
    except KeyboardInterrupt:
        await broker.ws_client.stop()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        await broker.ws_client.stop()

if __name__ == "__main__":
    # Ensure you have .env file with API keys and Telegram credentials
    asyncio.run(main())
