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

# Default configuration
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
    "MIN_SIGNAL_STRENGTH": 0.75,
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
    "USE_EMA": True
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
    # Calculate Simple Moving Average
    return data.rolling(window=window).mean()

def calculate_ema(data, window):
    # Calculate Exponential Moving Average
    return data.ewm(span=window, adjust=False).mean()

def calculate_rsi(data, window=14):
    # Calculate Relative Strength Index
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_atr(high, low, close, window=14):
    # Calculate Average True Range
    high_low = high - low
    high_close_prev = abs(high - close.shift())
    low_close_prev = abs(low - close.shift())
    true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
    atr = true_range.rolling(window=window).mean()
    return atr

def calculate_adx(high, low, close, window=14):
    # Calculate Average Directional Index (ADX) for trend strength
    # Calculate True Range
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=window).mean()
    
    # Calculate Directional Movement
    up_move = high - high.shift()
    down_move = low.shift() - low
    
    plus_dm = pd.Series(0.0, index=close.index)
    minus_dm = pd.Series(0.0, index=close.index)
    
    plus_dm[(up_move > down_move) & (up_move > 0)] = up_move
    minus_dm[(down_move > up_move) & (down_move > 0)] = down_move
    
    # Smooth the directional indicators
    plus_di = 100 * (plus_dm.rolling(window=window).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=window).mean() / atr)
    
    # Calculate DX and ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=window).mean()
    
    return adx, plus_di, minus_di

def calculate_bollinger_bands(close, window=20, num_std=2):
    # Calculate Bollinger Bands for mean reversion
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
        return True  # Default to True if no volume data
    
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
    
    # Calculate ADX for trend strength
    adx, plus_di, minus_di = calculate_adx(highs, lows, closes, 14)
    current_adx = adx.iloc[-1]
    
    # Calculate volatility percentile
    atr = calculate_atr(highs, lows, closes, 14)
    current_atr = atr.iloc[-1]
    atr_percentile = (atr <= current_atr).sum() / len(atr) * 100
    
    # Determine regime
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
        # Get hourly data
        hourly_bars = api.get_bars(symbol, "1Hour", limit=50).df
        if len(hourly_bars) < 50:
            return 'neutral'
        
        closes = hourly_bars['close']
        
        # Calculate hourly EMAs
        if USE_EMA:
            ema_short = calculate_ema(closes, 20)
            ema_long = calculate_ema(closes, 50)
        else:
            ema_short = calculate_sma(closes, 20)
            ema_long = calculate_sma(closes, 50)
        
        current_short = ema_short.iloc[-1]
        current_long = ema_long.iloc[-1]
        current_price = closes.iloc[-1]
        
        # Determine hourly trend
        if current_short > current_long and current_price > current_short:
            return 'bullish'
        elif current_short < current_long and current_price < current_short:
            return 'bearish'
        else:
            return 'neutral'
            
    except Exception as e:
        logger.warning(f"⚠️  Could not check multiframe confluence: {e}")
        return 'neutral'

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
    # Convert seconds to human-readable format (hours, minutes, seconds).
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
    # Format datetime object to readable string.
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
# Enhanced Trading Functions
# -----------------------------------------------------------------------------

