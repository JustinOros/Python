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
from pathlib import Path
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# Path configuration
SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "daytrader.json"
ENV_PATH = SCRIPT_DIR / ".env"

# Advanced configuration
DEFAULT_CONFIG = {
    "SYMBOL": "SPY",
    "RISK_PER_TRADE": 0.005,
    "SHORT_WINDOW": 20,
    "LONG_WINDOW": 50,
    "MIN_NOTIONAL": 1.0,
    "POLL_INTERVAL": 1800,
    "MAX_DRAWDOWN": 0.12,
    "PDT_RULE": True,
    "USE_TRAILING_STOP": True,
    "PROFIT_TARGET_1": 1.5,
    "PROFIT_TARGET_2": 3.0,
    "VOLATILITY_ADJUSTMENT": True,
    "MARKET_HOURS_FILTER": True,
    "ENABLE_SLIPPAGE": True,
    "SLIPPAGE_PCT": 0.0005,
    "COMMISSION_PCT": 0.0005,
    "MIN_SIGNAL_STRENGTH": 0.85,
    "BACKTEST_DAYS": 90,
    "USE_LIMIT_ORDERS": True,
    "LIMIT_ORDER_TIMEOUT": 60,
    "ADX_THRESHOLD": 20,
    "VOLUME_MULTIPLIER": 1.2,
    "ATR_STOP_MULTIPLIER": 1.5,
    "MAX_HOLD_TIME": 7200,
    "REGIME_DETECTION": True,
    "MULTIFRAME_FILTER": True,
    "BB_WINDOW": 20,
    "BB_STD": 2.0,
    "USE_EMA": True,
    "REQUIRE_CANDLE_PATTERN": True,
    "USE_PIVOT_POINTS": True,
    "VIX_THRESHOLD": 20,
    "USE_VIX_FILTER": True,
    "USE_FIBONACCI": True,
    "MAX_TRADES_PER_DAY": 2,
    "SKIP_MONDAYS_FRIDAYS": True,
    "USE_200_SMA_FILTER": True,
    "REQUIRE_MACD_CONFIRMATION": True,
    "MIN_RISK_REWARD": 2.0,
    "PULLBACK_PERCENTAGE": 0.382
}

# Load environment variables
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    # Create placeholder .env file
    with open(ENV_PATH, "w") as f:
        f.write('APCA_API_KEY_ID="YOUR_API_KEY_HERE"\n')
        f.write('APCA_API_SECRET_KEY="YOUR_SECRET_KEY_HERE"\n')
        f.write('APCA_API_BASE_URL="https://paper-api.alpaca.markets"\n')
    print("⚠️  Created placeholder .env file.")
    print("    Please add your Alpaca API keys to .env file")
    sys.exit(1)

