import pandas as pd
import json
from pathlib import Path

from .relative_strength_rotation import RelativeStrengthRotationStrategy

class FusedRSRStrategy(RelativeStrengthRotationStrategy):
    """
    Extends the RSR strategy by applying "Macro Regime Filters" based on
    sentiment and on-chain data to the baseline momentum portfolio.
    """
    def __init__(self, sentiment_path="data/derived/sentiment_feed.parquet", onchain_path="data/derived/onchain_daily.parquet", **kwargs):
        super().__init__(**kwargs)
        self.sentiment_path = Path(sentiment_path)
        self.onchain_path = Path(onchain_path)

        # Load macro data
        self.sentiment_df = pd.read_parquet(self.sentiment_path) if self.sentiment_path.exists() else pd.DataFrame()
        self.onchain_df = pd.read_parquet(self.onchain_path) if self.onchain_path.exists() else pd.DataFrame()

    def generate_target_portfolio(self, historical_data_slice):
        # 1. Get the baseline portfolio from the parent RSR strategy
        base_target_portfolio = super().generate_target_portfolio(historical_data_slice)

        if not base_target_portfolio:
            return {}

        print("Applying Macro Regime Filters...")
        filtered_portfolio = base_target_portfolio.copy()

        # --- Sentiment Filter ---
        if not self.sentiment_df.empty:
            # Average sentiment over the last 24 hours
            recent_sentiment = self.sentiment_df[self.sentiment_df['timestamp'] > (pd.Timestamp.utcnow() - pd.Timedelta(days=1))]
            avg_sentiment = recent_sentiment['sentiment_score'].mean() if not recent_sentiment.empty else 0.0

            if avg_sentiment < -0.3: # "Panic" or "Fear" threshold
                print(f"  - SENTIMENT FILTER: Negative sentiment ({avg_sentiment:.2f}) detected. Blocking all new buy signals.")
                return {} # Return an empty portfolio to liquidate positions

        # --- On-Chain Filter (Active Addresses) ---
        if not self.onchain_df.empty and 'btc_active_addresses' in self.onchain_df.columns:
            # Check 7-day momentum of BTC active addresses
            onchain_recent = self.onchain_df.tail(7)
            if len(onchain_recent) >= 7:
                momentum = onchain_recent['btc_active_addresses'].iloc[-1] - onchain_recent['btc_active_addresses'].iloc[0]
                if momentum < 0:
                    print(f"  - ON-CHAIN FILTER: Negative 7-day momentum in BTC active addresses. Reducing position sizes by 50%.")
                    for symbol in filtered_portfolio:
                        filtered_portfolio[symbol] *= 0.5 # Cut risk in half

        # Gas Filter is more suited for live trading logic (halting trades),
        # but we can simulate its effect by reducing portfolio size if needed.

        return filtered_portfolio

# --- Example Usage ---
if __name__ == '__main__':
    # Setup for a realistic test
    # (Requires dummy data files to be created first)
    pass
