import pandas as pd
import json
from pathlib import Path

class RelativeStrengthRotationStrategy:
    """
    A cross-sectional momentum strategy that rotates a portfolio based on relative strength.
    """
    def __init__(self, universe_path="data/meta/universe.json", lookback_period=90, top_k=5):
        """
        Initializes the RSR strategy.

        :param universe_path: Path to the universe.json file.
        :param lookback_period: The number of days to calculate returns for momentum scoring.
        :param top_k: The number of top-performing assets to include in the target portfolio.
        """
        self.universe_path = Path(universe_path)
        self.lookback_period = lookback_period
        self.top_k = top_k
        self._load_universe()

    def _load_universe(self):
        """Loads the TIER-1 and TIER-2 assets from the universe file."""
        if not self.universe_path.exists():
            raise FileNotFoundError(f"Universe file not found at {self.universe_path}")

        with open(self.universe_path, 'r') as f:
            universe_data = json.load(f)

        # We use TIER-1 and TIER-2 assets for our strategy
        self.universe = universe_data.get('tier_1_assets', []) + universe_data.get('tier_2_assets', [])
        print(f"RSR Strategy loaded a universe of {len(self.universe)} assets.")

    def generate_target_portfolio(self, historical_data_slice):
        """
        Generates the target portfolio based on relative strength scores.

        :param historical_data_slice: A dictionary of DataFrames {symbol: df} containing
                                      all historical data up to the rebalancing date.
        :return: A dictionary representing the target portfolio, e.g., {'BTC/USDT': 0.2, 'ETH/USDT': 0.2, ...}.
        """
        momentum_scores = {}

        for symbol in self.universe:
            if symbol in historical_data_slice and not historical_data_slice[symbol].empty:
                df = historical_data_slice[symbol]

                # Calculate Rate of Change (ROC) over the lookback period
                if len(df) >= self.lookback_period:
                    price_then = df['close'].iloc[-self.lookback_period]
                    price_now = df['close'].iloc[-1]
                    momentum = (price_now - price_then) / price_then if price_then != 0 else 0
                    momentum_scores[symbol] = momentum

        if not momentum_scores:
            return {}

        # Sort assets by their momentum score
        sorted_assets = sorted(momentum_scores.items(), key=lambda item: item[1], reverse=True)

        # Select the top K assets for the new portfolio
        top_assets = [item[0] for item in sorted_assets[:self.top_k]]

        # Assign equal weights to the top assets
        target_portfolio = {asset: 1.0 / self.top_k for asset in top_assets}

        print(f"  - Top {self.top_k} assets for target portfolio: {list(target_portfolio.keys())}")

        return target_portfolio

# --- Example Usage ---
if __name__ == '__main__':
    # This example requires a universe.json file and historical data for the assets.
    # We will simulate this for demonstration purposes.

    # 1. Create a dummy universe.json
    dummy_universe = {
        "tier_1_assets": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
        "tier_2_assets": ["XRP/USDT", "ADA/USDT", "DOGE/USDT"]
    }
    Path("data/meta").mkdir(parents=True, exist_ok=True)
    with open("data/meta/universe.json", "w") as f:
        json.dump(dummy_universe, f)

    # 2. Create dummy historical data
    dummy_data_slice = {}
    # Make ETH the strongest performer
    dummy_data_slice["BTC/USDT"] = pd.DataFrame({'close': np.linspace(100, 110, 100)})
    dummy_data_slice["ETH/USDT"] = pd.DataFrame({'close': np.linspace(100, 120, 100)})
    dummy_data_slice["SOL/USDT"] = pd.DataFrame({'close': np.linspace(100, 115, 100)})
    dummy_data_slice["XRP/USDT"] = pd.DataFrame({'close': np.linspace(100, 105, 100)})

    # 3. Instantiate and run the strategy
    rsr_strategy = RelativeStrengthRotationStrategy(lookback_period=90, top_k=2)
    target_portfolio = rsr_strategy.generate_target_portfolio(dummy_data_slice)

    print("\n--- Generated Target Portfolio ---")
    print(target_portfolio)
    # Expected output: {'ETH/USDT': 0.5, 'SOL/USDT': 0.5} because they have the highest returns.
