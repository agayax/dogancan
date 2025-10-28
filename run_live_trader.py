import asyncio
import sys
from pathlib import Path

# Add project root to the Python path
sys.path.append(str(Path(__file__).resolve().parent))

from app.live.trader import LiveTrader
from app.strategy.ema_atr import EmaAtrStrategy

def main():
    """
    Initializes and starts the live trading bot.
    """
    print("--- Initializing Live Trading Bot ---")

    # --- Configuration ---
    # WARNING: This bot will place REAL orders.
    # Start with a small amount of capital you are willing to lose.
    symbol = "BTCUSDT"
    interval = "1m"
    initial_capital = 15.0  # Use a small amount for testing, e.g., $15

    strategy_params = {
        'fast_ema_period': 12,
        'slow_ema_period': 26,
        'atr_period': 14
    }
    risk_params = {
        'daily_loss_limit_pct': 5.0 # Allow a bit more room for small accounts
    }

    # --- Setup ---
    strategy = EmaAtrStrategy(**strategy_params)
    trader = LiveTrader(
        symbol=symbol,
        interval=interval,
        strategy=strategy,
        initial_capital=initial_capital,
        risk_params=risk_params
    )

    # --- Run ---
    print(f"Starting live trading for {symbol} on {interval} interval.")
    print("WARNING: This bot will place REAL orders on your Binance account.")
    print("Press Ctrl+C to stop the bot.")

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(trader.start())
    except KeyboardInterrupt:
        print("\nStopping the live trader...")
        # Ensure flatten portfolio is called on exit
        loop.run_until_complete(trader.flatten_portfolio("Manual shutdown."))
        loop.run_until_complete(trader.ws_client.stop())
    finally:
        loop.close()
        print("Bot shut down gracefully.")

if __name__ == "__main__":
    # Ensure you have your .env file configured with REAL Binance API keys
    # and Telegram credentials for this to work.
    main()
