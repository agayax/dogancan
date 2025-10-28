import os
import asyncio
from telegram import Bot
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Notifier:
    """
    Handles sending messages to a Telegram channel.
    """
    def __init__(self):
        """
        Initializes the Notifier with credentials from environment variables.
        """
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")

        if not self.bot_token or not self.chat_id:
            print("Warning: Telegram bot token or chat ID is not set in the .env file. Notifications will be disabled.")
            self.bot = None
        else:
            self.bot = Bot(token=self.bot_token)
            print("Telegram Notifier initialized.")

    async def send_message(self, message):
        """
        Sends a message to the configured Telegram chat.

        :param message: The text message to send.
        """
        if self.bot:
            try:
                await self.bot.send_message(chat_id=self.chat_id, text=message, parse_mode='Markdown')
                print(f"Sent Telegram notification: '{message}'")
            except Exception as e:
                print(f"Failed to send Telegram notification: {e}")
        else:
            # If bot is not configured, just print the message to the console
            print(f"Skipping Telegram notification (not configured): '{message}'")

# --- Example Usage ---
async def main():
    """
    Main function to test the Notifier.
    """
    notifier = Notifier()

    # Check if the notifier was initialized correctly
    if notifier.bot:
        await notifier.send_message("Hello from the Binance Bot! This is a test message.")

        # Example of a formatted trade notification
        trade_message = (
            "*Trade Alert*\n\n"
            "*Type:* BUY\n"
            "*Symbol:* BTCUSDT\n"
            "*Price:* $70,000.50\n"
            "*Quantity:* 0.1 BTC"
        )
        await notifier.send_message(trade_message)
    else:
        print("Notifier example finished: Bot not configured.")

if __name__ == "__main__":
    # To run this example, you need to have a .env file with
    # TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID set.
    asyncio.run(main())
