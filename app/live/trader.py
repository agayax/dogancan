import asyncio
import pandas as pd
from collections import deque
import json
import uuid
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.data.ws import BinanceWebsocketClient
from app.data.fetcher import BinanceFetcher
from app.strategy.ema_atr import EmaAtrStrategy
from app.live.broker import LiveBroker
from app.live.risk import RiskManager
from app.live.notifier import Notifier

TRADES_LOG_FILE = Path(__file__).resolve().parents[2] / "trades_with_reasons.jsonl"

class LiveTrader:
    """
    Manages the live trading loop, now with cognitive logging for XAI.
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

        self.ohlcv_history = deque(maxlen=200)
        self.position_size = 0.0

    async def _initialize_history(self):
        # ... (same as before)
        print(f"Initializing historical data for {self.symbol}...")
        fetcher = BinanceFetcher()
        df = fetcher.get_klines(self.symbol, self.interval, start_str=f"250 hours ago UTC")
        if not df.empty:
            self.ohlcv_history.extend(df.reset_index().to_dict('records'))
            print(f"Initialized with {len(self.ohlcv_history)} historical klines.")
        else:
            raise RuntimeError("Could not fetch initial historical data.")

    async def _on_new_kline(self, kline_data):
        self.ohlcv_history.append(kline_data)
        current_df = pd.DataFrame(list(self.ohlcv_history)).set_index('timestamp')

        current_price = kline_data['close']
        usdt_balance = self.broker.get_balance('USDT')
        portfolio_value = usdt_balance + (self.position_size * current_price)
        self.risk_manager.update_peak_value(portfolio_value)

        if self.risk_manager.check_loss_limit(portfolio_value):
            if not self.risk_manager.is_paused:
                await self.flatten_portfolio("Daily loss limit breached.")
            return

        signals_df = self.strategy.generate_signals(current_df)
        if signals_df.empty: return

        last_row = signals_df.iloc[-1]
        last_signal = last_row['signal']
        reason = last_row['reason']

        if last_signal == 1 and self.position_size == 0:
            amount_to_buy = self.broker.get_balance('USDT') / current_price
            order = self.broker.create_market_buy_order(amount_to_buy)
            if order:
                self.position_size = order['filled']
                await self._log_and_notify_trade(order, reason)

        elif last_signal == -1 and self.position_size > 0:
            order = self.broker.create_market_sell_order(self.position_size)
            if order:
                self.position_size = 0.0
                await self._log_and_notify_trade(order, reason)

    async def flatten_portfolio(self, reason_text):
        self.risk_manager.flatten_and_pause()
        if self.position_size > 0:
            reason = {'emergency_exit': reason_text}
            order = self.broker.create_market_sell_order(self.position_size)
            if order:
                self.position_size = 0.0
                await self._log_and_notify_trade(order, reason, is_emergency=True)

    def _log_trade(self, order, reason):
        log_entry = {
            'trade_id': str(uuid.uuid4()),
            'timestamp': datetime.utcnow().isoformat(),
            'order_details': order,
            'reason': reason
        }
        with open(TRADES_LOG_FILE, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        print(f"Logged trade {log_entry['trade_id']}")

    async def _log_and_notify_trade(self, order, reason, is_emergency=False):
        self._log_trade(order, reason)

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
        # ... (same as before)
        try:
            balance = self.broker.exchange.fetch_balance()
            base_currency = self.ccxt_symbol.split('/')[0]
            self.position_size = balance['free'][base_currency]
            print(f"Initial position size for {base_currency}: {self.position_size}")
        except Exception as e:
            print(f"Could not fetch initial position size: {e}")
        await self._initialize_history()
        await self.ws_client.start()

# ... (main function remains the same)
if __name__ == "__main__":
    # ...
    pass
