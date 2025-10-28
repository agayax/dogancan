import click
import os
import sys
import subprocess
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

# Ensure the app directory is in the Python path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.data.fetcher import BinanceFetcher
from app.data.storage import DataStorage
from app.strategy.ema_atr import EmaAtrStrategy
from app.backtest.engine import BacktestEngine
from app.optimize.optimizer import Optimizer
from app.live.broker import LiveBroker
from app.live.notifier import Notifier

PID_FILE = Path(__file__).resolve().parents[2] / "live_bot.pid"

@click.group()
def cli():
    """Binance Bot Projesi - Orkestrasyon CLI"""
    pass

@cli.command()
@click.option('--symbol', default='BTCUSDT', help='Trading symbol (e.g., BTCUSDT).')
@click.option('--interval', default='1h', help='Candlestick interval (e.g., 1h, 4h, 1d).')
@click.option('--days', default=365, help='Number of days of data to fetch.')
def update_data(symbol, interval, days):
    """Fetches historical OHLCV data and saves it to Parquet."""
    click.echo(f"Fetching last {days} days of data for {symbol} on {interval} interval...")
    fetcher = BinanceFetcher()
    storage = DataStorage()

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    df = fetcher.get_klines(
        symbol,
        interval,
        start_str=start_date.strftime('%Y-%m-%d'),
        end_str=end_date.strftime('%Y-%m-%d')
    )

    if not df.empty:
        storage.save_ohlcv(df, symbol, interval)
        click.echo(f"Successfully downloaded and saved {len(df)} records.")
    else:
        click.echo("Failed to download data.")

@cli.command()
@click.option('--symbol', default='BTCUSDT', help='Symbol to backtest.')
@click.option('--interval', default='1h', help='Interval to backtest.')
@click.option('--fast-ema', default=12, help='Fast EMA period.')
@click.option('--slow-ema', default=26, help='Slow EMA period.')
def run_backtest(symbol, interval, fast_ema, slow_ema):
    """Runs a backtest with the given parameters and generates a report."""
    click.echo(f"Running backtest for {symbol}/{interval} with EMA params: {fast_ema}/{slow_ema}")
    storage = DataStorage()
    df = storage.read_ohlcv(symbol, interval)

    if df.empty:
        click.echo("No data found. Run 'update-data' first.", err=True)
        return

    strategy = EmaAtrStrategy(fast_ema_period=fast_ema, slow_ema_period=slow_ema)
    engine = BacktestEngine(df, strategy)
    engine.run()

    report_name = f"backtest_{symbol}_{interval}_ema_{fast_ema}_{slow_ema}.csv"
    engine.generate_report(report_filename=report_name)
    click.echo(f"Backtest complete. Report saved to reports/{report_name}")

@cli.command()
@click.option('--symbol', default='BTCUSDT', help='Symbol to optimize.')
@click.option('--interval', default='1h', help='Interval to optimize.')
@click.option('--trials', default=100, help='Number of optimization trials.')
def run_optimization(symbol, interval, trials):
    """Runs hyperparameter optimization for the strategy."""
    click.echo(f"Starting optimization for {symbol}/{interval} with {trials} trials...")
    try:
        optimizer = Optimizer(
            symbol=symbol,
            interval=interval,
            start_date="2023-01-01",
            end_date="2023-12-31"
        )
        optimizer.run_optimization(n_trials=trials)
        click.echo("Optimization complete. Report saved in 'reports/' directory.")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)

@cli.command()
def start_live():
    """Starts the live trading bot as a background process."""
    if PID_FILE.exists():
        click.echo("Live bot is already running. Check the PID file.", err=True)
        return

    script_path = Path(__file__).resolve().parents[2] / "run_live_trader.py"
    process = subprocess.Popen([sys.executable, str(script_path)])

    with open(PID_FILE, 'w') as f:
        f.write(str(process.pid))

    click.echo(f"Live trading bot started with PID: {process.pid}")

@cli.command()
def stop_live():
    """Stops the live trading bot."""
    if not PID_FILE.exists():
        click.echo("Live bot is not running (no PID file found).", err=True)
        return

    with open(PID_FILE, 'r') as f:
        pid = int(f.read().strip())

    try:
        os.kill(pid, 15) # 15 = SIGTERM, graceful shutdown
        click.echo(f"Sent stop signal to process {pid}.")
    except ProcessLookupError:
        click.echo(f"Process {pid} not found. It might have already stopped.", err=True)

    os.remove(PID_FILE)

@cli.command()
def daily_summary():
    """Fetches the current portfolio balance and sends a summary via Telegram."""
    click.echo("Sending daily portfolio summary...")
    try:
        broker = LiveBroker(symbol='BTC/USDT') # Symbol needed for market data
        usdt_balance = broker.get_balance('USDT')
        btc_balance = broker.get_balance('BTC')

        ticker = broker.exchange.fetch_ticker('BTC/USDT')
        btc_value_in_usdt = btc_balance * ticker['last']
        total_value = usdt_balance + btc_value_in_usdt

        message = (
            f"*📈 Daily Portfolio Summary*\n\n"
            f"*Total Value:* ${total_value:,.2f} USD\n"
            f"*USDT Balance:* {usdt_balance:,.2f}\n"
            f"*BTC Balance:* {btc_balance:.6f} (${btc_value_in_usdt:,.2f})"
        )

        notifier = Notifier()
        asyncio.run(notifier.send_message(message))
        click.echo("Summary sent successfully.")

    except Exception as e:
        click.echo(f"Failed to send summary: {e}", err=True)

if __name__ == '__main__':
    cli()
