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
from app.data.sentiment_fetcher import SentimentFetcher
from app.data.onchain_fetcher import OnChainFetcher
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
@click.option('--symbol', default='BTCUSDT', help='Trading symbol.')
@click.option('--interval', default='1h', help='Candlestick interval.')
@click.option('--days', default=365, help='Number of days to fetch.')
def update_data(symbol, interval, days):
    """Fetches historical OHLCV data."""
    click.echo(f"Fetching data for {symbol}...")
    fetcher = BinanceFetcher()
    storage = DataStorage()
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    df = fetcher.get_klines(symbol, interval, start_str=start_date.strftime('%Y-%m-%d'), end_str=end_date.strftime('%Y-%m-%d'))
    if not df.empty:
        storage.save_ohlcv(df, symbol, interval)
        click.echo(f"Saved {len(df)} records.")

@cli.command()
def update_sentiment():
    """Fetches news and updates the sentiment data feed."""
    click.echo("Updating sentiment data...")
    fetcher = SentimentFetcher()
    fetcher.fetch_and_analyze()
    click.echo("Sentiment data updated.")

@cli.command()
def update_onchain():
    """Generates and saves synthetic on-chain data."""
    click.echo("Updating on-chain data...")
    fetcher = OnChainFetcher()
    fetcher.generate_and_save_data()
    click.echo("On-chain data updated.")

@cli.command()
@click.option('--symbol', default='BTCUSDT', help='Symbol to backtest.')
@click.option('--interval', default='1h', help='Interval to backtest.')
@click.option('--fast-ema', default=12, help='Fast EMA period.')
@click.option('--slow-ema', default=26, help='Slow EMA period.')
def run_backtest(symbol, interval, fast_ema, slow_ema):
    """Runs a single-asset backtest."""
    storage = DataStorage()
    df = storage.read_ohlcv(symbol, interval)
    if df.empty:
        click.echo("No data found.", err=True)
        return
    strategy = EmaAtrStrategy(fast_ema_period=fast_ema, slow_ema_period=slow_ema)
    engine = BacktestEngine(df, strategy)
    engine.run()
    report_name = f"backtest_{symbol}_{interval}.txt"
    engine.generate_report(report_filename=report_name)
    click.echo(f"Backtest complete. Report: reports/{report_name}")

@cli.command()
@click.option('--symbol', default='BTCUSDT', help='Symbol to optimize.')
@click.option('--interval', default='1h', help='Interval to optimize.')
@click.option('--trials', default=50, help='Number of optimization trials.')
def run_optimization(symbol, interval, trials):
    """Runs hyperparameter optimization."""
    try:
        optimizer = Optimizer(symbol, interval, "2023-01-01", "2023-12-31")
        optimizer.run_optimization(n_trials=trials)
        click.echo("Optimization complete.")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)

@cli.command()
def start_live():
    """Starts the live trading bot as a background process."""
    if PID_FILE.exists():
        click.echo("Bot is already running.", err=True)
        return
    script_path = Path(__file__).resolve().parents[2] / "run_live_trader.py"
    process = subprocess.Popen([sys.executable, str(script_path)])
    with open(PID_FILE, 'w') as f: f.write(str(process.pid))
    click.echo(f"Live bot started with PID: {process.pid}")

@cli.command()
def stop_live():
    """Stops the live trading bot."""
    if not PID_FILE.exists():
        click.echo("Bot not running.", err=True)
        return
    with open(PID_FILE, 'r') as f: pid = int(f.read().strip())
    try:
        os.kill(pid, 15)
        click.echo(f"Stop signal sent to PID {pid}.")
    except ProcessLookupError:
        click.echo(f"Process {pid} not found.", err=True)
    os.remove(PID_FILE)

@cli.command()
def daily_summary():
    """Sends a daily portfolio summary."""
    click.echo("Sending daily summary...")
    try:
        broker = LiveBroker(symbol='BTC/USDT') # Dummy symbol for init
        balance = broker.get_portfolio_balance()
        total_usdt = balance['total']['USDT']
        message = f"*📈 Daily Portfolio Summary*\n\n*Total Value:* ${total_usdt:,.2f} USD"
        notifier = Notifier()
        asyncio.run(notifier.send_message(message))
        click.echo("Summary sent.")
    except Exception as e:
        click.echo(f"Failed to send summary: {e}", err=True)

if __name__ == '__main__':
    cli()
