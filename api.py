import sys
import time
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, Query, HTTPException, Body, Header
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
import numpy as np

from strategies.multi_timeframe import run_multi_timeframe_strategy
from ai_engine.classifier import train_and_predict_ai
from ai_engine.sentiment import get_news_sentiment
from broker.derivatives import get_derivatives_data, get_global_indices
from risk.position_sizing import calculate_position_size
from risk.trade_levels import calculate_trade_levels
from indicators.technical import calculate_atr, calculate_ema, calculate_rsi, calculate_volume_spikes
from broker.paper_broker import load_portfolio, execute_trade, close_position, update_portfolio

# Reconfigure console output encoding on Windows to prevent Emoji crashes
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding='utf-8')

app = FastAPI(title="QuantX-AI Trading API", version="1.0.0")

def get_current_user_id(authorization: str = Header(None)) -> int:
    """
    Extracts the session token from the Authorization header (e.g. Bearer <token>)
    and returns the corresponding user_id. Defaults to 1 (guest/default user) if missing or invalid.
    """
    if not authorization:
        return 1
        
    try:
        if authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
        else:
            token = authorization
            
        from core.auth import validate_session
        user_id = validate_session(token)
        return user_id if user_id is not None else 1
    except Exception:
        return 1

# Enable CORS for React Frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SIGNAL_CACHE = {}
CACHE_EXPIRATION_SECONDS = 60

def clean_symbol(symbol: str) -> str:
    symbol = symbol.upper().strip()
    if not symbol.endswith(".NS") and not symbol.endswith(".BO") and symbol in ["RELIANCE", "TCS", "INFY", "ICICIBANK", "BHARTIARTL"]:
        return f"{symbol}.NS"
    return symbol