# Load configuration
if CONFIG_PATH.exists():
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
else:
    # Create default config
    with open(CONFIG_PATH, "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=4)
    config = DEFAULT_CONFIG.copy()
    print(f"✅ Created default config file at {CONFIG_PATH}")

# Extract configuration values
SYMBOL = config["SYMBOL"]
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

# Initialize Alpaca API
api = tradeapi.REST(
    os.getenv('APCA_API_KEY_ID'),
    os.getenv('APCA_API_SECRET_KEY'),
    os.getenv('APCA_API_BASE_URL'),
    api_version='v2'
)

# -----------------------------------------------------------------------------
# Technical Analysis Functions
# -----------------------------------------------------------------------------

def calculate_sma(data, window):
    # Simple Moving Average
    return data.rolling(window=window).mean()

def calculate_ema(data, window):
    # Exponential Moving Average
    return data.ewm(span=window, adjust=False).mean()

def calculate_rsi(data, window=14):
    # Relative Strength Index
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_atr(high, low, close, window=14):
    # Average True Range
    high_low = high - low
    high_close_prev = abs(high - close.shift())
    low_close_prev = abs(low - close.shift())
    true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
    atr = true_range.rolling(window=window).mean()
    return atr

def calculate_adx(high, low, close, window=14):
    # Average Directional Index for trend strength
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
    # MACD indicator
    ema_fast = calculate_ema(close, fast)
    ema_slow = calculate_ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram

def calculate_bollinger_bands(close, window=20, num_std=2):
    # Bollinger Bands for mean reversion
    if USE_EMA:
        middle = calculate_ema(close, window)
    else:
        middle = calculate_sma(close, window)
    
    std = close.rolling(window=window).std()
    upper = middle + (std * num_std)
    lower = middle - (std * num_std)
    
    return upper, middle, lower

def check_volume_confirmation(bars):
    # Check if current volume exceeds threshold
    if 'volume' not in bars.columns or len(bars) < 20:
        return True
    
    avg_volume = bars['volume'].rolling(window=20).mean().iloc[-1]
    current_volume = bars['volume'].iloc[-1]
    
    return current_volume >= (avg_volume * VOLUME_MULTIPLIER)

def detect_market_regime(bars):
    # Detect market regime: trending, ranging, high_vol, low_vol
    if len(bars) < 50:
        return 'unknown'
    
    closes = bars['close']
    highs = bars['high']
    lows = bars['low']
    
    adx, plus_di, minus_di = calculate_adx(highs, lows, closes, 14)
    current_adx = adx.iloc[-1]
    
    atr = calculate_atr(highs, lows, closes, 14)
    current_atr = atr.iloc[-1]
    atr_percentile = (atr <= current_atr).sum() / len(atr) * 100
    
    if atr_percentile > 70:
        return 'high_vol'
    elif atr_percentile < 30:
        return 'low_vol'
    elif current_adx > ADX_THRESHOLD:
        return 'trend'
    else:
        return 'range'

def check_multiframe_confluence(symbol):
    # Check hourly timeframe for trend alignment
    if not MULTIFRAME_FILTER:
        return 'neutral'
    
    try:
        hourly_bars = api.get_bars(symbol, "1Hour", limit=50).df
        if len(hourly_bars) < 50:
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
        
        if current_short > current_long and current_price > current_short:
            return 'bullish'
        elif current_short < current_long and current_price < current_short:
            return 'bearish'
        else:
            return 'neutral'
            
    except Exception as e:
        logger.warning(f"⚠️  Could not check multiframe confluence: {e}")
        return 'neutral'

def check_candle_pattern(bars):
    # Check for bullish/bearish engulfing patterns
    if len(bars) < 2:
        return False, False
    
    last = bars.iloc[-1]
    prev = bars.iloc[-2]
    
    # Bullish engulfing
    bullish_engulfing = (
        last['close'] > last['open'] and
        prev['close'] < prev['open'] and
        last['close'] > prev['open'] and
        last['open'] < prev['close']
    )
    
    # Bearish engulfing
    bearish_engulfing = (
        last['close'] < last['open'] and
        prev['close'] > prev['open'] and
        last['close'] < prev['open'] and
        last['open'] > prev['close']
    )
    
    return bullish_engulfing, bearish_engulfing

def calculate_pivot_points(symbol):
    # Calculate yesterday's pivot points for support/resistance
    if not USE_PIVOT_POINTS:
        return None, None, None, None, None
    
    try:
        yesterday_bars = api.get_bars(symbol, "1Day", limit=2).df
        if len(yesterday_bars) < 2:
            return None, None, None, None, None
        
        h = yesterday_bars['high'].iloc[-2]
        l = yesterday_bars['low'].iloc[-2]
        c = yesterday_bars['close'].iloc[-2]
        
        pivot = (h + l + c) / 3
        r1 = 2 * pivot - l
        r2 = pivot + (h - l)
        s1 = 2 * pivot - h
        s2 = pivot - (h - l)
        
        return pivot, r1, r2, s1, s2
        
    except Exception as e:
        logger.warning(f"⚠️  Could not calculate pivot points: {e}")
        return None, None, None, None, None

def calculate_fibonacci_levels(bars, lookback=20):
    # Calculate Fibonacci retracement levels
    if not USE_FIBONACCI or len(bars) < lookback:
        return None, None, None, None, None
    
    recent_bars = bars.tail(lookback)
    swing_high = recent_bars['high'].max()
    swing_low = recent_bars['low'].min()
    
    diff = swing_high - swing_low
    
    fib_382 = swing_high - (diff * 0.382)
    fib_500 = swing_high - (diff * 0.500)
    fib_618 = swing_high - (diff * 0.618)
    
    return fib_382, fib_500, fib_618, swing_high, swing_low

def get_vix_level():
    # Get current VIX (fear index) level
    if not USE_VIX_FILTER:
        return 0
    
    try:
        vix_bars = api.get_bars("VIX", "1Day", limit=5).df
        if len(vix_bars) > 0:
            return vix_bars['close'].iloc[-1]
        else:
            # Estimate from S&P 500 volatility
            spy_bars = api.get_bars("SPY", "1Day", limit=20).df
            if len(spy_bars) >= 20:
                spy_returns = spy_bars['close'].pct_change()
                volatility = spy_returns.std() * np.sqrt(252) * 100
                return volatility
            return 15
    except Exception as e:
        logger.warning(f"⚠️  Could not get VIX level: {e}")
        return 15

def check_200_sma_filter(symbol):
    # Check 200-day SMA for major trend direction
    if not USE_200_SMA_FILTER:
        return 'neutral'
    
    try:
        daily_bars = api.get_bars(symbol, "1Day", limit=210).df
        if len(daily_bars) < 200:
            return 'neutral'
        
        closes = daily_bars['close']
        sma_200 = calculate_sma(closes, 200).iloc[-1]
        current_price = closes.iloc[-1]
        
        if current_price > sma_200 * 1.01:
            return 'bullish'
        elif current_price < sma_200 * 0.99:
            return 'bearish'
        else:
            return 'neutral'
            
    except Exception as e:
        logger.warning(f"⚠️  Could not check 200 SMA: {e}")
        return 'neutral'

def check_macd_confirmation(bars):
    # Check MACD for trend confirmation
    if not REQUIRE_MACD_CONFIRMATION or len(bars) < 35:
        return 'neutral'
    
    closes = bars['close']
    macd_line, signal_line, histogram = calculate_macd(closes)
    
    current_macd = macd_line.iloc[-1]
    current_signal = signal_line.iloc[-1]
    prev_macd = macd_line.iloc[-2]
    prev_signal = signal_line.iloc[-2]
    
    # Bullish: MACD crosses above signal
    if prev_macd <= prev_signal and current_macd > current_signal:
        return 'bullish'
    # Bearish: MACD crosses below signal
    elif prev_macd >= prev_signal and current_macd < current_signal:
        return 'bearish'
    # Continuation
    elif current_macd > current_signal:
        return 'bullish'
    elif current_macd < current_signal:
        return 'bearish'
    
    return 'neutral'

def should_skip_trading_day():
    # Check if today should be skipped (Monday/Friday)
    if not SKIP_MONDAYS_FRIDAYS:
        return False
    
    today = datetime.now().weekday()
    # 0 = Monday, 4 = Friday
    if today == 0 or today == 4:
        return True
    
    return False

# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

def seconds_to_human_readable(seconds):
    # Convert seconds to human-readable format
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
    # Format datetime object to readable string
    return dt_obj.strftime("%Y-%m-%d %I:%M:%S %p %Z")

def apply_slippage(price, is_buy=True):
    # Apply slippage and commission to price
    if not ENABLE_SLIPPAGE:
        return price
    
    slippage_adjustment = price * SLIPPAGE_PCT
    commission_adjustment = price * COMMISSION_PCT
    
    if is_buy:
        adjusted_price = price + slippage_adjustment + commission_adjustment
    else:
        adjusted_price = price - slippage_adjustment - commission_adjustment
    
    return adjusted_price

# -----------------------------------------------------------------------------
# Advanced Trading Functions
# -----------------------------------------------------------------------------

def advanced_backtest_strategy():
    # Comprehensive backtest with all advanced filters
    logger.info("📊 Running advanced backtest with all filters...")
    
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=BACKTEST_DAYS)
        
        bars = api.get_bars(SYMBOL, "15Min", start=start_date.isoformat(), 
                           end=end_date.isoformat()).df
        if len(bars) < 100:
            logger.warning("⚠️  Insufficient data for backtest")
            return True
        
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
        
        # Track performance
        initial_balance = 10000
        balance = initial_balance
        position = 0
        entry_price = 0
        entry_time = None
        stop_loss = 0
        trades = []
        winning_trades = 0
        daily_trades = {}
        
        for i in range(max(SHORT_WINDOW, LONG_WINDOW, BB_WINDOW, 35), len(bars)):
            current_price = closes.iloc[i]
            current_time = bars.index[i]
            current_date = current_time.date()
            current_adx = adx.iloc[i]
            current_rsi = rsi.iloc[i]
            current_atr = atr.iloc[i]
            
            # Check daily trade limit
            if current_date not in daily_trades:
                daily_trades[current_date] = 0
            
            regime = 'trend' if current_adx > ADX_THRESHOLD else 'range'
            macd_signal = 'bullish' if macd_line.iloc[i] > signal_line.iloc[i] else 'bearish'
            
            # Check candle pattern
            recent_bars = bars.iloc[max(0, i-1):i+1]
            bullish_eng, bearish_eng = check_candle_pattern(recent_bars)
            
            # Generate signals
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
            
            # Enter position
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
            
            # Exit position
            elif position != 0:
                exit_triggered = False
                exit_price = None
                exit_reason = None
                
                # Stop loss
                if position > 0 and current_price <= stop_loss:
                    exit_triggered = True
                    exit_price = apply_slippage(stop_loss, False)
                    exit_reason = 'stop_loss'
                elif position < 0 and current_price >= stop_loss:
                    exit_triggered = True
                    exit_price = apply_slippage(stop_loss, False)
                    exit_reason = 'stop_loss'
                
                # Time-based exit
                time_in_trade = (current_time - entry_time).total_seconds()
                if time_in_trade > MAX_HOLD_TIME:
                    exit_triggered = True
                    exit_price = apply_slippage(current_price, False)
                    exit_reason = 'time_limit'
                
                # Profit targets
                pnl_pct = (current_price - entry_price) / entry_price * position
                risk_amount = abs(entry_price - stop_loss) / entry_price
                
                if pnl_pct >= (risk_amount * PROFIT_TARGET_1):
                    exit_triggered = True
                    exit_price = apply_slippage(current_price, False)
                    exit_reason = 'target_1'
                
                # Signal reversal
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
        
        # Calculate statistics
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
        
        if total_trades < 5:
            logger.warning("⚠️  Very few trades - filters may be too strict")
        if win_rate < 0.45:
            logger.warning("⚠️  Win rate below target")
        if profit_factor < 1.3:
            logger.warning("⚠️  Profit factor < 1.3")
            
        return True
        
    except Exception as e:
        logger.warning(f"⚠️  Backtest failed: {e}")
        return True

