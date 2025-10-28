import pandas as pd
import numpy as np
import json

class EmaAtrStrategy:
    """
    A trading strategy based on EMA crossover and an ATR volatility filter,
    refactored to provide structured reasons for its signals (XAI).
    """
    def __init__(self, fast_ema_period=12, slow_ema_period=26, atr_period=14, atr_multiplier=2.0):
        self.fast_ema_period = fast_ema_period
        self.slow_ema_period = slow_ema_period
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier

    def _calculate_ema(self, series, period):
        return series.ewm(span=period, adjust=False).mean()

    def _calculate_atr(self, df, period):
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return self._calculate_ema(tr, period)

    def generate_signals(self, ohlcv_df):
        if ohlcv_df.empty:
            return pd.DataFrame()

        df = ohlcv_df.copy()

        # Calculate indicators
        fast_ema_col = f'EMA_{self.fast_ema_period}'
        slow_ema_col = f'EMA_{self.slow_ema_period}'
        atr_col = f'ATR_{self.atr_period}'

        df[fast_ema_col] = self._calculate_ema(df['close'], self.fast_ema_period)
        df[slow_ema_col] = self._calculate_ema(df['close'], self.slow_ema_period)
        df[atr_col] = self._calculate_atr(df, self.atr_period)

        df.dropna(inplace=True)

        if df.empty:
            return df

        atr_threshold = df[atr_col].rolling(window=self.slow_ema_period).mean() * self.atr_multiplier

        # --- Signal Logic with Explainability ---
        df['signal'] = 0
        df['reason'] = [{} for _ in range(len(df))]

        # Conditions
        crossover_up = (df[fast_ema_col] > df[slow_ema_col]) & (df[fast_ema_col].shift(1) <= df[slow_ema_col].shift(1))
        crossover_down = (df[fast_ema_col] < df[slow_ema_col]) & (df[fast_ema_col].shift(1) >= df[slow_ema_col].shift(1))
        volatility_filter_passed = (df[atr_col] > atr_threshold)

        # Generate signals and reasons
        for i in range(len(df)):
            reason = {}
            if crossover_up.iloc[i]:
                reason['ema_crossover'] = 'bullish'
                if volatility_filter_passed.iloc[i]:
                    reason['volatility_filter'] = 'passed'
                    df.iat[i, df.columns.get_loc('signal')] = 1
                else:
                    reason['volatility_filter'] = 'failed'

            elif crossover_down.iloc[i]:
                reason['ema_crossover'] = 'bearish'
                df.iat[i, df.columns.get_loc('signal')] = -1

            if reason:
                 # Use .loc with index to safely set the dictionary value
                df.at[df.index[i], 'reason'] = reason

        return df

if __name__ == '__main__':
    close_prices = [100 + i + (i % 10 - 5) * 2 + np.sin(i/5.0) * 3 for i in range(150)]
    data = {'open': [p - 1 for p in close_prices], 'high': [p + 2 for p in close_prices], 'low': [p - 2 for p in close_prices], 'close': close_prices, 'volume': [1000 + i * 10 for i in range(150)]}
    sample_df = pd.DataFrame(data, index=pd.to_datetime(pd.date_range(start='2023-01-01', periods=150)))

    strategy = EmaAtrStrategy(fast_ema_period=10, slow_ema_period=30, atr_period=14)
    signals_df = strategy.generate_signals(sample_df)

    print("--- Generated Signals with Reasons (XAI) ---")
    signals_with_trades = signals_df[signals_df['signal'] != 0].copy()

    if not signals_with_trades.empty:
        # Convert reason dict to string for printing
        signals_with_trades['reason_str'] = signals_with_trades['reason'].apply(lambda x: json.dumps(x))
        print(signals_with_trades[['close', 'signal', 'reason_str']])
    else:
        print("No signals generated for the sample data.")
