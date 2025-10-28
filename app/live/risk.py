class RiskManager:
    """
    Manages portfolio risk, including daily loss limits and emergency stops.
    """
    def __init__(self, initial_capital, daily_loss_limit_pct=2.0):
        """
        Initializes the RiskManager.

        :param initial_capital: The starting capital of the portfolio.
        :param daily_loss_limit_pct: The maximum percentage of capital that can be lost in a day.
        """
        self.initial_capital = initial_capital
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self.daily_loss_limit = initial_capital * (daily_loss_limit_pct / 100.0)

        # State variables
        self.is_paused = False
        self.peak_portfolio_value_today = initial_capital
        print(f"Risk Manager initialized with a daily loss limit of ${self.daily_loss_limit:.2f} ({self.daily_loss_limit_pct}%)")

    def update_peak_value(self, current_portfolio_value):
        """
        Updates the peak portfolio value seen today. This should be called periodically.
        """
        if current_portfolio_value > self.peak_portfolio_value_today:
            self.peak_portfolio_value_today = current_portfolio_value

    def check_loss_limit(self, current_portfolio_value):
        """
        Checks if the daily loss limit has been breached.

        :param current_portfolio_value: The current total value of the portfolio.
        :return: True if the limit is breached, False otherwise.
        """
        if self.is_paused:
            return True # Already paused, so treat as breached to prevent new trades

        drawdown = self.peak_portfolio_value_today - current_portfolio_value

        if drawdown >= self.daily_loss_limit:
            print(f"!!! RISK ALERT: Daily loss limit breached! ---")
            print(f"    Peak Value: ${self.peak_portfolio_value_today:.2f}")
            print(f"    Current Value: ${current_portfolio_value:.2f}")
            print(f"    Drawdown: ${drawdown:.2f} (Limit: ${self.daily_loss_limit:.2f})")
            return True

        return False

    def flatten_and_pause(self):
        """
        Activates the emergency stop mechanism.
        """
        print("--- EMERGENCY: FLATTEN AND PAUSE ACTIVATED ---")
        self.is_paused = True

    def reset_daily_state(self):
        """
        Resets the daily peak value. Should be called at the start of each trading day.
        """
        print("Resetting daily risk manager state.")
        self.peak_portfolio_value_today = self.initial_capital # Or last day's closing value
        self.is_paused = False

# --- Example Usage ---
def main():
    rm = RiskManager(initial_capital=10000, daily_loss_limit_pct=2.5) # 2.5% limit = $250

    # Simulate a good day
    print("\n--- Simulating a profitable day ---")
    portfolio_value = 10100
    rm.update_peak_value(portfolio_value)
    breached = rm.check_loss_limit(portfolio_value)
    print(f"Portfolio: ${portfolio_value}, Breached: {breached}") # Should be False

    # Simulate a small loss
    print("\n--- Simulating a small loss ---")
    portfolio_value = 10050
    rm.update_peak_value(portfolio_value) # Peak doesn't change
    breached = rm.check_loss_limit(portfolio_value)
    print(f"Portfolio: ${portfolio_value}, Breached: {breached}") # Should be False

    # Simulate a larger loss, but still within limits
    print("\n--- Simulating a larger loss ---")
    portfolio_value = 9900
    drawdown = 10100 - 9900 # $200 drawdown
    rm.update_peak_value(portfolio_value)
    breached = rm.check_loss_limit(portfolio_value)
    print(f"Portfolio: ${portfolio_value}, Drawdown: ${drawdown}, Breached: {breached}") # Should be False

    # Simulate a breach of the loss limit
    print("\n--- Simulating a breach ---")
    portfolio_value = 9840
    drawdown = 10100 - 9840 # $260 drawdown
    breached = rm.check_loss_limit(portfolio_value)
    print(f"Portfolio: ${portfolio_value}, Drawdown: ${drawdown}, Breached: {breached}") # Should be True

    if breached:
        rm.flatten_and_pause()

    # Check if new trades would be blocked
    print("\n--- Checking if paused ---")
    breached_after_pause = rm.check_loss_limit(portfolio_value)
    print(f"Is paused: {rm.is_paused}, New trade allowed: {not breached_after_pause}") # Should be True, False

if __name__ == "__main__":
    main()
