import numpy as np
import pandas as pd

def calculate_metrics(trades: list, equity_curve: list, initial_capital: float = 100000.0) -> dict:
    """
    Computes professional-grade performance metrics for strategy assessment.
    """
    total_trades = len(trades)
    if total_trades == 0:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "avg_profit": 0.0,
            "avg_loss": 0.0,
            "net_profit": 0.0,
            "profit_factor": 1.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 1.0,
            "sortino_ratio": 1.0,
            "calmar_ratio": 1.0,
            "avg_holding_time": 0.0
        }
        
    pnl_list = [t["pnl"] for t in trades]
    win_trades = [t for t in pnl_list if t > 0]
    loss_trades = [t for t in pnl_list if t < 0]
    
    winning_count = len(win_trades)
    losing_count = len(loss_trades)
    win_rate = round((winning_count / total_trades) * 100, 1)
    
    avg_profit = round(np.mean(win_trades), 2) if winning_count > 0 else 0.0
    avg_loss = round(np.mean(loss_trades), 2) if losing_count > 0 else 0.0
    net_profit = round(sum(pnl_list), 2)
    
    gross_profits = sum(win_trades)
    gross_losses = sum(abs(l) for l in loss_trades)
    profit_factor = round(gross_profits / gross_losses, 2) if gross_losses > 0 else round(gross_profits, 2)
    
    # Max Drawdown
    eq_arr = np.array(equity_curve)
    cum_max = np.maximum.accumulate(eq_arr)
    drawdowns = (eq_arr - cum_max) / (cum_max + 1e-10)
    max_dd = round(float(np.abs(drawdowns.min())) * 100, 2)
    
    # Return metrics for Sharpe/Sortino
    returns = pd.Series(pnl_list) / initial_capital
    mean_ret = returns.mean()
    std_ret = returns.std()
    
    sharpe = round(float((mean_ret / std_ret) * np.sqrt(252)), 2) if std_ret > 0 else 1.0
    
    downside_returns = returns[returns < 0]
    std_downside = downside_returns.std()
    sortino = round(float((mean_ret / std_downside) * np.sqrt(252)), 2) if std_downside > 0 else 1.0
    
    total_ret = net_profit / initial_capital
    calmar = round(float(total_ret / (max_dd / 100.0)), 2) if max_dd > 0 else 1.0
    
    avg_holding = round(float(np.mean([t["holding_time"] for t in trades])), 1)
    
    return {
        "total_trades": total_trades,
        "winning_trades": winning_count,
        "losing_trades": losing_count,
        "win_rate": win_rate,
        "avg_profit": avg_profit,
        "avg_loss": avg_loss,
        "net_profit": net_profit,
        "profit_factor": profit_factor,
        "max_drawdown": max_dd,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "calmar_ratio": calmar,
        "avg_holding_time": avg_holding
    }

def run_monte_carlo(trades: list, iterations: int = 1000, initial_capital: float = 100000.0) -> dict:
    """
    Shuffles trade logs randomly 1000 times to model the worst-case drawdowns 
    and evaluate trade sequence risk.
    """
    if len(trades) < 5:
        return {"95th_percentile_drawdown": 0.0, "avg_shuffled_drawdown": 0.0}
        
    pnl_list = [t["pnl"] for t in trades]
    drawdowns = []
    
    for _ in range(iterations):
        shuffled = np.random.permutation(pnl_list)
        eq = [initial_capital]
        current = initial_capital
        for p in shuffled:
            current += p
            eq.append(current)
            
        eq_arr = np.array(eq)
        cum_max = np.maximum.accumulate(eq_arr)
        dds = (eq_arr - cum_max) / (cum_max + 1e-10)
        drawdowns.append(np.abs(dds.min()))
        
    drawdowns = np.array(drawdowns) * 100.0
    
    return {
        "95th_percentile_drawdown": round(float(np.percentile(drawdowns, 95)), 2),
        "avg_shuffled_drawdown": round(float(np.mean(drawdowns)), 2),
        "worst_shuffled_drawdown": round(float(np.max(drawdowns)), 2)
    }