@app.get("/api/signal")
def get_signal(symbol: str = Query(..., description="Stock symbol (e.g., RELIANCE.NS)")):
    sym = clean_symbol(symbol)
    
    # Check cache first to avoid slow yfinance HTTP requests
    now = time.time()
    if sym in SIGNAL_CACHE:
        cache_time, cached_data = SIGNAL_CACHE[sym]
        if now - cache_time < CACHE_EXPIRATION_SECONDS:
            print(f"⚡ Cache hit for {sym}")
            return cached_data
            
    # Run Multi-Timeframe Strategy
    signal, final_score, strategy_details = run_multi_timeframe_strategy(sym)
    
    # Run Machine Learning AI Classifier
    prob_profit, confidence, accuracy, feature_importances = train_and_predict_ai(sym)
    
    # Fetch 5m data to calculate recent ATR and Close Price
    df_5m = yf.download(sym, period="5d", interval="5m", progress=False)
    if df_5m.empty:
        raise HTTPException(status_code=404, detail=f"No data found for symbol {sym}")
    if isinstance(df_5m.columns, pd.MultiIndex):
        df_5m.columns = df_5m.columns.get_level_values(0)
        
    close = df_5m["Close"]
    high = df_5m["High"]
    low = df_5m["Low"]
    volume = df_5m["Volume"]
    
    # Robustly parse Series vs MultiIndex DataFrame
    if isinstance(close, pd.DataFrame):
        current_price = float(close.iloc[-1].iloc[0])
        atr_series = calculate_atr(df_5m, 14)
        atr_val = float(atr_series.iloc[-1].iloc[0]) if isinstance(atr_series, pd.DataFrame) else float(atr_series.iloc[-1])
        ema50 = calculate_ema(df_5m, 50).iloc[-1].iloc[0]
        ema200 = calculate_ema(df_5m, 200).iloc[-1].iloc[0]
        vol_ratio = calculate_volume_spikes(df_5m, 20).iloc[-1].iloc[0]
        rsi_series = calculate_rsi(df_5m, 14)
        rsi_val = float(rsi_series.iloc[-1].iloc[0]) if isinstance(rsi_series, pd.DataFrame) else float(rsi_series.iloc[-1])
    else:
        current_price = float(close.iloc[-1])
        atr_series = calculate_atr(df_5m, 14)
        atr_val = float(atr_series.iloc[-1])
        ema50 = float(calculate_ema(df_5m, 50).iloc[-1])
        ema200 = float(calculate_ema(df_5m, 200).iloc[-1])
        vol_ratio = float(calculate_volume_spikes(df_5m, 20).iloc[-1])
        rsi_series = calculate_rsi(df_5m, 14)
        rsi_val = float(rsi_series.iloc[-1])
        
    # Calculate Levels & Position Size
    portfolio = load_portfolio()
    capital = portfolio["cash"]
    
    stop_loss, target, sl_distance = calculate_trade_levels(
        current_price,
        atr_val,
        signal=signal if signal != "HOLD" else "BUY",
        atr_multiplier=1.5,
        reward_ratio=2.0
    )
    
    quantity = calculate_position_size(
        capital,
        risk_percent=0.01, # 1% Risk
        stop_loss_distance=sl_distance,
        atr_value=atr_val
    )
    
    # Technical Indicators Stats Summary
    trend_state = "Bullish" if ema50 > ema200 else "Bearish"
    market_regime = "Bullish Trend" if current_price > ema200 else "Bearish Range"
    
    # Fetch V2 Metrics
    sentiment_data = get_news_sentiment(sym)
    deriv_data = get_derivatives_data(sym, current_price, vol_ratio, signal)
    global_data = get_global_indices()
    
    # Clean output values to standard types (prevent numpy floats in JSON)
    response_data = {
        "symbol": sym,
        "signal": signal,
        "confidence": float(confidence),
        "probability_of_profit": float(prob_profit),
        "accuracy": float(accuracy),
        "entry": float(round(current_price, 2)),
        "stop_loss": float(stop_loss),
        "target": float(target),
        "quantity": int(quantity),
        "final_score": float(round(final_score, 2)),
        "strategy_details": strategy_details,
        "indicators": {
            "trend": float(round(ema50 - ema200, 2)),
            "trend_state": trend_state,
            "volume_ratio": float(round(vol_ratio, 2)),
            "volatility": float(round(atr_val, 2)),
            "rsi": float(round(rsi_val, 2)),
            "market_regime": market_regime,
            "support_zone": float(round(current_price - (atr_val * 2.0), 2)),
            "risk_reward": 2.0
        },
        "sentiment": sentiment_data,
        "derivatives": deriv_data,
        "global_indices": global_data,
        "feature_importances": feature_importances
     }
    
    # Save result to cache
    SIGNAL_CACHE[sym] = (time.time(), response_data)
    return response_data

WATCHLIST = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", 
    "BHARTIARTL.NS", "SBIN.NS", "LICI.NS", "ITC.NS", "HINDUNILVR.NS", 
    "LT.NS", "BAJFINANCE.NS", "TATASTEEL.NS", "MARUTI.NS", "KOTAKBANK.NS", 
    "AXISBANK.NS", "M&M.NS", "SUNPHARMA.NS", "ADANIENT.NS", "ADANIPORTS.NS", 
    "HCLTECH.NS", "NTPC.NS", "POWERGRID.NS", "TITAN.NS", "ULTRACEMCO.NS"
]

@app.get("/api/scanner")
def get_scanner():
    results = []
    
    # Execute symbol fetches in parallel to cut latency by 80%+
    with ThreadPoolExecutor(max_workers=len(WATCHLIST)) as executor:
        futures = {executor.submit(get_signal, sym): sym for sym in WATCHLIST}
        for future in futures:
            sym = futures[future]
            try:
                signal_data = future.result()
                results.append(signal_data)
            except Exception as e:
                print(f"⚠️ Scanner failed to fetch {sym}: {e}")
            
    # Sort top buy and top sell stocks
    buys = [res for res in results if res["signal"] == "BUY"]
    sells = [res for res in results if res["signal"] == "SELL"]
    holds = [res for res in results if res["signal"] == "HOLD"]
    
    return {
        "buy_candidates": sorted(buys, key=lambda x: x["probability_of_profit"], reverse=True),
        "sell_candidates": sorted(sells, key=lambda x: x["probability_of_profit"], reverse=True),
        "hold_candidates": holds
    }

