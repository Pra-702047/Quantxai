def calculate_position_size(capital: float, risk_percent: float, stop_loss_distance: float, atr_value: float = 0.0, win_rate: float = 0.612) -> int:
    """
    Calculates volatility-adjusted position sizing using a safe Quarter-Kelly fraction 
    aligned to ATR values.
    
    Position Size = (Capital * Kelly Fraction) / Stop Loss Distance (or ATR)
    """
    if stop_loss_distance <= 0:
        # Fallback to ATR-based distance if stop loss is not resolved
        stop_loss_distance = atr_value * 1.5 if atr_value > 0 else 10.0
        
    # Kelly Criterion calculation: K = W - (1 - W)/R
    # Assume 1:2 risk-to-reward ratio (R = 2.0)
    r_to_r = 2.0
    w_rate = win_rate if 0.0 < win_rate < 1.0 else (win_rate / 100.0 if win_rate > 1.0 else 0.612)
    
    kelly_percentage = w_rate - (1.0 - w_rate) / r_to_r
    
    # Use safe Quarter-Kelly (25% of Kelly fraction) capped at 5% max risk per trade
    safe_kelly_fraction = max(0.005, min(kelly_percentage * 0.25, 0.05))
    
    # If the user explicitly passed a custom risk_percent (e.g. from UI settings), blend them
    selected_risk = min(risk_percent, safe_kelly_fraction)
    
    risk_amount = capital * selected_risk
    
    position_size = risk_amount / stop_loss_distance
    return max(1, round(position_size))