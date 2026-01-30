#!/usr/bin/env python3
# Description: Day-Trading Script (Alpaca API)
# Usage: python3 daytrader.py
# Author: Justin Oros
# Source: https://github.com/JustinOros 

import os
import sys
import time
import logging
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from pathlib import Path
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi

SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "daytrader.json"
ENV_PATH = SCRIPT_DIR / ".env"

DEFAULT_CONFIG = {
    "DEBUG_MODE": True,
    "SYMBOL": "SPY",
    "BAR_TIMEFRAME": "5Min",
    "RISK_PER_TRADE": 0.005,
    "SHORT_WINDOW": 20,
    "LONG_WINDOW": 50,
    "MIN_NOTIONAL": 1.0,
    "POLL_INTERVAL": 120,
    "MAX_DRAWDOWN": 0.12,
    "PDT_RULE": True,
    "USE_TRAILING_STOP": True,
    "PROFIT_TARGET_1": 1.5,
    "PROFIT_TARGET_2": 3.0,
    "VOLATILITY_ADJUSTMENT": True,
    "MARKET_HOURS_FILTER": False,
    "ENABLE_SLIPPAGE": True,
    "SLIPPAGE_PCT": 0.0005,
    "COMMISSION_PCT": 0.0005,
    "MIN_SIGNAL_STRENGTH": 0.50,
    "BACKTEST_DAYS": 90,
    "USE_LIMIT_ORDERS": True,
    "LIMIT_ORDER_TIMEOUT": 60,
    "ADX_THRESHOLD": 20,
    "VOLUME_MULTIPLIER": 0.5,
    "ATR_STOP_MULTIPLIER": 1.5,
    "MAX_HOLD_TIME": 7200,
    "REGIME_DETECTION": True,
    "MULTIFRAME_FILTER": False,
    "BB_WINDOW": 20,
    "BB_STD": 2.0,
    "USE_EMA": True,
    "REQUIRE_CANDLE_PATTERN": False,
    "USE_PIVOT_POINTS": False,
    "VIX_THRESHOLD": 20,
    "USE_VIX_FILTER": True,
    "USE_FIBONACCI": False,
    "MAX_TRADES_PER_DAY": 1000,
    "SKIP_MONDAYS_FRIDAYS": False,
    "USE_200_SMA_FILTER": False,
    "REQUIRE_MACD_CONFIRMATION": False,
    "MIN_RISK_REWARD": 1.5,
    "PULLBACK_PERCENTAGE": 0.382,
    "ENABLE_SHORT_SELLING": False
}

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    with open(ENV_PATH, "w") as f:
        f.write('APCA_API_KEY_ID="YOUR_API_KEY_HERE"\n')
        f.write('APCA_API_SECRET_KEY="YOUR_SECRET_KEY_HERE"\n')
        f.write('APCA_API_BASE_URL="https://paper-api.alpaca.markets"\n')
    print("⚠️  Created placeholder .env file.")
    print("    Please add your Alpaca API keys to .env file")
    sys.exit(1)

if CONFIG_PATH.exists():
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
else:
    with open(CONFIG_PATH, "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=4)
    config = DEFAULT_CONFIG.copy()
    print(f"✅ Created default config file at {CONFIG_PATH}")

DEBUG_MODE = bool(config.get("DEBUG_MODE", False))
SYMBOL = config["SYMBOL"]
BAR_TIMEFRAME = config.get("BAR_TIMEFRAME", "5Min")
RISK_PER_TRADE = float(config["RISK_PER_TRADE"])
SHORT_WINDOW = int(config["SHORT_WINDOW"])
LONG_WINDOW = int(config["LONG_WINDOW"])
MIN_NOTIONAL = float(config["MIN_NOTIONAL"])
POLL_INTERVAL = int(config["POLL_INTERVAL"])
MAX_DRAWDOWN = float(config["MAX_DRAWDOWN"])
PDT_RULE = bool(config["PDT_RULE"])
USE_TRAILING_STOP = bool(config["USE_TRAILING_STOP"])
PROFIT_TARGET_1 = float(config["PROFIT_TARGET_1"])
PROFIT_TARGET_2 = float(config["PROFIT_TARGET_2"])
VOLATILITY_ADJUSTMENT = bool(config["VOLATILITY_ADJUSTMENT"])
MARKET_HOURS_FILTER = bool(config["MARKET_HOURS_FILTER"])
ENABLE_SLIPPAGE = bool(config["ENABLE_SLIPPAGE"])
SLIPPAGE_PCT = float(config["SLIPPAGE_PCT"])
COMMISSION_PCT = float(config["COMMISSION_PCT"])
MIN_SIGNAL_STRENGTH = float(config["MIN_SIGNAL_STRENGTH"])
BACKTEST_DAYS = int(config["BACKTEST_DAYS"])
USE_LIMIT_ORDERS = bool(config["USE_LIMIT_ORDERS"])
LIMIT_ORDER_TIMEOUT = int(config["LIMIT_ORDER_TIMEOUT"])
ADX_THRESHOLD = float(config["ADX_THRESHOLD"])
VOLUME_MULTIPLIER = float(config["VOLUME_MULTIPLIER"])
ATR_STOP_MULTIPLIER = float(config["ATR_STOP_MULTIPLIER"])
MAX_HOLD_TIME = int(config["MAX_HOLD_TIME"])
REGIME_DETECTION = bool(config["REGIME_DETECTION"])
MULTIFRAME_FILTER = bool(config["MULTIFRAME_FILTER"])
BB_WINDOW = int(config["BB_WINDOW"])
BB_STD = float(config["BB_STD"])
USE_EMA = bool(config["USE_EMA"])
REQUIRE_CANDLE_PATTERN = bool(config["REQUIRE_CANDLE_PATTERN"])
USE_PIVOT_POINTS = bool(config["USE_PIVOT_POINTS"])
VIX_THRESHOLD = float(config["VIX_THRESHOLD"])
USE_VIX_FILTER = bool(config["USE_VIX_FILTER"])
USE_FIBONACCI = bool(config["USE_FIBONACCI"])
MAX_TRADES_PER_DAY = int(config["MAX_TRADES_PER_DAY"])
SKIP_MONDAYS_FRIDAYS = bool(config["SKIP_MONDAYS_FRIDAYS"])
USE_200_SMA_FILTER = bool(config["USE_200_SMA_FILTER"])
REQUIRE_MACD_CONFIRMATION = bool(config["REQUIRE_MACD_CONFIRMATION"])
MIN_RISK_REWARD = float(config["MIN_RISK_REWARD"])
PULLBACK_PERCENTAGE = float(config["PULLBACK_PERCENTAGE"])
ENABLE_SHORT_SELLING = bool(config.get("ENABLE_SHORT_SELLING", False))

EASTERN = pytz.timezone('US/Eastern')

api = tradeapi.REST(
    os.getenv('APCA_API_KEY_ID'),
    os.getenv('APCA_API_SECRET_KEY'),
    os.getenv('APCA_API_BASE_URL'),
    api_version='v2'
)

LOG_PATH = SCRIPT_DIR / "daytrader.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def debug_print(message):
    if DEBUG_MODE:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
        print(f"{timestamp} - DEBUG - 🔎  {message}", flush=True)

def calculate_sma(data, window):
    debug_print(f"Calculating SMA with window={window}")
    return data.rolling(window=window).mean()

def calculate_ema(data, window):
    debug_print(f"Calculating EMA with window={window}")
    return data.ewm(span=window, adjust=False).mean()

def calculate_rsi(data, window=14):
    debug_print(f"Calculating RSI with window={window}")
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_atr(high, low, close, window=14):
    debug_print(f"Calculating ATR with window={window}")
    high_low = high - low
    high_close_prev = abs(high - close.shift())
    low_close_prev = abs(low - close.shift())
    true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
    atr = true_range.rolling(window=window).mean()
    return atr

def calculate_adx(high, low, close, window=14):
    debug_print(f"Calculating ADX with window={window}")
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=window).mean()
    
    up_move = high - high.shift()
    down_move = low.shift() - low
    
    plus_dm = pd.Series(0.0, index=close.index)
    minus_dm = pd.Series(0.0, index=close.index)
    
    plus_dm[(up_move > down_move) & (up_move > 0)] = up_move
    minus_dm[(down_move > up_move) & (down_move > 0)] = down_move
    
    plus_di = 100 * (plus_dm.rolling(window=window).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=window).mean() / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=window).mean()
    
    return adx, plus_di, minus_di

def calculate_macd(close, fast=12, slow=26, signal=9):
    debug_print(f"Calculating MACD (fast={fast}, slow={slow}, signal={signal})")
    ema_fast = calculate_ema(close, fast)
    ema_slow = calculate_ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram

def calculate_bollinger_bands(close, window=20, num_std=2):
    debug_print(f"Calculating Bollinger Bands (window={window}, std={num_std})")
    if USE_EMA:
        middle = calculate_ema(close, window)
    else:
        middle = calculate_sma(close, window)
    
    std = close.rolling(window=window).std()
    upper = middle + (std * num_std)
    lower = middle - (std * num_std)
    
    return upper, middle, lower

def check_volume_confirmation(bars):
    debug_print("Checking volume confirmation...")
    if 'volume' not in bars.columns or len(bars) < 20:
        debug_print("Volume check: insufficient data, returning True")
        return True
    
    avg_volume = bars['volume'].rolling(window=20).mean().iloc[-1]
    current_volume = bars['volume'].iloc[-1]
    ratio = current_volume / avg_volume if avg_volume > 0 else 0
    
    result = current_volume >= (avg_volume * VOLUME_MULTIPLIER)
    debug_print(f"Volume: current={current_volume:.0f}, avg={avg_volume:.0f}, ratio={ratio:.2f}, pass={result}")
    return result

def detect_market_regime(bars):
    debug_print("Detecting market regime...")
    if len(bars) < 50:
        debug_print("Regime: insufficient data, returning 'unknown'")
        return 'unknown'
    
    closes = bars['close']
    highs = bars['high']
    lows = bars['low']
    
    adx, plus_di, minus_di = calculate_adx(highs, lows, closes, 14)
    current_adx = adx.iloc[-1]
    
    atr = calculate_atr(highs, lows, closes, 14)
    current_atr = atr.iloc[-1]
    atr_percentile = (atr <= current_atr).sum() / len(atr) * 100
    
    debug_print(f"Regime indicators: ADX={current_adx:.2f}, ATR_percentile={atr_percentile:.1f}%")
    
    if atr_percentile > 70:
        debug_print("Regime: HIGH_VOL")
        return 'high_vol'
    elif atr_percentile < 30:
        debug_print("Regime: LOW_VOL")
        return 'low_vol'
    elif current_adx > ADX_THRESHOLD:
        debug_print("Regime: TREND")
        return 'trend'
    else:
        debug_print("Regime: RANGE")
        return 'range'