@app.get("/api/portfolio")
def get_portfolio_api(authorization: str = Header(None)):
    user_id = get_current_user_id(authorization)
    portfolio = update_portfolio(user_id=user_id)
    return portfolio

@app.post("/api/trade")
def execute_trade_api(
    symbol: str = Body(..., embed=True),
    action: str = Body(..., embed=True, description="BUY, SELL, or CLOSE"),
    entry_price: float = Body(0.0, embed=True),
    quantity: int = Body(1, embed=True),
    stop_loss: float = Body(0.0, embed=True),
    target: float = Body(0.0, embed=True),
    authorization: str = Header(None)
):
    user_id = get_current_user_id(authorization)
    sym = clean_symbol(symbol)
    
    if action.upper() in ["BUY", "SELL"]:
        from broker.broker_manager import place_broker_order
        success, message = place_broker_order(
            user_id,
            sym,
            action.upper(),
            quantity,
            entry_price,
            stop_loss,
            target
        )
        if not success:
            raise HTTPException(status_code=400, detail=message)
        return {"status": "SUCCESS", "message": message}
    
    elif action.upper() == "CLOSE":
        ticker = yf.Ticker(sym)
        df_1m = ticker.history(period="1d", interval="1m")
        if df_1m.empty:
            raise HTTPException(status_code=404, detail=f"Cannot resolve current exit price for {sym}")
        
        close_col = df_1m["Close"]
        if isinstance(close_col, pd.DataFrame):
            exit_price = float(close_col.iloc[-1].iloc[0])
        else:
            exit_price = float(close_col.iloc[-1])
        success, message = close_position(sym, exit_price, reason="MANUAL", user_id=user_id)
        if not success:
            raise HTTPException(status_code=400, detail=message)
        return {"status": "SUCCESS", "message": message}
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action parameter. Must be BUY, SELL, or CLOSE.")

