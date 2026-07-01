import pandas as pd
import numpy as np

def run_simulation(df: pd.DataFrame, signals: pd.Series, initial_capital: float = 100000.0) -> dict:
    """
    Simulates trading orders chronologically using strategy signals.
    Applies 0.05% slippage + ₹20 Flat Brokerage fee per side.
    Supports profit target exits and trailing stop loss exits.
    """
    capital = initial_capital
    position = None  # Holds trade dict: {"symbol": str, "type": "BUY"|"SELL", "entry_price": float, "qty": int, "sl": float, "tp": float, "time": Timestamp}
    
    trades_log = []
    equity_curve = [initial_capital]
    equity_timestamps = [df.index[0].isoformat()]
    
    closes = df["Close"]
    highs = df["High"]
    lows = df["Low"]
    
    # Calculate ATR for position exits
    from indicators.technical import calculate_atr
    atr = calculate_atr(df, 14)
    
    for i in range(1, len(df)):
        idx = df.index[i]
        close_val = float(closes.iloc[i])
        high_val = float(highs.iloc[i])
        low_val = float(lows.iloc[i])
        atr_val = float(atr.iloc[i]) if not np.isnan(atr.iloc[i]) else (close_val * 0.01)
        
        # Check active position exits
        if position:
            p_type = position["type"]
            entry = position["entry_price"]
            qty = position["qty"]
            sl = position["sl"]
            tp = position["tp"]
            
            closed = False
            exit_price = close_val
            reason = "CLOSE_BAR"
            
            if p_type == "BUY":
                if low_val <= sl:
                    closed = True
                    exit_price = sl
                    reason = "STOP_LOSS"
                elif high_val >= tp:
                    closed = True
                    exit_price = tp
                    reason = "TAKE_PROFIT"
            else: # SELL
                if high_val >= sl:
                    closed = True
                    exit_price = sl
                    reason = "STOP_LOSS"
                elif low_val <= tp:
                    closed = True
                    exit_price = tp
                    reason = "TAKE_PROFIT"
                    
            if closed:
                # Apply 0.05% slippage on exit + Flat ₹20 Brokerage
                slippage = exit_price * 0.0005
                exit_price_adjusted = (exit_price - slippage) if p_type == "BUY" else (exit_price + slippage)
                
                pnl = (exit_price_adjusted - entry) * qty if p_type == "BUY" else (entry - exit_price_adjusted) * qty
                pnl -= 20.0 # Exit Brokerage
                
                capital += (entry * qty) + pnl
                
                # holding time in hours
                holding_time = float((idx - position["entry_time"]).total_seconds() / 3600.0)
                
                trades_log.append({
                    "date": idx.strftime("%Y-%m-%d %H:%M"),
                    "type": p_type,
                    "entry_price": round(entry, 2),
                    "exit_price": round(exit_price_adjusted, 2),
                    "quantity": qty,
                    "pnl": round(pnl, 2),
                    "reason": reason,
                    "holding_time": round(holding_time, 2)
                })
                
                position = None
                equity_curve.append(round(capital, 2))
                equity_timestamps.append(idx.isoformat())
                continue
                
        # Check strategy entry signals (If flat)
        if not position:
            sig = signals.iloc[i]
            if sig in ["BUY", "SELL"]:
                # Risk position sizing (1% account risk)
                sl_dist = atr_val * 1.5
                if sl_dist > 0:
                    qty = int((capital * 0.01) / sl_dist)
                    qty = max(1, min(qty, int(capital / close_val)))  # Max buying power limit
                    
                    # Apply 0.05% slippage on entry + Flat ₹20 Brokerage
                    slippage = close_val * 0.0005
                    entry_price_adjusted = (close_val + slippage) if sig == "BUY" else (close_val - slippage)
                    
                    sl_level = entry_price_adjusted - sl_dist if sig == "BUY" else entry_price_adjusted + sl_dist
                    tp_level = entry_price_adjusted + (sl_dist * 2.0) if sig == "BUY" else entry_price_adjusted - (sl_dist * 2.0)
                    
                    capital -= (entry_price_adjusted * qty)
                    capital -= 20.0 # Entry Brokerage
                    
                    position = {
                        "type": sig,
                        "entry_price": entry_price_adjusted,
                        "qty": qty,
                        "sl": sl_level,
                        "tp": tp_level,
                        "entry_time": idx
                    }
                    
        # Append current equity point
        active_value = 0.0
        if position:
            p_type = position["type"]
            entry = position["entry_price"]
            qty = position["qty"]
            pnl = (close_val - entry) * qty if p_type == "BUY" else (entry - close_val) * qty
            active_value = (entry * qty) + pnl
            
        equity_curve.append(round(capital + active_value, 2))
        equity_timestamps.append(idx.isoformat())
        
    return {
        "trades": trades_log,
        "equity_curve": equity_curve,
        "equity_timestamps": equity_timestamps,
        "final_capital": round(capital, 2)
    }