def check_multiframe_confluence(symbol):
    debug_print(f"Checking multiframe confluence for {symbol}...")
    if not MULTIFRAME_FILTER:
        debug_print("Multiframe filter disabled, returning 'neutral'")
        return 'neutral'
    
    try:
        debug_print("Fetching hourly bars...")
        hourly_bars = api.get_bars(symbol, "1Hour", limit=50).df
        if len(hourly_bars) < 50:
            debug_print(f"Insufficient hourly data: {len(hourly_bars)} bars")
            return 'neutral'
        
        closes = hourly_bars['close']
        
        if USE_EMA:
            ema_short = calculate_ema(closes, 20)
            ema_long = calculate_ema(closes, 50)
        else:
            ema_short = calculate_sma(closes, 20)
            ema_long = calculate_sma(closes, 50)
        
        current_short = ema_short.iloc[-1]
        current_long = ema_long.iloc[-1]
        current_price = closes.iloc[-1]
        
        debug_print(f"Hourly: price={current_price:.2f}, short_MA={current_short:.2f}, long_MA={current_long:.2f}")
        
        if current_short > current_long and current_price > current_short:
            debug_print("Multiframe: BULLISH")
            return 'bullish'
        elif current_short < current_long and current_price < current_short:
            debug_print("Multiframe: BEARISH")
            return 'bearish'
        else:
            debug_print("Multiframe: NEUTRAL")
            return 'neutral'
            
    except Exception as e:
        logger.warning(f"⚠️  Could not check multiframe confluence: {e}")
        debug_print(f"Multiframe check failed: {e}")
        return 'neutral'

def check_candle_pattern(bars):
    debug_print("Checking candle patterns...")
    if len(bars) < 2:
        debug_print("Candle pattern: insufficient data")
        return False, False
    
    last = bars.iloc[-1]
    prev = bars.iloc[-2]
    
    bullish_engulfing = (
        last['close'] > last['open'] and
        prev['close'] < prev['open'] and
        last['close'] > prev['open'] and
        last['open'] < prev['close']
    )
    
    bearish_engulfing = (
        last['close'] < last['open'] and
        prev['close'] > prev['open'] and
        last['close'] < prev['open'] and
        last['open'] > prev['close']
    )
    
    debug_print(f"Candle pattern: bullish_engulfing={bullish_engulfing}, bearish_engulfing={bearish_engulfing}")
    return bullish_engulfing, bearish_engulfing

def calculate_pivot_points(symbol):
    debug_print(f"Calculating pivot points for {symbol}...")
    if not USE_PIVOT_POINTS:
        debug_print("Pivot points disabled")
        return None, None, None, None, None
    
    try:
        debug_print("Fetching yesterday's daily bars...")
        yesterday_bars = api.get_bars(symbol, "1Day", limit=2).df
        if len(yesterday_bars) < 2:
            debug_print(f"Insufficient daily data: {len(yesterday_bars)} bars")
            return None, None, None, None, None
        
        h = yesterday_bars['high'].iloc[-2]
        l = yesterday_bars['low'].iloc[-2]
        c = yesterday_bars['close'].iloc[-2]
        
        pivot = (h + l + c) / 3
        r1 = 2 * pivot - l
        r2 = pivot + (h - l)
        s1 = 2 * pivot - h
        s2 = pivot - (h - l)
        
        debug_print(f"Pivots: S2={s2:.2f}, S1={s1:.2f}, P={pivot:.2f}, R1={r1:.2f}, R2={r2:.2f}")
        return pivot, r1, r2, s1, s2
        
    except Exception as e:
        logger.warning(f"⚠️  Could not calculate pivot points: {e}")
        debug_print(f"Pivot calculation failed: {e}")
        return None, None, None, None, None

def calculate_fibonacci_levels(bars, lookback=20):
    debug_print(f"Calculating Fibonacci levels (lookback={lookback})...")
    if not USE_FIBONACCI or len(bars) < lookback:
        debug_print("Fibonacci disabled or insufficient data")
        return None, None, None, None, None
    
    recent_bars = bars.tail(lookback)
    swing_high = recent_bars['high'].max()
    swing_low = recent_bars['low'].min()
    
    diff = swing_high - swing_low
    
    fib_382 = swing_high - (diff * 0.382)
    fib_500 = swing_high - (diff * 0.500)
    fib_618 = swing_high - (diff * 0.618)
    
    debug_print(f"Fibonacci: high={swing_high:.2f}, low={swing_low:.2f}, 38.2%={fib_382:.2f}, 50%={fib_500:.2f}, 61.8%={fib_618:.2f}")
    return fib_382, fib_500, fib_618, swing_high, swing_low

def get_vix_level():
    debug_print("Getting VIX level...")
    if not USE_VIX_FILTER:
        debug_print("VIX filter disabled, returning 0")
        return 0
    
    try:
        debug_print("Fetching VIX data...")
        vix_bars = api.get_bars("VIX", "1Day", limit=5).df
        if len(vix_bars) > 0:
            vix = vix_bars['close'].iloc[-1]
            debug_print(f"VIX from data: {vix:.2f}")
            return vix
        else:
            debug_print(f"No VIX data, estimating from {SYMBOL} volatility...")
            spy_bars = api.get_bars(SYMBOL, "1Day", limit=20).df
            if len(spy_bars) >= 20:
                spy_returns = spy_bars['close'].pct_change()
                volatility = spy_returns.std() * np.sqrt(252) * 100
                debug_print(f"VIX estimated: {volatility:.2f}")
                return volatility
            debug_print("Returning default VIX: 15")
            return 15
    except Exception as e:
        logger.warning(f"⚠️  Could not get VIX level: {e}")
        debug_print(f"VIX fetch failed: {e}, returning 15")
        return 15

def check_200_sma_filter(symbol):
    debug_print(f"Checking 200 SMA filter for {symbol}...")
    if not USE_200_SMA_FILTER:
        debug_print("200 SMA filter disabled")
        return 'neutral'
    
    try:
        debug_print("Fetching 210 days of daily bars...")
        daily_bars = api.get_bars(symbol, "1Day", limit=210).df
        if len(daily_bars) < 200:
            debug_print(f"Insufficient data for 200 SMA: {len(daily_bars)} bars")
            return 'neutral'
        
        closes = daily_bars['close']
        sma_200 = calculate_sma(closes, 200).iloc[-1]
        current_price = closes.iloc[-1]
        
        debug_print(f"200 SMA: price={current_price:.2f}, SMA={sma_200:.2f}, ratio={current_price/sma_200:.4f}")
        
        if current_price > sma_200 * 1.01:
            debug_print("200 SMA: BULLISH")
            return 'bullish'
        elif current_price < sma_200 * 0.99:
            debug_print("200 SMA: BEARISH")
            return 'bearish'
        else:
            debug_print("200 SMA: NEUTRAL")
            return 'neutral'
            
    except Exception as e:
        logger.warning(f"⚠️  Could not check 200 SMA: {e}")
        debug_print(f"200 SMA check failed: {e}")
        return 'neutral'

def check_macd_confirmation(bars):
    debug_print("Checking MACD confirmation...")
    if not REQUIRE_MACD_CONFIRMATION or len(bars) < 35:
        debug_print("MACD confirmation disabled or insufficient data")
        return 'neutral'
    
    closes = bars['close']
    macd_line, signal_line, histogram = calculate_macd(closes)
    
    current_macd = macd_line.iloc[-1]
    current_signal = signal_line.iloc[-1]
    prev_macd = macd_line.iloc[-2]
    prev_signal = signal_line.iloc[-2]
    
    debug_print(f"MACD: current={current_macd:.4f}, signal={current_signal:.4f}, prev_macd={prev_macd:.4f}, prev_signal={prev_signal:.4f}")
    
    if prev_macd <= prev_signal and current_macd > current_signal:
        debug_print("MACD: BULLISH crossover")
        return 'bullish'
    elif prev_macd >= prev_signal and current_macd < current_signal:
        debug_print("MACD: BEARISH crossover")
        return 'bearish'
    elif current_macd > current_signal:
        debug_print("MACD: BULLISH continuation")
        return 'bullish'
    elif current_macd < current_signal:
        debug_print("MACD: BEARISH continuation")
        return 'bearish'
    
    debug_print("MACD: NEUTRAL")
    return 'neutral'

def should_skip_trading_day():
    debug_print("Checking if should skip trading day...")
    if not SKIP_MONDAYS_FRIDAYS:
        debug_print("Skip Monday/Friday disabled")
        return False
    
    today = datetime.now().weekday()
    day_name = datetime.now(EASTERN).strftime("%A")
    if today == 0 or today == 4:
        debug_print(f"Skipping {day_name} (skip_mondays_fridays enabled)")
        return True
    
    debug_print(f"Not skipping {day_name}")
    return False

def seconds_to_human_readable(seconds):
    if seconds < 0:
        return "0 seconds"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    time_parts = []
    if hours > 0:
        time_parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        time_parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if secs > 0 and hours == 0:
        time_parts.append(f"{secs} second{'s' if secs != 1 else ''}")
    
    return " ".join(time_parts) if time_parts else "0 seconds"

def format_market_time(dt_obj):
    if hasattr(dt_obj, 'to_pydatetime'):
        dt_obj = dt_obj.to_pydatetime()
    
    if dt_obj.tzinfo is None:
        dt_obj = EASTERN.localize(dt_obj)
    elif dt_obj.tzinfo != EASTERN:
        dt_obj = dt_obj.astimezone(EASTERN)
    
    eastern_time = dt_obj.strftime("%Y-%m-%d %I:%M:%S %p %Z")
    local_time = dt_obj.astimezone().strftime("%I:%M%p").lstrip('0')
    return f"{eastern_time} ({local_time} local)"

