import asyncio
from binance import AsyncClient, BinanceSocketManager
import pandas as pd

class BinanceWebsocketClient:
    """
    Connects to Binance WebSocket streams and processes live candlestick data.
    """
    def __init__(self, symbol, interval, data_callback):
        """
        Initializes the WebSocket client.

        :param symbol: The trading symbol (e.g., 'BTCUSDT').
        :param interval: The interval for k-lines (e.g., '1m', '5m').
        :param data_callback: An async function to be called with each new kline data.
        """
        self.symbol = symbol
        self.interval = interval
        self.data_callback = data_callback
        self.bsm = None
        self.client = None

    async def _process_message(self, msg):
        """
        Processes an incoming WebSocket message and calls the callback.
        """
        if msg.get('e') == 'error':
            print(f"WebSocket Error: {msg['m']}")
        elif msg.get('e') == 'kline':
            kline = msg['k']
            if kline['x']:  # Check if the kline is closed
                # Format the kline data similarly to the historical fetcher for consistency
                kline_data = {
                    'timestamp': pd.to_datetime(kline['t'], unit='ms'),
                    'open': float(kline['o']),
                    'high': float(kline['h']),
                    'low': float(kline['l']),
                    'close': float(kline['c']),
                    'volume': float(kline['v']),
                }
                # The callback function must be awaitable
                await self.data_callback(kline_data)

    async def start(self):
        """
        Starts the WebSocket connection and listens for data.
        """
        self.client = await AsyncClient.create()
        self.bsm = BinanceSocketManager(self.client)

        socket = self.bsm.kline_socket(self.symbol, self.interval)

        print(f"Connecting to Binance WebSocket for {self.symbol}@{self.interval}...")
        async with socket as stream:
            while True:
                msg = await stream.recv()
                await self._process_message(msg)

    async def stop(self):
        """
        Closes the WebSocket connection.
        """
        if self.client:
            await self.client.close_connection()
        print("WebSocket connection closed.")


# --- Example Usage ---
async def example_callback(kline_data):
    """
    An example callback function that just prints the received kline data.
    """
    df = pd.DataFrame([kline_data]).set_index('timestamp')
    print("\n--- New Kline Received ---")
    print(df)
    print("------------------------")

async def main():
    """
    Main function to run the example.
    """
    # Use a well-known symbol that has frequent updates
    ws_client = BinanceWebsocketClient(symbol="BTCUSDT", interval="1m", data_callback=example_callback)

    try:
        await ws_client.start()
    except KeyboardInterrupt:
        await ws_client.stop()

if __name__ == "__main__":
    # To run this example, you might need to install nest_asyncio in some environments
    # pip install nest_asyncio
    # import nest_asyncio
    # nest_asyncio.apply()

    # Run the asyncio event loop
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program interrupted by user.")