def enhanced_backtest_strategy():
    # Comprehensive backtest with improved strategy
    logger.info("📊 Running enhanced backtest with improved strategy...")
    
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=BACKTEST_DAYS)
        
        bars = api.get_bars(SYMBOL, "15Min", start=start_date.isoformat(), 
                           end=end_date.isoformat()).df
        if len(bars) < 100:
            logger.warning("⚠️  Insufficient data for backtest")
            return True
        
        # Enhanced backtest with new strategy
        closes = bars['close']
        highs = bars['high']
        lows = bars['low']
        
        # Calculate indicators
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
        
        # Track performance
        initial_balance = 10000
        balance = initial_balance
        position = 0
        entry_price = 0
        entry_time = None
        stop_loss = 0
        trades = []
        winning_trades = 0
        
        for i in range(max(SHORT_WINDOW, LONG_WINDOW, BB_WINDOW, 20), len(bars)):
            current_price = closes.iloc[i]
            current_time = bars.index[i]
            current_adx = adx.iloc[i]
            current_rsi = rsi.iloc[i]
            current_atr = atr.iloc[i]
            
            # Determine regime
            regime = 'trend' if current_adx > ADX_THRESHOLD else 'range'
            
            # Generate signals based on regime
            if regime == 'trend':
                # Trend-following logic
                ma_signal = 1 if short_ma.iloc[i] > long_ma.iloc[i] else -1
                rsi_signal = 1 if current_rsi < 65 else (-1 if current_rsi > 35 else 0)
                combined_signal = ma_signal + (rsi_signal * 0.3)
            else:
                # Mean reversion logic (Bollinger Bands)
                if current_price <= lower_bb.iloc[i] and current_rsi < 30:
                    combined_signal = 1.5  # Strong buy
                elif current_price >= upper_bb.iloc[i] and current_rsi > 70:
                    combined_signal = -1.5  # Strong sell
                else:
                    combined_signal = 0
            
            # Check volume (simplified for backtest)
            volume_ok = True
            
            # Enter position
            if position == 0 and abs(combined_signal) >= 1.2 and volume_ok:
                position = 1 if combined_signal > 0 else -1
                entry_price = apply_slippage(current_price, combined_signal > 0)
                entry_time = current_time
                
                # Set ATR-based stop loss
                stop_distance = current_atr * ATR_STOP_MULTIPLIER
                if position > 0:
                    stop_loss = entry_price - stop_distance
                else:
                    stop_loss = entry_price + stop_distance
                
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
                
                # Stop loss check
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
                
                # Profit target exits
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
        
        # Calculate additional metrics
        winning_pnl = sum([t['pnl'] for t in trades if 'pnl' in t and t['pnl'] > 0])
        losing_pnl = sum([abs(t['pnl']) for t in trades if 'pnl' in t and t['pnl'] < 0])
        profit_factor = winning_pnl / losing_pnl if losing_pnl > 0 else 0
        
        logger.info(f"📈 Enhanced Backtest Results:")
        logger.info(f"   Total trades: {total_trades}")
        logger.info(f"   Win rate: {win_rate:.1%}")
        logger.info(f"   Total return: {total_return:.1%}")
        logger.info(f"   Profit factor: {profit_factor:.2f}")
        logger.info(f"   Final balance: ${balance:.2f}")
        
        if total_trades < 5:
            logger.warning("⚠️  Very few trades generated - consider adjusting parameters")
            return True
        
        if win_rate < 0.35:
            logger.warning("⚠️  Low win rate in backtest - strategy may need optimization")
            return True
        
        if profit_factor < 1.0:
            logger.warning("⚠️  Profit factor < 1.0 - losing more than winning")
            return True
            
        return True
        
    except Exception as e:
        logger.warning(f"⚠️  Backtest failed: {e}")
        return True

