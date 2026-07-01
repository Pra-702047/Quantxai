import yfinance as yf
import numpy as np

# High-impact and Normal-impact Financial Keyword Lexicons with Weights
POSITIVE_KEYWORDS = {
    # High-impact (+1.0)
    'beat': 1.0, 
    'upgrade': 1.0, 
    'merger': 1.0, 
    'acquisition': 1.0, 
    'approval': 1.0, 
    'breakthrough': 1.0,
    # Normal (+0.5)
    'profit': 0.5, 
    'growth': 0.5, 
    'record': 0.5, 
    'surge': 0.5, 
    'buy': 0.5, 
    'win': 0.5, 
    'dividend': 0.5, 
    'earnings': 0.5, 
    'jump': 0.5, 
    'high': 0.5, 
    'bullish': 0.5, 
    'positive': 0.5, 
    'gain': 0.5, 
    'acquire': 0.5, 
    'success': 0.5, 
    'expand': 0.5, 
    'up': 0.3
}

NEGATIVE_KEYWORDS = {
    # High-impact (-1.0)
    'lawsuit': -1.0, 
    'miss': -1.0, 
    'misses': -1.0, 
    'downgrade': -1.0, 
    'penalty': -1.0, 
    'fraud': -1.0, 
    'investigation': -1.0, 
    'crash': -1.0, 
    'fine': -1.0, 
    'scam': -1.0,
    # Normal (-0.5)
    'loss': -0.5, 
    'decline': -0.5, 
    'drop': -0.5, 
    'fall': -0.5, 
    'dispute': -0.5, 
    'resign': -0.5, 
    'fail': -0.5, 
    'lower': -0.5, 
    'weak': -0.5, 
    'bearish': -0.5, 
    'warning': -0.5, 
    'debt': -0.5, 
    'down': -0.3, 
    'risk': -0.4
}

def analyze_headline_sentiment(headline: str) -> float:
    """Calculates weighted sentiment score from -1.0 to 1.0 for a headline."""
    words = headline.lower().replace(',', ' ').replace('.', ' ').replace('\'', ' ').split()
    score = 0.0
    for w in words:
        if w in POSITIVE_KEYWORDS:
            score += POSITIVE_KEYWORDS[w]
        elif w in NEGATIVE_KEYWORDS:
            score += NEGATIVE_KEYWORDS[w]
            
    return float(np.clip(score, -1.0, 1.0))

def get_news_sentiment(symbol: str) -> dict:
    """
    Downloads news for a symbol, filters for articles within the last 20 days, 
    performs lexicon sentiment analysis, and returns parsed articles with timestamps.
    """
    import time
    cutoff_time = time.time() - (20 * 24 * 3600)
    
    try:
        ticker = yf.Ticker(symbol)
        news_list = ticker.news
    except Exception as e:
        print(f"⚠️ Failed to download news for {symbol}: {e}")
        news_list = None
        
    if not news_list:
        return {
            "score": 0.0,
            "sentiment": "Neutral",
            "articles": [
                {"title": f"No recent news articles found for {symbol}.", "publisher": "System", "sentiment": "Neutral", "date": "Today"}
            ]
        }
        
    articles_data = []
    total_score = 0.0
    valid_count = 0
    
    for item in news_list:
        title = item.get("title", "")
        publisher = item.get("publisher", "Yahoo Finance")
        pub_time = item.get("providerPublishTime", 0)
        
        # 1. 20 Days News Filter (Must be newer than cutoff_time)
        if pub_time > 0 and pub_time < cutoff_time:
            continue
            
        if not title:
            continue
            
        score = analyze_headline_sentiment(title)
        
        if score > 0.15:
            sent_label = "Positive"
        elif score < -0.15:
            sent_label = "Negative"
        else:
            sent_label = "Neutral"
            
        # Format date safely
        date_str = time.strftime("%b %d, %Y", time.localtime(pub_time)) if pub_time > 0 else "Recent"
            
        articles_data.append({
            "title": title,
            "publisher": publisher,
            "sentiment": sent_label,
            "date": date_str
        })
        
        total_score += score
        valid_count += 1
        
    # Fallback if all news were filtered out
    if not articles_data:
        return {
            "score": 0.0,
            "sentiment": "Neutral",
            "articles": [
                {"title": f"No news articles found in the last 20 days for {symbol}.", "publisher": "System", "sentiment": "Neutral", "date": "Last 20d"}
            ]
        }
        
    avg_score = round(total_score / valid_count, 2) if valid_count > 0 else 0.0
    
    if avg_score > 0.15:
        overall_sent = "Positive"
    elif avg_score < -0.15:
        overall_sent = "Negative"
    else:
        overall_sent = "Neutral"
        
    return {
        "score": avg_score,
        "sentiment": overall_sent,
        "articles": articles_data
    }
