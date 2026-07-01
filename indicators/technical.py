import pandas as pd
import numpy as np

def clean_series(df, col_name):
    """
    Safely extract a 1D Pandas Series from a DataFrame column,
    handling yfinance MultiIndex structures.
    """
    col = df[col_name]
    if isinstance(col, pd.DataFrame):
        return col.iloc[:, 0]
    return col

def calculate_ema(data, span=14):
    close = clean_series(data, 'Close')
    return close.ewm(span=span, adjust=False).mean()

def calculate_atr(data, window=14):
    high = clean_series(data, 'High')
    low = clean_series(data, 'Low')
    close = clean_series(data, 'Close')
    
    high_low = high - low
    high_close = (high - close.shift()).abs()
    low_close = (low - close.shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=window).mean()
    return atr

def calculate_rsi(data, window=14):
    close = clean_series(data, 'Close')
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / (loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_adx(data, window=14):
    high = clean_series(data, 'High')
    low = clean_series(data, 'Low')
    close = clean_series(data, 'Close')
    
    up_move = high.diff()
    down_move = -low.diff()
    
    pos_dm = pd.Series(0.0, index=data.index)
    neg_dm = pd.Series(0.0, index=data.index)
    
    pos_dm.loc[(up_move > down_move) & (up_move > 0)] = up_move
    neg_dm.loc[(down_move > up_move) & (down_move > 0)] = down_move
    
    high_low = high - low
    high_close = (high - close.shift()).abs()
    low_close = (low - close.shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    
    smooth_tr = tr.rolling(window=window).mean()
    smooth_pos_dm = pos_dm.rolling(window=window).mean()
    smooth_neg_dm = neg_dm.rolling(window=window).mean()
    
    pos_di = 100 * (smooth_pos_dm / (smooth_tr + 1e-10))
    neg_di = 100 * (smooth_neg_dm / (smooth_tr + 1e-10))
    
    dx = 100 * (pos_di - neg_di).abs() / (pos_di + neg_di + 1e-10)
    adx = dx.rolling(window=window).mean()
    return adx

def calculate_vwap(data):
    high = clean_series(data, 'High')
    low = clean_series(data, 'Low')
    close = clean_series(data, 'Close')
    volume = clean_series(data, 'Volume')
    
    typical_price = (high + low + close) / 3
    tp_vol = typical_price * volume
    try:
        # Group by day if index is datetime
        dates = data.index.date
        cum_tp_vol = tp_vol.groupby(dates).cumsum()
        cum_vol = volume.groupby(dates).cumsum()
        vwap = cum_tp_vol / (cum_vol + 1e-10)
    except Exception:
        # Fallback to cumulative sum
        vwap = tp_vol.cumsum() / (volume.cumsum() + 1e-10)
    return vwap

def calculate_volume_spikes(data, window=20):
    volume = clean_series(data, 'Volume')
    avg_vol = volume.rolling(window=window).mean()
    ratio = volume / (avg_vol + 1e-10)
    return ratio

def calculate_bollinger_bands(data, window=20, num_std=2):
    close = clean_series(data, 'Close')
    middle_band = close.rolling(window=window).mean()
    std_dev = close.rolling(window=window).std()
    upper_band = middle_band + (num_std * std_dev)
    lower_band = middle_band - (num_std * std_dev)
    return upper_band, middle_band, lower_band

def calculate_rvol(data, window=20):
    volume = clean_series(data, 'Volume')
    avg_vol = volume.rolling(window=window).mean()
    rvol = volume / (avg_vol + 1e-10)
    return rvol