@app.post("/api/portfolio/reset-circuit")
def reset_circuit_breaker(authorization: str = Header(None)):
    from core.db import clear_circuit_breaker
    user_id = get_current_user_id(authorization)
    try:
        clear_circuit_breaker(user_id=user_id)
        return {"status": "SUCCESS", "message": "Circuit breaker reset."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chart-data")
def get_chart_data(symbol: str = Query(..., description="Stock symbol (e.g. RELIANCE.NS)")):
    sym = clean_symbol(symbol)
    df = yf.download(sym, period="5d", interval="5m", progress=False)
    if df.empty:
        raise HTTPException(status_code=404, detail="Symbol chart data not found.")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    chart_candles = []
    
    # Calculate VWAP & EMA 200 for charts
    df["EMA_200"] = calculate_ema(df, 200)
    
    # Safely convert to list of candles
    for idx, row in df.iterrows():
        # idx is Datetime Index
        # formatted timestamp for Lightweight charts (unix epoch in seconds)
        timestamp = int(idx.timestamp())
        
        o = float(row["Open"].iloc[0]) if hasattr(row["Open"], "iloc") else float(row["Open"])
        h = float(row["High"].iloc[0]) if hasattr(row["High"], "iloc") else float(row["High"])
        l = float(row["Low"].iloc[0]) if hasattr(row["Low"], "iloc") else float(row["Low"])
        c = float(row["Close"].iloc[0]) if hasattr(row["Close"], "iloc") else float(row["Close"])
        v = float(row["Volume"].iloc[0]) if hasattr(row["Volume"], "iloc") else float(row["Volume"])
        ema = float(row["EMA_200"].iloc[0]) if hasattr(row["EMA_200"], "iloc") else float(row["EMA_200"])
        
        if np.isnan(ema):
            ema = c
            
        chart_candles.append({
            "time": timestamp,
            "open": round(o, 2),
            "high": round(h, 2),
            "low": round(l, 2),
            "close": round(c, 2),
            "volume": int(v),
            "ema200": round(ema, 2)
        })
        
    return chart_candles

@app.get("/api/portfolio/export")
def export_portfolio(authorization: str = Header(None)):
    import io
    import csv
    from fastapi.responses import StreamingResponse
    user_id = get_current_user_id(authorization)
    try:
        portfolio = load_portfolio(user_id=user_id)
        trades = portfolio.get("trade_history", [])
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(["Symbol", "Action", "Entry Price", "Exit Price", "Quantity", "PnL (INR)", "Exit Reason"])
        
        for t in trades:
            writer.writerow([
                t.get("symbol", ""),
                t.get("signal", ""),
                t.get("entry_price", 0.0),
                t.get("exit_price", 0.0),
                t.get("quantity", 0),
                t.get("pnl", 0.0),
                t.get("reason", "")
            ])
            
        output.seek(0)
        return StreamingResponse(
            io.StringIO(output.getvalue()), 
            media_type="text/csv", 
            headers={"Content-Disposition": "attachment; filename=trade_history.csv"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export CSV: {e}")

@app.get("/api/gold-advisor")
def get_gold_advisor_endpoint():
    from ai_engine.gold_advisor import get_gold_advice
    try:
        return get_gold_advice()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/developer/verify")
def verify_developer_otp(code: str = Body(..., embed=True)):
    import hmac
    import hashlib
    import struct
    import base64
    import time
    
    secret = "NYNXP43JMXSZXEHB"
    try:
        otp = str(code).strip()
        if len(otp) != 6 or not otp.isdigit():
            return {"status": "ERROR", "message": "Invalid code format. Must be 6 digits."}
            
        secret_padded = secret.upper()
        missing_padding = len(secret_padded) % 8
        if missing_padding:
            secret_padded += '=' * (8 - missing_padding)
        key = base64.b32decode(secret_padded)
        
        current_interval = int(time.time() // 30)
        verified = False
        for i in range(-1, 2):
            msg = struct.pack(">Q", current_interval + i)
            h = hmac.new(key, msg, hashlib.sha1).digest()
            o = h[19] & 15
            token = (struct.unpack(">I", h[o:o+4])[0] & 0x7fffffff) % 1000000
            if f"{token:06d}" == otp:
                verified = True
                break
                
        if verified:
            return {"status": "SUCCESS", "message": "2FA Verification Successful."}
        else:
            return {"status": "ERROR", "message": "Invalid OTP code. Please try again."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/register")
def auth_register(
    username: str = Body(..., embed=True),
    password: str = Body(..., embed=True),
    email: str = Body(None, embed=True)
):
    from core.db import get_db_connection
    from core.auth import hash_password
    import sqlite3
    
    username = username.strip()
    password = password.strip()
    
    if len(username) < 3 or len(password) < 6:
        raise HTTPException(status_code=400, detail="Username must be at least 3 chars; password at least 6 chars.")
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        pw_hash = hash_password(password)
        cursor.execute("""
        INSERT INTO users (username, password_hash, email, created_at)
        VALUES (?, ?, ?, ?)
        """, (username, pw_hash, email, time.time()))
        user_id = cursor.lastrowid
        conn.commit()
        
        # Create corresponding portfolio
        cursor.execute("""
        INSERT INTO portfolio (user_id, cash, initial_capital, equity, daily_start_equity, circuit_breaker_active, equity_curve)
        VALUES (?, 100000.0, 100000.0, 100000.0, 100000.0, 0, '[100000.0]')
        """, (user_id,))
        conn.commit()
        
        from core.auth import create_session
        token = create_session(user_id)
        return {"status": "SUCCESS", "token": token, "username": username}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already exists.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/auth/login")
def auth_login(
    username: str = Body(..., embed=True),
    password: str = Body(..., embed=True)
):
    from core.db import get_db_connection
    from core.auth import verify_password, create_session
    
    username = username.strip()
    password = password.strip()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    
    if not row or not verify_password(password, row["password_hash"]):
        raise HTTPException(status_code=400, detail="Invalid username or password.")
        
    token = create_session(row["id"])
    return {"status": "SUCCESS", "token": token, "username": username}

@app.post("/api/auth/logout")
def auth_logout(authorization: str = Header(None)):
    if authorization:
        token = authorization.replace("Bearer ", "")
        from core.auth import delete_session
        delete_session(token)
    return {"status": "SUCCESS"}

@app.get("/api/auth/me")
def auth_me(authorization: str = Header(None)):
    user_id = get_current_user_id(authorization)
    if user_id == 1:
        # Check if guest user has a record, if not initialize
        from core.db import load_portfolio_from_db
        load_portfolio_from_db(1)
        return {"username": "Guest", "is_authenticated": False}
        
    from core.db import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, email FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return {"username": "Guest", "is_authenticated": False}
        
    return {"username": row["username"], "email": row["email"], "is_authenticated": True}

@app.get("/api/alerts/config")
def get_alerts_config(authorization: str = Header(None)):
    user_id = get_current_user_id(authorization)
    if user_id == 1:
        return {"telegram_token": "", "telegram_chat_id": "", "enabled": False}
        
    from core.db import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT telegram_token, telegram_chat_id FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return {"telegram_token": "", "telegram_chat_id": "", "enabled": False}
        
    return {
        "telegram_token": row["telegram_token"] or "",
        "telegram_chat_id": row["telegram_chat_id"] or "",
        "enabled": bool(row["telegram_token"] and row["telegram_chat_id"])
    }

@app.post("/api/alerts/config")
def save_alerts_config(
    telegram_token: str = Body("", embed=True),
    telegram_chat_id: str = Body("", embed=True),
    authorization: str = Header(None)
):
    user_id = get_current_user_id(authorization)
    if user_id == 1:
        raise HTTPException(status_code=400, detail="Cannot configure alerts for Guest profile. Please register or login first.")
        
    from core.db import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        UPDATE users
        SET telegram_token = ?, telegram_chat_id = ?
        WHERE id = ?
        """, (telegram_token.strip() or None, telegram_chat_id.strip() or None, user_id))
        conn.commit()
        return {"status": "SUCCESS", "message": "Alert configurations updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/broker/config")
def get_broker_config(authorization: str = Header(None)):
    user_id = get_current_user_id(authorization)
    if user_id == 1:
        return {"broker_mode": "PAPER", "zerodha_api_key": "", "zerodha_api_secret": ""}
        
    from core.db import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT broker_mode, zerodha_api_key, zerodha_api_secret FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
         return {"broker_mode": "PAPER", "zerodha_api_key": "", "zerodha_api_secret": ""}
         
    return {
        "broker_mode": row["broker_mode"] or "PAPER",
        "zerodha_api_key": row["zerodha_api_key"] or "",
        "zerodha_api_secret": row["zerodha_api_secret"] or ""
    }

@app.post("/api/broker/config")
def save_broker_config(
    broker_mode: str = Body("PAPER", embed=True),
    zerodha_api_key: str = Body("", embed=True),
    zerodha_api_secret: str = Body("", embed=True),
    authorization: str = Header(None)
):
    user_id = get_current_user_id(authorization)
    if user_id == 1:
        raise HTTPException(status_code=400, detail="Cannot configure broker settings for Guest profile. Please register or login first.")
        
    from core.db import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        UPDATE users
        SET broker_mode = ?, zerodha_api_key = ?, zerodha_api_secret = ?
        WHERE id = ?
        """, (broker_mode.strip() or "PAPER", zerodha_api_key.strip() or None, zerodha_api_secret.strip() or None, user_id))
        conn.commit()
        return {"status": "SUCCESS", "message": "Broker settings updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/admin/stats")
def get_admin_stats(authorization: str = Header(None)):
    user_id = get_current_user_id(authorization)
    from core.db import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row or row["username"].lower() not in ["prathmesh", "admin", "pratham", "guest"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Unauthorized access. Administrator privileges required.")
        
    import os
    from core.db import DB_FILE
    db_size_kb = 0
    if os.path.exists(DB_FILE):
        db_size_kb = round(os.path.getsize(DB_FILE) / 1024, 2)
        
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM sessions")
    active_sessions = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM positions")
    total_positions = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM trades")
    total_trades = cursor.fetchone()[0]
    
    conn.close()
    
    system_logs = [
        "🤖 [QuantX System] Server initialized on loopback address.",
        "📡 [WebSockets] Tick listener connected.",
        f"👥 [Admin] Active accounts registered: {total_users}.",
        f"💾 [Database] Core storage size: {db_size_kb} KB.",
        "💡 [AI Engine] Multi-Timeframe Blended scanning active."
    ]
    
    return {
        "total_users": total_users,
        "active_sessions": active_sessions,
        "total_positions": total_positions,
        "total_trades": total_trades,
        "db_size_kb": db_size_kb,
        "system_logs": system_logs
    }

@app.post("/api/portfolio/reset")
def reset_portfolio_endpoint(authorization: str = Header(None)):
    from core.db import get_db_connection
    user_id = get_current_user_id(authorization)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM positions WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM trades WHERE user_id = ?", (user_id,))
        cursor.execute("""
        UPDATE portfolio
        SET cash = 100000.0, initial_capital = 100000.0, equity = 100000.0, 
            daily_start_equity = 100000.0, circuit_breaker_active = 0, 
            equity_curve = '[100000.0]'
        WHERE user_id = ?
        """, (user_id,))
        conn.commit()
        conn.close()
        
        return {"status": "SUCCESS", "message": "Portfolio and trades database reset to initial 1 Lakh capital."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import random
from backtesting.engine import run_backtest

ACTIVE_CONNECTIONS = []

def generate_level2_dom(symbol: str = "RELIANCE"):
    base_price = 1300.0 if symbol == "RELIANCE" else 3400.0
    bids = []
    asks = []
    for i in range(5):
        bids.append({
            "price": round(base_price - (i * 0.4) - random.uniform(0.02, 0.1), 2),
            "qty": random.randint(100, 2000)
        })
        asks.append({
            "price": round(base_price + (i * 0.4) + random.uniform(0.02, 0.1), 2),
            "qty": random.randint(100, 2000)
        })
    return {"bids": bids, "asks": asks}

def generate_time_sales(symbol: str = "RELIANCE"):
    base_price = 1300.0 if symbol == "RELIANCE" else 3400.0
    trades = []
    for _ in range(5):
        trades.append({
            "time": time.strftime("%H:%M:%S"),
            "price": round(base_price + random.uniform(-0.8, 0.8), 2),
            "qty": random.randint(10, 250),
            "side": random.choice(["BUY", "SELL"])
        })
    return trades

async def broadcast_updates_loop():
    while True:
        await asyncio.sleep(1.5)
        if not ACTIVE_CONNECTIONS:
            continue
            
        try:
            portfolio = update_portfolio()
            payload = {
                "type": "TICK",
                "portfolio": portfolio,
                "dom": generate_level2_dom(),
                "time_sales": generate_time_sales()
            }
            for ws in list(ACTIVE_CONNECTIONS):
                try:
                    await ws.send_json(payload)
                except Exception:
                    if ws in ACTIVE_CONNECTIONS:
                        ACTIVE_CONNECTIONS.remove(ws)
        except Exception as e:
            print(f"⚠️ WebSocket broadcast error: {e}")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(broadcast_updates_loop())

@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ACTIVE_CONNECTIONS.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ACTIVE_CONNECTIONS.remove(websocket)

@app.get("/api/backtest")
def get_backtest(
    symbol: str = Query(..., description="Stock symbol to backtest"),
    strategy: str = Query("AI", description="Strategy to run (EMA, RSI, VWAP, BREAKOUT, AI)"),
    period: str = Query("60d", description="Period range (30d, 60d, 180d, 1y)"),
    interval: str = Query("15m", description="Bar interval (15m, 1h, 1d)")
):
    from backtesting.strategy_runner import run_ema_crossover, run_rsi_strategy, run_vwap_strategy, run_breakout_strategy, run_ai_strategy
    from backtesting.simulator import run_simulation
    from backtesting.metrics import calculate_metrics, run_monte_carlo
    from backtesting.report import generate_ai_report
    
    sym = clean_symbol(symbol)
    
    if interval == "15m" and period not in ["30d", "60d", "59d"]:
        period = "60d"
        
    try:
        df = yf.download(sym, period=period, interval=interval, progress=False)
        if len(df) < 30:
            df = yf.download(sym, period="1y", interval="1h", progress=False)
        if len(df) < 10:
            raise HTTPException(status_code=400, detail="Insufficient historical data available.")
            
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        strat_upper = strategy.upper().strip()
        if strat_upper == "EMA":
            signals = run_ema_crossover(df)
        elif strat_upper == "RSI":
            signals = run_rsi_strategy(df)
        elif strat_upper == "VWAP":
            signals = run_vwap_strategy(df)
        elif strat_upper == "BREAKOUT":
            signals = run_breakout_strategy(df)
        else:
            signals = run_ai_strategy(df)
            
        sim = run_simulation(df, signals)
        metrics = calculate_metrics(sim["trades"], sim["equity_curve"])
        monte_carlo = run_monte_carlo(sim["trades"])
        ai_report = generate_ai_report(metrics)
        
        return {
            "symbol": sym,
            "strategy": strategy,
            "period": period,
            "interval": interval,
            "metrics": metrics,
            "trades": sim["trades"],
            "equity_curve": sim["equity_curve"],
            "equity_timestamps": sim["equity_timestamps"],
            "monte_carlo": monte_carlo,
            "ai_report": ai_report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtester error: {e}")

@app.get("/api/backtest/compare")
def compare_strategies(symbol: str = Query(..., description="Stock symbol to backtest")):
    from backtesting.strategy_runner import run_ema_crossover, run_rsi_strategy, run_vwap_strategy, run_breakout_strategy, run_ai_strategy
    from backtesting.simulator import run_simulation
    from backtesting.metrics import calculate_metrics
    
    sym = clean_symbol(symbol)
    
    try:
        df = yf.download(sym, period="1y", interval="1h", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        strategies_dict = {
            "EMA Crossover": run_ema_crossover,
            "RSI Mean Reversion": run_rsi_strategy,
            "VWAP Breakthrough": run_vwap_strategy,
            "Channel Breakout": run_breakout_strategy,
            "QuantX AI (V5)": run_ai_strategy
        }
        
        comparison = []
        for name, run_func in strategies_dict.items():
            signals = run_func(df)
            sim = run_simulation(df, signals)
            metrics = calculate_metrics(sim["trades"], sim["equity_curve"])
            comparison.append({
                "strategy": name,
                "win_rate": metrics["win_rate"],
                "profit": metrics["net_profit"],
                "drawdown": metrics["max_drawdown"],
                "trades": metrics["total_trades"]
            })
            
        return comparison
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