def advanced_signal_generator(symbol):
    # Advanced signal generation with ALL filters
    # Returns: signal ('buy', 'sell', None), strength (0-1), stop_loss_price
    bars = get_recent_bars(symbol, 100)
    if bars is None or len(bars) < 50:
        return None, 0, 0
    
    closes = bars['close']
    highs = bars['high']
    lows = bars['low']
    current_price = closes.iloc[-1]
    
    # Calculate indicators
    if USE_EMA:
        short_ma = calculate_ema(closes, SHORT_WINDOW).iloc[-1]
        long_ma = calculate_ema(closes, LONG_WINDOW).iloc[-1]
    else:
        short_ma = calculate_sma(closes, SHORT_WINDOW).iloc[-1]
        long_ma = calculate_sma(closes, LONG_WINDOW).iloc[-1]
    
    rsi = calculate_rsi(closes, 14).iloc[-1]
    adx, plus_di, minus_di = calculate_adx(highs, lows, closes, 14)
    current_adx = adx.iloc[-1]
    atr = calculate_atr(highs, lows, closes, 14).iloc[-1]
    upper_bb, middle_bb, lower_bb = calculate_bollinger_bands(closes, BB_WINDOW, BB_STD)
    
    # Filters
    vix_level = get_vix_level()
    if USE_VIX_FILTER and vix_level > VIX_THRESHOLD:
        logger.info(f"📉  VIX too high: {vix_level:.1f} > {VIX_THRESHOLD}")
        return None, 0, 0
    
    sma_200_trend = check_200_sma_filter(symbol)
    if USE_200_SMA_FILTER and sma_200_trend == 'bearish':
        logger.info(f"📉  Below 200 SMA - avoiding longs")
    
    volume_ok = check_volume_confirmation(bars)
    if not volume_ok:
        logger.info(f"📊  Insufficient volume")
        return None, 0, 0
    
    bullish_eng, bearish_eng = check_candle_pattern(bars)
    macd_signal = check_macd_confirmation(bars)
    hourly_trend = check_multiframe_confluence(symbol)
    pivot, r1, r2, s1, s2 = calculate_pivot_points(symbol)
    fib_382, fib_500, fib_618, swing_high, swing_low = calculate_fibonacci_levels(bars, 20)
    
    regime = detect_market_regime(bars)
    
    if regime == 'low_vol':
        logger.info("📉  Low volatility regime")
        return None, 0, 0
    
    signal = None
    signal_strength = 0
    stop_loss = 0
    
    # TREND REGIME
    if regime == 'trend':
        if current_adx > ADX_THRESHOLD:
            # Bullish trend - wait for pullback
            if short_ma > long_ma:
                pullback_ok = False
                if USE_FIBONACCI and fib_382 is not None:
                    if abs(current_price - fib_382) / current_price < 0.01:
                        pullback_ok = True
                elif current_price < short_ma * 1.005:
                    pullback_ok = True
                
                if pullback_ok and rsi < 55:
                    if hourly_trend in ['bullish', 'neutral']:
                        if REQUIRE_CANDLE_PATTERN and not bullish_eng:
                            logger.info("❌  No bullish engulfing")
                            return None, 0, 0
                        
                        if REQUIRE_MACD_CONFIRMATION and macd_signal != 'bullish':
                            logger.info("❌  MACD not bullish")
                            return None, 0, 0
                        
                        if USE_200_SMA_FILTER and sma_200_trend == 'bearish':
                            logger.info("❌  Below 200 SMA - no longs")
                            return None, 0, 0
                        
                        if USE_PIVOT_POINTS and s1 is not None:
                            if current_price < s1 * 1.02:
                                signal = 'buy'
                                signal_strength = min(1.0, (current_adx / 40) * 0.8 + 0.2)
                                stop_loss = current_price - (atr * ATR_STOP_MULTIPLIER)
                        else:
                            signal = 'buy'
                            signal_strength = min(1.0, (current_adx / 40) * 0.7 + 0.3)
                            stop_loss = current_price - (atr * ATR_STOP_MULTIPLIER)
            
            # Bearish trend - wait for pullback
            elif short_ma < long_ma:
                pullback_ok = False
                if USE_FIBONACCI and fib_618 is not None:
                    if abs(current_price - fib_618) / current_price < 0.01:
                        pullback_ok = True
                elif current_price > short_ma * 0.995:
                    pullback_ok = True
                
                if pullback_ok and rsi > 45:
                    if hourly_trend in ['bearish', 'neutral']:
                        if REQUIRE_CANDLE_PATTERN and not bearish_eng:
                            logger.info("❌  No bearish engulfing")
                            return None, 0, 0
                        
                        if REQUIRE_MACD_CONFIRMATION and macd_signal != 'bearish':
                            logger.info("❌  MACD not bearish")
                            return None, 0, 0
                        
                        if USE_PIVOT_POINTS and r1 is not None:
                            if current_price > r1 * 0.98:
                                signal = 'sell'
                                signal_strength = min(1.0, (current_adx / 40) * 0.8 + 0.2)
                                stop_loss = current_price + (atr * ATR_STOP_MULTIPLIER)
                        else:
                            signal = 'sell'
                            signal_strength = min(1.0, (current_adx / 40) * 0.7 + 0.3)
                            stop_loss = current_price + (atr * ATR_STOP_MULTIPLIER)
    
    # RANGE REGIME
    elif regime == 'range':
        # Oversold at lower band
        if current_price <= lower_bb.iloc[-1] and rsi < 30:
            if hourly_trend != 'bearish':
                if REQUIRE_CANDLE_PATTERN and not bullish_eng:
                    logger.info("❌  No bullish engulfing in range")
                    return None, 0, 0
                
                if USE_200_SMA_FILTER and sma_200_trend == 'bearish':
                    logger.info("❌  Below 200 SMA - no mean reversion longs")
                    return None, 0, 0
                
                signal = 'buy'
                signal_strength = 0.85
                stop_loss = current_price - (atr * ATR_STOP_MULTIPLIER)
        
        # Overbought at upper band
        elif current_price >= upper_bb.iloc[-1] and rsi > 70:
            if hourly_trend != 'bullish':
                if REQUIRE_CANDLE_PATTERN and not bearish_eng:
                    logger.info("❌  No bearish engulfing in range")
                    return None, 0, 0
                
                signal = 'sell'
                signal_strength = 0.85
                stop_loss = current_price + (atr * ATR_STOP_MULTIPLIER)
    
    # HIGH VOL REGIME
    elif regime == 'high_vol':
        if short_ma > long_ma and rsi < 35:
            if hourly_trend == 'bullish':
                if REQUIRE_CANDLE_PATTERN and not bullish_eng:
                    return None, 0, 0
                
                if REQUIRE_MACD_CONFIRMATION and macd_signal != 'bullish':
                    return None, 0, 0
                
                signal = 'buy'
                signal_strength = 0.6
                stop_loss = current_price - (atr * ATR_STOP_MULTIPLIER * 1.5)
        
        elif short_ma < long_ma and rsi > 65:
            if hourly_trend == 'bearish':
                if REQUIRE_CANDLE_PATTERN and not bearish_eng:
                    return None, 0, 0
                
                if REQUIRE_MACD_CONFIRMATION and macd_signal != 'bearish':
                    return None, 0, 0
                
                signal = 'sell'
                signal_strength = 0.6
                stop_loss = current_price + (atr * ATR_STOP_MULTIPLIER * 1.5)
    
    # Check minimum signal strength
    if signal_strength < MIN_SIGNAL_STRENGTH:
        logger.info(f"❌  Signal strength {signal_strength:.2f} < {MIN_SIGNAL_STRENGTH:.2f}")
        return None, signal_strength, 0
    
    # Final risk/reward check
    if signal and stop_loss != 0:
        potential_reward = abs(current_price - stop_loss) * MIN_RISK_REWARD
        if USE_PIVOT_POINTS:
            if signal == 'buy' and r1 is not None:
                actual_reward = r1 - current_price
                if actual_reward < potential_reward:
                    logger.info(f"❌  R:R too low: {actual_reward:.2f} < {potential_reward:.2f}")
                    return None, signal_strength, 0
            elif signal == 'sell' and s1 is not None:
                actual_reward = current_price - s1
                if actual_reward < potential_reward:
                    logger.info(f"❌  R:R too low: {actual_reward:.2f} < {potential_reward:.2f}")
                    return None, signal_strength, 0
    
    return signal, signal_strength, stop_loss