def apply_slippage(price, is_buy=True):
    debug_print(f"Applying slippage to price={price:.2f}, is_buy={is_buy}")
    if not ENABLE_SLIPPAGE:
        debug_print("Slippage disabled")
        return price
    
    slippage_adjustment = price * SLIPPAGE_PCT
    commission_adjustment = price * COMMISSION_PCT
    
    if is_buy:
        adjusted_price = price + slippage_adjustment + commission_adjustment
    else:
        adjusted_price = price - slippage_adjustment - commission_adjustment
    
    debug_print(f"Adjusted price: {adjusted_price:.2f}")
    return adjusted_price

def advanced_backtest_strategy():
    logger.info("📊 Running advanced backtest with all filters...")
    debug_print("=== STARTING BACKTEST ===")
    
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=BACKTEST_DAYS)
        
        debug_print(f"Backtest period: {start_date.date()} to {end_date.date()}")
        debug_print(f"Fetching {BACKTEST_DAYS} days of {BAR_TIMEFRAME} bars for {SYMBOL}...")
        
        bars = api.get_bars(SYMBOL, BAR_TIMEFRAME, start=start_date.strftime('%Y-%m-%d'), 
                           end=end_date.strftime('%Y-%m-%d')).df
        debug_print(f"Received {len(bars)} bars")
        
        if len(bars) < 100:
            logger.warning("⚠️  Insufficient data for backtest")
            debug_print("Insufficient data for backtest, aborting")
            return
        
        debug_print("Calculating indicators for backtest...")
        closes = bars['close']
        highs = bars['high']
        lows = bars['low']
        
        if USE_EMA:
            short_ma = calculate_ema(closes, SHORT_WINDOW)
            long_ma = calculate_ema(closes, LONG_WINDOW)
        else:
            short_ma = calculate_sma(closes, SHORT_WINDOW)
            long_ma = calculate_sma(closes, LONG_WINDOW)
        
        rsi = calculate_rsi(closes, 14)
        adx, plus_di, minus_di = calculate_adx(highs, lows, closes, 14)
        atr = calculate_atr(highs, lows, closes, 14)
        upper_bb, middle_bb, lower_bb = calculate_bollinger_bands(closes, BB_WINDOW, BB_STD)
        macd_line, signal_line, histogram = calculate_macd(closes)
        
        debug_print("Indicators calculated, starting backtest simulation...")
        
        initial_balance = 10000
        balance = initial_balance
        position = 0
        entry_price = 0
        entry_time = None
        stop_loss = 0
        trades = []
        winning_trades = 0
        daily_trades = {}
        
        debug_print(f"Initial balance: ${initial_balance}")
        
        for i in range(max(SHORT_WINDOW, LONG_WINDOW, BB_WINDOW, 35), len(bars)):
            current_price = closes.iloc[i]
            current_time = bars.index[i]
            current_date = current_time.date()
            current_adx = adx.iloc[i]
            current_rsi = rsi.iloc[i]
            current_atr = atr.iloc[i]
            
            if current_date not in daily_trades:
                daily_trades[current_date] = 0
            
            regime = 'trend' if current_adx > ADX_THRESHOLD else 'range'
            macd_signal = 'bullish' if macd_line.iloc[i] > signal_line.iloc[i] else 'bearish'
            
            recent_bars = bars.iloc[max(0, i-1):i+1]
            bullish_eng, bearish_eng = check_candle_pattern(recent_bars)
            
            if regime == 'trend':
                ma_signal = 1 if short_ma.iloc[i] > long_ma.iloc[i] else -1
                rsi_signal = 1 if current_rsi < 65 else (-1 if current_rsi > 35 else 0)
                combined_signal = ma_signal + (rsi_signal * 0.3)
            else:
                if current_price <= lower_bb.iloc[i] and current_rsi < 30:
                    combined_signal = 1.5
                elif current_price >= upper_bb.iloc[i] and current_rsi > 70:
                    combined_signal = -1.5
                else:
                    combined_signal = 0
            
            if position == 0 and abs(combined_signal) >= 1.2:
                if daily_trades[current_date] >= MAX_TRADES_PER_DAY:
                    continue
                
                if REQUIRE_CANDLE_PATTERN:
                    if combined_signal > 0 and not bullish_eng:
                        continue
                    if combined_signal < 0 and not bearish_eng:
                        continue
                
                if REQUIRE_MACD_CONFIRMATION:
                    if combined_signal > 0 and macd_signal != 'bullish':
                        continue
                    if combined_signal < 0 and macd_signal != 'bearish':
                        continue
                
                position = 1 if combined_signal > 0 else -1
                entry_price = apply_slippage(current_price, combined_signal > 0)
                entry_time = current_time
                
                stop_distance = current_atr * ATR_STOP_MULTIPLIER
                if position > 0:
                    stop_loss = entry_price - stop_distance
                else:
                    stop_loss = entry_price + stop_distance
                
                daily_trades[current_date] += 1
                
                trades.append({
                    'entry_price': entry_price,
                    'position': position,
                    'entry_time': entry_time,
                    'stop_loss': stop_loss,
                    'regime': regime
                })
            
            elif position != 0:
                exit_triggered = False
                exit_price = None
                exit_reason = None
                
                if position > 0 and current_price <= stop_loss:
                    exit_triggered = True
                    exit_price = apply_slippage(stop_loss, False)
                    exit_reason = 'stop_loss'
                elif position < 0 and current_price >= stop_loss:
                    exit_triggered = True
                    exit_price = apply_slippage(stop_loss, False)
                    exit_reason = 'stop_loss'
                
                time_in_trade = (current_time - entry_time).total_seconds()
                if time_in_trade > MAX_HOLD_TIME:
                    exit_triggered = True
                    exit_price = apply_slippage(current_price, False)
                    exit_reason = 'time_limit'
                
                pnl_pct = (current_price - entry_price) / entry_price * position
                risk_amount = abs(entry_price - stop_loss) / entry_price
                
                if pnl_pct >= (risk_amount * PROFIT_TARGET_1):
                    exit_triggered = True
                    exit_price = apply_slippage(current_price, False)
                    exit_reason = 'target_1'
                
                exit_signal = -1 if position > 0 else 1
                if (combined_signal * exit_signal) > 0.8:
                    exit_triggered = True
                    exit_price = apply_slippage(current_price, False)
                    exit_reason = 'signal_reversal'
                
                if exit_triggered:
                    pnl = (exit_price - entry_price) * position
                    balance += pnl
                    
                    if pnl > 0:
                        winning_trades += 1
                    
                    position = 0
                    trades[-1]['exit_price'] = exit_price
                    trades[-1]['pnl'] = pnl
                    trades[-1]['exit_reason'] = exit_reason
        
        debug_print("Backtest simulation complete, calculating statistics...")
        
        total_trades = len([t for t in trades if 'exit_price' in t])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        total_return = (balance - initial_balance) / initial_balance
        
        winning_pnl = sum([t['pnl'] for t in trades if 'pnl' in t and t['pnl'] > 0])
        losing_pnl = sum([abs(t['pnl']) for t in trades if 'pnl' in t and t['pnl'] < 0])
        profit_factor = winning_pnl / losing_pnl if losing_pnl > 0 else 0
        
        avg_win = winning_pnl / winning_trades if winning_trades > 0 else 0
        avg_loss = losing_pnl / (total_trades - winning_trades) if (total_trades - winning_trades) > 0 else 0
        
        logger.info(f"📈 Advanced Backtest Results:")
        logger.info(f"   Total trades: {total_trades}")
        logger.info(f"   Win rate: {win_rate:.1%}")
        logger.info(f"   Total return: {total_return:.1%}")
        logger.info(f"   Profit factor: {profit_factor:.2f}")
        logger.info(f"   Avg win: ${avg_win:.2f}")
        logger.info(f"   Avg loss: ${avg_loss:.2f}")
        logger.info(f"   Final balance: ${balance:.2f}")
        
        debug_print(f"Backtest results: trades={total_trades}, winrate={win_rate:.1%}, return={total_return:.1%}, PF={profit_factor:.2f}")
        
        if total_trades < 5:
            logger.warning("⚠️  Very few trades - filters may be too strict")
        if win_rate < 0.45:
            logger.warning("⚠️  Win rate below target")
        if profit_factor < 1.3:
            logger.warning("⚠️  Profit factor < 1.3")
            
    except Exception as e:
        error_msg = str(e).lower()
        if 'subscription' in error_msg or 'permit' in error_msg:
            logger.warning(f"⚠️  Backtest unavailable: Your subscription doesn't permit historical data access")
            debug_print(f"Backtest failed: subscription issue - {e}")
        else:
            logger.warning(f"⚠️  Backtest failed: {e}")
            debug_print(f"Backtest failed: {e}")

