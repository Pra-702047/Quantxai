import yfinance as yf
import time
import numpy as np

# Gold specific sentiment words
GOLD_BULLISH = {
    'rate cut': 1.0, 'rate cuts': 1.0, 'inflation': 0.8, 'stimulus': 0.8, 
    'geopolitical': 0.8, 'tension': 0.6, 'crisis': 0.8, 'safe haven': 0.9, 
    'rally': 0.5, 'surge': 0.5, 'weak dollar': 0.8, 'cpi rise': 0.7, 'cut': 0.4
}

GOLD_BEARISH = {
    'rate hike': -1.0, 'rate hikes': -1.0, 'strong dollar': -0.8, 'recovery': -0.5, 
    'fall': -0.5, 'drop': -0.5, 'hawkish': -0.8, 'cpi drop': -0.7, 'hike': -0.5
}

def analyze_gold_headline(headline: str) -> float:
    words = headline.lower().replace(',', ' ').replace('.', ' ').split()
    score = 0.0
    for w in words:
        if w in GOLD_BULLISH:
            score += GOLD_BULLISH[w]
        elif w in GOLD_BEARISH:
            score += GOLD_BEARISH[w]
    return float(np.clip(score, -1.0, 1.0))

def get_gold_advice() -> dict:
    """
    Downloads COMEX Gold Futures (GC=F) and NSE Gold BeES (GOLDBEES.NS) data.
    Analyzes gold-specific news to generate Buy/Sell signals and entry/exit advice.
    """
    gold_futures_price = 2330.0
    gold_bees_price = 61.50
    change_pct = +0.15
    
    # 1. Fetch Live Gold Prices
    try:
        futures_ticker = yf.Ticker("GC=F")
        futures_history = futures_ticker.history(period="1d")
        if not futures_history.empty:
            gold_futures_price = float(futures_history["Close"].iloc[-1])
            prev_close = float(futures_ticker.info.get("previousClose", gold_futures_price))
            change_pct = round(((gold_futures_price - prev_close) / prev_close) * 100, 2)
    except Exception as e:
        print(f"⚠️ Failed to fetch COMEX Gold price: {e}")
        
    try:
        bees_ticker = yf.Ticker("GOLDBEES.NS")
        bees_history = bees_ticker.history(period="1d")
        if not bees_history.empty:
            gold_bees_price = float(bees_history["Close"].iloc[-1])
    except Exception as e:
        print(f"⚠️ Failed to fetch NSE Gold BeES price: {e}")
        
    # 2. Fetch Gold News & Calculate Sentiment
    articles = []
    total_score = 0.0
    valid_count = 0
    cutoff_time = time.time() - (20 * 24 * 3600) # 20 days rolling
    
    try:
        news_list = yf.Ticker("GC=F").news
    except Exception:
        news_list = None
        
    if news_list:
        for item in news_list:
            title = item.get("title", "")
            publisher = item.get("publisher", "Reuters")
            pub_time = item.get("providerPublishTime", 0)
            
            if pub_time > 0 and pub_time < cutoff_time:
                continue
                
            score = analyze_gold_headline(title)
            sent_label = "Positive" if score > 0.15 else "Negative" if score < -0.15 else "Neutral"
            date_str = time.strftime("%b %d, %Y", time.localtime(pub_time)) if pub_time > 0 else "Recent"
            
            articles.append({
                "title": title,
                "publisher": publisher,
                "sentiment": sent_label,
                "date": date_str
            })
            
            total_score += score
            valid_count += 1
            
    avg_score = round(total_score / valid_count, 2) if valid_count > 0 else 0.0
    
    # 3. Generate Buy/Sell Signals and Timing Recommendations
    if avg_score > 0.10:
        signal = "BUY"
        recommendation = "Gold is a safe haven. Inflation expectations or rate cut discussions are supporting prices. Buy on dips."
        entry_advice = f"Accumulate GOLDBEES below ₹{round(gold_bees_price * 0.995, 2)}"
        target_advice = f"Target Target: ₹{round(gold_bees_price * 1.05, 2)}"
    elif avg_score < -0.10:
        signal = "SELL"
        recommendation = "Strong dollar and hawkish Fed statements are creating headwinds for commodities. Reduce long positions."
        entry_advice = "Avoid buying here. Wait for consolidation."
        target_advice = f"Short levels at GC=F resistance: ${round(gold_futures_price * 1.01, 1)}"
    else:
        signal = "HOLD"
        recommendation = "Gold is trading in a tight range. Neutral macroeconomic signals. Consolidate positions."
        entry_advice = "Hold current positions. Neutral regime."
        target_advice = "Range-bound trading expected."

    return {
        "futures_price": round(gold_futures_price, 2),
        "bees_price": round(gold_bees_price, 2),
        "change_pct": change_pct,
        "sentiment_score": avg_score,
        "signal": signal,
        "recommendation": recommendation,
        "entry_advice": entry_advice,
        "target_advice": target_advice,
        "articles": articles[:5] if articles else [{"title": "No recent gold macroeconomic headlines.", "publisher": "System", "sentiment": "Neutral", "date": "Recent"}]
    }
