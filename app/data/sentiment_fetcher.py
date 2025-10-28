import feedparser
import pandas as pd
from pathlib import Path
import time
from datetime import datetime
import random

# Adjust import path to access the LLM service
import sys
sys.path.append(str(Path(__file__).resolve().parents[2]))
from app.services.llm import LLMService

class SentimentFetcher:
    """
    Fetches news from RSS feeds, performs sentiment analysis using a simulated LLM,
    and stores the results in a Parquet file.
    """
    def __init__(self, output_path="data/derived/sentiment_feed.parquet"):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.llm_service = LLMService() # Using the simulated service

        # A list of public crypto news RSS feeds
        self.rss_feeds = [
            "https://cointelegraph.com/rss",
            "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "https://bitcoinmagazine.com/.rss/full/",
        ]

    def _get_sentiment_score(self, text):
        """
        Simulates LLM sentiment analysis.
        In a real scenario, this would call an actual LLM.
        Here, we use keywords for a basic simulation.
        """
        text_lower = text.lower()
        if any(word in text_lower for word in ["crash", "hack", "scam", "ban", "fear"]):
            return random.uniform(-1.0, -0.5)
        elif any(word in text_lower for word in ["bullish", "rally", "partnership", "growth", "adopt"]):
            return random.uniform(0.5, 1.0)
        elif any(word in text_lower for word in ["regulation", "stable", "discussion"]):
            return random.uniform(-0.2, 0.2)
        else:
            return random.uniform(-0.4, 0.4)

    def fetch_and_analyze(self):
        """
        Fetches new entries from all RSS feeds and appends them to the Parquet file.
        """
        print("Fetching and analyzing news sentiment...")

        new_entries = []
        for feed_url in self.rss_feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries:
                    published_time = time.mktime(entry.published_parsed)
                    new_entries.append({
                        'timestamp': datetime.fromtimestamp(published_time),
                        'source': feed.feed.title,
                        'title': entry.title,
                        'summary': entry.summary,
                        'link': entry.link,
                        'sentiment_score': self._get_sentiment_score(entry.title + " " + entry.summary)
                    })
            except Exception as e:
                print(f"Failed to parse feed {feed_url}: {e}")

        if not new_entries:
            print("No new entries found.")
            return

        new_df = pd.DataFrame(new_entries)

        # --- Append to Parquet file, handling duplicates ---
        if self.output_path.exists():
            existing_df = pd.read_parquet(self.output_path)
            combined_df = pd.concat([existing_df, new_df]).drop_duplicates(subset=['link'], keep='last')
        else:
            combined_df = new_df

        combined_df.sort_values(by='timestamp', ascending=False, inplace=True)
        combined_df.to_parquet(self.output_path, index=False)

        print(f"Sentiment analysis complete. Total entries in feed: {len(combined_df)}")

# --- Example Usage ---
if __name__ == '__main__':
    fetcher = SentimentFetcher()
    fetcher.fetch_and_analyze()

    # Verify the output
    if Path("data/derived/sentiment_feed.parquet").exists():
        df = pd.read_parquet("data/derived/sentiment_feed.parquet")
        print("\n--- Sentiment Feed Sample ---")
        print(df.head())
        print("---------------------------")