def advanced_signal_generator(symbol):
    debug_print(f"=== GENERATING SIGNAL FOR {symbol} ===")
    
    debug_print("Fetching recent bars...")
    bars = get_recent_bars(symbol, 100)
    if bars is None or len(bars) < 50:
        debug_print("Insufficient bars for signal generation")
        return None, 0, 0
    
    debug_print(f"Received {len(bars)} bars")
    
    closes = bars['close']
    highs = bars['high']
    lows = bars['low']
    current_price = closes.iloc[-1]
    
    debug_print(f"Current price: ${current_price:.2f}")
    
    debug_print("Calculating indicators for signal...")
    if USE_EMA:
        short_ma = calculate_ema(closes, SHORT_WINDOW).iloc[-1]
        long_ma = calculate_ema(closes, LONG_WINDOW).iloc[-1]
    else:
        short_ma = calculate_sma(closes, SHORT_WINDOW).iloc[-1]
        long_ma = calculate_sma(closes, LONG_WINDOW).iloc[-1]
    
    debug_print(f"Moving averages: short={short_ma:.2f}, long={long_ma:.2f}")
    
    rsi = calculate_rsi(closes, 14).iloc[-1]
    debug_print(f"RSI: {rsi:.2f}")
    
    adx, plus_di, minus_di = calculate_adx(highs, lows, closes, 14)
    current_adx = adx.iloc[-1]
    debug_print(f"ADX: {current_adx:.2f}")
    
    atr = calculate_atr(highs, lows, closes, 14).iloc[-1]
    debug_print(f"ATR: {atr:.4f}")
    
    upper_bb, middle_bb, lower_bb = calculate_bollinger_bands(closes, BB_WINDOW, BB_STD)
    debug_print(f"Bollinger Bands: upper={upper_bb.iloc[-1]:.2f}, middle={middle_bb.iloc[-1]:.2f}, lower={lower_bb.iloc[-1]:.2f}")
    
    debug_print("Applying filters...")
    vix_level = get_vix_level()
    if USE_VIX_FILTER and vix_level > VIX_THRESHOLD:
        logger.info(f"📉  VIX too high: {vix_level:.1f} > {VIX_THRESHOLD}")
        debug_print(f"FILTER FAILED: VIX too high ({vix_level:.1f} > {VIX_THRESHOLD})")
        return None, 0, 0
    
    sma_200_trend = check_200_sma_filter(symbol)
    if USE_200_SMA_FILTER and sma_200_trend == 'bearish':
        logger.info(f"📉  Below 200 SMA - avoiding longs")
        debug_print("WARNING: Below 200 SMA - will avoid longs")
    
    volume_ok = check_volume_confirmation(bars)
    if not volume_ok:
        logger.info(f"📊  Insufficient volume")
        debug_print("FILTER FAILED: Insufficient volume")
        return None, 0, 0
    
    bullish_eng, bearish_eng = check_candle_pattern(bars)
    macd_signal = check_macd_confirmation(bars)
    hourly_trend = check_multiframe_confluence(symbol)
    pivot, r1, r2, s1, s2 = calculate_pivot_points(symbol)
    fib_382, fib_500, fib_618, swing_high, swing_low = calculate_fibonacci_levels(bars, 20)
    
    regime = detect_market_regime(bars)
    debug_print(f"Market regime: {regime}")
    
    if regime == 'low_vol':
        logger.info("📉  Low volatility regime")
        debug_print("FILTER FAILED: Low volatility regime")
        return None, 0, 0
    
    signal = None
    signal_strength = 0
    stop_loss = 0
    
    debug_print("Evaluating trading signals...")
    
    if regime == 'trend':
        debug_print("Processing TREND regime logic...")
        if current_adx > ADX_THRESHOLD:
            if short_ma > long_ma:
                debug_print(f"Bullish trend detected (short_ma > long_ma)")
                pullback_ok = False
                if USE_FIBONACCI and fib_382 is not None:
                    if abs(current_price - fib_382) / current_price < 0.01:
                        pullback_ok = True
                        debug_print(f"Pullback OK: near fib 38.2% ({fib_382:.2f})")
                elif current_price < short_ma * 1.005:
                    pullback_ok = True
                    debug_print(f"Pullback OK: price near short MA")
                
                if pullback_ok and rsi < 55:
                    debug_print(f"Pullback and RSI conditions met (RSI={rsi:.2f})")
                    if hourly_trend in ['bullish', 'neutral']:
                        debug_print(f"Hourly trend favorable: {hourly_trend}")
                        if REQUIRE_CANDLE_PATTERN and not bullish_eng:
                            logger.info("❌  No bullish engulfing")
                            debug_print("REJECTED: No bullish engulfing pattern")
                            return None, 0, 0
                        
                        if REQUIRE_MACD_CONFIRMATION and macd_signal != 'bullish':
                            logger.info("❌  MACD not bullish")
                            debug_print(f"REJECTED: MACD not bullish ({macd_signal})")
                            return None, 0, 0
                        
                        if USE_200_SMA_FILTER and sma_200_trend == 'bearish':
                            logger.info("❌  Below 200 SMA - no longs")
                            debug_print("REJECTED: Below 200 SMA")
                            return None, 0, 0
                        
                        if USE_PIVOT_POINTS and s1 is not None:
                            if current_price < s1 * 1.02:
                                signal = 'buy'
                                signal_strength = min(1.0, (current_adx / 40) * 0.8 + 0.2)
                                stop_loss = current_price - (atr * ATR_STOP_MULTIPLIER)
                                debug_print(f"SIGNAL: BUY (trend with pivot, strength={signal_strength:.2f}, stop={stop_loss:.2f})")
                        else:
                            signal = 'buy'
                            signal_strength = min(1.0, (current_adx / 40) * 0.7 + 0.3)
                            stop_loss = current_price - (atr * ATR_STOP_MULTIPLIER)
                            debug_print(f"SIGNAL: BUY (trend, strength={signal_strength:.2f}, stop={stop_loss:.2f})")
            
            elif short_ma < long_ma:
                debug_print(f"Bearish trend detected (short_ma < long_ma)")
                pullback_ok = False
                if USE_FIBONACCI and fib_618 is not None:
                    if abs(current_price - fib_618) / current_price < 0.01:
                        pullback_ok = True
                        debug_print(f"Pullback OK: near fib 61.8% ({fib_618:.2f})")
                elif current_price > short_ma * 0.995:
                    pullback_ok = True
                    debug_print(f"Pullback OK: price near short MA")
                
                if pullback_ok and rsi < 55:
                    debug_print(f"Pullback and RSI conditions met (RSI={rsi:.2f})")
                    if hourly_trend in ['bearish', 'neutral']:
                        debug_print(f"Hourly trend favorable: {hourly_trend}")
                        if REQUIRE_CANDLE_PATTERN and not bearish_eng:
                            logger.info("❌  No bearish engulfing")
                            debug_print("REJECTED: No bearish engulfing pattern")
                            return None, 0, 0
                        
                        if REQUIRE_MACD_CONFIRMATION and macd_signal != 'bearish':
                            logger.info("❌  MACD not bearish")
                            debug_print(f"REJECTED: MACD not bearish ({macd_signal})")
                            return None, 0, 0
                        
                        if USE_PIVOT_POINTS and r1 is not None:
                            if current_price > r1 * 0.98:
                                signal = 'sell'
                                signal_strength = min(1.0, (current_adx / 40) * 0.8 + 0.2)
                                stop_loss = current_price + (atr * ATR_STOP_MULTIPLIER)
                                debug_print(f"SIGNAL: SELL (trend with pivot, strength={signal_strength:.2f}, stop={stop_loss:.2f})")
                        else:
                            signal = 'sell'
                            signal_strength = min(1.0, (current_adx / 40) * 0.7 + 0.3)
                            stop_loss = current_price + (atr * ATR_STOP_MULTIPLIER)
                            debug_print(f"SIGNAL: SELL (trend, strength={signal_strength:.2f}, stop={stop_loss:.2f})")
    
    elif regime == 'range':
        debug_print("Processing RANGE regime logic...")
        if current_price <= lower_bb.iloc[-1] and rsi < 30:
            debug_print(f"Oversold condition: price at/below lower BB and RSI < 30")
            if hourly_trend != 'bearish':
                debug_print(f"Hourly trend not bearish: {hourly_trend}")
                if REQUIRE_CANDLE_PATTERN and not bullish_eng:
                    logger.info("❌  No bullish engulfing in range")
                    debug_print("REJECTED: No bullish engulfing in range")
                    return None, 0, 0
                
                if USE_200_SMA_FILTER and sma_200_trend == 'bearish':
                    logger.info("❌  Below 200 SMA - no mean reversion longs")
                    debug_print("REJECTED: Below 200 SMA for mean reversion")
                    return None, 0, 0
                
                signal = 'buy'
                signal_strength = 0.85
                stop_loss = current_price - (atr * ATR_STOP_MULTIPLIER)
                debug_print(f"SIGNAL: BUY (range oversold, strength={signal_strength:.2f}, stop={stop_loss:.2f})")
        
        elif current_price >= upper_bb.iloc[-1] and rsi > 70:
            debug_print(f"Overbought condition: price at/above upper BB and RSI > 70")
            if hourly_trend != 'bullish':
                debug_print(f"Hourly trend not bullish: {hourly_trend}")
                if REQUIRE_CANDLE_PATTERN and not bearish_eng:
                    logger.info("❌  No bearish engulfing in range")
                    debug_print("REJECTED: No bearish engulfing in range")
                    return None, 0, 0
                
                signal = 'sell'
                signal_strength = 0.85
                stop_loss = current_price + (atr * ATR_STOP_MULTIPLIER)
                debug_print(f"SIGNAL: SELL (range overbought, strength={signal_strength:.2f}, stop={stop_loss:.2f})")
    
    elif regime == 'high_vol':
        debug_print("Processing HIGH_VOL regime logic...")
        if short_ma > long_ma and rsi < 35:
            debug_print(f"High vol bullish setup: short_ma > long_ma and RSI < 35")
            if hourly_trend == 'bullish':
                debug_print(f"Hourly trend bullish")
                if REQUIRE_CANDLE_PATTERN and not bullish_eng:
                    debug_print("REJECTED: No bullish engulfing in high vol")
                    return None, 0, 0
                
                if REQUIRE_MACD_CONFIRMATION and macd_signal != 'bullish':
                    debug_print(f"REJECTED: MACD not bullish in high vol ({macd_signal})")
                    return None, 0, 0
                
                signal = 'buy'
                signal_strength = 0.6
                stop_loss = current_price - (atr * ATR_STOP_MULTIPLIER * 1.5)
                debug_print(f"SIGNAL: BUY (high vol, strength={signal_strength:.2f}, stop={stop_loss:.2f})")
        
        elif short_ma < long_ma and rsi > 65:
            debug_print(f"High vol bearish setup: short_ma < long_ma and RSI > 65")
            if hourly_trend == 'bearish':
                debug_print(f"Hourly trend bearish")
                if REQUIRE_CANDLE_PATTERN and not bearish_eng:
                    debug_print("REJECTED: No bearish engulfing in high vol")
                    return None, 0, 0
                
                if REQUIRE_MACD_CONFIRMATION and macd_signal != 'bearish':
                    debug_print(f"REJECTED: MACD not bearish in high vol ({macd_signal})")
                    return None, 0, 0
                
                signal = 'sell'
                signal_strength = 0.6
                stop_loss = current_price + (atr * ATR_STOP_MULTIPLIER * 1.5)
                debug_print(f"SIGNAL: SELL (high vol, strength={signal_strength:.2f}, stop={stop_loss:.2f})")
    
    if signal_strength < MIN_SIGNAL_STRENGTH:
        logger.info(f"❌  Signal strength {signal_strength:.2f} < {MIN_SIGNAL_STRENGTH:.2f}")
        debug_print(f"REJECTED: Signal strength {signal_strength:.2f} < threshold {MIN_SIGNAL_STRENGTH:.2f}")
        return None, signal_strength, 0
    
    if signal and stop_loss != 0:
        debug_print("Performing risk/reward check...")
        potential_reward = abs(current_price - stop_loss) * MIN_RISK_REWARD
        if USE_PIVOT_POINTS:
            if signal == 'buy' and r1 is not None:
                actual_reward = r1 - current_price
                debug_print(f"R:R check (buy): actual_reward={actual_reward:.2f}, potential_reward={potential_reward:.2f}")
                if actual_reward < potential_reward:
                    logger.info(f"❌  R:R too low: {actual_reward:.2f} < {potential_reward:.2f}")
                    debug_print(f"REJECTED: R:R too low")
                    return None, signal_strength, 0
            elif signal == 'sell' and s1 is not None:
                actual_reward = current_price - s1
                debug_print(f"R:R check (sell): actual_reward={actual_reward:.2f}, potential_reward={potential_reward:.2f}")
                if actual_reward < potential_reward:
                    logger.info(f"❌  R:R too low: {actual_reward:.2f} < {potential_reward:.2f}")
                    debug_print(f"REJECTED: R:R too low")
                    return None, signal_strength, 0
    
    if signal:
        debug_print(f"=== FINAL SIGNAL: {signal.upper()}, strength={signal_strength:.2f}, stop=${stop_loss:.2f} ===")
    else:
        debug_print("=== NO SIGNAL GENERATED ===")
    
    return signal, signal_strength, stop_loss

