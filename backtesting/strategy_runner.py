import pandas as pd
import numpy as np
from indicators.technical import calculate_ema, calculate_rsi, calculate_vwap, calculate_adx, calculate_bollinger_bands, calculate_rvol
from indicators.patterns import detect_candlestick_patterns, detect_sr_breakout

def run_ema_crossover(df: pd.DataFrame) -> pd.Series:
    """EMA Crossover (9 vs 21 EMA) Strategy."""
    ema9 = calculate_ema(df, 9)
    ema21 = calculate_ema(df, 21)
    
    signals = pd.Series("HOLD", index=df.index)
    
    for i in range(1, len(df)):
        prev_9, curr_9 = float(ema9.iloc[i-1]), float(ema9.iloc[i])
        prev_21, curr_21 = float(ema21.iloc[i-1]), float(ema21.iloc[i])
        
        if prev_9 <= prev_21 and curr_9 > curr_21:
            signals.iloc[i] = "BUY"
        elif prev_9 >= prev_21 and curr_9 < curr_21:
            signals.iloc[i] = "SELL"
            
    return signals

def run_rsi_strategy(df: pd.DataFrame) -> pd.Series:
    """RSI Strategy (Buy < 30, Sell > 70)."""
    rsi = calculate_rsi(df, 14)
    signals = pd.Series("HOLD", index=df.index)
    
    for i in range(1, len(df)):
        prev_rsi, curr_rsi = float(rsi.iloc[i-1]), float(rsi.iloc[i])
        
        if prev_rsi >= 30 and curr_rsi < 30:
            signals.iloc[i] = "BUY"
        elif prev_rsi <= 70 and curr_rsi > 70:
            signals.iloc[i] = "SELL"
            
    return signals

def run_vwap_strategy(df: pd.DataFrame) -> pd.Series:
    """VWAP Cross Strategy (Buy on cross-above, Sell on cross-below)."""
    vwap = calculate_vwap(df)
    closes = df["Close"]
    signals = pd.Series("HOLD", index=df.index)
    
    for i in range(1, len(df)):
        prev_c, curr_c = float(closes.iloc[i-1]), float(closes.iloc[i])
        prev_v, curr_v = float(vwap.iloc[i-1]), float(vwap.iloc[i])
        
        if prev_c <= prev_v and curr_c > curr_v:
            signals.iloc[i] = "BUY"
        elif prev_c >= prev_v and curr_c < curr_v:
            signals.iloc[i] = "SELL"
            
    return signals

def run_breakout_strategy(df: pd.DataFrame) -> pd.Series:
    """Breakout Strategy (breaks above/below 20-period High/Low channel)."""
    highs = df["High"]
    lows = df["Low"]
    closes = df["Close"]
    signals = pd.Series("HOLD", index=df.index)
    
    for i in range(21, len(df)):
        curr_c = float(closes.iloc[i])
        
        # 20-period channel bands excluding last bar
        res = float(highs.iloc[i-21:i-1].max())
        supp = float(lows.iloc[i-21:i-1].min())
        
        if curr_c > res:
            signals.iloc[i] = "BUY"
        elif curr_c < supp:
            signals.iloc[i] = "SELL"
            
    return signals

def run_ai_strategy(df: pd.DataFrame) -> pd.Series:
    """Tuned V5 Blended Gated Strategy."""
    ema50 = calculate_ema(df, 50)
    ema200 = calculate_ema(df, 200)
    rsi = calculate_rsi(df, 14)
    adx = calculate_adx(df, 14)
    upper, middle, lower = calculate_bollinger_bands(df, 20, 2)
    rvol = calculate_rvol(df)
    
    signals = pd.Series("HOLD", index=df.index)
    
    for i in range(50, len(df)):
        c_val = float(df["Close"].iloc[i])
        rvol_val = float(rvol.iloc[i])
        adx_val = float(adx.iloc[i])
        rsi_val = float(rsi.iloc[i])
        ema50_val = float(ema50.iloc[i])
        ema200_val = float(ema200.iloc[i])
        upper_val = float(upper.iloc[i])
        lower_val = float(lower.iloc[i])
        
        # 1. Crossover / Momentum Score
        cross_score = 0.5 if ema50_val > ema200_val else -0.5
        if rsi_val > 60:
            cross_score += 0.5
        elif rsi_val < 40:
            cross_score -= 0.5
        cross_score = np.clip(cross_score, -1.0, 1.0)
        
        # 2. Bollinger Mean-Reversion Score
        mr_score = 0.0
        if c_val < lower_val:
            mr_score += 0.6
        elif c_val > upper_val:
            mr_score -= 0.6
        mr_score = np.clip(mr_score, -1.0, 1.0)
        
        # 3. Adaptive Blending based on ADX Regime
        if adx_val > 25:
            score = (cross_score * 0.7) + (mr_score * 0.3)
        else:
            score = (cross_score * 0.3) + (mr_score * 0.7)
            
        # Volume gating
        if adx_val > 25 and rvol_val < 1.5:
            score *= 0.5
            
        threshold = 0.25
        if score >= threshold:
            signals.iloc[i] = "BUY"
        elif score <= -threshold:
            signals.iloc[i] = "SELL"
            
    return signals
