import asyncio
import pandas as pd
from collections import deque

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.data.ws import BinanceWebsocketClient
from app.data.fetcher import BinanceFetcher
from app.strategy.ema_atr import EmaAtrStrategy
from app.live.broker import LiveBroker
from app.live.risk import RiskManager
from app.live.notifier import Notifier

class LiveTrader:
    """
    Manages the live trading loop, integrating data, strategy, execution, and risk management.
    """
    def __init__(self, symbol, interval, strategy, initial_capital, risk_params):
        self.symbol = symbol
        self.ccxt_symbol = symbol.replace('USDT', '/USDT')
        self.interval = interval
        self.strategy = strategy
        self.initial_capital = initial_capital

        self.notifier = Notifier()
        self.risk_manager = RiskManager(initial_capital, **risk_params)
        self.broker = LiveBroker(symbol=self.ccxt_symbol)
        self.ws_client = BinanceWebsocketClient(self.symbol, self.interval, self._on_new_kline)

        self.ohlcv_history = deque(maxlen=200) # Keep enough history for indicators
        self.position_size = 0.0 # Base currency (e.g., BTC)

    async def _initialize_history(self):
        print(f"Initializing historical data for {self.symbol}...")
        fetcher = BinanceFetcher()
        df = fetcher.get_klines(self.symbol, self.interval, start_str=f"250 hours ago UTC")
        if not df.empty:
            self.ohlcv_history.extend(df.reset_index().to_dict('records'))
            print(f"Successfully initialized with {len(self.ohlcv_history)} historical klines.")
        else:
            raise RuntimeError("Could not fetch initial historical data. Cannot start trader.")

    async def _on_new_kline(self, kline_data):
        self.ohlcv_history.append(kline_data)
        current_df = pd.DataFrame(list(self.ohlcv_history)).set_index('timestamp')

        # --- Risk Management Check ---
        current_price = kline_data['close']
        usdt_balance = self.broker.get_balance('USDT')
        portfolio_value = usdt_balance + (self.position_size * current_price)
        self.risk_manager.update_peak_value(portfolio_value)

        if self.risk_manager.check_loss_limit(portfolio_value):
            if not self.risk_manager.is_paused:
                await self.flatten_portfolio("Daily loss limit breached.")
            return

        # --- Strategy and Signal Generation ---
        signals_df = self.strategy.generate_signals(current_df)
        if signals_df.empty: return
        last_signal = signals_df['signal'].iloc[-1]

        # --- Trade Execution ---
        if last_signal == 1 and self.position_size == 0:
            usdt_balance = self.broker.get_balance('USDT')
            amount_to_buy = usdt_balance / current_price
            order = self.broker.create_market_buy_order(amount_to_buy)
            if order:
                self.position_size = order['filled']
                await self._notify_trade(order)

        elif last_signal == -1 and self.position_size > 0:
            order = self.broker.create_market_sell_order(self.position_size)
            if order:
                self.position_size = 0.0
                await self._notify_trade(order)

    async def flatten_portfolio(self, reason):
        """
        Closes any open position immediately.
        """
        self.risk_manager.flatten_and_pause()
        print(f"--- FLATTENING PORTFOLIO: {reason} ---")
        if self.position_size > 0:
            order = self.broker.create_market_sell_order(self.position_size)
            if order:
                self.position_size = 0.0
                await self._notify_trade(order, is_emergency=True)

    async def _notify_trade(self, order, is_emergency=False):
        emergency_text = "EMERGENCY " if is_emergency else ""
        message = (
            f"*{emergency_text}LIVE TRADE: {order['side'].upper()} FILLED*\n\n"
            f"*Symbol:* {order['symbol']}\n"
            f"*Price:* ${float(order['average']):,.2f}\n"
            f"*Quantity:* {order['filled']}\n"
            f"*Cost:* ${float(order['cost']):,.2f}"
        )
        await self.notifier.send_message(message)

    async def start(self):
        # Fetch current position from exchange on startup
        try:
            balance = self.broker.exchange.fetch_balance()
            base_currency = self.ccxt_symbol.split('/')[0]
            self.position_size = balance['free'][base_currency]
            print(f"Initial position size for {base_currency}: {self.position_size}")
        except Exception as e:
            print(f"Could not fetch initial position size: {e}")

        await self._initialize_history()
        await self.ws_client.start()

async def main():
    strategy = EmaAtrStrategy()
    trader = LiveTrader(
        symbol="BTCUSDT",
        interval="1m",
        strategy=strategy,
        initial_capital=1000.0, # Example capital
        risk_params={'daily_loss_limit_pct': 2.0}
    )
    try:
        await trader.start()
    except (KeyboardInterrupt, RuntimeError) as e:
        print(f"Stopping the live trader due to: {e}")
        await trader.ws_client.stop()
    finally:
        print("Trader shut down.")

if __name__ == "__main__":
    asyncio.run(main())
