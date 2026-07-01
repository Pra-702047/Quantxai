import os
import json

def load_position(filepath="positions.json"):
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not data or data.get("status") != "OPEN":
                return None
            return data
    except Exception as e:
        print(f"⚠️ Error loading position: {e}")
        return None

def save_position(signal, entry_price, quantity, stop_loss, target, filepath="positions.json"):
    data = {
        "status": "OPEN",
        "signal": signal.upper(),
        "entry_price": float(entry_price),
        "quantity": int(quantity),
        "stop_loss": float(stop_loss),
        "target": float(target)
    }
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"💾 Position saved to {filepath} | {signal} | Entry: {entry_price} | Qty: {quantity} | SL: {stop_loss} | TP: {target}")
    except Exception as e:
        print(f"⚠️ Error saving position: {e}")

def clear_position(filepath="positions.json"):
    if os.path.exists(filepath):
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=4)
            print(f"🗑️ Position cleared in {filepath}")
        except Exception as e:
            print(f"⚠️ Error clearing position: {e}")
