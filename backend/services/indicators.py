import pandas as pd
import numpy as np
from backend.config import settings

def calculate_supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0):
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift(1)).abs()
    low_close = (df['low'] - df['close'].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    hl2 = (df['high'] + df['low']) / 2

    basic_upper = hl2 + (multiplier * atr)
    basic_lower = hl2 - (multiplier * atr)

    final_upper = basic_upper.copy()
    final_lower = basic_lower.copy()
    supertrend = pd.Series(np.nan, index=df.index)
    trend = pd.Series(1, index=df.index)

    for i in range(period, len(df)):
        if basic_lower.iloc[i] > final_lower.iloc[i - 1] or df['close'].iloc[i - 1] < final_lower.iloc[i - 1]:
            final_lower.iloc[i] = basic_lower.iloc[i]
        else:
            final_lower.iloc[i] = final_lower.iloc[i - 1]

        if basic_upper.iloc[i] < final_upper.iloc[i - 1] or df['close'].iloc[i - 1] > final_upper.iloc[i - 1]:
            final_upper.iloc[i] = basic_upper.iloc[i]
        else:
            final_upper.iloc[i] = final_upper.iloc[i - 1]

        prev_trend = trend.iloc[i - 1]
        if prev_trend == 1:
            if df['close'].iloc[i] < final_lower.iloc[i]:
                trend.iloc[i] = -1
                supertrend.iloc[i] = final_upper.iloc[i]
            else:
                trend.iloc[i] = 1
                supertrend.iloc[i] = final_lower.iloc[i]
        else:
            if df['close'].iloc[i] > final_upper.iloc[i]:
                trend.iloc[i] = 1
                supertrend.iloc[i] = final_lower.iloc[i]
            else:
                trend.iloc[i] = -1
                supertrend.iloc[i] = final_upper.iloc[i]

    trend_direction = trend.map({1: "BULLISH", -1: "BEARISH"})
    return supertrend, trend_direction, atr

def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0.0).fillna(0.0)
    loss = (-delta.where(delta < 0, 0.0)).fillna(0.0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50.0)

def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['volume'] = df['volume'].fillna(0).astype(float)
    st, direction, atr = calculate_supertrend(
        df, period=settings.ST_PERIOD, multiplier=settings.ST_MULTIPLIER
    )
    df['supertrend'] = st
    df['trend_direction'] = direction
    df['atr_14'] = atr
    df['rsi'] = calculate_rsi(df, period=settings.RSI_PERIOD)
    df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
    return df

def evaluate_rule_signal(row: pd.Series) -> str:
    """Local deterministic rule engine to compare with Gemini."""
    c = row['close']
    st = row['supertrend']
    e9, e21 = row['ema_9'], row['ema_21']
    rsi = row['rsi']

    if c > st and c > e9 and e9 >= e21 and 52 <= rsi <= 70:
        return "BUY_CE"
    if c < st and c < e9 and e9 <= e21 and 30 <= rsi <= 48:
        return "BUY_PE"
    return "NO_TRADE"