def wait_until_market_open():
    # Wait until the market opens
    clock = api.get_clock()
    now = clock.timestamp
    next_open = clock.next_open
    
    if not clock.is_open:
        seconds_until_open = (next_open - now).total_seconds()
        if seconds_until_open > 0:
            readable_time = seconds_to_human_readable(seconds_until_open)
            logger.info(f"🕒  Market opens at {format_market_time(next_open)}")
            logger.info(f"⏱️  Waiting {readable_time}...")
            
            while seconds_until_open > 0:
                sleep_time = min(60, seconds_until_open)
                time.sleep(sleep_time)
                seconds_until_open -= sleep_time
                
                if sleep_time >= 60:
                    remaining_readable = seconds_to_human_readable(seconds_until_open)
                    logger.info(f"⏱️  {remaining_readable} remaining...")
        else:
            logger.info("✅  Market is open!")
    else:
        logger.info("✅  Market is open!")

def fetch_equity():
    # Fetch the current account equity
    try:
        account = api.get_account()
        return float(account.equity)
    except Exception as e:
        logger.error(f"❌  Failed to fetch equity: {e}")
        return 0.0

def fetch_buying_power():
    # Fetch the current buying power
    try:
        account = api.get_account()
        return float(account.buying_power)
    except Exception as e:
        logger.error(f"❌  Failed to fetch buying power: {e}")
        return 0.0

