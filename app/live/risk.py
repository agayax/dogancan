import pandas as pd

class RiskManager:
    """
    Manages portfolio risk, including daily loss limits, emergency stops,
    and a correlation filter for multi-asset portfolios.
    """
    def __init__(self, initial_capital, daily_loss_limit_pct=2.0, correlation_threshold=0.8):
        self.initial_capital = initial_capital
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self.daily_loss_limit = initial_capital * (daily_loss_limit_pct / 100.0)
        self.correlation_threshold = correlation_threshold

        self.is_paused = False
        self.peak_portfolio_value_today = initial_capital
        print(f"Risk Manager initialized with daily loss limit: ${self.daily_loss_limit:.2f}, correlation threshold: {self.correlation_threshold}")

    def update_peak_value(self, current_portfolio_value):
        if current_portfolio_value > self.peak_portfolio_value_today:
            self.peak_portfolio_value_today = current_portfolio_value

    def check_loss_limit(self, current_portfolio_value):
        if self.is_paused:
            return True
        drawdown = self.peak_portfolio_value_today - current_portfolio_value
        if drawdown >= self.daily_loss_limit:
            print(f"!!! RISK ALERT: Daily loss limit breached! Drawdown: ${drawdown:.2f}")
            return True
        return False

    def check_correlation(self, new_asset_symbol, current_portfolio_assets, historical_data_dict):
        """
        Checks if a new asset is too correlated with assets already in the portfolio.

        :param new_asset_symbol: The symbol of the asset to be added.
        :param current_portfolio_assets: A list of symbols currently in the portfolio.
        :param historical_data_dict: A dictionary of historical data DataFrames for all relevant assets.
        :return: True if correlation is too high, False otherwise.
        """
        if not current_portfolio_assets:
            return False # No existing assets to correlate against

        # Combine the returns of all assets into a single DataFrame
        returns_list = []
        all_assets = current_portfolio_assets + [new_asset_symbol]
        for symbol in all_assets:
            if symbol in historical_data_dict:
                returns = historical_data_dict[symbol]['close'].pct_change().rename(symbol)
                returns_list.append(returns)

        if len(returns_list) < 2:
            return False # Not enough data to compare

        combined_returns = pd.concat(returns_list, axis=1).dropna()
        correlation_matrix = combined_returns.corr()

        # Get the correlations of the new asset with the existing ones
        correlations_with_new = correlation_matrix[new_asset_symbol].drop(new_asset_symbol)

        # Check if any correlation exceeds the threshold
        if (correlations_with_new > self.correlation_threshold).any():
            highly_correlated_asset = correlations_with_new[correlations_with_new > self.correlation_threshold].idxmax()
            print(f"!!! RISK ALERT: High correlation detected for {new_asset_symbol} with {highly_correlated_asset} ({correlations_with_new.max():.2f}). Trade blocked.")
            return True

        return False

    def flatten_and_pause(self):
        print("--- EMERGENCY: FLATTEN AND PAUSE ACTIVATED ---")
        self.is_paused = True

    def reset_daily_state(self):
        self.peak_portfolio_value_today = self.initial_capital
        self.is_paused = False
