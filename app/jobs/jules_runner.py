import click
import os
import sys
import subprocess
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.data.fetcher import BinanceFetcher
from app.data.storage import DataStorage
from app.data.sentiment_fetcher import SentimentFetcher
from app.data.onchain_fetcher import OnChainFetcher
from app.features.engineer import FeatureEngineer
from app.model.train import ModelTrainer
from app.model.monitor import DriftMonitor
from app.live.broker import LiveBroker
from app.live.notifier import Notifier

PID_FILE = Path(__file__).resolve().parents[2] / "live_bot.pid"

@click.group()
def cli():
    """Binance Bot Projesi - Orkestrasyon CLI"""
    pass

# --- Data Population Group ---
@click.group(name='update')
def update_group():
    """Commands to update various data sources."""
    pass

@update_group.command(name='ohlcv')
def update_ohlcv():
    """Fetches historical OHLCV data."""
    click.echo("Fetching OHLCV data...")
    fetcher = BinanceFetcher()
    storage = DataStorage()
    df = fetcher.get_klines('BTCUSDT', '1h', "365 days ago UTC")
    if not df.empty:
        storage.save_ohlcv(df, 'BTCUSDT', '1h')
    click.echo("OHLCV data updated.")

@update_group.command(name='sentiment')
def update_sentiment():
    """Updates the sentiment data feed."""
    click.echo("Updating sentiment data...")
    SentimentFetcher().fetch_and_analyze()

@update_group.command(name='onchain')
def update_onchain():
    """Updates synthetic on-chain data."""
    click.echo("Updating on-chain data...")
    OnChainFetcher().generate_and_save_data()

# --- Model Lifecycle Group ---
@click.group(name='model')
def model_group():
    """Commands for the AI model lifecycle."""
    pass

@model_group.command(name='generate-features')
def generate_features():
    """Generates feature set for training."""
    click.echo("Generating model features...")
    FeatureEngineer().create_features()

@model_group.command(name='train')
def train_model():
    """Trains a new ADE model and generates baseline stats."""
    click.echo("Training new model...")
    ModelTrainer().train_model()
    DriftMonitor().generate_baseline_stats()
    click.echo("Model training and baseline generation complete.")

@model_group.command(name='monitor-drift')
def monitor_drift():
    """Checks for model drift."""
    click.echo("Monitoring for model drift...")
    features_df = pd.read_parquet("data/derived/model_features.parquet")
    live_sample = features_df.tail(1000)
    drift_report = DriftMonitor().check_for_drift(live_sample)
    if drift_report:
        click.echo("Drift detected!", err=True)

# --- Live Bot Management ---
@cli.command()
def start_live():
    if PID_FILE.exists():
        click.echo("Bot is already running.", err=True)
        return
    script_path = Path(__file__).resolve().parents[2] / "run_live_trader.py"
    process = subprocess.Popen([sys.executable, str(script_path)])
    with open(PID_FILE, 'w') as f: f.write(str(process.pid))
    click.echo(f"Live bot started with PID: {process.pid}")

@cli.command()
def stop_live():
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

cli.add_command(update_group)
cli.add_command(model_group)

if __name__ == '__main__':
    cli()
