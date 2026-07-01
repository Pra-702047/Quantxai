import sqlite3
import os
import json
import time

if os.environ.get("VERCEL") == "1":
    DB_FILE = "/tmp/quantx.db"
else:
    DB_FILE = "quantx.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """Initializes the database schemas for trades, positions, and portfolio tracking."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Create Portfolio Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER DEFAULT 1,
        cash REAL NOT NULL,
        initial_capital REAL NOT NULL,
        equity REAL NOT NULL,
        daily_start_equity REAL NOT NULL,
        circuit_breaker_active INTEGER DEFAULT 0,
        equity_curve TEXT DEFAULT '[]'
    )
    """)
    
    # 2. Create Trades Table (Recent closed trades log)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER DEFAULT 1,
        symbol TEXT NOT NULL,
        signal TEXT NOT NULL,
        entry_price REAL NOT NULL,
        exit_price REAL NOT NULL,
        quantity INTEGER NOT NULL,
        pnl REAL NOT NULL,
        reason TEXT NOT NULL,
        timestamp REAL NOT NULL
    )
    """)
    
    # 3. Create Positions Table (Active paper trades)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS positions (
        symbol TEXT NOT NULL,
        user_id INTEGER DEFAULT 1,
        signal TEXT NOT NULL,
        entry_price REAL NOT NULL,
        quantity INTEGER NOT NULL,
        stop_loss REAL NOT NULL,
        target REAL NOT NULL,
        current_price REAL NOT NULL,
        unrealized_pnl REAL NOT NULL,
        PRIMARY KEY (symbol, user_id)
    )
    """)
    
    # 4. Create Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        email TEXT,
        telegram_token TEXT,
        telegram_chat_id TEXT,
        created_at REAL NOT NULL
    )
    """)
    
    # 5. Create Sessions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        expires_at REAL NOT NULL
    )
    """)
    
    # Schema Migration: Alter old tables if they don't have user_id
    try:
        cursor.execute("ALTER TABLE portfolio ADD COLUMN user_id INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE trades ADD COLUMN user_id INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE positions ADD COLUMN user_id INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN telegram_token TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN telegram_chat_id TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN broker_mode TEXT DEFAULT 'PAPER'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN zerodha_api_key TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN zerodha_api_secret TEXT")
    except sqlite3.OperationalError:
        pass

    # Seed initial portfolio value for default/guest user (id=1)
    cursor.execute("SELECT COUNT(*) FROM portfolio WHERE user_id = 1")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO portfolio (user_id, cash, initial_capital, equity, daily_start_equity, circuit_breaker_active, equity_curve)
        VALUES (1, 100000.0, 100000.0, 100000.0, 100000.0, 0, '[100000.0]')
        """)
        
    conn.commit()
    conn.close()

# Helper Functions to fetch/update data matching previous JSON structure

def load_portfolio_from_db(user_id: int = 1) -> dict:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM portfolio WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row:
        # Auto-create portfolio for new user on load
        cursor.execute("""
        INSERT INTO portfolio (user_id, cash, initial_capital, equity, daily_start_equity, circuit_breaker_active, equity_curve)
        VALUES (?, 100000.0, 100000.0, 100000.0, 100000.0, 0, '[100000.0]')
        """, (user_id,))
        conn.commit()
        cursor.execute("SELECT * FROM portfolio WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
    port_dict = {
        "cash": row["cash"],
        "initial_capital": row["initial_capital"],
        "equity": row["equity"],
        "daily_start_equity": row["daily_start_equity"],
        "circuit_breaker_active": bool(row["circuit_breaker_active"]),
        "equity_curve": json.loads(row["equity_curve"])
    }
    
    # Fetch active open positions for user
    cursor.execute("SELECT * FROM positions WHERE user_id = ?", (user_id,))
    pos_rows = cursor.fetchall()
    port_dict["open_positions"] = [dict(r) for r in pos_rows]
    
    # Fetch closed trades history for user (limit to last 50)
    cursor.execute("SELECT * FROM trades WHERE user_id = ? ORDER BY timestamp DESC LIMIT 50", (user_id,))
    trade_rows = cursor.fetchall()
    port_dict["trade_history"] = [dict(r) for r in trade_rows]
    
    conn.close()
    return port_dict

def save_portfolio_to_db(cash: float, equity: float, circuit_breaker_active: bool, equity_curve: list, user_id: int = 1):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE portfolio
    SET cash = ?, equity = ?, circuit_breaker_active = ?, equity_curve = ?
    WHERE user_id = ?
    """, (cash, equity, int(circuit_breaker_active), json.dumps(equity_curve), user_id))
    conn.commit()
    conn.close()

def save_closed_trade(symbol: str, signal: str, entry_price: float, exit_price: float, quantity: int, pnl: float, reason: str, user_id: int = 1):
    t_now = time.time()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO trades (user_id, symbol, signal, entry_price, exit_price, quantity, pnl, reason, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, symbol, signal, entry_price, exit_price, quantity, pnl, reason, t_now))
    conn.commit()
    conn.close()

    # Append to local trades.csv for easy access
    if os.environ.get("VERCEL") == "1":
        csv_file = "/tmp/trades.csv"
    else:
        csv_file = "trades.csv"
    import csv
    file_exists = os.path.exists(csv_file)
    try:
        with open(csv_file, mode="a", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Timestamp", "User ID", "Symbol", "Action", "Entry Price", "Exit Price", "Quantity", "PnL (INR)", "Exit Reason"])
            writer.writerow([
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t_now)),
                user_id,
                symbol,
                signal,
                entry_price,
                exit_price,
                quantity,
                pnl,
                reason
            ])
    except Exception as e:
        print(f"⚠️ Failed to write trade to local CSV: {e}")

def add_position(symbol: str, signal: str, entry_price: float, quantity: int, stop_loss: float, target: float, user_id: int = 1):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO positions (symbol, user_id, signal, entry_price, quantity, stop_loss, target, current_price, unrealized_pnl)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0)
    """, (symbol, user_id, signal, entry_price, quantity, stop_loss, target, entry_price))
    conn.commit()
    conn.close()

def remove_position(symbol: str, user_id: int = 1):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM positions WHERE symbol = ? AND user_id = ?", (symbol, user_id))
    conn.commit()
    conn.close()

def clear_circuit_breaker(user_id: int = 1):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT equity FROM portfolio WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    current_equity = row[0] if row else 100000.0
    cursor.execute("""
    UPDATE portfolio
    SET circuit_breaker_active = 0, daily_start_equity = ?
    WHERE user_id = ?
    """, (current_equity, user_id))
    conn.commit()
    conn.close()

# Auto-initialize database on import
initialize_database()
