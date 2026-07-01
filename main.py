import sys
import pandas as pd
from core.mode_selector import get_trading_mode
from data.fetch_data import get_data
from strategies.ema_strategy import apply_ema_strategy
from risk.position_sizing import calculate_position_size
from broker.paper_broker import place_order
from risk.trade_levels import calculate_trade_levels
from core.position_tracker import load_position, save_position, clear_position
import config

# Reconfigure stdout to UTF-8 on Windows to prevent Emoji print crashes
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding='utf-8')

def run_bot():
    print("🚀 Bot Started")

    # ---- Detect Mode First ----
    mode = get_trading_mode(config.TIMEFRAME)
    print(f"⏱ Timeframe: {config.TIMEFRAME}")
    print(f"🧠 Trading Mode: {mode}")

    # ---- Fetch Data ----
    data = get_data()
    print("✅ Data fetched")

    # ---- Extract Current Price Robustly ----
    close_col = data["Close"]
    if isinstance(close_col, pd.Series):
        current_price = float(close_col.iloc[-1])
    else:
        current_price = float(close_col.iloc[-1].iloc[0])
    print(f"📍 Current Price: {current_price}")

    # ---- Position Tracking & Monitoring ----
    position = load_position()

    if position is not None:
        pos_signal = position["signal"]
        stop_loss = position["stop_loss"]
        target = position["target"]
        qty = position["quantity"]

        print(f"🔄 Active Position Found → {pos_signal} | Qty: {qty} | Entry: {position['entry_price']} | SL: {stop_loss} | TP: {target}")

        # Check for exits
        exit_triggered = False
        exit_reason = ""

        if pos_signal == "BUY":
            if current_price <= stop_loss:
                exit_triggered = True
                exit_reason = "STOP_LOSS"
            elif current_price >= target:
                exit_triggered = True
                exit_reason = "TAKE_PROFIT"
        elif pos_signal == "SELL":
            if current_price >= stop_loss:
                exit_triggered = True
                exit_reason = "STOP_LOSS"
            elif current_price <= target:
                exit_triggered = True
                exit_reason = "TAKE_PROFIT"

        if exit_triggered:
            print(f"🚨 Exit Triggered: {exit_reason} at {current_price}")
            place_order(f"CLOSE_{pos_signal}", qty)
            clear_position()
        else:
            print("⏳ Holding position. Exit conditions not met.")

    else:
        # ---- Strategy Signal Generation ----
        signal = apply_ema_strategy(data)
        print("📊 Signal:", signal)

        if signal in ["BUY", "SELL"]:
            # ---- Risk Calculation ----
            quantity = calculate_position_size(
                config.ACCOUNT_BALANCE,
                config.RISK_PERCENT,
                config.STOP_LOSS_DISTANCE
            )
            print("💰 Quantity:", quantity)

            # ---- Trade Levels ----
            stop_loss, target = calculate_trade_levels(
                current_price,
                config.STOP_LOSS_DISTANCE,
                signal=signal
            )

            print(f"🛑 Stop Loss: {stop_loss}")
            print(f"🎯 Target: {target}")

            # ---- Execute Order & Save State ----
            place_order(signal, quantity)
            save_position(signal, current_price, quantity, stop_loss, target)
        else:
            print("😴 No trade signal. Idle state.")

if __name__ == "__main__":
    run_bot()