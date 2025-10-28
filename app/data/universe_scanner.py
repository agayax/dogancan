import ccxt
import pandas as pd
import json
from sklearn.preprocessing import MinMaxScaler
from pathlib import Path

class UniverseScanner:
    """
    Scans the exchange for all USDT pairs, scores them based on volume and volatility,
    and categorizes them into tiers.
    """
    def __init__(self, output_path="data/meta/universe.json"):
        self.exchange = ccxt.binance({'options': {'defaultType': 'spot'}})
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def scan_and_score(self, w_volume=0.7, w_volatility=0.3):
        """
        Fetches all USDT pairs, calculates metrics, scores them, and saves the result.

        The score is a weighted average of normalized 24h volume and 24h volatility.
        score = w1 * norm(volume_24h) + w2 * norm(volatility_24h)
        """
        print("Scanning the universe of USDT pairs...")

        # 1. Fetch all tickers
        tickers = self.exchange.fetch_tickers()
        usdt_pairs = [ticker for ticker in tickers.values() if 'USDT' in ticker['symbol'] and '/' in ticker['symbol']]

        if not usdt_pairs:
            print("No USDT pairs found.")
            return

        # 2. Build a DataFrame with relevant metrics
        data = []
        for pair in usdt_pairs:
            # Calculate 24h volatility
            high = pair.get('high', 0)
            low = pair.get('low', 0)
            if high is not None and low is not None and high > 0:
                volatility_24h = ((high - low) / high) * 100
            else:
                volatility_24h = 0

            data.append({
                'symbol': pair['symbol'],
                'volume_24h': pair.get('quoteVolume', 0),
                'volatility_24h': volatility_24h,
            })

        df = pd.DataFrame(data)
        df = df[df['volume_24h'] > 1000000] # Pre-filter pairs with very low volume
        df.set_index('symbol', inplace=True)

        # 3. Normalize metrics using MinMaxScaler
        scaler = MinMaxScaler()
        df_scaled = pd.DataFrame(scaler.fit_transform(df), columns=df.columns, index=df.index)

        # 4. Calculate the final score
        df['score'] = (w_volume * df_scaled['volume_24h'] + w_volatility * df_scaled['volatility_24h'])
        df = df.sort_values(by='score', ascending=False)

        # 5. Categorize into Tiers
        # TIER-1: Top 20
        # TIER-2: Next 30
        # TIER-3: The rest
        tier1 = df.head(20).index.tolist()
        tier2 = df.iloc[20:50].index.tolist()
        tier3 = df.iloc[50:].index.tolist()

        universe = {
            'timestamp': pd.Timestamp.utcnow().isoformat(),
            'tier_1_assets': tier1,
            'tier_2_assets': tier2,
            'tier_3_assets': tier3,
            'details': df.reset_index().to_dict(orient='records')
        }

        # 6. Save to JSON
        with open(self.output_path, 'w') as f:
            json.dump(universe, f, indent=4)

        print(f"Universe scan complete. {len(df)} assets scored and categorized.")
        print(f"Results saved to {self.output_path}")
        print(f"Top 5 TIER-1 Assets: {tier1[:5]}")

# --- Example Usage ---
if __name__ == '__main__':
    scanner = UniverseScanner()
    scanner.scan_and_score()
