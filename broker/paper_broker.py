import pandas as pd
import yfinance as yf
import time
import os
import sqlite3
from core.db import (
    load_portfolio_from_db, 
    save_portfolio_to_db, 
    add_position, 
    remove_position, 
    save_closed_trade
)

def sqlite3_connect():
    conn = sqlite3.connect("quantx.db")
    conn.row_factory = sqlite3.Row
    return conn

def load_portfolio(user_id: int = 1) -> dict:
    """Delegates portfolio loading to the SQLite database for a specific user."""
    return load_portfolio_from_db(user_id)

def save_portfolio(portfolio: dict, user_id: int = 1):
    """Saves the main portfolio variables back to SQLite for a specific user."""
    save_portfolio_to_db(
        portfolio["cash"],
        portfolio["equity"],
        portfolio.get("circuit_breaker_active", False),
        portfolio.get("equity_curve", [100000.0]),
        user_id
    )

def execute_trade(symbol: str, signal: str, entry_price: float, quantity: int, stop_loss: float, target: float, user_id: int = 1):
    """
    Executes a paper order, deducting balance, verifying daily loss bounds, 
    and storing the active position in SQLite for a specific user.
    """
    portfolio = load_portfolio_from_db(user_id)
    
    # 1. Risk Protection Circuit Breaker Check
    if portfolio.get("circuit_breaker_active", False):
        print(f"⚠️ Rejecting trade for {symbol}: Daily Loss Circuit Breaker Active (-1.5% limit hit).")
        return False, "Circuit breaker active! Trading is halted."
        
    # Check if position already exists
    for pos in portfolio["open_positions"]:
        if pos["symbol"] == symbol:
            print(f"⚠️ Position already open for {symbol}")
            return False, "Position already open"
            
    # Calculate margin required
    margin_required = entry_price * quantity
    if portfolio["cash"] < margin_required:
        print(f"⚠️ Insufficient balance for {symbol}. Needed: ₹{margin_required}, Available: ₹{portfolio['cash']}")
        return False, f"Insufficient cash balance. Needed: ₹{margin_required:.2f}"
        
    # Deduct margin from cash balance
    new_cash = portfolio["cash"] - margin_required
    
    # Save active position
    add_position(symbol, signal, entry_price, quantity, stop_loss, target, user_id)
    
    # Recalculate portfolio equity
    open_positions = portfolio["open_positions"] + [{
        "symbol": symbol,
        "signal": signal,
        "entry_price": entry_price,
        "quantity": quantity,
        "stop_loss": stop_loss,
        "target": target,
        "current_price": entry_price,
        "unrealized_pnl": 0.0
    }]
    
    current_equity = new_cash + sum(p.get("current_price", p["entry_price"]) * p["quantity"] for p in open_positions)
    
    equity_curve = portfolio.get("equity_curve", [100000.0])
    equity_curve.append(round(current_equity, 2))
    if len(equity_curve) > 50:
        equity_curve.pop(0)
        
    save_portfolio_to_db(new_cash, current_equity, False, equity_curve, user_id)
    
    print(f"🚀 Executed {signal} order for {quantity} shares of {symbol} at ₹{entry_price}")
    return True, "Executed successfully"

def close_position(symbol: str, exit_price: float, reason: str = "MANUAL", user_id: int = 1):
    """
    Closes an open trade, calculates PnL, adds to cash balance,
    and moves position to closed trades log.
    """
    portfolio = load_portfolio_from_db(user_id)
    open_positions = portfolio["open_positions"]
    
    target_pos = None
    for pos in open_positions:
        if pos["symbol"] == symbol:
            target_pos = pos
            break
            
    if not target_pos:
        print(f"⚠️ No active position found for {symbol}")
        return False, "No active position"
        
    # Remove from SQLite positions table
    remove_position(symbol, user_id)
    
    # Calculate PnL
    entry_price = target_pos["entry_price"]
    qty = target_pos["quantity"]
    sig = target_pos["signal"]
    
    if sig == "BUY":
        pnl = (exit_price - entry_price) * qty
        cash_returned = (entry_price * qty) + pnl
    else: # SELL
        pnl = (entry_price - exit_price) * qty
        cash_returned = (entry_price * qty) + pnl
        
    new_cash = portfolio["cash"] + cash_returned
    
    # Save closed trade to DB
    save_closed_trade(symbol, sig, entry_price, float(exit_price), qty, round(pnl, 2), reason, user_id)
    
    # Recalculate remaining positions equity
    remaining_positions = [p for p in open_positions if p["symbol"] != symbol]
    current_equity = new_cash + sum(p.get("current_price", p["entry_price"]) * p["quantity"] for p in remaining_positions)
    
    # Update curve
    equity_curve = portfolio.get("equity_curve", [100000.0])
    equity_curve.append(round(current_equity, 2))
    if len(equity_curve) > 50:
        equity_curve.pop(0)
        
    # Re-load from DB to preserve other state flags
    temp_port = load_portfolio_from_db(user_id)
    
    save_portfolio_to_db(new_cash, current_equity, temp_port.get("circuit_breaker_active", False), equity_curve, user_id)
    
    print(f"🛑 Closed position for {symbol} at ₹{exit_price} | PnL: ₹{pnl:.2f} ({reason})")
    
    # Send Telegram Notification for closed position
    try:
        from core.notifier import send_telegram_alert
        emoji = "🚨" if reason == "STOP_LOSS" else "🎉" if reason == "TAKE_PROFIT" else "ℹ️"
        title = "Stop Loss Hit" if reason == "STOP_LOSS" else "Profit Target Hit" if reason == "TAKE_PROFIT" else f"Position Closed ({reason})"
        footer = "⚠️ Stop loss breached. Trade closed automatically." if reason == "STOP_LOSS" else "💵 Profit booked successfully!" if reason == "TAKE_PROFIT" else "Position closed manually."
        
        msg = (
            f"{emoji} *QuantX Alert: {title}*\n\n"
            f"• *Symbol*: `{symbol.replace('.NS', '')}`\n"
            f"• *Action*: `{sig}`\n"
            f"• *Entry Price*: `₹{entry_price:.2f}`\n"
            f"• *Exit Price*: `₹{exit_price:.2f}`\n"
            f"• *Quantity*: `{qty}` shares\n"
            f"• *PnL*: `₹{pnl:+.2f}`\n\n"
            f"{footer}"
        )
        send_telegram_alert(user_id, msg)
    except Exception as e:
        print(f"⚠️ Failed to send close position Telegram alert: {e}")
            
    return True, f"Closed at {exit_price}"

