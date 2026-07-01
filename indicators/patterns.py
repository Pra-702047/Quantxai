import pandas as pd
import numpy as np

def clean_series(df, col_name):
    col = df[col_name]
    if isinstance(col, pd.DataFrame):
        return col.iloc[:, 0]
    return col

def detect_candlestick_patterns(df) -> dict:
    """
    Scans the last 2 candles for key price action formations:
    Engulfing, Hammer, Shooting Star, and Doji.
    """
    if len(df) < 5:
        return {"pattern": "None", "signal": 0}
        
    opens = clean_series(df, "Open")
    highs = clean_series(df, "High")
    lows = clean_series(df, "Low")
    closes = clean_series(df, "Close")
    
    # Last candle values (index -1)
    o0, h0, l0, c0 = float(opens.iloc[-1]), float(highs.iloc[-1]), float(lows.iloc[-1]), float(closes.iloc[-1])
    # Previous candle values (index -2)
    o1, h1, l1, c1 = float(opens.iloc[-2]), float(highs.iloc[-2]), float(lows.iloc[-2]), float(closes.iloc[-2])
    
    body0 = abs(c0 - o0)
    range0 = h0 - l0 if (h0 - l0) > 0 else 0.01
    
    # 1. Doji Detection
    if body0 <= (range0 * 0.1):
        return {"pattern": "Doji Indecision", "signal": 0}
        
    # 2. Engulfing Detection
    if c1 < o1 and c0 > o0:  # Bearish -> Bullish
        if c0 >= o1 and o0 <= c1:
            return {"pattern": "Bullish Engulfing", "signal": 1}
    elif c1 > o1 and c0 < o0:  # Bullish -> Bearish
        if c0 <= o1 and o0 >= c1:
            return {"pattern": "Bearish Engulfing", "signal": -1}
            
    # 3. Hammer / Shooting Star Detection
    upper_shadow0 = h0 - max(o0, c0)
    lower_shadow0 = min(o0, c0) - l0
    
    if body0 > 0:
        # Hammer (Bullish Reversal at bottom)
        if lower_shadow0 >= (body0 * 2) and upper_shadow0 <= (body0 * 0.5):
            return {"pattern": "Bullish Hammer", "signal": 1}
        # Shooting Star (Bearish Reversal at top)
        if upper_shadow0 >= (body0 * 2) and lower_shadow0 <= (body0 * 0.5):
            return {"pattern": "Bearish Shooting Star", "signal": -1}
            
    return {"pattern": "Standard Candle", "signal": 0}

def detect_sr_breakout(df) -> dict:
    """
    Checks if the last close breaks out of a 20-period Support/Resistance range.
    """
    if len(df) < 25:
        return {"breakout": "None", "signal": 0}
        
    closes = clean_series(df, "Close")
    highs = clean_series(df, "High")
    lows = clean_series(df, "Low")
    
    current_close = float(closes.iloc[-1])
    
    # 20-period Support & Resistance bands (excluding last candle)
    resistance = float(highs.iloc[-21:-1].max())
    support = float(lows.iloc[-21:-1].min())
    
    if current_close > resistance:
        return {"breakout": "Resistance Breakout", "signal": 1}
    elif current_close < support:
        return {"breakout": "Support Breakdown", "signal": -1}
        
    return {"breakout": "Range Bound", "signal": 0}