def get_day_trade_count():
    # Get the current day trade count
    try:
        account = api.get_account()
        return int(account.day_trade_count)
    except Exception as e:
        logger.error(f"❌  Failed to fetch day trade count: {e}")
        return 0

def submit_limit_buy(symbol, notional, limit_price):
    # Submit a limit buy order
    if notional < MIN_NOTIONAL:
        logger.warning(f"⚠️  Notional ${notional:.2f} < minimum ${MIN_NOTIONAL}")
        return False
    
    try:
        shares = int(notional / limit_price)
        
        if shares == 0:
            logger.warning(f"⚠️  Cannot buy fractional shares with ${notional:.2f}")
            return False
        
        order = api.submit_order(
            symbol=symbol,
            qty=shares,
            side="buy",
            type="limit",
            limit_price=round(limit_price, 2),
            time_in_force="gtc"
        )
        
        logger.info(f"🟢  LIMIT BUY: {shares} shares @ ${limit_price:.2f}")
        
        # Wait for fill or timeout
        start_time = time.time()
        while (time.time() - start_time) < LIMIT_ORDER_TIMEOUT:
            order_status = api.get_order(order.id)
            if order_status.status == 'filled':
                filled_price = float(order_status.filled_avg_price)
                logger.info(f"✅  FILLED @ ${filled_price:.2f}")
                return filled_price
            elif order_status.status in ['cancelled', 'expired', 'rejected']:
                logger.warning(f"⚠️  Limit order {order_status.status}")
                return False
            time.sleep(2)
        
        # Timeout - cancel and use market order
        logger.warning("⏱️  Timeout - switching to market")
        api.cancel_order(order.id)
        return submit_market_buy(symbol, notional)
        
    except Exception as e:
        logger.error(f"❌  Failed limit buy: {e}")
        return False

def submit_market_buy(symbol, notional):
    # Submit a market buy order (fallback)
    try:
        current_price = get_current_price(symbol)
        if current_price == 0:
            return False
        
        execution_price = apply_slippage(current_price, True)
        shares = int(notional / execution_price)
        
        if shares == 0:
            return False
        
        api.submit_order(
            symbol=symbol,
            qty=shares,
            side="buy",
            type="market",
            time_in_force="day"
        )
        logger.info(f"🟢  MARKET BUY: {shares} shares @ ~${execution_price:.2f}")
        return execution_price
    except Exception as e:
        logger.error(f"❌  Failed buy: {e}")
        return False

def submit_limit_sell(symbol, qty, limit_price):
    # Submit a limit sell order
    try:
        order = api.submit_order(
            symbol=symbol,
            qty=qty,
            side="sell",
            type="limit",
            limit_price=round(limit_price, 2),
            time_in_force="gtc"
        )
        
        logger.info(f"🔴  LIMIT SELL: {qty} shares @ ${limit_price:.2f}")
        
        # Wait for fill or timeout
        start_time = time.time()
        while (time.time() - start_time) < LIMIT_ORDER_TIMEOUT:
            order_status = api.get_order(order.id)
            if order_status.status == 'filled':
                filled_price = float(order_status.filled_avg_price)
                logger.info(f"✅  FILLED @ ${filled_price:.2f}")
                return filled_price
            elif order_status.status in ['cancelled', 'expired', 'rejected']:
                logger.warning(f"⚠️  Limit order {order_status.status}")
                return False
            time.sleep(2)
        
        # Timeout - cancel and use market order
        logger.warning("⏱️  Timeout - switching to market")
        api.cancel_order(order.id)
        return submit_market_sell(symbol, qty)
        
    except Exception as e:
        logger.error(f"❌  Failed limit sell: {e}")
        return False

def submit_market_sell(symbol, qty):
    # Submit a market sell order (fallback)
    try:
        current_price = get_current_price(symbol)
        if current_price == 0:
            return False
        
        execution_price = apply_slippage(current_price, False)
        
        api.submit_order(
            symbol=symbol,
            qty=qty,
            side="sell",
            type="market",
            time_in_force="day"
        )
        logger.info(f"🔴  MARKET SELL: {qty} shares @ ~${execution_price:.2f}")
        return execution_price
    except Exception as e:
        logger.error(f"❌  Failed sell: {e}")
        return False

