class LLMService:
    """
    A simulated LLM service for generating natural language explanations.
    This avoids the need for a real API key for core functionality.
    """

    def summarize_backtest(self, metrics):
        """
        Generates a natural language summary of backtest performance metrics.

        :param metrics: A dictionary of performance metrics (e.g., {'Total Return (%)': 15.5, 'Sharpe Ratio': 1.2}).
        :return: A string containing a natural language summary.
        """
        total_return = metrics.get('Total Return (%)', [0])[0]
        sharpe = metrics.get('Sharpe Ratio (Annualized)', [0])[0]
        max_drawdown = metrics.get('Max Drawdown (%)', [0])[0]

        summary = "### LLM-Powered Performance Analysis\n\n"

        # Performance commentary
        if total_return > 20:
            summary += f"The strategy showed strong performance with a total return of {total_return:.2f}%. "
        elif total_return > 5:
            summary += f"The strategy delivered a moderate positive return of {total_return:.2f}%. "
        else:
            summary += f"The strategy's performance was weak, with a total return of {total_return:.2f}%. "

        # Sharpe ratio commentary
        if sharpe > 1.0:
            summary += f"Its risk-adjusted return is excellent, indicated by a Sharpe Ratio of {sharpe:.2f}. "
        elif sharpe > 0.5:
            summary += f"The risk-adjusted return is decent, with a Sharpe Ratio of {sharpe:.2f}. "
        else:
            summary += f"However, its risk-adjusted return is low (Sharpe Ratio: {sharpe:.2f}), suggesting returns may not justify the risk. "

        # Drawdown commentary
        if abs(max_drawdown) > 20:
            summary += f"The strategy experienced a significant maximum drawdown of {max_drawdown:.2f}%, which is a key area for improvement. "
        elif abs(max_drawdown) > 10:
            summary += f"It managed risk reasonably well, with a maximum drawdown of {max_drawdown:.2f}%. "

        # Recommendations
        summary += "\n\n**Recommendations:**\n"
        if sharpe < 0.8 and abs(max_drawdown) > 15:
            summary += "- Consider adding a market regime filter (e.g., using a long-term moving average) to avoid trading in unfavorable market conditions.\n"
        if total_return < 5:
            summary += "- The strategy parameters may not be optimal. Further hyperparameter tuning is recommended.\n"

        summary += "- Always assess this strategy's performance on out-of-sample data before considering live deployment.\n"

        return summary

    def explain_trade_reason(self, reason_dict):
        """
        Converts a structured trade reason into a natural language explanation.

        :param reason_dict: A dictionary explaining the trade (e.g., {'ema_crossover': 'bullish', 'volatility_filter': 'passed'}).
        :return: A string containing a natural language explanation.
        """
        if not reason_dict:
            return "No specific reason was logged for this action."

        explanation = "I executed this trade based on the following logic:\n"

        # EMA Crossover
        crossover = reason_dict.get('ema_crossover')
        if crossover == 'bullish':
            explanation += "- **EMA Crossover:** The fast Exponential Moving Average crossed above the slow EMA, indicating potential upward momentum.\n"
        elif crossover == 'bearish':
            explanation += "- **EMA Crossover:** The fast Exponential Moving Average crossed below the slow EMA, suggesting potential downward momentum.\n"

        # Volatility Filter
        vol_filter = reason_dict.get('volatility_filter')
        if vol_filter == 'passed':
            explanation += "- **Volatility Filter:** The market volatility (measured by ATR) was high enough, confirming the signal's strength.\n"
        elif vol_filter == 'failed':
            explanation += "- **Signal Ignored:** Although an EMA crossover occurred, the market volatility was too low, so the signal was filtered out to avoid a potentially weak move.\n"

        return explanation.strip()

# --- Example Usage ---
def main():
    llm = LLMService()

    # 1. Example: Summarize backtest results
    print("--- Backtest Summary Example ---")
    mock_metrics = {
        'Total Return (%)': [8.2],
        'Sharpe Ratio (Annualized)': [0.65],
        'Max Drawdown (%)': [-12.5],
    }
    summary = llm.summarize_backtest(mock_metrics)
    print(summary)

    # 2. Example: Explain a trade reason
    print("\n--- Trade Explanation Example ---")
    mock_reason = {'ema_crossover': 'bullish', 'volatility_filter': 'passed'}
    explanation = llm.explain_trade_reason(mock_reason)
    print(explanation)

if __name__ == "__main__":
    main()