def wait_until_market_open():
    debug_print("Checking if market is open...")
    try:
        clock = api.get_clock()
    except Exception as e:
        logger.warning(f"⚠️  Failed to get clock: {e}")
        debug_print(f"Failed to get clock: {e}")
        time.sleep(60)
        return
    
    now = clock.timestamp
    if now.tzinfo is None:
        now = EASTERN.localize(now)
    else:
        now = now.astimezone(EASTERN)
    
    next_open = clock.next_open
    if next_open.tzinfo is None:
        next_open = EASTERN.localize(next_open)
    else:
        next_open = next_open.astimezone(EASTERN)
    
    if not clock.is_open:
        seconds_until_open = (next_open - now).total_seconds()
        readable_time = seconds_to_human_readable(seconds_until_open)
        debug_print(f"Market closed, {readable_time} until open")
        if seconds_until_open > 0:
            readable_time = seconds_to_human_readable(seconds_until_open)
            logger.info(f"🕒  Market opens at {format_market_time(next_open)}")
            logger.info(f"⏱️  Waiting {readable_time}...")
            
            while seconds_until_open > 0:
                sleep_time = min(60, seconds_until_open)
                time.sleep(sleep_time)
                seconds_until_open -= sleep_time
                
                if sleep_time >= 60 and (seconds_until_open % 3600 < 60 or seconds_until_open < 3600):
                    remaining_readable = seconds_to_human_readable(seconds_until_open)
                    logger.info(f"⏱️  {remaining_readable} remaining...")
                    debug_print(f"Waiting... {remaining_readable} remaining")
        else:
            logger.info("✅  Market is open!")
            debug_print("Market is open")
    else:
        logger.info("✅  Market is open!")
        debug_print("Market is open")

def fetch_equity():
    debug_print("Fetching account equity...")
    try:
        account = api.get_account()
        equity = float(account.equity)
        debug_print(f"Account equity: ${equity:.2f}")
        return equity
    except Exception as e:
        logger.error(f"❌  Failed to fetch equity: {e}")
        debug_print(f"Failed to fetch equity: {e}")
        return 0.0

def fetch_buying_power():
    debug_print("Fetching buying power...")
    try:
        account = api.get_account()
        bp = float(account.buying_power)
        debug_print(f"Buying power: ${bp:.2f}")
        return bp
    except Exception as e:
        logger.error(f"❌  Failed to fetch buying power: {e}")
        debug_print(f"Failed to fetch buying power: {e}")
        return 0.0

def get_day_trade_count():
    debug_print("Getting day trade count...")
    try:
        account = api.get_account()
        count = int(account.daytrade_count)
        debug_print(f"Day trade count: {count}")
        return count
    except Exception as e:
        logger.error(f"❌  Failed to fetch day trade count: {e}")
        debug_print(f"Failed to fetch day trade count: {e}")
        return 0

def submit_limit_buy(symbol, notional, limit_price):
    debug_print(f"=== SUBMITTING LIMIT BUY ORDER ===")
    debug_print(f"Symbol: {symbol}, Notional: ${notional:.2f}, Limit: ${limit_price:.2f}")
    
    if notional < MIN_NOTIONAL:
        logger.warning(f"⚠️  Notional ${notional:.2f} < minimum ${MIN_NOTIONAL}")
        debug_print(f"Order rejected: notional too small")
        return False
    
    try:
        shares = int(notional / limit_price)
        debug_print(f"Calculated shares: {shares}")
        
        if shares == 0:
            logger.warning(f"⚠️  Cannot buy fractional shares with ${notional:.2f}")
            debug_print(f"Order rejected: shares = 0")
            return False
        
        debug_print(f"Submitting limit buy order to API...")
        order = api.submit_order(
            symbol=symbol,
            qty=shares,
            side="buy",
            type="limit",
            limit_price=round(limit_price, 2),
            time_in_force="gtc"
        )
        
        debug_print(f"Order submitted, ID: {order.id}")
        logger.info(f"🟢  LIMIT BUY: {shares} shares @ ${limit_price:.2f}")
        
        start_time = time.time()
        debug_print(f"Waiting for fill (timeout: {LIMIT_ORDER_TIMEOUT}s)...")
        while (time.time() - start_time) < LIMIT_ORDER_TIMEOUT:
            order_status = api.get_order(order.id)
            debug_print(f"Order status: {order_status.status}")
            if order_status.status == 'filled':
                filled_price = float(order_status.filled_avg_price)
                logger.info(f"✅  FILLED @ ${filled_price:.2f}")
                debug_print(f"Order filled at ${filled_price:.2f}")
                return filled_price
            elif order_status.status in ['cancelled', 'expired', 'rejected']:
                logger.warning(f"⚠️  Limit order {order_status.status}")
                debug_print(f"Order {order_status.status}")
                return False
            time.sleep(2)
        
        logger.warning("⏱️  Timeout - switching to market")
        debug_print("Timeout reached, canceling order and switching to market")
        api.cancel_order(order.id)
        return submit_market_buy(symbol, notional)
        
    except Exception as e:
        logger.error(f"❌  Failed limit buy: {e}")
        debug_print(f"Limit buy failed: {e}")
        return False

def submit_market_buy(symbol, notional):
    debug_print(f"=== SUBMITTING MARKET BUY ORDER ===")
    debug_print(f"Symbol: {symbol}, Notional: ${notional:.2f}")
    
    try:
        current_price = get_current_price(symbol)
        if current_price == 0:
            debug_print("Market buy failed: could not get current price")
            return False
        
        execution_price = apply_slippage(current_price, True)
        shares = int(notional / execution_price)
        debug_print(f"Shares: {shares}, Expected execution: ${execution_price:.2f}")
        
        if shares == 0:
            debug_print("Market buy failed: shares = 0")
            return False
        
        debug_print("Submitting market buy order to API...")
        api.submit_order(
            symbol=symbol,
            qty=shares,
            side="buy",
            type="market",
            time_in_force="day"
        )
        logger.info(f"🟢  MARKET BUY: {shares} shares @ ~${execution_price:.2f}")
        debug_print(f"Market buy order submitted")
        return execution_price
    except Exception as e:
        logger.error(f"❌  Failed buy: {e}")
        debug_print(f"Market buy failed: {e}")
        return False

def submit_short_sell(symbol, notional):
    """Open a short position by selling shares we don't own"""
    debug_print(f"=== SUBMITTING SHORT SELL (OPENING SHORT POSITION) ===")
    debug_print(f"Symbol: {symbol}, Notional: ${notional:.2f}")
    
    try:
        current_price = get_current_price(symbol)
        if current_price == 0:
            debug_print("Short sell failed: could not get current price")
            return False
        
        execution_price = apply_slippage(current_price, False)
        shares = int(notional / execution_price)
        debug_print(f"Shares to short: {shares}, Expected execution: ${execution_price:.2f}")
        
        if shares == 0:
            debug_print("Short sell failed: shares = 0")
            return False
        
        debug_print("Submitting short sell order to API...")
        api.submit_order(
            symbol=symbol,
            qty=shares,
            side="sell",
            type="market",
            time_in_force="day"
        )
        logger.info(f"🔴 SHORT SELL: {shares} shares @ ~${execution_price:.2f}")
        debug_print(f"Short sell order submitted (opened short position)")
        return execution_price
    except Exception as e:
        logger.error(f"❌  Failed short sell: {e}")
        debug_print(f"Short sell failed: {e}")
        return False

def submit_limit_short_sell(symbol, notional, limit_price):
    """Open a short position using limit order"""
    debug_print(f"=== SUBMITTING LIMIT SHORT SELL (OPENING SHORT POSITION) ===")
    debug_print(f"Symbol: {symbol}, Notional: ${notional:.2f}, Limit: ${limit_price:.2f}")
    
    if notional < MIN_NOTIONAL:
        logger.warning(f"⚠️  Notional ${notional:.2f} < minimum ${MIN_NOTIONAL}")
        debug_print(f"Order rejected: notional too small")
        return False
    
    try:
        shares = int(notional / limit_price)
        debug_print(f"Calculated shares to short: {shares}")
        
        if shares == 0:
            logger.warning(f"⚠️  Cannot short fractional shares with ${notional:.2f}")
            debug_print(f"Order rejected: shares = 0")
            return False
        
        debug_print(f"Submitting limit short sell order to API...")
        order = api.submit_order(
            symbol=symbol,
            qty=shares,
            side="sell",
            type="limit",
            limit_price=round(limit_price, 2),
            time_in_force="gtc"
        )
        
        debug_print(f"Order submitted, ID: {order.id}")
        logger.info(f"🔴 LIMIT SHORT SELL: {shares} shares @ ${limit_price:.2f}")
        
        start_time = time.time()
        debug_print(f"Waiting for fill (timeout: {LIMIT_ORDER_TIMEOUT}s)...")
        while (time.time() - start_time) < LIMIT_ORDER_TIMEOUT:
            order_status = api.get_order(order.id)
            debug_print(f"Order status: {order_status.status}")
            if order_status.status == 'filled':
                filled_price = float(order_status.filled_avg_price)
                logger.info(f"✅  FILLED @ ${filled_price:.2f}")
                debug_print(f"Order filled at ${filled_price:.2f}")
                return filled_price
            elif order_status.status in ['cancelled', 'expired', 'rejected']:
                logger.warning(f"⚠️  Limit order {order_status.status}")
                debug_print(f"Order {order_status.status}")
                return False
            time.sleep(2)
        
        logger.warning("⏱️  Timeout - switching to market")
        debug_print("Timeout reached, canceling order and switching to market")
        api.cancel_order(order.id)
        return submit_short_sell(symbol, notional)
        
    except Exception as e:
        logger.error(f"❌  Failed limit short sell: {e}")
        debug_print(f"Limit short sell failed: {e}")
        return False