def close_all_positions():
    # Close all open positions
    try:
        positions = api.list_positions()
        if not positions:
            logger.info("✅  No open positions")
            return
        
        logger.warning("⚠️  Closing all positions...")
        for pos in positions:
            submit_market_sell(pos.symbol, int(float(pos.qty)))
        logger.info("✅  All positions closed")
    except Exception as e:
        logger.error(f"❌  Failed to close positions: {e}")

def get_recent_bars(symbol, limit=100):
    # Get recent bar data for a symbol
    try:
        timeframe = "15Min"
        bars = api.get_bars(symbol, timeframe, limit=limit).df
        return bars
    except Exception as e:
        logger.error(f"❌  Failed to fetch bars: {e}")
        return None

def current_position_qty(symbol):
    # Get the current position quantity
    try:
        positions = api.list_positions()
        for pos in positions:
            if pos.symbol == symbol:
                return int(float(pos.qty))
        return 0
    except Exception as e:
        logger.error(f"❌  Failed to fetch positions: {e}")
        return 0

def pdt_allows_new_trade():
    # Check if PDT rules allow a new trade
    if not PDT_RULE:
        return True
    
    equity = fetch_equity()
    day_trade_count = get_day_trade_count()
    
    if equity < 25000:
        if day_trade_count >= 3:
            logger.error(f"🛑  PDT rule: {day_trade_count} trades in 5-day window")
            return False
    
    return True

def get_market_status():
    # Get current market status
    clock = api.get_clock()
    status = "open" if clock.is_open else "closed"
    next_event = clock.next_open if not clock.is_open else clock.next_close
    event_type = "open" if not clock.is_open else "close"
    
    return {
        "status": status,
        "next_event": next_event,
        "event_type": event_type,
        "timestamp": clock.timestamp
    }

def calculate_position_size(equity, stop_loss, entry_price, regime='normal'):
    # Calculate position size based on fixed risk per trade
    risk_amount = equity * RISK_PER_TRADE
    
    if regime == 'high_vol':
        risk_amount *= 0.5
        logger.info(f"📊  High vol - reducing position 50%")
    
    stop_distance = abs(entry_price - stop_loss)
    if stop_distance == 0:
        return MIN_NOTIONAL
    
    position_size = risk_amount / stop_distance * entry_price
    position_size = max(MIN_NOTIONAL, position_size)
    
    logger.info(f"💰  Position: Risk=${risk_amount:.2f}, Stop=${stop_distance:.2f}, Size=${position_size:.2f}")
    
    return position_size

def should_trade_based_on_market_hours():
    # Avoid trading during low-volume periods
    if not MARKET_HOURS_FILTER:
        return True
        
    now = datetime.now().time()
    
    # Avoid first 30 min
    open_buffer_end = datetime.strptime("10:00", "%H:%M").time()
    
    # Avoid last 30 min
    close_buffer_start = datetime.strptime("15:30", "%H:%M").time()
    
    if now < open_buffer_end:
        return False
    
    if now >= close_buffer_start:
        return False
    
    return True

def atr_based_trailing_stop(symbol, entry_price, current_price, stop_loss, position_type='long'):
    # ATR-based trailing stop loss
    if not USE_TRAILING_STOP:
        if position_type == 'long' and current_price <= stop_loss:
            return True
        elif position_type == 'short' and current_price >= stop_loss:
            return True
        return False
    
    position_qty = current_position_qty(symbol)
    if position_qty == 0:
        return False
    
    # Get ATR for dynamic stop
    bars = get_recent_bars(symbol, 20)
    if bars is not None and len(bars) > 14:
        atr = calculate_atr(bars['high'], bars['low'], bars['close'], 14).iloc[-1]
        trail_distance = atr * ATR_STOP_MULTIPLIER
    else:
        trail_distance = abs(entry_price - stop_loss)
    
    # Update trailing stop
    if not hasattr(atr_based_trailing_stop, 'trailing_stop'):
        atr_based_trailing_stop.trailing_stop = stop_loss
    
    if position_type == 'long':
        new_stop = current_price - trail_distance
        if new_stop > atr_based_trailing_stop.trailing_stop:
            atr_based_trailing_stop.trailing_stop = new_stop
            logger.info(f"📈  Trailing stop → ${new_stop:.2f}")
        
        if current_price <= atr_based_trailing_stop.trailing_stop:
            logger.info(f"🛑  Trailing stop hit @ ${current_price:.2f}")
            return True
    
    elif position_type == 'short':
        new_stop = current_price + trail_distance
        if new_stop < atr_based_trailing_stop.trailing_stop:
            atr_based_trailing_stop.trailing_stop = new_stop
            logger.info(f"📉  Trailing stop → ${new_stop:.2f}")
        
        if current_price >= atr_based_trailing_stop.trailing_stop:
            logger.info(f"🛑  Trailing stop hit @ ${current_price:.2f}")
            return True
    
    return False

def scale_out_profit_taking(symbol, entry_price, current_price, stop_loss, position_type='long'):
    # Scale out at profit targets
    position_qty = current_position_qty(symbol)
    if position_qty == 0:
        return False
    
    risk_distance = abs(entry_price - stop_loss)
    
    if position_type == 'long':
        profit_pct = (current_price - entry_price) / entry_price
        profit_in_r = (current_price - entry_price) / risk_distance if risk_distance > 0 else 0
    else:
        profit_pct = (entry_price - current_price) / entry_price
        profit_in_r = (entry_price - current_price) / risk_distance if risk_distance > 0 else 0
    
    # First target: 1.5R
    if profit_in_r >= PROFIT_TARGET_1:
        if not hasattr(scale_out_profit_taking, 'target_1_hit'):
            scale_out_profit_taking.target_1_hit = True
            partial_qty = position_qty // 2
            
            if partial_qty > 0:
                if USE_LIMIT_ORDERS:
                    limit_price = current_price
                    submit_limit_sell(symbol, partial_qty, limit_price)
                else:
                    submit_market_sell(symbol, partial_qty)
                
                logger.info(f"🎯  Target 1 ({PROFIT_TARGET_1}R) - 50% out @ ${current_price:.2f}")
                
                # Move stop to breakeven
                atr_based_trailing_stop.trailing_stop = entry_price
                logger.info(f"🔒  Stop → breakeven: ${entry_price:.2f}")
                return True
    
    # Second target: 3R
    if profit_in_r >= PROFIT_TARGET_2:
        remaining_qty = current_position_qty(symbol)
        if remaining_qty > 0:
            if USE_LIMIT_ORDERS:
                limit_price = current_price
                submit_limit_sell(symbol, remaining_qty, limit_price)
            else:
                submit_market_sell(symbol, remaining_qty)
            
            logger.info(f"🎯🎯  Target 2 ({PROFIT_TARGET_2}R) - Full exit @ ${current_price:.2f}")
            return True
    
    return False

