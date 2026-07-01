def get_trading_mode(timeframe):
    intraday = ["1m", "5m", "15m"]
    swing = ["1h"]
    delivery = ["1d"]

    if timeframe in intraday:
        return "INTRADAY"
    elif timeframe in swing:
        return "SWING"
    elif timeframe in delivery:
        return "DELIVERY"
    else:
        return "UNKNOWN"