def submit_buy_to_cover(symbol, qty):
    """Close a short position by buying back shares"""
    debug_print(f"=== SUBMITTING BUY TO COVER (CLOSING SHORT POSITION) ===")
    debug_print(f"Symbol: {symbol}, Qty: {qty}")
    
    try:
        current_price = get_current_price(symbol)
        if current_price == 0:
            debug_print("Buy to cover failed: could not get current price")
            return False
        
        execution_price = apply_slippage(current_price, True)
        debug_print(f"Expected execution: ${execution_price:.2f}")
        
        debug_print("Submitting buy to cover order to API...")
        api.submit_order(
            symbol=symbol,
            qty=qty,
            side="buy",
            type="market",
            time_in_force="day"
        )
        logger.info(f"🟢 BUY TO COVER: {qty} shares @ ~${execution_price:.2f}")
        debug_print(f"Buy to cover order submitted (closed short position)")
        return execution_price
    except Exception as e:
        logger.error(f"❌  Failed buy to cover: {e}")
        debug_print(f"Buy to cover failed: {e}")
        return False

def submit_limit_sell(symbol, qty, limit_price):
    debug_print(f"=== SUBMITTING LIMIT SELL ORDER ===")
    debug_print(f"Symbol: {symbol}, Qty: {qty}, Limit: ${limit_price:.2f}")
    
    try:
        debug_print("Submitting limit sell order to API...")
        order = api.submit_order(
            symbol=symbol,
            qty=qty,
            side="sell",
            type="limit",
            limit_price=round(limit_price, 2),
            time_in_force="gtc"
        )
        
        debug_print(f"Order submitted, ID: {order.id}")
        logger.info(f"🔴  LIMIT SELL: {qty} shares @ ${limit_price:.2f}")
        
        start_time = time.time()
        debug_print(f"Waiting for fill (timeout: {LIMIT_ORDER_TIMEOUT}s)...")
        while (time.time() - start_time) < LIMIT_ORDER_TIMEOUT:
            order_status = api.get_order(order.id)
            debug_print(f"Order status: {order_status.status}")
            if order_status.status == 'filled':
                filled_price = float(order_status.filled_avg_price)
                logger.info(f"✅  FILLED @ ${filled_price:.2f}")
                debug_print(f"Order filled at ${filled_price:.2f}")
                return filled_price
            elif order_status.status in ['cancelled', 'expired', 'rejected']:
                logger.warning(f"⚠️  Limit order {order_status.status}")
                debug_print(f"Order {order_status.status}")
                return False
            time.sleep(2)
        
        logger.warning("⏱️  Timeout - switching to market")
        debug_print("Timeout reached, canceling order and switching to market")
        api.cancel_order(order.id)
        return submit_market_sell(symbol, qty)
        
    except Exception as e:
        logger.error(f"❌  Failed limit sell: {e}")
        debug_print(f"Limit sell failed: {e}")
        return False

def submit_market_sell(symbol, qty):
    debug_print(f"=== SUBMITTING MARKET SELL ORDER ===")
    debug_print(f"Symbol: {symbol}, Qty: {qty}")
    
    try:
        current_price = get_current_price(symbol)
        if current_price == 0:
            debug_print("Market sell failed: could not get current price")
            return False
        
        execution_price = apply_slippage(current_price, False)
        debug_print(f"Expected execution: ${execution_price:.2f}")
        
        debug_print("Submitting market sell order to API...")
        api.submit_order(
            symbol=symbol,
            qty=qty,
            side="sell",
            type="market",
            time_in_force="day"
        )
        logger.info(f"🔴  MARKET SELL: {qty} shares @ ~${execution_price:.2f}")
        debug_print(f"Market sell order submitted")
        return execution_price
    except Exception as e:
        logger.error(f"❌  Failed sell: {e}")
        debug_print(f"Market sell failed: {e}")
        return False

def close_all_positions():
    debug_print("Closing all positions...")
    try:
        positions = api.list_positions()
        if not positions:
            logger.info("✅  No open positions")
            debug_print("No open positions to close")
            return
        
        debug_print(f"Found {len(positions)} positions to close")
        logger.warning("⚠️  Closing all positions...")
        for pos in positions:
            qty = int(float(pos.qty))
            debug_print(f"Closing position: {pos.symbol}, qty={qty}")
            if qty > 0:
                submit_market_sell(pos.symbol, qty)
            elif qty < 0:
                submit_buy_to_cover(pos.symbol, abs(qty))
        logger.info("✅  All positions closed")
        debug_print("All positions closed successfully")
    except Exception as e:
        logger.error(f"❌  Failed to close positions: {e}")
        debug_print(f"Failed to close positions: {e}")

def get_recent_bars(symbol, limit=100):
    debug_print(f"Fetching {limit} recent {BAR_TIMEFRAME} bars for {symbol}...")
    try:
        bars = api.get_bars(symbol, BAR_TIMEFRAME, limit=limit).df
        debug_print(f"Received {len(bars)} bars")
        return bars
    except Exception as e:
        logger.error(f"❌  Failed to fetch bars: {e}")
        debug_print(f"Failed to fetch bars: {e}")
        return None

def current_position_qty(symbol):
    debug_print(f"Checking position quantity for {symbol}...")
    try:
        positions = api.list_positions()
        for pos in positions:
            if pos.symbol == symbol:
                qty = int(float(pos.qty))
                debug_print(f"Position qty: {qty} ({'SHORT' if qty < 0 else 'LONG'})")
                return qty
        debug_print("No position found")
        return 0
    except Exception as e:
        logger.error(f"❌  Failed to fetch positions: {e}")
        debug_print(f"Failed to fetch positions: {e}")
        return 0

def pdt_allows_new_trade():
    debug_print("Checking PDT rules...")
    if not PDT_RULE:
        debug_print("PDT rule disabled, allowing trade")
        return True
    
    equity = fetch_equity()
    day_trade_count = get_day_trade_count()
    
    debug_print(f"PDT check: equity=${equity:.2f}, day_trades={day_trade_count}")
    
    if equity < 25000:
        if day_trade_count >= 3:
            logger.error(f"🛑  PDT rule: {day_trade_count} trades in 5-day window")
            debug_print(f"PDT violation: {day_trade_count} >= 3 with equity < $25k")
            return False
    
    debug_print("PDT check passed")
    return True

def get_market_status():
    debug_print("Getting market status...")
    try:
        clock = api.get_clock()
        status = "open" if clock.is_open else "closed"
        next_event = clock.next_open if not clock.is_open else clock.next_close
        event_type = "open" if not clock.is_open else "close"
        
        debug_print(f"Market status: {status}, next {event_type} at {next_event}")
        
        return {
            "status": status,
            "next_event": next_event,
            "event_type": event_type,
            "timestamp": clock.timestamp
        }
    except Exception as e:
        logger.warning(f"⚠️  Failed to get market status: {e}")
        debug_print(f"Failed to get market status: {e}")
        return {
            "status": "unknown",
            "next_event": None,
            "event_type": "unknown",
            "timestamp": datetime.now()
        }

def calculate_position_size(equity, stop_loss, entry_price, regime='normal'):
    debug_print(f"Calculating position size: equity=${equity:.2f}, entry=${entry_price:.2f}, stop=${stop_loss:.2f}, regime={regime}")
    
    risk_amount = equity * RISK_PER_TRADE
    
    if regime == 'high_vol':
        risk_amount *= 0.5
        logger.info(f"📊  High vol - reducing position 50%")
        debug_print("High vol: reducing risk by 50%")
    
    stop_distance = abs(entry_price - stop_loss)
    if stop_distance == 0:
        debug_print("Stop distance is 0, returning MIN_NOTIONAL")
        return MIN_NOTIONAL
    
    position_size = risk_amount / stop_distance * entry_price
    position_size = max(MIN_NOTIONAL, position_size)
    
    logger.info(f"💰  Position: Risk=${risk_amount:.2f}, Stop=${stop_distance:.2f}, Size=${position_size:.2f}")
    debug_print(f"Position size: ${position_size:.2f}")
    
    return position_size

def should_trade_based_on_market_hours():
    debug_print("Checking if in tradeable market hours...")
    if not MARKET_HOURS_FILTER:
        debug_print("Market hours filter disabled")
        return True
    
    now_eastern = datetime.now(EASTERN).time()
    
    open_buffer_end = datetime.strptime("10:00", "%H:%M").time()
    close_buffer_start = datetime.strptime("15:30", "%H:%M").time()
    
    debug_print(f"Current time (ET): {now_eastern}")
    
    if now_eastern < open_buffer_end:
        debug_print("Before 10:00 AM ET, outside trading hours")
        return False
    
    if now_eastern >= close_buffer_start:
        debug_print("After 3:30 PM ET, outside trading hours")
        return False
    
    debug_print("Within trading hours")
    return True

