import os
import ccxt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LiveBroker:
    """
    Handles live trading interactions with the Binance exchange via ccxt.
    """
    def __init__(self, symbol):
        """
        Initializes the LiveBroker.
        :param symbol: The trading symbol (e.g., 'BTC/USDT').
        """
        self.symbol = symbol

        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")

        if not api_key or not api_secret:
            raise ValueError("Binance API key and secret must be set in the .env file for live trading.")

        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'options': {
                'defaultType': 'spot',
            },
            # Uncomment for testnet
            # 'urls': {
            #     'api': {
            #         'public': 'https://testnet.binance.vision/api',
            #         'private': 'https://testnet.binance.vision/api',
            #     }
            # }
        })

        # Load market data for the symbol
        print("Loading market data for validation...")
        self.exchange.load_markets()
        self.market = self.exchange.market(self.symbol)

        # Extract validation rules
        self.min_notional = self.market['limits']['cost']['min']
        self.lot_step = self.market['limits']['amount']['step']
        self.price_step = self.market['limits']['price']['step']

        print(f"Market limits for {self.symbol}:")
        print(f"  - Min Notional: {self.min_notional}")
        print(f"  - Lot Step (Amount): {self.lot_step}")
        print(f"  - Price Step: {self.price_step}")

    def get_balance(self, currency='USDT'):
        """
        Fetches the free balance for a specific currency.
        """
        balance = self.exchange.fetch_balance()
        return balance['free'][currency]

    def validate_order(self, amount, price):
        """
        Validates an order against the exchange's rules.
        :return: A validated amount or None if validation fails.
        """
        # 1. Check Min Notional
        notional_value = amount * price
        if notional_value < self.min_notional:
            print(f"Validation Error: Order notional ({notional_value:.2f}) is below the minimum ({self.min_notional:.2f}).")
            return None

        # 2. Adjust to Lot Step
        # The amount needs to be a multiple of the lot step size
        validated_amount = self.exchange.amount_to_precision(self.symbol, amount)
        if float(validated_amount) <= 0:
            print(f"Validation Error: Amount is too small to meet lot step requirements.")
            return None

        print(f"Validated order: Amount adjusted from {amount} to {validated_amount}")
        return float(validated_amount)

    def create_market_buy_order(self, amount):
        """
        Creates a market buy order.
        :param amount: The amount of the base currency to buy.
        :return: The order result from the exchange.
        """
        try:
            # First, get the current price to validate the order
            ticker = self.exchange.fetch_ticker(self.symbol)
            price = ticker['last']

            validated_amount = self.validate_order(amount, price)

            if validated_amount:
                print(f"Placing MARKET BUY order for {validated_amount} {self.symbol}...")
                order = self.exchange.create_market_buy_order(self.symbol, validated_amount)
                print("Order placed successfully.")
                return order
            return None
        except Exception as e:
            print(f"An error occurred placing buy order: {e}")
            return None

    def create_market_sell_order(self, amount):
        """
        Creates a market sell order.
        :param amount: The amount of the base currency to sell.
        :return: The order result from the exchange.
        """
        try:
            # We don't need the price for validation on sell, as we're selling what we have,
            # but we still need to respect the lot step.
            validated_amount = self.exchange.amount_to_precision(self.symbol, amount)

            if float(validated_amount) > 0:
                print(f"Placing MARKET SELL order for {validated_amount} {self.symbol}...")
                order = self.exchange.create_market_sell_order(self.symbol, validated_amount)
                print("Order placed successfully.")
                return order
            return None
        except Exception as e:
            print(f"An error occurred placing sell order: {e}")
            return None

# --- Example Usage ---
if __name__ == '__main__':
    # This is a LIVE example. It will place orders if you have API keys.
    # USE A SMALL AMOUNT OF CAPITAL FOR TESTING.
    try:
        broker = LiveBroker(symbol='BTC/USDT')

        # Fetch balance
        usdt_balance = broker.get_balance('USDT')
        print(f"\nAvailable balance: {usdt_balance:.2f} USDT")

        # Example: Try to buy a small amount (e.g., ~$15 worth of BTC)
        if usdt_balance > 15:
            btc_to_buy = 15 / broker.exchange.fetch_ticker('BTC/USDT')['last']
            buy_order = broker.create_market_buy_order(btc_to_buy)
            if buy_order:
                print("\nBuy Order Result:")
                print(buy_order)

                # Wait and then sell it back
                import time
                time.sleep(5)

                # Fetch filled amount from the order
                filled_amount = buy_order['filled']
                sell_order = broker.create_market_sell_order(filled_amount)
                if sell_order:
                    print("\nSell Order Result:")
                    print(sell_order)
            else:
                print("Buy order failed validation or execution.")

    except ValueError as e:
        print(e)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
