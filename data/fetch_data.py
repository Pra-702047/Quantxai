import yfinance as yf
import config

def get_data():
    data = yf.download(
        config.SYMBOL,
        period="1mo",
        interval=config.TIMEFRAME
    )
    return data