def atr_based_trailing_stop(symbol, entry_price, current_price, stop_loss, position_type='long'):
    debug_print(f"Checking trailing stop: entry=${entry_price:.2f}, current=${current_price:.2f}, stop=${stop_loss:.2f}, type={position_type}")
    
    if not USE_TRAILING_STOP:
        debug_print("Trailing stop disabled, checking fixed stop")
        if position_type == 'long' and current_price <= stop_loss:
            debug_print("Fixed stop hit (long)")
            return True
        elif position_type == 'short' and current_price >= stop_loss:
            debug_print("Fixed stop hit (short)")
            return True
        return False
    
    position_qty = current_position_qty(symbol)
    if position_qty == 0:
        debug_print("No position, skipping stop check")
        return False
    
    bars = get_recent_bars(symbol, 20)
    if bars is not None and len(bars) > 14:
        atr = calculate_atr(bars['high'], bars['low'], bars['close'], 14).iloc[-1]
        trail_distance = atr * ATR_STOP_MULTIPLIER
        debug_print(f"ATR trail distance: {trail_distance:.4f}")
    else:
        trail_distance = abs(entry_price - stop_loss)
        debug_print(f"Using fixed trail distance: {trail_distance:.4f}")
    
    if not hasattr(atr_based_trailing_stop, 'trailing_stop'):
        atr_based_trailing_stop.trailing_stop = stop_loss
        debug_print(f"Initialized trailing stop: ${stop_loss:.2f}")
    
    if position_type == 'long':
        new_stop = current_price - trail_distance
        if new_stop > atr_based_trailing_stop.trailing_stop:
            atr_based_trailing_stop.trailing_stop = new_stop
            logger.info(f"📈  Trailing stop → ${new_stop:.2f}")
            debug_print(f"Trailing stop updated (long): ${new_stop:.2f}")
        
        if current_price <= atr_based_trailing_stop.trailing_stop:
            logger.info(f"🛑  Trailing stop hit @ ${current_price:.2f}")
            debug_print(f"Trailing stop hit (long): price=${current_price:.2f} <= stop=${atr_based_trailing_stop.trailing_stop:.2f}")
            return True
    
    elif position_type == 'short':
        new_stop = current_price + trail_distance
        if new_stop < atr_based_trailing_stop.trailing_stop:
            atr_based_trailing_stop.trailing_stop = new_stop
            logger.info(f"📉  Trailing stop → ${new_stop:.2f}")
            debug_print(f"Trailing stop updated (short): ${new_stop:.2f}")
        
        if current_price >= atr_based_trailing_stop.trailing_stop:
            logger.info(f"🛑  Trailing stop hit @ ${current_price:.2f}")
            debug_print(f"Trailing stop hit (short): price=${current_price:.2f} >= stop=${atr_based_trailing_stop.trailing_stop:.2f}")
            return True
    
    debug_print("Trailing stop not hit")
    return False

def scale_out_profit_taking(symbol, entry_price, current_price, stop_loss, position_type='long'):
    debug_print(f"Checking profit targets: entry=${entry_price:.2f}, current=${current_price:.2f}, stop=${stop_loss:.2f}")
    
    position_qty = current_position_qty(symbol)
    if position_qty == 0:
        debug_print("No position, skipping profit targets")
        return False
    
    risk_distance = abs(entry_price - stop_loss)
    
    if position_type == 'long':
        profit_pct = (current_price - entry_price) / entry_price
        profit_in_r = (current_price - entry_price) / risk_distance if risk_distance > 0 else 0
    else:
        profit_pct = (entry_price - current_price) / entry_price
        profit_in_r = (entry_price - current_price) / risk_distance if risk_distance > 0 else 0
    
    debug_print(f"Profit: {profit_pct:.2%}, {profit_in_r:.2f}R")
    
    if profit_in_r >= PROFIT_TARGET_1:
        if not hasattr(scale_out_profit_taking, 'target_1_hit'):
            scale_out_profit_taking.target_1_hit = True
            partial_qty = position_qty // 2
            
            debug_print(f"Target 1 ({PROFIT_TARGET_1}R) hit, scaling out {partial_qty} shares")
            
            if partial_qty != 0:
                if position_type == 'long':
                    if USE_LIMIT_ORDERS:
                        limit_price = current_price
                        submit_limit_sell(symbol, partial_qty, limit_price)
                    else:
                        submit_market_sell(symbol, partial_qty)
                else:
                    submit_buy_to_cover(symbol, partial_qty)
                
                logger.info(f"🎯  Target 1 ({PROFIT_TARGET_1}R) - 50% out @ ${current_price:.2f}")
                
                atr_based_trailing_stop.trailing_stop = entry_price
                logger.info(f"🔒  Stop → breakeven: ${entry_price:.2f}")
                debug_print(f"Stop moved to breakeven: ${entry_price:.2f}")
                return True
    
    if profit_in_r >= PROFIT_TARGET_2:
        remaining_qty = current_position_qty(symbol)
        debug_print(f"Target 2 ({PROFIT_TARGET_2}R) hit, exiting {abs(remaining_qty)} shares")
        if remaining_qty != 0:
            if position_type == 'long':
                if USE_LIMIT_ORDERS:
                    limit_price = current_price
                    submit_limit_sell(symbol, remaining_qty, limit_price)
                else:
                    submit_market_sell(symbol, remaining_qty)
            else:
                submit_buy_to_cover(symbol, abs(remaining_qty))
            
            logger.info(f"🎯🎯  Target 2 ({PROFIT_TARGET_2}R) - Full exit @ ${current_price:.2f}")
            return True
    
    debug_print("No profit targets hit")
    return False

def get_current_price(symbol):
    debug_print(f"Getting current price for {symbol}...")
    try:
        bars = api.get_bars(symbol, "1Min", limit=5).df
        if len(bars) > 0:
            price = bars['close'].iloc[-1]
            debug_print(f"Current price: ${price:.2f}")
            return price
        else:
            debug_print("No bars returned")
            return 0
    except Exception as e:
        logger.error(f"❌  Failed to get price: {e}")
        debug_print(f"Failed to get price: {e}")
        return 0

def get_bid_ask(symbol):
    debug_print(f"Getting bid/ask for {symbol}...")
    try:
        quote = api.get_latest_quote(symbol)
        bid = float(quote.bid_price)
        ask = float(quote.ask_price)
        debug_print(f"Bid: ${bid:.2f}, Ask: ${ask:.2f}")
        return bid, ask
    except Exception as e:
        logger.warning(f"⚠️  Could not get bid/ask: {e}")
        debug_print(f"Failed to get bid/ask: {e}, using current price")
        current_price = get_current_price(symbol)
        return current_price, current_price