def enhanced_signal_generator(symbol):
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
    
    # Volume confirmation
    volume_ok = check_volume_confirmation(bars)
    if not volume_ok:
        return None, 0, 0
    
    # Multi-timeframe filter
    hourly_trend = check_multiframe_confluence(symbol)
    
    # Detect regime
    regime = detect_market_regime(bars)
    
    # Avoid low volatility regimes
    if regime == 'low_vol':
        logger.info("📉  Low volatility regime detected - avoiding trade")
        return None, 0, 0
    
    # Initialize signal
    signal = None
    signal_strength = 0
    stop_loss = 0
    
    # TREND REGIME: Trend-following with pullbacks
    if regime == 'trend':
        if current_adx > ADX_THRESHOLD:
            # Bullish trend with pullback
            if short_ma > long_ma and current_price < short_ma and rsi < 50:
                if hourly_trend in ['bullish', 'neutral']:
                    signal = 'buy'
                    signal_strength = min(1.0, (current_adx / 40) * 0.7 + 0.3)
                    stop_loss = current_price - (atr * ATR_STOP_MULTIPLIER)
            
            # Bearish trend with pullback
            elif short_ma < long_ma and current_price > short_ma and rsi > 50:
                if hourly_trend in ['bearish', 'neutral']:
                    signal = 'sell'
                    signal_strength = min(1.0, (current_adx / 40) * 0.7 + 0.3)
                    stop_loss = current_price + (atr * ATR_STOP_MULTIPLIER)
    
    # RANGE REGIME: Mean reversion (Bollinger Bands)
    elif regime == 'range':
        bb_width = (upper_bb.iloc[-1] - lower_bb.iloc[-1]) / middle_bb.iloc[-1]
        
        # Oversold at lower band
        if current_price <= lower_bb.iloc[- 1] and rsi < 30:
            if hourly_trend != 'bearish':
                signal = 'buy'
                signal_strength = 0.8
                stop_loss = current_price - (atr * ATR_STOP_MULTIPLIER)
        
        # Overbought at upper band
        elif current_price >= upper_bb.iloc[-1] and rsi > 70:
            if hourly_trend != 'bullish':
                signal = 'sell'
                signal_strength = 0.8
                stop_loss = current_price + (atr * ATR_STOP_MULTIPLIER)
    
    # HIGH VOL REGIME: Reduce position sizing (handled elsewhere)
    elif regime == 'high_vol':
        # Still generate signals but will reduce position size
        if short_ma > long_ma and rsi < 40:
            if hourly_trend in ['bullish', 'neutral']:
                signal = 'buy'
                signal_strength = 0.6
                stop_loss = current_price - (atr * ATR_STOP_MULTIPLIER * 1.5)
        elif short_ma < long_ma and rsi > 60:
            if hourly_trend in ['bearish', 'neutral']:
                signal = 'sell'
                signal_strength = 0.6
                stop_loss = current_price + (atr * ATR_STOP_MULTIPLIER * 1.5)
    
    # Check minimum signal strength
    if signal_strength < MIN_SIGNAL_STRENGTH:
        return None, signal_strength, 0
    
    return signal, signal_strength, stop_loss

def wait_until_market_open():
    # Wait until the market opens.
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
    # Fetch the current account equity.
    try:
        account = api.get_account()
        return float(account.equity)
    except Exception as e:
        logger.error(f"❌  Failed to fetch equity: {e}")
        return 0.0

def fetch_buying_power():
    # Fetch the current buying power.
    try:
        account = api.get_account()
        return float(account.buying_power)
    except Exception as e:
        logger.error(f"❌  Failed to fetch buying power: {e}")
        return 0.0

def get_day_trade_count():
    # Get the current day trade count.
    try:
        account = api.get_account()
        return int(account.day_trade_count)
    except Exception as e:
        logger.error(f"❌  Failed to fetch day trade count: {e}")
        return 0

def submit_limit_buy(symbol, notional, limit_price):
    # Submit a limit buy order
    if notional < MIN_NOTIONAL:
        logger.warning(f"⚠️  Notional ${notional:.2f} < minimum ${MIN_NOTIONAL} - skipping.")
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
        
        logger.info(f"🟢  LIMIT BUY order submitted: {shares} shares of {symbol} @ ${limit_price:.2f}")
        
        # Wait for fill or timeout
        start_time = time.time()
        while (time.time() - start_time) < LIMIT_ORDER_TIMEOUT:
            order_status = api.get_order(order.id)
            if order_status.status == 'filled':
                filled_price = float(order_status.filled_avg_price)
                logger.info(f"✅  Limit buy FILLED @ ${filled_price:.2f}")
                return filled_price
            elif order_status.status in ['cancelled', 'expired', 'rejected']:
                logger.warning(f"⚠️  Limit order {order_status.status}")
                return False
            time.sleep(2)
        
        # Timeout - cancel and use market order
        logger.warning("⏱️  Limit order timeout - switching to market order")
        api.cancel_order(order.id)
        return submit_market_buy(symbol, notional)
        
    except Exception as e:
        logger.error(f"❌  Failed to submit limit buy: {e}")
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
        logger.info(f"🟢  MARKET BUY {shares} shares of {symbol} at ~${execution_price:.2f}")
        return execution_price
    except Exception as e:
        logger.error(f"❌  Failed to buy {symbol}: {e}")
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
        
        logger.info(f"🔴  LIMIT SELL order submitted: {qty} shares of {symbol} @ ${limit_price:.2f}")
        
        # Wait for fill or timeout
        start_time = time.time()
        while (time.time() - start_time) < LIMIT_ORDER_TIMEOUT:
            order_status = api.get_order(order.id)
            if order_status.status == 'filled':
                filled_price = float(order_status.filled_avg_price)
                logger.info(f"✅  Limit sell FILLED @ ${filled_price:.2f}")
                return filled_price
            elif order_status.status in ['cancelled', 'expired', 'rejected']:
                logger.warning(f"⚠️  Limit order {order_status.status}")
                return False
            time.sleep(2)
        
        # Timeout - cancel and use market order
        logger.warning("⏱️  Limit order timeout - switching to market order")
        api.cancel_order(order.id)
        return submit_market_sell(symbol, qty)
        
    except Exception as e:
        logger.error(f"❌  Failed to submit limit sell: {e}")
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
        logger.info(f"🔴  MARKET SELL {qty} shares of {symbol} at ~${execution_price:.2f}")
        return execution_price
    except Exception as e:
        logger.error(f"❌  Failed to sell {symbol}: {e}")
        return False

