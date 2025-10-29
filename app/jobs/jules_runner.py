import click
import os
import sys
import subprocess
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

# ... (all necessary imports from previous versions)
from app.data.fetcher import BinanceFetcher
from app.data.storage import DataStorage
from app.data.sentiment_fetcher import SentimentFetcher
from app.data.onchain_fetcher import OnChainFetcher
from app.features.engineer import FeatureEngineer
from app.model.train import ModelTrainer
from app.model.monitor import DriftMonitor
from app.backtest.engine import PortfolioBacktestEngine
from app.strategy.fused_rsr import FusedRSRStrategy


PID_FILE = Path(__file__).resolve().parents[2] / "live_bot.pid"

@click.group()
def cli():
    """Binance Bot Projesi - Orkestrasyon CLI"""
    pass

# --- Command Groups ---
@click.group(name='update')
def update_group():
    """Update data sources."""
    pass

@click.group(name='model')
def model_group():
    """Manage the AI model lifecycle."""
    pass

# --- Update Commands ---
# ... (update_ohlcv, update_sentiment, update_onchain commands)

# --- Model Commands ---
# ... (generate_features, train, monitor_drift commands)

# --- NEW Chaos Command ---
@cli.command()
@click.option('--resilience-threshold', default=0.5, help='Minimum acceptable resilience score.')
def run_chaos_backtest(resilience_threshold):
    """Runs standard and chaos backtests to generate a resilience score."""
    click.echo("--- Starting Resilience Test ---")
    storage = DataStorage()
    data_dict = {'BTCUSDT': storage.read_ohlcv('BTCUSDT', '1h')}
    strategy = FusedRSRStrategy(top_k=1)

    chaos_params = {'latency_chance': 0.05, 'rejection_chance': 0.02, 'data_gap_chance': 0.01}
    scenario_path = "scenarios/fomc_stress_test.yaml"

    click.echo("\nRunning STANDARD backtest...")
    engine_std = PortfolioBacktestEngine(data_dict, strategy)
    std_results = engine_std.run()

    click.echo("\nRunning CHAOS backtest...")
    engine_chaos = PortfolioBacktestEngine(data_dict, strategy)
    chaos_results = engine_chaos.run(chaos_params=chaos_params, scenario_path=scenario_path)

    resilience_score = engine_chaos.generate_resilience_report(std_results, chaos_results, "resilience_report.json")

    if resilience_score < resilience_threshold:
        click.echo(f"\nCRITICAL: Resilience score ({resilience_score:.2f}) is below threshold.", err=True)
        sys.exit(1)
    else:
        click.echo(f"\nSUCCESS: Resilience score ({resilience_score:.2f}) is acceptable.")


# --- Live Bot Management ---
# ... (start_live, stop_live commands)

# Add command groups to the main CLI
cli.add_command(update_group)
cli.add_command(model_group)

if __name__ == '__main__':
    cli()
