import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

class OnChainFetcher:
    """
    Simulates the fetching of daily on-chain metrics.
    This generates a synthetic but realistic dataset to avoid reliance on external APIs.
    """
    def __init__(self, output_path="data/derived/onchain_daily.parquet"):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def generate_and_save_data(self, days=365):
        """
        Generates synthetic daily on-chain data and saves it to a Parquet file.
        """
        print("Generating synthetic on-chain data...")

        # --- Data Generation ---
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        date_range = pd.to_datetime(pd.date_range(start=start_date, end=end_date, freq='D'))

        # 1. BTC Active Addresses
        # Simulates a random walk with some trend
        btc_active_addresses = 500000 + (np.random.randn(len(date_range)).cumsum() * 5000) + (np.arange(len(date_range)) * 1000)

        # 2. ETH Active Addresses
        eth_active_addresses = 400000 + (np.random.randn(len(date_range)).cumsum() * 4000) + (np.arange(len(date_range)) * 800)

        # 3. ETH Average Gas Price (Gwei)
        # Simulates base fee with occasional spikes
        gas_base = 20 + np.sin(np.arange(len(date_range)) / 30) * 10
        gas_spikes = np.random.choice([0, 0, 0, 1, 0], size=len(date_range)) * np.random.uniform(50, 200, size=len(date_range))
        eth_gas_gwei = gas_base + gas_spikes

        # --- DataFrame Creation ---
        df = pd.DataFrame({
            'timestamp': date_range,
            'btc_active_addresses': btc_active_addresses.astype(int),
            'eth_active_addresses': eth_active_addresses.astype(int),
            'eth_avg_gas_gwei': eth_gas_gwei.round(2),
        })

        # --- Save to Parquet ---
        df.to_parquet(self.output_path, index=False)
        print(f"Synthetic on-chain data generated and saved to {self.output_path}")

# --- Example Usage ---
if __name__ == '__main__':
    fetcher = OnChainFetcher()
    fetcher.generate_and_save_data()

    # Verify the output
    if Path("data/derived/onchain_daily.parquet").exists():
        df = pd.read_parquet("data/derived/onchain_daily.parquet")
        print("\n--- On-Chain Data Sample ---")
        print(df.head())
        print("...")
        print(df.tail())
        print("----------------------------")