def close_all_positions():
    # Close all open positions.
    try:
        positions = api.list_positions()
        if not positions:
            logger.info("✅  No open positions to close.")
            return
        
        logger.warning("⚠️  Closing all open positions...")
        for pos in positions:
            submit_market_sell(pos.symbol, int(float(pos.qty)))
        logger.info("✅  All positions closed.")
    except Exception as e:
        logger.error(f"❌  Failed to close positions: {e}")

def get_recent_bars(symbol, limit=100):
    # Get recent bar data for a symbol.
    try:
        timeframe = "15Min"
        bars = api.get_bars(
            symbol,
            timeframe,
            limit=limit
        ).df
        return bars
    except Exception as e:
        logger.error(f"❌  Failed to fetch bars for {symbol}: {e}")
        return None

def current_position_qty(symbol):
    # Get the current position quantity for a symbol.
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
    # Check if PDT rules allow a new trade.
    if not PDT_RULE:
        return True
    
    equity = fetch_equity()
    day_trade_count = get_day_trade_count()
    
    if equity < 25000:
        if day_trade_count >= 3:
            logger.error(f"🛑  PDT rule triggered: {day_trade_count} day-trades in rolling 5-day window")
            return False
    
    return True

def get_market_status():
    # Get current market status and next open/close times.
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
    
    # Adjust for high volatility regime
    if regime == 'high_vol':
        risk_amount *= 0.5
        logger.info(f"📊  High volatility - reducing position size by 50%")
    
    stop_distance = abs(entry_price - stop_loss)
    if stop_distance == 0:
        return MIN_NOTIONAL
    
    position_size = risk_amount / stop_distance * entry_price
    
    # Ensure minimum notional
    position_size = max(MIN_NOTIONAL, position_size)
    
    logger.info(f"💰  Position sizing: Risk=${risk_amount:.2f}, Stop=${stop_distance:.2f}, Size=${position_size:.2f}")
    
    return position_size

def should_trade_based_on_market_hours():
    # Avoid trading during low-volume periods
    if not MARKET_HOURS_FILTER:
        return True
        
    now = datetime.now().time()
    
    # Avoid first 30 minutes
    market_open = datetime.strptime("09:30", "%H:%M").time()
    open_buffer_end = datetime.strptime("10:00", "%H:%M").time()
    
    # Avoid last 30 minutes
    market_close = datetime.strptime("16:00", "%H:%M").time()
    close_buffer_start = datetime.strptime("15:30", "%H:%M").time()
    
    if now < open_buffer_end:
        logger.info("⏳  Waiting for opening volatility to settle (10:00 AM)")
        return False
    
    if now >= close_buffer_start:
        logger.info("⏳  Avoiding late-day trading (after 3:30 PM)")
        return False
    
    return True

