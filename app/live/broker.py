import os
import ccxt
from dotenv import load_dotenv

class LiveBroker:
    """
    Handles live trading for a multi-asset portfolio.
    It calculates rebalancing orders and validates them against exchange rules.
    """
    def __init__(self):
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        if not api_key or not api_secret:
            raise ValueError("Binance API credentials must be set in .env for live trading.")

        self.exchange = ccxt.binance({'apiKey': api_key, 'secret': api_secret})
        print("Loading exchange markets for validation rules...")
        self.exchange.load_markets()

    def get_portfolio_balance(self):
        """Fetches the current balance of all assets in the portfolio."""
        return self.exchange.fetch_balance()

    def rebalance_portfolio(self, target_portfolio, risk_manager, historical_data):
        """
        Calculates and executes trades to align the current portfolio with the target portfolio.

        :param target_portfolio: Dict of {'SYMBOL': target_weight}.
        :param risk_manager: The risk manager instance for correlation checks.
        :param historical_data: Dict of historical data for correlation calculation.
        """
        print("\n--- Initiating Portfolio Rebalance ---")

        # 1. Get current state
        balance = self.get_portfolio_balance()
        total_value_usdt = float(balance['total']['USDT']) # Approximation
        current_positions = {sym: info for sym, info in balance['total'].items() if info > 0}

        # 2. Determine trades needed
        # Sell positions no longer in target
        positions_to_exit = set(current_positions.keys()) - set(target_portfolio.keys()) - {'USDT'}
        for symbol_base in positions_to_exit:
            symbol = f"{symbol_base}/USDT"
            amount = current_positions[symbol_base]
            print(f"Selling entire position of {amount} {symbol}")
            self.create_market_sell_order(symbol, amount)

        # Adjust current positions
        for symbol, target_weight in target_portfolio.items():
            symbol_base = symbol.split('/')[0]

            target_value = total_value_usdt * target_weight
            current_units = current_positions.get(symbol_base, 0)

            ticker = self.exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            current_value = current_units * current_price

            delta_value = target_value - current_value
            delta_units = delta_value / current_price

            if delta_units > 0.00001: # Buy more
                # --- Correlation Check ---
                current_assets = [s.split('/')[0] for s in target_portfolio.keys() if s != symbol]
                if risk_manager.check_correlation(symbol_base, current_assets, historical_data):
                    continue # Skip trade if correlation is too high

                self.create_market_buy_order(symbol, delta_units, current_price)

            elif delta_units < -0.00001: # Sell some
                self.create_market_sell_order(symbol, abs(delta_units))

    def _validate_order(self, symbol, amount, price):
        market = self.exchange.market(symbol)
        min_notional = market['limits']['cost']['min']

        if (amount * price) < min_notional:
            print(f"Validation Error for {symbol}: Notional value too small.")
            return None

        validated_amount = self.exchange.amount_to_precision(symbol, amount)
        if float(validated_amount) <= 0:
            print(f"Validation Error for {symbol}: Amount too small after precision adjustment.")
            return None

        return float(validated_amount)

    def create_market_buy_order(self, symbol, amount, price):
        validated_amount = self._validate_order(symbol, amount, price)
        if validated_amount:
            print(f"Placing MARKET BUY for {validated_amount} {symbol}...")
            # self.exchange.create_market_buy_order(symbol, validated_amount) # UNCOMMENT FOR REAL TRADES
            print("--- (SIMULATED) BUY ORDER PLACED ---")
            return True
        return False

    def create_market_sell_order(self, symbol, amount):
        validated_amount = self.exchange.amount_to_precision(symbol, amount)
        if float(validated_amount) > 0:
            print(f"Placing MARKET SELL for {validated_amount} {symbol}...")
            # self.exchange.create_market_sell_order(symbol, validated_amount) # UNCOMMENT FOR REAL TRADES
            print("--- (SIMULATED) SELL ORDER PLACED ---")
            return True
        return False
