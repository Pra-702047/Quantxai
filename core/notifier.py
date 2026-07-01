import threading
import urllib.request
import urllib.parse
import json

def send_telegram_alert(user_id: int, message: str):
    """Sends a Telegram push alert in a daemon thread so it never blocks execution."""
    def send():
        from core.db import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT telegram_token, telegram_chat_id FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return
            
        token = row["telegram_token"]
        chat_id = row["telegram_chat_id"]
        
        if not token or not chat_id:
            return
            
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = json.dumps({
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }).encode('utf-8')
            
            req = urllib.request.Request(
                url, 
                data=data, 
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                response.read()
        except Exception as e:
            print(f"⚠️ Failed to send Telegram alert: {e}")
            
    threading.Thread(target=send, daemon=True).start()