def atr_based_trailing_stop(symbol, entry_price, current_price, stop_loss, position_type='long'):
    # Implement ATR-based trailing stop loss
    if not USE_TRAILING_STOP:
        # Just check fixed stop
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
        # Update trailing stop as price rises
        new_stop = current_price - trail_distance
        if new_stop > atr_based_trailing_stop.trailing_stop:
            atr_based_trailing_stop.trailing_stop = new_stop
            logger.info(f"📈  Trailing stop updated to ${new_stop:.2f}")
        
        # Check if stop hit
        if current_price <= atr_based_trailing_stop.trailing_stop:
            logger.info(f"🛑  Trailing stop hit at ${current_price:.2f}")
            return True
    
    elif position_type == 'short':
        # Update trailing stop as price falls
        new_stop = current_price + trail_distance
        if new_stop < atr_based_trailing_stop.trailing_stop:
            atr_based_trailing_stop.trailing_stop = new_stop
            logger.info(f"📉  Trailing stop updated to ${new_stop:.2f}")
        
        # Check if stop hit
        if current_price >= atr_based_trailing_stop.trailing_stop:
            logger.info(f"🛑  Trailing stop hit at ${current_price:.2f}")
            return True
    
    return False

def scale_out_profit_taking(symbol, entry_price, current_price, stop_loss, position_type='long'):
    # Scale out of position at profit targets
    position_qty = current_position_qty(symbol)
    if position_qty == 0:
        return False
    
    # Calculate R (risk amount)
    risk_distance = abs(entry_price - stop_loss)
    
    if position_type == 'long':
        profit_pct = (current_price - entry_price) / entry_price
        profit_in_r = (current_price - entry_price) / risk_distance if risk_distance > 0 else 0
    else:
        profit_pct = (entry_price - current_price) / entry_price
        profit_in_r = (entry_price - current_price) / risk_distance if risk_distance > 0 else 0
    
    # First target: 1.5R - scale out 50%
    if profit_in_r >= PROFIT_TARGET_1:
        if not hasattr(scale_out_profit_taking, 'target_1_hit'):
            scale_out_profit_taking.target_1_hit = True
            partial_qty = position_qty // 2
            
            if partial_qty > 0:
                # Use limit order at current ask/bid
                if USE_LIMIT_ORDERS:
                    limit_price = current_price if position_type == 'long' else current_price
                    submit_limit_sell(symbol, partial_qty, limit_price)
                else:
                    submit_market_sell(symbol, partial_qty)
                
                logger.info(f"🎯  Target 1 hit ({PROFIT_TARGET_1}R) - Scaled out 50% at ${current_price:.2f}")
                
                # Move stop to breakeven
                atr_based_trailing_stop.trailing_stop = entry_price
                logger.info(f"🔒  Stop moved to breakeven: ${entry_price:.2f}")
                return True
    
    # Second target: 3R - close remaining position
    if profit_in_r >= PROFIT_TARGET_2:
        remaining_qty = current_position_qty(symbol)
        if remaining_qty > 0:
            if USE_LIMIT_ORDERS:
                limit_price = current_price
                submit_limit_sell(symbol, remaining_qty, limit_price)
            else:
                submit_market_sell(symbol, remaining_qty)
            
            logger.info(f"🎯🎯  Target 2 hit ({PROFIT_TARGET_2}R) - Full exit at ${current_price:.2f}")
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
        logger.error(f"❌  Failed to get current price for {symbol}: {e}")
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
# Main Trading Loop
# -----------------------------------------------------------------------------