def update_portfolio(user_id: int = 1) -> dict:
    """
    Loops active trades, checks targets, and enforces the Daily Loss Circuit Breaker
    if P&L falls below -1.5% of daily start capital.
    """
    portfolio = load_portfolio_from_db(user_id)
    open_positions = portfolio["open_positions"]
    
    # If no open positions, just update equity and return
    if not open_positions:
        save_portfolio_to_db(portfolio["cash"], portfolio["cash"], portfolio.get("circuit_breaker_active", False), portfolio.get("equity_curve", [100000.0]), user_id)
        return load_portfolio_from_db(user_id)
        
    updated_positions = []
    
    for pos in open_positions:
        symbol = pos["symbol"]
        try:
            ticker = yf.Ticker(symbol)
            todays_data = ticker.history(period="1d", interval="1m")
            if todays_data.empty:
                updated_positions.append(pos)
                continue
                
            close_col = todays_data["Close"]
            if isinstance(close_col, pd.DataFrame):
                current_price = float(close_col.iloc[-1].iloc[0])
            else:
                current_price = float(close_col.iloc[-1])
            
            entry = pos["entry_price"]
            qty = pos["quantity"]
            sig = pos["signal"]
            sl = pos["stop_loss"]
            tp = pos["target"]
            
            if sig == "BUY":
                pnl = (current_price - entry) * qty
                pos["unrealized_pnl"] = round(pnl, 2)
                
                if current_price <= sl:
                    close_position(symbol, current_price, reason="STOP_LOSS", user_id=user_id)
                    continue
                elif current_price >= tp:
                    close_position(symbol, current_price, reason="TAKE_PROFIT", user_id=user_id)
                    continue
            else: # SELL
                pnl = (entry - current_price) * qty
                pos["unrealized_pnl"] = round(pnl, 2)
                
                if current_price >= sl:
                    close_position(symbol, current_price, reason="STOP_LOSS", user_id=user_id)
                    continue
                elif current_price <= tp:
                    close_position(symbol, current_price, reason="TAKE_PROFIT", user_id=user_id)
                    continue
                    
            pos["current_price"] = current_price
            updated_positions.append(pos)
            
            # Update position tick data in positions table for this user
            conn = sqlite3_connect()
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE positions
            SET current_price = ?, unrealized_pnl = ?
            WHERE symbol = ? AND user_id = ?
            """, (current_price, round(pnl, 2), symbol, user_id))
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"⚠️ Error updating position for {symbol}: {e}")
            updated_positions.append(pos)
            
    # Re-load from db after closures
    portfolio = load_portfolio_from_db(user_id)
    active_positions = portfolio["open_positions"]
    
    current_equity = portfolio["cash"] + sum(p.get("current_price", p["entry_price"]) * p["quantity"] for p in active_positions)
    portfolio["equity"] = round(current_equity, 2)
    
    # Enforce Daily Loss Circuit Breaker (-1.5%)
    daily_start = portfolio["daily_start_equity"]
    daily_drawdown = (current_equity - daily_start) / daily_start
    
    circuit_breaker = portfolio.get("circuit_breaker_active", False)
    if daily_drawdown <= -0.015 and not circuit_breaker:
        print(f"🚨 Daily Loss Circuit Breaker Triggered ({daily_drawdown * 100:.2f}% daily drop)! Halting trade and closing open positions.")
        circuit_breaker = True
        for pos in list(active_positions):
            close_position(pos["symbol"], pos.get("current_price", pos["entry_price"]), reason="CIRCUIT_BREAKER", user_id=user_id)
        active_positions = []
        current_equity = portfolio["cash"]
        portfolio["equity"] = round(current_equity, 2)
        
    save_portfolio_to_db(portfolio["cash"], current_equity, circuit_breaker, portfolio.get("equity_curve", [100000.0]), user_id)
    
    return load_portfolio_from_db(user_id)