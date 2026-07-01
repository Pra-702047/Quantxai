def calculate_trade_levels(entry_price, atr_value, signal="BUY", atr_multiplier=1.5, reward_ratio=2.0):
    stop_loss_distance = atr_value * atr_multiplier
    if stop_loss_distance <= 0:
        stop_loss_distance = entry_price * 0.01  # Fallback: 1% of price
        
    if signal.upper() == "SELL":
        stop_loss = entry_price + stop_loss_distance
        target = entry_price - (stop_loss_distance * reward_ratio)
    else:
        stop_loss = entry_price - stop_loss_distance
        target = entry_price + (stop_loss_distance * reward_ratio)
    return round(stop_loss, 2), round(target, 2), round(stop_loss_distance, 2)