def get_current_price(symbol):
    # Get current price for a symbol
    try:
        bars = api.get_bars(symbol, "1Min", limit=5).df
        if len(bars) > 0:
            return bars['close'].iloc[-1]
        else:
            return 0
    except Exception as e:
        logger.error(f"❌  Failed to get price: {e}")
        return 0

def get_bid_ask(symbol):
    # Get current bid/ask prices
    try:
        quote = api.get_latest_quote(symbol)
        return float(quote.bid_price), float(quote.ask_price)
    except Exception as e:
        logger.warning(f"⚠️  Could not get bid/ask: {e}")
        current_price = get_current_price(symbol)
        return current_price, current_price

# -----------------------------------------------------------------------------
# Main Trading Loop - Continuous Operation
# -----------------------------------------------------------------------------

def main():
    # Main trading function - runs continuously 24/7
    logger.info("🚀  Starting daytrader.py - continuous operation")
    
    # Run backtest once at startup
    if not advanced_backtest_strategy():
        logger.error("❌  Backtest failed. Exiting...")
        return
    
    # Track daily state
    last_reset_date = None
    trades_today = 0
    
    try:
        while True:  # Infinite loop for continuous operation
            try:
                # Check if we need to reset daily counters
                current_date = datetime.now().date()
                if last_reset_date != current_date:
                    trades_today = 0
                    last_reset_date = current_date
                    logger.info(f"📅  New day: {current_date}")
                    
                    # Reset function attributes
                    if hasattr(scale_out_profit_taking, 'target_1_hit'):
                        delattr(scale_out_profit_taking, 'target_1_hit')
                    if hasattr(atr_based_trailing_stop, 'trailing_stop'):
                        delattr(atr_based_trailing_stop, 'trailing_stop')
                
                # Check if should skip today
                if should_skip_trading_day():
                    day_name = datetime.now().strftime("%A")
                    logger.info(f"📅  Skipping {day_name} - monitoring mode")
                    time.sleep(3600)  # Sleep 1 hour
                    continue
                
                # Display market status
                market_info = get_market_status()
                
                if market_info['status'] == 'closed':
                    logger.info(f"🏛️  Market closed")
                    logger.info(f"📅  Next open: {format_market_time(market_info['next_event'])}")
                    wait_until_market_open()
                    continue
                
                # Market is open
                logger.info(f"🏛️  Market OPEN - starting session")
                
                # Record opening equity
                opening_equity = fetch_equity()
                if opening_equity == 0:
                    logger.error("💥  No equity. Waiting 5 min...")
                    time.sleep(300)
                    continue
                
                logger.info(f"💰  Opening equity: ${opening_equity:.2f}")
                
                # Get VIX and 200 SMA
                vix_level = get_vix_level()
                logger.info(f"📊  VIX: {vix_level:.1f}")
                
                sma_200_trend = check_200_sma_filter(SYMBOL)
                logger.info(f"📈  200 SMA: {sma_200_trend.upper()}")
                
                # Display config
                logger.info(f"⚙️  Config: {SYMBOL}, Risk={RISK_PER_TRADE:.2%}, Trades={trades_today}/{MAX_TRADES_PER_DAY}")
                
                # Session variables
                trade_count = 0
                entry_price = 0
                entry_time = None
                stop_loss = 0
                position_active = False
                position_type = None
                total_pnl = 0
                
                # Trading session loop
                while True:
                    # Check market still open
                    clock = api.get_clock()
                    if not clock.is_open:
                        logger.info("❌  Market closed")
                        break
                    
                    # Check day changed
                    if datetime.now().date() != current_date:
                        logger.info("📅  Day changed - resetting")
                        break
                    
                    # Check drawdown
                    current_equity = fetch_equity()
                    drawdown = (opening_equity - current_equity) / opening_equity
                    
                    if drawdown > MAX_DRAWDOWN:
                        logger.error(f"💸  Max drawdown: {drawdown:.2%}")
                        break
                    
                    # Market hours filter
                    if not should_trade_based_on_market_hours():
                        time.sleep(300)
                        continue
                    
                    # PDT check
                    if not pdt_allows_new_trade():
                        logger.error("🛑  PDT violation")
                        break
                    
                    # Get current price
                    current_price = get_current_price(SYMBOL)
                    if current_price == 0:
                        logger.warning("⚠️  No price, retrying...")
                        time.sleep(60)
                        continue
                    
                    # Manage existing position
                    if position_active:
                        # Time-based exit
                        if entry_time:
                            time_in_trade = (datetime.now() - entry_time).total_seconds()
                            if time_in_trade > MAX_HOLD_TIME:
                                logger.info(f"⏰  Max hold time ({MAX_HOLD_TIME//60} min)")
                                qty = current_position_qty(SYMBOL)
                                if qty > 0:
                                    submit_market_sell(SYMBOL, qty)
                                    position_active = False
                                    trade_count += 1
                                    if hasattr(scale_out_profit_taking, 'target_1_hit'):
                                        delattr(scale_out_profit_taking, 'target_1_hit')
                                    if hasattr(atr_based_trailing_stop, 'trailing_stop'):
                                        delattr(atr_based_trailing_stop, 'trailing_stop')
                                    time.sleep(POLL_INTERVAL)
                                    continue
                        
                        # Profit targets
                        if scale_out_profit_taking(SYMBOL, entry_price, current_price, stop_loss, position_type):
                            remaining_qty = current_position_qty(SYMBOL)
                            if remaining_qty == 0:
                                position_active = False
                                trade_pnl = (current_price - entry_price) * 100
                                total_pnl += trade_pnl
                                logger.info(f"✅  Position closed (PnL: ${trade_pnl:.2f})")
                                if hasattr(scale_out_profit_taking, 'target_1_hit'):
                                    delattr(scale_out_profit_taking, 'target_1_hit')
                                if hasattr(atr_based_trailing_stop, 'trailing_stop'):
                                    delattr(atr_based_trailing_stop, 'trailing_stop')
                                time.sleep(POLL_INTERVAL)
                                continue
                        
                        # Trailing stop
                        if atr_based_trailing_stop(SYMBOL, entry_price, current_price, stop_loss, position_type):
                            qty = current_position_qty(SYMBOL)
                            if qty > 0:
                                submit_market_sell(SYMBOL, qty)
                                position_active = False
                                trade_count += 1
                                logger.info(f"🛑  Stop hit")
                                if hasattr(scale_out_profit_taking, 'target_1_hit'):
                                    delattr(scale_out_profit_taking, 'target_1_hit')
                                if hasattr(atr_based_trailing_stop, 'trailing_stop'):
                                    delattr(atr_based_trailing_stop, 'trailing_stop')
                                time.sleep(POLL_INTERVAL)
                                continue
                    
                    # Daily trade limit
                    if trades_today >= MAX_TRADES_PER_DAY:
                        logger.info(f"📊  Daily limit ({MAX_TRADES_PER_DAY}) - monitoring only")
                        time.sleep(POLL_INTERVAL)
                        continue
                    
                    # Generate signal
                    signal, strength, signal_stop_loss = advanced_signal_generator(SYMBOL)
                    
                    # Get regime
                    bars = get_recent_bars(SYMBOL, 50)
                    if bars is not None:
                        regime = detect_market_regime(bars)
                    else:
                        regime = 'unknown'
                    
                    # Execute trades
                    if signal in ['buy', 'sell'] and not position_active:
                        buying_power = fetch_buying_power()
                        
                        position_size = calculate_position_size(current_equity, signal_stop_loss, current_price, regime)
                        
                        if buying_power >= position_size:
                            # Use limit orders
                            if USE_LIMIT_ORDERS and signal == 'buy':
                                bid, ask = get_bid_ask(SYMBOL)
                                limit_price = bid
                                execution_price = submit_limit_buy(SYMBOL, position_size, limit_price)
                            else:
                                execution_price = submit_market_buy(SYMBOL, position_size)
                            
                            if execution_price:
                                trade_count += 1
                                trades_today += 1
                                entry_price = execution_price
                                entry_time = datetime.now()
                                stop_loss = signal_stop_loss
                                position_active = True
                                position_type = 'long' if signal == 'buy' else 'short'
                                
                                risk_amount = abs(entry_price - stop_loss) / entry_price
                                logger.info(f"✅  {signal.upper()} executed")
                                logger.info(f"    Entry=${entry_price:.2f}, Stop=${stop_loss:.2f}, Risk={risk_amount:.2%}")
                                logger.info(f"    Regime={regime}, Strength={strength:.2f}, Trade #{trade_count} ({trades_today}/{MAX_TRADES_PER_DAY})")
                                
                                # Initialize trailing stop
                                atr_based_trailing_stop.trailing_stop = stop_loss
                        else:
                            logger.warning(f"⚠️  Insufficient buying power: ${buying_power:.2f} < ${position_size:.2f}")
                    
                    # Status display
                    position_status = f"{position_type.upper()}" if position_active else "FLAT"
                    current_time = clock.timestamp.strftime("%I:%M:%S %p")
                    hourly_trend = check_multiframe_confluence(SYMBOL)
                    
                    status_msg = f"⏱️  {current_time} | {position_status} | {regime.upper()}"
                    if position_active:
                        pnl_pct = ((current_price - entry_price) / entry_price) * 100 if position_type == 'long' else ((entry_price - current_price) / entry_price) * 100
                        status_msg += f" | PnL: {pnl_pct:+.2f}%"
                    status_msg += f" | H:{hourly_trend} | VIX:{vix_level:.1f} | {trades_today}/{MAX_TRADES_PER_DAY}"
                    
                    logger.info(status_msg)
                    time.sleep(POLL_INTERVAL)
                
                # End of trading day
                logger.info("🔚  Session ending...")
                close_all_positions()
                final_equity = fetch_equity()
                session_pnl = final_equity - opening_equity
                session_pnl_pct = (session_pnl / opening_equity) * 100 if opening_equity > 0 else 0
                logger.info(f"📊  Summary: {trade_count} trades")
                logger.info(f"💰  Final: ${final_equity:.2f} (PNL: ${session_pnl:+.2f}, {session_pnl_pct:+.2f}%)")
                logger.info("✅  Day complete. Waiting for next session...")
                
                # Sleep before checking again
                time.sleep(3600)
                
            except Exception as e:
                logger.error(f"💥  Session error: {e}")
                import traceback
                logger.error(traceback.format_exc())
                logger.info("⏳  Waiting 5 min before retry...")
                time.sleep(300)
                
    except KeyboardInterrupt:
        logger.info("🛑  User interrupt")
        close_all_positions()
    except Exception as e:
        logger.error(f"💥  Fatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        logger.info("🔚  Shutdown")

if __name__ == "__main__":
    main()