import pandas as pd
import numpy as np
import yfinance as yf
from indicators.technical import (
    calculate_ema, 
    calculate_rsi, 
    calculate_adx, 
    calculate_bollinger_bands,
    calculate_rvol
)
from indicators.patterns import detect_candlestick_patterns, detect_sr_breakout
from ai_engine.sentiment import get_news_sentiment

def score_timeframe(df):
    if len(df) < 50:
        return 0.0
    
    # Calculate Indicators
    ema50 = calculate_ema(df, 50).iloc[-1]
    ema200 = calculate_ema(df, 200).iloc[-1]
    rsi = calculate_rsi(df, 14).iloc[-1]
    adx = calculate_adx(df, 14).iloc[-1]
    
    upper, middle, lower = calculate_bollinger_bands(df, 20, 2)
    upper_val = upper.iloc[-1]
    lower_val = lower.iloc[-1]
    close = df["Close"]
    close_val = close.iloc[-1].iloc[0] if isinstance(close, pd.DataFrame) else close.iloc[-1]
    
    # Handle potentially multi-indexed DataFrame outputs from yfinance
    if isinstance(ema50, pd.Series):
        ema50 = ema50.iloc[0]
        ema200 = ema200.iloc[0]
        rsi = rsi.iloc[0]
        adx = adx.iloc[0]
        upper_val = upper_val.iloc[0]
        lower_val = lower_val.iloc[0]
        close_val = close_val.iloc[0]
        
    ema50 = float(ema50)
    ema200 = float(ema200)
    rsi = float(rsi)
    adx = float(adx)
    upper_val = float(upper_val)
    lower_val = float(lower_val)
    close_val = float(close_val)
    
    # 1. Crossover / Momentum Score
    crossover_score = 0.0
    if ema50 > ema200:
        crossover_score += 0.5
    else:
        crossover_score -= 0.5
        
    if rsi > 60:
        crossover_score += 0.5
    elif rsi < 40:
        crossover_score -= 0.5
    crossover_score = np.clip(crossover_score, -1.0, 1.0)
    
    # 2. Bollinger Mean-Reversion Score
    mr_score = 0.0
    if close_val < lower_val:
        mr_score += 0.6
        if rsi < 30:
            mr_score += 0.2
    elif close_val > upper_val:
        mr_score -= 0.6
        if rsi > 70:
            mr_score -= 0.2
            
    mr_score = np.clip(mr_score, -1.0, 1.0)
    
    # 3. Adaptive Blending based on ADX Trend Strength
    if adx > 25:
        blended_score = (crossover_score * 0.7) + (mr_score * 0.3)
    else:
        blended_score = (crossover_score * 0.3) + (mr_score * 0.7)
        
    if adx > 25:
        blended_score *= 1.2
        
    return float(np.clip(blended_score, -1.0, 1.0))

def run_multi_timeframe_strategy(symbol):
    try:
        # Download data for all three timeframes
        df_5m = yf.download(symbol, period="5d", interval="5m", progress=False)
        df_15m = yf.download(symbol, period="10d", interval="15m", progress=False)
        df_1h = yf.download(symbol, period="1mo", interval="1h", progress=False)
        
        if df_5m.empty or df_15m.empty or df_1h.empty:
            print("⚠️ Insufficient historical data found for multi-timeframe analysis.")
            return "HOLD", 0.0, {}
            
        # Flatten MultiIndex columns if present
        for df in [df_5m, df_15m, df_1h]:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
        
        score_5m = score_timeframe(df_5m)
        score_15m = score_timeframe(df_15m)
        score_1h = score_timeframe(df_1h)
        
        # Blended Strategy Score
        final_score = (score_5m * 0.3) + (score_15m * 0.3) + (score_1h * 0.4)
        
        # ----------------- V5 Gated Filters & Price Action Confirmations -----------------
        
        # A. Relative Volume (RVOL) Gating
        rvol = calculate_rvol(df_5m)
        rvol_val = float(rvol.iloc[-1].iloc[0]) if hasattr(rvol.iloc[-1], "iloc") else float(rvol.iloc[-1])
        
        # B. News Sentiment Lock
        news = get_news_sentiment(symbol)
        news_score = news.get("score", 0.0)
        
        # C. Price Action Patterns
        pa = detect_candlestick_patterns(df_5m)
        sr = detect_sr_breakout(df_5m)
        
        # Apply Gating Rules:
        # 1. Block BUYs on strongly negative News Sentiment
        if news_score <= -0.3 and final_score > 0.0:
            print(f"🔒 News Gate Triggered: Blocking BUY signal for {symbol} due to negative news sentiment ({news_score}).")
            final_score = 0.0
            
        # 2. Downgrade trend breakouts on low volume (RVOL < 1.5)
        adx_5m = calculate_adx(df_5m, 14).iloc[-1]
        adx_5m_val = float(adx_5m.iloc[0]) if isinstance(adx_5m, pd.Series) else float(adx_5m)
        if adx_5m_val > 25 and rvol_val < 1.5:
            # We degrade the signal confidence because there is no volume confirmation
            final_score *= 0.5
            
        # 3. Boost score based on Price Action Patterns
        if pa["signal"] == 1:
            final_score += 0.15  # Bullish Hammer / Engulfing boost
        elif pa["signal"] == -1:
            final_score -= 0.15  # Bearish Shooting Star / Engulfing boost
            
        if sr["signal"] == 1:
            final_score += 0.1   # S/R Breakout boost
        elif sr["signal"] == -1:
            final_score -= 0.1   # S/R Breakdown boost
            
        final_score = float(np.clip(final_score, -1.0, 1.0))
        
        # Determine signal based on gated weights
        threshold = 0.22
        if final_score >= threshold:
            signal = "BUY"
        elif final_score <= -threshold:
            signal = "SELL"
        else:
            signal = "HOLD"
            
        details = {
            "score_5m": score_5m,
            "score_15m": score_15m,
            "score_1h": score_1h,
            "final_score": final_score,
            "rvol": round(rvol_val, 2),
            "news_score": news_score,
            "pattern": pa["pattern"],
            "breakout": sr["breakout"]
        }
        return signal, final_score, details
    except Exception as e:
        print(f"⚠️ Error running multi-timeframe strategy: {e}")
        return "HOLD", 0.0, {}
