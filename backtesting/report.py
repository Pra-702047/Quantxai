def generate_ai_report(metrics: dict) -> dict:
    """
    Evaluates backtest metrics to output professional trading advice 
    diagnosing system weaknesses, optimal regimes, and improvements.
    """
    win_rate = metrics.get("win_rate", 0.0)
    profit_factor = metrics.get("profit_factor", 1.0)
    max_dd = metrics.get("max_drawdown", 0.0)
    total_trades = metrics.get("total_trades", 0)
    
    # 1. Weakness Detection
    if total_trades > 30 and win_rate < 42.0:
        weakness = "High trade count with low win rate indicates frequent whipsaws, likely trading noise inside consolidations."
    elif max_dd > 15.0:
        weakness = "High maximum drawdown warns of excessive position sizes or lack of risk mitigation during trend reversals."
    elif profit_factor < 1.05:
        weakness = "Strategy expectancy is marginal; profits are heavily eroded by slippage and execution costs."
    else:
        weakness = "Normal risk profile, but potential stagnation during prolonged low-volatility regimes."
        
    # 2. Optimal Market Condition
    if win_rate > 55.0 and profit_factor > 1.8:
        best_condition = "Highly suited for trending impulses (bullish markup phases) with sustained volume."
    else:
        best_condition = "Performs best in directional breakouts where ADX remains sustained above 25."
        
    # 3. Worst Market Condition
    if win_rate < 45.0:
        worst_condition = "Choppy, sideways range consolidations where SMA crossovers and lagging indicators yield false breakouts."
    else:
        worst_condition = "Low volume sideways drift where mean reversion bands are repeatedly tested without follow-through."
        
    # 4. Best Risk Sizing
    if max_dd > 12.0:
        suggested_risk = "0.5% - 1.0% Risk per trade maximum. High drawdowns necessitate conservative position sizing."
    else:
        suggested_risk = "1.0% - 1.5% Risk per trade utilizing dynamic volatility-adjusted ATR position sizing."
        
    # 5. Suggested Improvements
    improvements = []
    if win_rate < 45.0:
        improvements.append("Deploy Bollinger Bands or RSI limits to prevent chasing entries near channel boundaries.")
    if max_dd > 10.0:
        improvements.append("Implement a Trailing Stop Loss (1.5x ATR) to defend unrealized profits on trending swings.")
    if total_trades > 50:
        improvements.append("Add an ADX filter (ADX > 25) to block trend trades when structural momentum is flat.")
        
    if not improvements:
        improvements.append("Calibrate ML feature classifiers to predict probability of profit prior to entry execution.")
        
    return {
        "weakness": weakness,
        "best_condition": best_condition,
        "worst_condition": worst_condition,
        "suggested_risk": suggested_risk,
        "improvements": ", ".join(improvements)
    }
