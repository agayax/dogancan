import pandas as pd
import numpy as np

class EmaAtrStrategy:
    """
    A trading strategy based on EMA crossover and an ATR volatility filter.
    Indicator calculations are implemented manually using pandas.
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
        df[f'EMA_{self.fast_ema_period}'] = self._calculate_ema(df['close'], self.fast_ema_period)
        df[f'EMA_{self.slow_ema_period}'] = self._calculate_ema(df['close'], self.slow_ema_period)
        df[f'ATR_{self.atr_period}'] = self._calculate_atr(df, self.atr_period)

        df.dropna(inplace=True)

        if df.empty:
            return df

        atr_threshold = df[f'ATR_{self.atr_period}'].rolling(window=self.slow_ema_period).mean() * self.atr_multiplier

        # Generate signals
        df['signal'] = 0
        long_condition = (df[f'EMA_{self.fast_ema_period}'] > df[f'EMA_{self.slow_ema_period}']) & \
                         (df[f'EMA_{self.fast_ema_period}'].shift(1) <= df[f'EMA_{self.slow_ema_period}'].shift(1)) & \
                         (df[f'ATR_{self.atr_period}'] > atr_threshold)

        short_condition = (df[f'EMA_{self.fast_ema_period}'] < df[f'EMA_{self.slow_ema_period}']) & \
                          (df[f'EMA_{self.fast_ema_period}'].shift(1) >= df[f'EMA_{self.slow_ema_period}'].shift(1))

        df.loc[long_condition, 'signal'] = 1
        df.loc[short_condition, 'signal'] = -1

        return df

if __name__ == '__main__':
    close_prices = [100 + i + (i % 5 - 2) * 3 for i in range(100)]
    data = {
        'open': [p - 1 for p in close_prices],
        'high': [p + 2 for p in close_prices],
        'low': [p - 2 for p in close_prices],
        'close': close_prices,
        'volume': [1000 + i * 10 for i in range(100)]
    }
    sample_df = pd.DataFrame(data, index=pd.to_datetime(pd.date_range(start='2023-01-01', periods=100)))

    strategy = EmaAtrStrategy(fast_ema_period=5, slow_ema_period=10, atr_period=7)
    signals_df = strategy.generate_signals(sample_df)

    print("Generated Signals:")
    signals_with_trades = signals_df[signals_df['signal'] != 0]
    if not signals_with_trades.empty:
        print(signals_with_trades[['close', f'EMA_5', f'EMA_10', f'ATR_7', 'signal']])
    else:
        print("No signals generated for the sample data.")