def main():
    logger.info("🚀  Starting daytrader.py - continuous operation")
    if DEBUG_MODE:
        print("\n" + "="*70)
        print("DEBUG MODE ENABLED - Verbose output active")
        print("="*70 + "\n")
    
    logger.info("🔍  Validating API connectivity...")
    debug_print("Starting API validation...")
    try:
        account = api.get_account()
        logger.info(f"✅  API connected successfully")
        logger.info(f"✅  Account ID: {account.id}")
        logger.info(f"✅  Equity: ${float(account.equity):.2f}")
        logger.info(f"✅  Buying Power: ${float(account.buying_power):.2f}")
        logger.info(f"✅  Day Trade Count: {int(account.daytrade_count)}")
        logger.info(f"✅  Pattern Day Trader: {account.pattern_day_trader}")
        
        debug_print(f"API validation successful")
        
        debug_print(f"Testing market data access for {SYMBOL}...")
        test_bars = api.get_bars(SYMBOL, "1Day", limit=1).df
        if len(test_bars) > 0:
            logger.info(f"✅  Market data access verified for {SYMBOL}")
            debug_print("Market data access verified")
        else:
            logger.warning(f"⚠️  No market data returned for {SYMBOL}")
            debug_print("WARNING: No market data returned")
        
        debug_print("Testing clock access...")
        clock = api.get_clock()
        logger.info(f"✅  Clock access verified - Market is {'OPEN' if clock.is_open else 'CLOSED'}")
        debug_print(f"Clock access verified, market is {'OPEN' if clock.is_open else 'CLOSED'}")
        
    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"❌  API validation failed")
        debug_print(f"API validation failed: {e}")
        
        if 'unauthorized' in error_msg or 'forbidden' in error_msg:
            logger.error(f"🔑  Invalid API credentials detected")
            logger.error(f"Please update your .env file with valid API keys")
            debug_print("Invalid API credentials detected")
        else:
            logger.error(f"Error: {e}")
            logger.error(f"Please check your .env file and network connection")
        
        return
    
    try:
        advanced_backtest_strategy()
    except Exception as e:
        logger.warning(f"⚠️  Backtest skipped: {e}")
        logger.info(f"ℹ️  Continuing without backtest - this is optional")
        debug_print(f"Backtest skipped: {e}")
    
    last_reset_date = None
    trades_today = 0
    
    try:
        while True:
            debug_print("=== NEW MAIN LOOP ITERATION ===")
            try:
                current_date = datetime.now(EASTERN).date()
                if last_reset_date != current_date:
                    trades_today = 0
                    last_reset_date = current_date
                    logger.info(f"📅  New day: {current_date}")
                    debug_print(f"New day: {current_date}, resetting counters")
                    
                    if hasattr(scale_out_profit_taking, 'target_1_hit'):
                        delattr(scale_out_profit_taking, 'target_1_hit')
                        debug_print("Reset target_1_hit attribute")
                    if hasattr(atr_based_trailing_stop, 'trailing_stop'):
                        delattr(atr_based_trailing_stop, 'trailing_stop')
                        debug_print("Reset trailing_stop attribute")
                
                if should_skip_trading_day():
                    day_name = datetime.now(EASTERN).strftime("%A")
                    logger.info(f"📅  Skipping {day_name} - monitoring mode")
                    debug_print(f"Skipping trading today ({day_name})")
                    time.sleep(3600)
                    continue
                
                market_info = get_market_status()
                
                if market_info['status'] == 'closed':
                    logger.info(f"🏛️  Market closed")
                    logger.info(f"📅  Next open: {format_market_time(market_info['next_event'])}")
                    debug_print("Market closed, waiting for open...")
                    wait_until_market_open()
                    continue
                
                logger.info(f"🏛️  Market OPEN - starting session")
                debug_print("=== MARKET OPEN - STARTING SESSION ===")
                
                opening_equity = fetch_equity()
                if opening_equity == 0:
                    logger.error("💥  No equity. Waiting 5 min...")
                    debug_print("No equity detected, waiting 5 minutes...")
                    time.sleep(300)
                    continue
                
                logger.info(f"💰  Opening equity: ${opening_equity:.2f}")
                debug_print(f"Opening equity: ${opening_equity:.2f}")
                
                vix_level = get_vix_level()
                logger.info(f"📊  VIX: {vix_level:.1f}")
                
                sma_200_trend = check_200_sma_filter(SYMBOL)
                logger.info(f"📈  200 SMA: {sma_200_trend.upper()}")
                
                short_status = "ON" if ENABLE_SHORT_SELLING else "OFF"
                logger.info(f"⚙️  Config: {SYMBOL}, Risk={RISK_PER_TRADE:.2%}, Trades={trades_today}/{MAX_TRADES_PER_DAY}, Shorts={short_status}")
                debug_print(f"Config: SYMBOL={SYMBOL}, RISK={RISK_PER_TRADE:.2%}, TRADES={trades_today}/{MAX_TRADES_PER_DAY}, SHORT_SELLING={ENABLE_SHORT_SELLING}")
                
                trade_count = 0
                entry_price = 0
                entry_time = None
                stop_loss = 0
                position_active = False
                position_type = None
                total_pnl = 0
                
                while True:
                    debug_print("--- Session loop iteration ---")
                    
                    try:
                        clock = api.get_clock()
                        if not clock.is_open:
                            logger.info("❌  Market closed")
                            debug_print("Market closed, exiting session loop")
                            break
                    except Exception as e:
                        logger.warning(f"⚠️  Clock check failed: {e}")
                        debug_print(f"Clock check failed: {e}, waiting 1 minute")
                        time.sleep(60)
                        continue
                    
                    if datetime.now(EASTERN).date() != current_date:
                        logger.info("📅  Day changed - resetting")
                        debug_print("Day changed, exiting session loop")
                        break
                    
                    current_equity = fetch_equity()
                    drawdown = (opening_equity - current_equity) / opening_equity
                    debug_print(f"Drawdown check: opening=${opening_equity:.2f}, current=${current_equity:.2f}, drawdown={drawdown:.2%}")
                    
                    if drawdown > MAX_DRAWDOWN:
                        logger.error(f"💸  Max drawdown: {drawdown:.2%}")
                        debug_print(f"Max drawdown exceeded: {drawdown:.2%} > {MAX_DRAWDOWN:.2%}")
                        break
                    
                    if not should_trade_based_on_market_hours():
                        debug_print("Outside trading hours, sleeping 5 minutes")
                        time.sleep(300)
                        continue
                    
                    if not pdt_allows_new_trade():
                        logger.error("🛑  PDT violation")
                        debug_print("PDT violation detected, breaking")
                        break
                    
                    current_price = get_current_price(SYMBOL)
                    if current_price == 0:
                        logger.warning("⚠️  No price, retrying...")
                        debug_print("No price data, waiting 1 minute")
                        time.sleep(60)
                        continue
                    
                    if position_active:
                        debug_print(f"Managing active position: type={position_type}, entry=${entry_price:.2f}")
                        
                        if entry_time:
                            time_in_trade = (datetime.now(EASTERN) - entry_time).total_seconds()
                            debug_print(f"Time in trade: {time_in_trade:.0f}s (max: {MAX_HOLD_TIME}s)")
                            if time_in_trade > MAX_HOLD_TIME:
                                logger.info(f"⏰  Max hold time ({MAX_HOLD_TIME//60} min)")
                                debug_print(f"Max hold time exceeded, closing position")
                                qty = current_position_qty(SYMBOL)
                                if qty != 0:
                                    if position_type == 'long':
                                        submit_market_sell(SYMBOL, qty)
                                    else:
                                        submit_buy_to_cover(SYMBOL, abs(qty))
                                    position_active = False
                                    trade_count += 1
                                    if hasattr(scale_out_profit_taking, 'target_1_hit'):
                                        delattr(scale_out_profit_taking, 'target_1_hit')
                                    if hasattr(atr_based_trailing_stop, 'trailing_stop'):
                                        delattr(atr_based_trailing_stop, 'trailing_stop')
                                    debug_print(f"Sleeping {seconds_to_human_readable(POLL_INTERVAL)} after exit")
                                    time.sleep(POLL_INTERVAL)
                                    continue
                        
                        if scale_out_profit_taking(SYMBOL, entry_price, current_price, stop_loss, position_type):
                            remaining_qty = current_position_qty(SYMBOL)
                            if remaining_qty == 0:
                                position_active = False
                                if position_type == 'long':
                                    trade_pnl = (current_price - entry_price) * 100
                                else:
                                    trade_pnl = (entry_price - current_price) * 100
                                total_pnl += trade_pnl
                                logger.info(f"✅  Position closed (PnL: ${trade_pnl:.2f})")
                                debug_print(f"Position fully closed, PnL: ${trade_pnl:.2f}")
                                if hasattr(scale_out_profit_taking, 'target_1_hit'):
                                    delattr(scale_out_profit_taking, 'target_1_hit')
                                if hasattr(atr_based_trailing_stop, 'trailing_stop'):
                                    delattr(atr_based_trailing_stop, 'trailing_stop')
                                debug_print(f"Sleeping {seconds_to_human_readable(POLL_INTERVAL)} after exit")
                                time.sleep(POLL_INTERVAL)
                                continue
                        
                        if atr_based_trailing_stop(SYMBOL, entry_price, current_price, stop_loss, position_type):
                            qty = current_position_qty(SYMBOL)
                            if qty != 0:
                                if position_type == 'long':
                                    submit_market_sell(SYMBOL, qty)
                                else:
                                    submit_buy_to_cover(SYMBOL, abs(qty))
                                position_active = False
                                trade_count += 1
                                logger.info(f"🛑  Stop hit")
                                debug_print("Stop hit, position closed")
                                if hasattr(scale_out_profit_taking, 'target_1_hit'):
                                    delattr(scale_out_profit_taking, 'target_1_hit')
                                if hasattr(atr_based_trailing_stop, 'trailing_stop'):
                                    delattr(atr_based_trailing_stop, 'trailing_stop')
                                debug_print(f"Sleeping {seconds_to_human_readable(POLL_INTERVAL)} after exit")
                                time.sleep(POLL_INTERVAL)
                                continue
                    
                    if trades_today >= MAX_TRADES_PER_DAY:
                        logger.info(f"📊  Daily limit ({MAX_TRADES_PER_DAY}) - monitoring only")
                        debug_print(f"Daily trade limit reached ({trades_today}/{MAX_TRADES_PER_DAY})")
                        time.sleep(POLL_INTERVAL)
                        continue
                    
                    signal, strength, signal_stop_loss = advanced_signal_generator(SYMBOL)
                    
                    bars = get_recent_bars(SYMBOL, 50)
                    if bars is not None:
                        regime = detect_market_regime(bars)
                    else:
                        regime = 'unknown'
                    
                    if signal in ['buy', 'sell'] and not position_active:
                        debug_print(f"Signal detected: {signal}, executing trade...")
                        buying_power = fetch_buying_power()
                        
                        position_size = calculate_position_size(current_equity, signal_stop_loss, current_price, regime)
                        
                        if buying_power >= position_size:
                            if signal == 'buy':
                                if USE_LIMIT_ORDERS:
                                    bid, ask = get_bid_ask(SYMBOL)
                                    limit_price = bid
                                    execution_price = submit_limit_buy(SYMBOL, position_size, limit_price)
                                else:
                                    execution_price = submit_market_buy(SYMBOL, position_size)
                            elif signal == 'sell' and ENABLE_SHORT_SELLING:
                                if USE_LIMIT_ORDERS:
                                    bid, ask = get_bid_ask(SYMBOL)
                                    limit_price = ask
                                    execution_price = submit_limit_short_sell(SYMBOL, position_size, limit_price)
                                else:
                                    execution_price = submit_short_sell(SYMBOL, position_size)
                            else:
                                logger.warning("⚠️  Short selling disabled - skipping sell signal")
                                debug_print("Short selling disabled, skipping sell signal")
                                execution_price = False
                            
                            if execution_price:
                                trade_count += 1
                                trades_today += 1
                                entry_price = execution_price
                                entry_time = datetime.now(EASTERN)
                                stop_loss = signal_stop_loss
                                position_active = True
                                position_type = 'long' if signal == 'buy' else 'short'
                                
                                risk_amount = abs(entry_price - stop_loss) / entry_price
                                logger.info(f"    Entry=${entry_price:.2f}, Stop=${stop_loss:.2f}, Risk={risk_amount:.2%}")
                                logger.info(f"    Regime={regime}, Strength={strength:.2f}, Trade #{trade_count} ({trades_today}/{MAX_TRADES_PER_DAY})")
                                
                                debug_print(f"Trade executed: entry=${entry_price:.2f}, stop=${stop_loss:.2f}, regime={regime}")
                                
                                atr_based_trailing_stop.trailing_stop = stop_loss
                                debug_print(f"Trailing stop initialized: ${stop_loss:.2f}")
                        else:
                            logger.warning(f"⚠️  Insufficient buying power: ${buying_power:.2f} < ${position_size:.2f}")
                            debug_print(f"Insufficient buying power: ${buying_power:.2f} < ${position_size:.2f}")
                    
                    position_status = f"{position_type.upper()}" if position_active else "FLAT"
                    try:
                        current_time = clock.timestamp.strftime("%I:%M:%S %p ET")
                    except:
                        current_time = datetime.now().strftime("%I:%M:%S %p ET")
                    
                    hourly_trend = check_multiframe_confluence(SYMBOL)
                    
                    status_msg = f"⏱️  {current_time} | {position_status} | {regime.upper()}"
                    if position_active:
                        pnl_pct = ((current_price - entry_price) / entry_price) * 100 if position_type == 'long' else ((entry_price - current_price) / entry_price) * 100
                        status_msg += f" | PnL: {pnl_pct:+.2f}%"
                    status_msg += f" | H:{hourly_trend} | VIX:{vix_level:.1f} | {trades_today}/{MAX_TRADES_PER_DAY}"
                    
                    logger.info(status_msg)
                    debug_print(f"Sleeping {seconds_to_human_readable(POLL_INTERVAL)}...")
                    time.sleep(POLL_INTERVAL)
                
                logger.info("🔚  Session ending...")
                debug_print("Session ending, closing all positions...")
                close_all_positions()
                final_equity = fetch_equity()
                session_pnl = final_equity - opening_equity
                session_pnl_pct = (session_pnl / opening_equity) * 100 if opening_equity > 0 else 0
                logger.info(f"📊  Summary: {trade_count} trades")
                logger.info(f"💰  Final: ${final_equity:.2f} (PNL: ${session_pnl:+.2f}, {session_pnl_pct:+.2f}%)")
                logger.info("✅  Day complete. Waiting for next session...")
                debug_print(f"Day complete. Trades: {trade_count}, PnL: ${session_pnl:+.2f}")
                
                time.sleep(3600)
                
            except Exception as e:
                logger.error(f"💥  Session error: {e}")
                debug_print(f"Session error: {e}")
                import traceback
                logger.error(traceback.format_exc())
                logger.info("⏳  Waiting 5 min before retry...")
                time.sleep(300)
                
    except KeyboardInterrupt:
        logger.info("🛑  User interrupt")
        debug_print("User interrupt detected")
        close_all_positions()
    except Exception as e:
        logger.error(f"💥  Fatal error: {e}")
        debug_print(f"Fatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        logger.info("🔚  Shutdown")
        debug_print("Script shutdown")

if __name__ == "__main__":
    main()

