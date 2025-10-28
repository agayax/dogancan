import asyncio
import sys
from pathlib import Path

# Add project root to the Python path
sys.path.append(str(Path(__file__).resolve().parent))

from app.live.paper import PaperTradingBroker
from app.strategy.ema_atr import EmaAtrStrategy

def main():
    """
    Initializes and starts the paper trading bot.
    """
    print("Initializing Paper Trading Bot...")

    # --- Configuration ---
    # In a real application, you might load this from a config file
    symbol = "BTCUSDT"
    interval = "1m"
    strategy_params = {
        'fast_ema_period': 12,
        'slow_ema_period': 26,
        'atr_period': 14
    }

    # --- Setup ---
    strategy = EmaAtrStrategy(**strategy_params)
    broker = PaperTradingBroker(symbol=symbol, interval=interval, strategy=strategy)

    # --- Run ---
    print(f"Starting paper trading for {symbol} on {interval} interval.")
    print("Press Ctrl+C to stop the bot.")

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(broker.start())
    except KeyboardInterrupt:
        print("\nStopping the paper trading bot...")
        loop.run_until_complete(broker.ws_client.stop())
    finally:
        loop.close()
        print("Bot shut down gracefully.")

if __name__ == "__main__":
    # Ensure you have your .env file configured with Binance API keys
    # and Telegram credentials for this to work.
    main()
