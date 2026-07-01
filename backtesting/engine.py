import yfinance as yf
import pandas as pd
import numpy as np
from indicators.technical import calculate_ema, calculate_rsi, calculate_adx, calculate_atr, calculate_bollinger_bands

def run_backtest(symbol: str, days: int = 59) -> dict:
    """
    Runs a chronological backtest simulation of the blended QuantX strategy.
    Applies 0.05% slippage + Flat ₹20 Brokerage fee per side.
    Calculates Sharpe, Sortino, Max Drawdown, and Calmar ratios.
    """
    try:
        if days > 59:
            days = 59
        df = yf.download(symbol, period=f"{days}d", interval="15m", progress=False)
        if len(df) < 50:
            df = yf.download(symbol, period="1y", interval="1h", progress=False)
        if len(df) < 50:
            return {"error": "Insufficient historical data for backtesting."}
            
        # Flatten columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Compute Strategy Indicators
        df["EMA_50"] = calculate_ema(df, 50)
        df["EMA_200"] = calculate_ema(df, 200)
        df["RSI"] = calculate_rsi(df, 14)
        df["ADX"] = calculate_adx(df, 14)
        df["ATR"] = calculate_atr(df, 14)
        
        upper, middle, lower = calculate_bollinger_bands(df, 20, 2)
        df["BB_Upper"] = upper
        df["BB_Lower"] = lower
        
        df = df.dropna(subset=["EMA_200", "RSI", "ADX", "ATR", "BB_Upper", "BB_Lower"])
        
        initial_capital = 100000.0
        capital = initial_capital
        position = None  # Holds active trade dict: {"entry_price": float, "qty": int, "type": "BUY"|"SELL", "sl": float, "tp": float}
        
        trades_log = []
        equity_curve = [initial_capital]
        
        # Chronological Simulation Loop
        for idx, row in df.iterrows():
            close_val = float(row["Close"])
            atr_val = float(row["ATR"])
            ema50 = float(row["EMA_50"])
            ema200 = float(row["EMA_200"])
            rsi = float(row["RSI"])
            adx = float(row["ADX"])
            upper_val = float(row["BB_Upper"])
            lower_val = float(row["BB_Lower"])
            
            # Check Active Position Exits
            if position:
                p_type = position["type"]
                entry = position["entry_price"]
                qty = position["qty"]
                sl = position["sl"]
                tp = position["tp"]
                
                # Check limits
                closed = False
                exit_price = close_val
                reason = "CLOSE_BAR"
                
                if p_type == "BUY":
                    if close_val <= sl:
                        closed = True
                        exit_price = sl
                        reason = "STOP_LOSS"
                    elif close_val >= tp:
                        closed = True
                        exit_price = tp
                        reason = "TAKE_PROFIT"
                else: # SELL
                    if close_val >= sl:
                        closed = True
                        exit_price = sl
                        reason = "STOP_LOSS"
                    elif close_val <= tp:
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
                    trades_log.append(pnl)
                    position = None
                    equity_curve.append(capital)
                    continue
            
            # Check Strategy Entry Signals (If flat)
            if not position:
                # 1. Crossover Score
                cross_score = 0.5 if ema50 > ema200 else -0.5
                if rsi > 60:
                    cross_score += 0.5
                elif rsi < 40:
                    cross_score -= 0.5
                
                # 2. Bollinger Mean-Reversion Score
                mr_score = 0.0
                if close_val < lower_val:
                    mr_score += 0.6
                elif close_val > upper_val:
                    mr_score -= 0.6
                    
                # 3. Blending based on ADX Regime
                if adx > 25:
                    score = (cross_score * 0.7) + (mr_score * 0.3)
                else:
                    score = (cross_score * 0.3) + (mr_score * 0.7)
                    
                # Entry signals
                threshold = 0.25
                trade_type = None
                if score >= threshold:
                    trade_type = "BUY"
                elif score <= -threshold:
                    trade_type = "SELL"
                    
                if trade_type:
                    # Risk position sizing (1% account risk)
                    sl_dist = atr_val * 1.5
                    if sl_dist > 0:
                        qty = int((capital * 0.01) / sl_dist)
                        qty = max(1, min(qty, int(capital / close_val)))  # Max buying power gate
                        
                        # Apply 0.05% slippage on entry + Flat ₹20 Brokerage
                        slippage = close_val * 0.0005
                        entry_price_adjusted = (close_val + slippage) if trade_type == "BUY" else (close_val - slippage)
                        
                        sl_level = entry_price_adjusted - sl_dist if trade_type == "BUY" else entry_price_adjusted + sl_dist
                        tp_level = entry_price_adjusted + (sl_dist * 2.0) if trade_type == "BUY" else entry_price_adjusted - (sl_dist * 2.0)
                        
                        capital -= (entry_price_adjusted * qty)
                        capital -= 20.0 # Entry Brokerage
                        
                        position = {
                            "type": trade_type,
                            "entry_price": entry_price_adjusted,
                            "qty": qty,
                            "sl": sl_level,
                            "tp": tp_level
                        }
            
            # Append current equity point
            active_value = 0.0
            if position:
                # Unrealized position value
                p_type = position["type"]
                entry = position["entry_price"]
                qty = position["qty"]
                pnl = (close_val - entry) * qty if p_type == "BUY" else (entry - close_val) * qty
                active_value = (entry * qty) + pnl
            equity_curve.append(capital + active_value)

        # Calculate Performance Analytics
        total_trades = len(trades_log)
        if total_trades == 0:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "profit_factor": 1.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 1.0,
                "sortino_ratio": 1.0,
                "calmar_ratio": 1.0,
                "net_profit": 0.0
            }
            
        win_trades = sum(1 for t in trades_log if t > 0)
        win_rate = round((win_trades / total_trades) * 100, 1)
        
        gross_profits = sum(t for t in trades_log if t > 0)
        gross_losses = sum(abs(t) for t in trades_log if t < 0)
        profit_factor = round(gross_profits / gross_losses, 2) if gross_losses > 0 else round(gross_profits, 2)
        
        # Max Drawdown
        eq_arr = np.array(equity_curve)
        cum_max = np.maximum.accumulate(eq_arr)
        drawdowns = (eq_arr - cum_max) / cum_max
        max_dd = round(float(np.abs(drawdowns.min())) * 100, 2)
        
        # Returns for Sharpe and Sortino
        returns = pd.Series(trades_log) / initial_capital
        mean_ret = returns.mean()
        std_ret = returns.std()
        
        # Sharpe
        sharpe = round(float((mean_ret / std_ret) * np.sqrt(252)), 2) if std_ret > 0 else 1.0
        
        # Sortino (Downside standard deviation only)
        downside_returns = returns[returns < 0]
        std_downside = downside_returns.std()
        sortino = round(float((mean_ret / std_downside) * np.sqrt(252)), 2) if std_downside > 0 else 1.0
        
        # Calmar Ratio (CAGR / Max Drawdown)
        total_ret = (capital - initial_capital) / initial_capital
        calmar = round(float(total_ret / (max_dd/100)), 2) if max_dd > 0 else 1.0
        
        return {
            "total_trades": total_trades,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "max_drawdown": max_dd,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "calmar_ratio": calmar,
            "net_profit": round(capital - initial_capital, 2)
        }
    except Exception as e:
        print(f"⚠️ Error running backtester: {e}")
        return {"error": str(e)}
