import pandas as pd

def apply_ema_strategy(data):
    if len(data) < 2:
        return "HOLD"

    data["EMA_9"] = data["Close"].ewm(span=9, adjust=False).mean()
    data["EMA_21"] = data["Close"].ewm(span=21, adjust=False).mean()

    current_ema9 = data["EMA_9"].iloc[-1]
    current_ema21 = data["EMA_21"].iloc[-1]
    prev_ema9 = data["EMA_9"].iloc[-2]
    prev_ema21 = data["EMA_21"].iloc[-2]

    # Handle potential DataFrame/Series structures due to MultiIndex columns
    if isinstance(current_ema9, pd.Series):
        current_ema9 = current_ema9.iloc[0]
        current_ema21 = current_ema21.iloc[0]
        prev_ema9 = prev_ema9.iloc[0]
        prev_ema21 = prev_ema21.iloc[0]

    current_ema9 = float(current_ema9)
    current_ema21 = float(current_ema21)
    prev_ema9 = float(prev_ema9)
    prev_ema21 = float(prev_ema21)

    if prev_ema9 <= prev_ema21 and current_ema9 > current_ema21:
        return "BUY"
    elif prev_ema9 >= prev_ema21 and current_ema9 < current_ema21:
        return "SELL"
    else:
        return "HOLD"