def main():
    logger.info("🚀  Starting daytrader.py...")
    
    # Run enhanced backtest first
    if not enhanced_backtest_strategy():
        logger.error("❌  Backtest failed. Exiting...")
        return
    
    # Display current market status
    market_info = get_market_status()
    logger.info(f"🏛️  Market is currently {market_info['status'].upper()}")
    
    if market_info['status'] == 'closed':
        logger.info(f"📅  Next market {market_info['event_type']}: {format_market_time(market_info['next_event'])}")
    
    # Wait for market to open
    wait_until_market_open()
    
    # Record opening equity
    opening_equity = fetch_equity()
    if opening_equity == 0:
        logger.error("💥  No equity available. Exiting...")
        return
    
    logger.info(f"💰  Opening equity: ${opening_equity:.2f}")
    
    # Display enhanced trading parameters
    logger.info(f"⚙️  ENHANCED trading configuration:")
    logger.info(f"    Symbol: {SYMBOL}")
    logger.info(f"    Risk per trade: {RISK_PER_TRADE:.2%} (ATR-based stops)")
    logger.info(f"    MA Windows: {SHORT_WINDOW}/{LONG_WINDOW} ({'EMA' if USE_EMA else 'SMA'})")
    logger.info(f"    Poll interval: {POLL_INTERVAL}s ({POLL_INTERVAL//60} min)")
    logger.info(f"    Signal strength threshold: {MIN_SIGNAL_STRENGTH:.1%}")
    logger.info(f"    Profit targets: {PROFIT_TARGET_1}R / {PROFIT_TARGET_2}R")
    logger.info(f"    ATR stop multiplier: {ATR_STOP_MULTIPLIER}x")
    logger.info(f"    Max hold time: {MAX_HOLD_TIME//60} minutes")
    logger.info(f"    Limit orders: {USE_LIMIT_ORDERS}")
    logger.info(f"    Multi-timeframe filter: {MULTIFRAME_FILTER}")
    logger.info(f"    Regime detection: {REGIME_DETECTION}")
    
    # Main trading loop variables
    trade_count = 0
    entry_price = 0
    entry_time = None
    stop_loss = 0
    position_active = False
    position_type = None
    total_pnl = 0
    
    # Reset function attributes
    if hasattr(scale_out_profit_taking, 'target_1_hit'):
        delattr(scale_out_profit_taking, 'target_1_hit')
    if hasattr(atr_based_trailing_stop, 'trailing_stop'):
        delattr(atr_based_trailing_stop, 'trailing_stop')
    
    try:
        while True:
            # Check if market is open
            clock = api.get_clock()
            if not clock.is_open:
                logger.info("❌  Market is closed. Exiting...")
                break
            
            # Check equity drop
            current_equity = fetch_equity()
            drawdown = (opening_equity - current_equity) / opening_equity
            
            if drawdown > MAX_DRAWDOWN:
                logger.error(f"💸  Maximum drawdown exceeded: {drawdown:.2%}. Stopping...")
                break
            
            # Market hours filter
            if not should_trade_based_on_market_hours():
                time.sleep(POLL_INTERVAL)
                continue
            
            # Check PDT rule
            if not pdt_allows_new_trade():
                logger.error("🛑  PDT rule violation. Stopping...")
                break
            
            # Get current price
            current_price = get_current_price(SYMBOL)
            if current_price == 0:
                logger.warning("⚠️  Could not fetch current price, skipping iteration")
                time.sleep(POLL_INTERVAL)
                continue
            
            # Manage existing position
            if position_active:
                # Time-based exit (max hold time)
                if entry_time:
                    time_in_trade = (datetime.now() - entry_time).total_seconds()
                    if time_in_trade > MAX_HOLD_TIME:
                        logger.info(f"⏰  Max hold time reached ({MAX_HOLD_TIME//60} min) - exiting position")
                        qty = current_position_qty(SYMBOL)
                        if qty > 0:
                            submit_market_sell(SYMBOL, qty)
                            position_active = False
                            trade_count += 1
                            # Reset function attributes
                            if hasattr(scale_out_profit_taking, 'target_1_hit'):
                                delattr(scale_out_profit_taking, 'target_1_hit')
                            if hasattr(atr_based_trailing_stop, 'trailing_stop'):
                                delattr(atr_based_trailing_stop, 'trailing_stop')
                            time.sleep(POLL_INTERVAL)
                            continue
                
                # Check profit targets (scale out strategy)
                if scale_out_profit_taking(SYMBOL, entry_price, current_price, stop_loss, position_type):
                    # Check if fully closed
                    remaining_qty = current_position_qty(SYMBOL)
                    if remaining_qty == 0:
                        position_active = False
                        trade_pnl = (current_price - entry_price) * 100  # Approximate
                        total_pnl += trade_pnl
                        logger.info(f"✅  Position fully closed (Approx PnL: ${trade_pnl:.2f})")
                        # Reset function attributes
                        if hasattr(scale_out_profit_taking, 'target_1_hit'):
                            delattr(scale_out_profit_taking, 'target_1_hit')
                        if hasattr(atr_based_trailing_stop, 'trailing_stop'):
                            delattr(atr_based_trailing_stop, 'trailing_stop')
                        time.sleep(POLL_INTERVAL)
                        continue
                
                # Check trailing stop loss
                if atr_based_trailing_stop(SYMBOL, entry_price, current_price, stop_loss, position_type):
                    qty = current_position_qty(SYMBOL)
                    if qty > 0:
                        submit_market_sell(SYMBOL, qty)
                        position_active = False
                        trade_count += 1
                        logger.info(f"🛑  Stop loss triggered - position closed")
                        # Reset function attributes
                        if hasattr(scale_out_profit_taking, 'target_1_hit'):
                            delattr(scale_out_profit_taking, 'target_1_hit')
                        if hasattr(atr_based_trailing_stop, 'trailing_stop'):
                            delattr(atr_based_trailing_stop, 'trailing_stop')
                        time.sleep(POLL_INTERVAL)
                        continue
            
            # Generate trading signal (ENHANCED)
            signal, strength, signal_stop_loss = enhanced_signal_generator(SYMBOL)
            
            # Get market regime for logging
            bars = get_recent_bars(SYMBOL, 50)
            if bars is not None:
                regime = detect_market_regime(bars)
            else:
                regime = 'unknown'
            
            # Execute trades based on signal
            if signal in ['buy', 'sell'] and not position_active:
                buying_power = fetch_buying_power()
                
                # Calculate position size based on risk and stop loss
                position_size = calculate_position_size(current_equity, signal_stop_loss, current_price, regime)
                
                if buying_power >= position_size:
                    # Use limit orders for better execution
                    if USE_LIMIT_ORDERS and signal == 'buy':
                        bid, ask = get_bid_ask(SYMBOL)
                        limit_price = bid  # Buy at bid for better fill
                        execution_price = submit_limit_buy(SYMBOL, position_size, limit_price)
                    else:
                        execution_price = submit_market_buy(SYMBOL, position_size)
                    
                    if execution_price:
                        trade_count += 1
                        entry_price = execution_price
                        entry_time = datetime.now()
                        stop_loss = signal_stop_loss
                        position_active = True
                        position_type = 'long' if signal == 'buy' else 'short'
                        
                        risk_amount = abs(entry_price - stop_loss) / entry_price
                        logger.info(f"✅  {signal.upper()} order executed")
                        logger.info(f"    Entry: ${entry_price:.2f}, Stop: ${stop_loss:.2f}, Risk: {risk_amount:.2%}")
                        logger.info(f"    Regime: {regime}, Strength: {strength:.2f}, Trade #{trade_count}")
                        
                        # Initialize trailing stop
                        atr_based_trailing_stop.trailing_stop = stop_loss
                else:
                    logger.warning(f"⚠️  Insufficient buying power: ${buying_power:.2f} < ${position_size:.2f}")
            
            # Display current status
            position_status = f"{position_type.upper()}" if position_active else "FLAT"
            current_time = clock.timestamp.strftime("%I:%M:%S %p")
            hourly_trend = check_multiframe_confluence(SYMBOL)
            
            status_msg = f"⏱️  {current_time} | {position_status} | Regime: {regime.upper()}"
            if position_active:
                pnl_pct = ((current_price - entry_price) / entry_price) * 100 if position_type == 'long' else ((entry_price - current_price) / entry_price) * 100
                status_msg += f" | PnL: {pnl_pct:+.2f}%"
            status_msg += f" | H-Trend: {hourly_trend} | Next poll: {POLL_INTERVAL//60}m"
            
            logger.info(status_msg)
            time.sleep(POLL_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("🛑  Script interrupted by user")
    except Exception as e:
        logger.error(f"💥  Unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        logger.info("🔚  Script ending. Closing any remaining positions...")
        close_all_positions()
        final_equity = fetch_equity()
        session_pnl = final_equity - opening_equity
        session_pnl_pct = (session_pnl / opening_equity) * 100 if opening_equity > 0 else 0
        logger.info(f"📊  Session summary: {trade_count} trades executed")
        logger.info(f"💰  Final equity: ${final_equity:.2f} (PNL: ${session_pnl:+.2f}, {session_pnl_pct:+.2f}%)")
        logger.info("✅  ENHANCED daytrader.py finished.")

if __name__ == "__main__":
    main()
