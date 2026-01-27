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
    "RISK_FRACTION": 0.02,
    "SHORT_WINDOW": 5,
    "LONG_WINDOW": 20,
    "MIN_NOTIONAL": 1.0,
    "POLL_INTERVAL": 30,
    "MAX_DRAWDOWN": 0.05,
    "PDT_RULE": True,
    "USE_TRAILING_STOP": True,
    "PROFIT_TARGETS": [0.03, 0.05],
    "VOLATILITY_ADJUSTMENT": True,
    "MARKET_HOURS_FILTER": True,
    "MULTI_INDICATOR": True
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
RISK_FRACTION = float(config["RISK_FRACTION"])
SHORT_WINDOW = int(config["SHORT_WINDOW"])
LONG_WINDOW = int(config["LONG_WINDOW"])
MIN_NOTIONAL = float(config["MIN_NOTIONAL"])
POLL_INTERVAL = int(config["POLL_INTERVAL"])
MAX_DRAWDOWN = float(config["MAX_DRAWDOWN"])
PDT_RULE = bool(config["PDT_RULE"])
USE_TRAILING_STOP = bool(config["USE_TRAILING_STOP"])
PROFIT_TARGETS = config["PROFIT_TARGETS"]
VOLATILITY_ADJUSTMENT = bool(config["VOLATILITY_ADJUSTMENT"])
MARKET_HOURS_FILTER = bool(config["MARKET_HOURS_FILTER"])
MULTI_INDICATOR = bool(config["MULTI_INDICATOR"])

# Initialize Alpaca API
api = tradeapi.REST(
    os.getenv('APCA_API_KEY_ID'),
    os.getenv('APCA_API_SECRET_KEY'),
    os.getenv('APCA_API_BASE_URL'),
    api_version='v2'
)

# -----------------------------------------------------------------------------
# Technical Analysis Functions (Pure Python)
# -----------------------------------------------------------------------------

def calculate_sma(data, window):
    """Calculate Simple Moving Average"""
    return data.rolling(window=window).mean()

def calculate_ema(data, window):
    """Calculate Exponential Moving Average"""
    return data.ewm(span=window, adjust=False).mean()

def calculate_rsi(data, window=14):
    """Calculate Relative Strength Index"""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(data, fast=12, slow=26, signal=9):
    """Calculate MACD"""
    ema_fast = calculate_ema(data, fast)
    ema_slow = calculate_ema(data, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    return macd_line, signal_line

def calculate_bollinger_bands(data, window=20, num_std=2):
    """Calculate Bollinger Bands"""
    sma = calculate_sma(data, window)
    std = data.rolling(window=window).std()
    upper_band = sma + (std * num_std)
    lower_band = sma - (std * num_std)
    return upper_band, sma, lower_band

def calculate_atr(high, low, close, window=14):
    """Calculate Average True Range"""
    high_low = high - low
    high_close_prev = abs(high - close.shift())
    low_close_prev = abs(low - close.shift())
    true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
    atr = true_range.rolling(window=window).mean()
    return atr

# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------

# Set up logging to daytrader.log in script directory
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
    """Convert seconds to human-readable format (hours, minutes, seconds)."""
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
    if secs > 0 and hours == 0:  # Only show seconds if less than an hour
        time_parts.append(f"{secs} second{'s' if secs != 1 else ''}")
    
    return " ".join(time_parts) if time_parts else "0 seconds"

def format_market_time(dt_obj):
    """Format datetime object to readable string."""
    return dt_obj.strftime("%Y-%m-%d %I:%M:%S %p %Z")

# -----------------------------------------------------------------------------
# Trading Functions
# -----------------------------------------------------------------------------

def wait_until_market_open():
    """Wait until the market opens."""
    clock = api.get_clock()
    now = clock.timestamp
    next_open = clock.next_open
    
    if not clock.is_open:
        seconds_until_open = (next_open - now).total_seconds()
        if seconds_until_open > 0:
            readable_time = seconds_to_human_readable(seconds_until_open)
            logger.info(f"🕒  Market opens at {format_market_time(next_open)}")
            logger.info(f"⏱️  Waiting {readable_time}...")
            
            # Sleep in smaller chunks to allow for graceful interruption
            while seconds_until_open > 0:
                sleep_time = min(60, seconds_until_open)  # Check every minute max
                time.sleep(sleep_time)
                seconds_until_open -= sleep_time
                
                # Update remaining time display periodically
                if sleep_time >= 60:
                    remaining_readable = seconds_to_human_readable(seconds_until_open)
                    logger.info(f"⏱️  {remaining_readable} remaining...")
        else:
            logger.info("✅  Market is open!")
    else:
        logger.info("✅  Market is open!")

def fetch_equity():
    """Fetch the current account equity."""
    try:
        account = api.get_account()
        return float(account.equity)
    except Exception as e:
        logger.error(f"❌  Failed to fetch equity: {e}")
        return 0.0

def fetch_buying_power():
    """Fetch the current buying power."""
    try:
        account = api.get_account()
        return float(account.buying_power)
    except Exception as e:
        logger.error(f"❌  Failed to fetch buying power: {e}")
        return 0.0

def get_day_trade_count():
    """Get the current day trade count."""
    try:
        account = api.get_account()
        return int(account.day_trade_count)
    except Exception as e:
        logger.error(f"❌  Failed to fetch day trade count: {e}")
        return 0

def submit_buy(symbol, notional):
    """Submit a buy order."""
    if notional < MIN_NOTIONAL:
        logger.warning(f"⚠️  Notional ${notional:.2f} < minimum ${MIN_NOTIONAL} - skipping.")
        return False
    
    try:
        api.submit_order(
            symbol=symbol,
            notional=round(notional, 2),
            side="buy",
            type="market",
            time_in_force="day"
        )
        logger.info(f"🟢  BUY ${notional:.2f} of {symbol}")
        return True
    except Exception as e:
        logger.error(f"❌  Failed to buy {symbol}: {e}")
        return False

def submit_sell(symbol, qty):
    """Submit a sell order."""
    try:
        api.submit_order(
            symbol=symbol,
            qty=qty,
            side="sell",
            type="market",
            time_in_force="day"
        )
        logger.info(f"🔴  SELL {qty} shares of {symbol}")
        return True
    except Exception as e:
        logger.error(f"❌  Failed to sell {symbol}: {e}")
        return False

def close_all_positions():
    """Close all open positions."""
    try:
        positions = api.list_positions()
        if not positions:
            logger.info("✅  No open positions to close.")
            return
        
        logger.warning("⚠️  Closing all open positions...")
        for pos in positions:
            submit_sell(pos.symbol, int(float(pos.qty)))
        logger.info("✅  All positions closed.")
    except Exception as e:
        logger.error(f"❌  Failed to close positions: {e}")

def get_recent_bars(symbol, limit=100):
    """Get recent bar data for a symbol."""
    try:
        timeframe = "minute" if limit <= 200 else "15Min"  # Use 15Min for larger requests
        bars = api.get_bars(
            symbol,
            timeframe,
            limit=limit
        ).df
        return bars
    except Exception as e:
        logger.error(f"❌  Failed to fetch bars for {symbol}: {e}")
        return None

def enhanced_signal_generator(symbol):
    """Multiple technical indicators for better signal confidence"""
    if not MULTI_INDICATOR:
        return simple_ma_cross_signal(symbol)
    
    bars = get_recent_bars(symbol, 100)
    if bars is None or len(bars) < 50:
        return None
    
    closes = bars['close']
    highs = bars['high']
    lows = bars['low']
    volumes = bars['volume']
    
    # Multiple indicators
    short_ma = calculate_sma(closes, SHORT_WINDOW).iloc[-1]
    long_ma = calculate_sma(closes, LONG_WINDOW).iloc[-1]
    rsi = calculate_rsi(closes, 14).iloc[-1]
    macd_line, signal_line = calculate_macd(closes)
    macd_current = macd_line.iloc[-1] if not pd.isna(macd_line.iloc[-1]) else 0
    macd_prev = macd_line.iloc[-2] if len(macd_line) > 1 else 0
    signal_current = signal_line.iloc[-1] if not pd.isna(signal_line.iloc[-1]) else 0
    signal_prev = signal_line.iloc[-2] if len(signal_line) > 1 else 0
    
    # Volume analysis
    volume_sma = calculate_sma(volumes, 20).iloc[-1]
    current_volume = volumes.iloc[-1]
    volume_ratio = current_volume / volume_sma if volume_sma > 0 else 1
    
    # Signal scoring system
    buy_score = 0
    sell_score = 0
    
    # Moving average crossover
    if short_ma > long_ma:
        buy_score += 2
    else:
        sell_score += 2
    
    # RSI momentum
    if rsi < 30:  # Oversold
        buy_score += 1
    elif rsi > 70:  # Overbought
        sell_score += 1
    
    # MACD signal
    if macd_current > signal_current and macd_prev <= signal_prev:
        buy_score += 1
    elif macd_current < signal_current and macd_prev >= signal_prev:
        sell_score += 1
    
    # Volume confirmation
    if volume_ratio > 1.2:  # High volume confirmation
        if buy_score > sell_score:
            buy_score += 1
        elif sell_score > buy_score:
            sell_score += 1
    
    # Minimum threshold for action
    if buy_score >= 3 and buy_score > sell_score:
        return "buy"
    elif sell_score >= 3 and sell_score > buy_score:
        return "sell"
    
    return None

def simple_ma_cross_signal(symbol):
    """Simple moving average crossover signal (original logic)"""
    bars = get_recent_bars(symbol, LONG_WINDOW + 5)
    if bars is None or len(bars) < LONG_WINDOW:
        return None
    
    closes = bars['close']
    short_ma = calculate_sma(closes, SHORT_WINDOW).iloc[-1]
    long_ma = calculate_sma(closes, LONG_WINDOW).iloc[-1]
    
    if short_ma > long_ma:
        return "buy"
    elif short_ma < long_ma:
        return "sell"
    else:
        return None

def current_position_qty(symbol):
    """Get the current position quantity for a symbol."""
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
    """Check if PDT rules allow a new trade."""
    if not PDT_RULE:
        return True
    
    equity = fetch_equity()
    day_trade_count = get_day_trade_count()
    
    # PDT rule: If equity < $25,000, max 3 day trades per 5 rolling days
    if equity < 25000:
        if day_trade_count >= 3:
            logger.error(f"🛑  PDT rule triggered: {day_trade_count} day-trades in rolling 5-day window")
            return False
    
    return True

def get_market_status():
    """Get current market status and next open/close times."""
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

def dynamic_position_sizing(opening_equity):
    """Adjust position size based on market volatility"""
    if not VOLATILITY_ADJUSTMENT:
        return max(MIN_NOTIONAL, opening_equity * RISK_FRACTION)
    
    bars = get_recent_bars(SYMBOL, 50)
    if bars is None or len(bars) < 20:
        return max(MIN_NOTIONAL, opening_equity * RISK_FRACTION)
    
    # Calculate recent volatility (ATR)
    highs = bars['high']
    lows = bars['low']
    closes = bars['close']
    atr = calculate_atr(highs, lows, closes, 14).iloc[-1]
    current_price = closes.iloc[-1]
    
    # Volatility adjustment - reduce position size in high volatility
    if current_price > 0:
        volatility_factor = max(0.5, min(2.0, 1.0 / (atr / current_price * 10)))
    else:
        volatility_factor = 1.0
    
    adjusted_notional = opening_equity * RISK_FRACTION * volatility_factor
    logger.info(f"📊  Volatility factor: {volatility_factor:.2f}, Adjusted notional: ${adjusted_notional:.2f}")
    return max(MIN_NOTIONAL, adjusted_notional)

def trailing_stop_loss(symbol, entry_price, current_price):
    """Implement trailing stop loss"""
    if not USE_TRAILING_STOP:
        return False
        
    position_qty = current_position_qty(symbol)
    if position_qty == 0:
        return False
    
    # Calculate current P&L
    current_pnl = (current_price - entry_price) / entry_price
    
    # Set trailing stop at 2% below highest price since entry
    if hasattr(trailing_stop_loss, 'highest_price'):
        trailing_stop_loss.highest_price = max(trailing_stop_loss.highest_price, current_price)
    else:
        trailing_stop_loss.highest_price = current_price
    
    stop_price = trailing_stop_loss.highest_price * 0.98  # 2% trailing stop
    
    if current_price <= stop_price and current_pnl > -0.01:  # Only stop if not already at big loss
        logger.info(f"🛑  Trailing stop triggered at ${stop_price:.2f}")
        submit_sell(symbol, position_qty)
        return True
    
    return False

def get_market_trend():
    """Determine overall market trend using SPY"""
    try:
        spy_bars = api.get_bars("SPY", "30Min", limit=50).df
        if len(spy_bars) < 20:
            return "neutral"
        
        spy_closes = spy_bars['close']
        short_trend = calculate_sma(spy_closes, 10).iloc[-1] > calculate_sma(spy_closes, 20).iloc[-1]
        medium_trend = calculate_sma(spy_closes, 20).iloc[-1] > calculate_sma(spy_closes, 50).iloc[-1]
        
        if short_trend and medium_trend:
            return "bullish"
        elif not short_trend and not medium_trend:
            return "bearish"
        else:
            return "neutral"
    except Exception as e:
        logger.warning(f"⚠️  Could not determine market trend: {e}")
        return "neutral"

def should_trade_based_on_market_hours():
    """Avoid trading during low-volume periods"""
    if not MARKET_HOURS_FILTER:
        return True
        
    now = datetime.now().time()
    
    # Avoid first/last 30 minutes (high volatility/uncertainty)
    market_open = datetime.strptime("09:30", "%H:%M").time()
    market_close = datetime.strptime("16:00", "%H:%M").time()
    
    open_buffer_start = datetime.strptime("10:00", "%H:%M").time()
    open_buffer_end = datetime.strptime("15:30", "%H:%M").time()
    
    if now < open_buffer_start or now > open_buffer_end:
        logger.info("⏳  Waiting for optimal trading hours (10AM-3:30PM)")
        return False
    
    return True

def take_profit_check(symbol, entry_price, current_price):
    """Implement profit-taking logic"""
    position_qty = current_position_qty(symbol)
    if position_qty == 0:
        return False
    
    profit_pct = (current_price - entry_price) / entry_price
    
    # Scale out strategy
    if profit_pct >= PROFIT_TARGETS[0] and len(PROFIT_TARGETS) > 1:  # First target
        partial_qty = position_qty // 2
        if partial_qty > 0:
            submit_sell(symbol, partial_qty)
            logger.info(f"✅  Taking partial profits at {profit_pct:.2%}")
            return True
    
    if profit_pct >= PROFIT_TARGETS[-1]:  # Final target
        submit_sell(symbol, position_qty)
        logger.info(f"🎯  Full profit taken at {profit_pct:.2%}")
        return True
    
    return False

def get_current_price(symbol):
    """Get current price for a symbol"""
    try:
        bars = api.get_bars(symbol, "minute", limit=5)
        if bars and len(bars) > 0:
            return bars[-1].c
        else:
            return 0
    except Exception as e:
        logger.error(f"❌  Failed to get current price for {symbol}: {e}")
        return 0

# -----------------------------------------------------------------------------
# Main Trading Loop
# -----------------------------------------------------------------------------

def main():
    """Main trading function."""
    logger.info("🎯  Starting enhanced daytrader.py...")
    
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
    
    # Compute per-trade notional
    per_trade_notional = dynamic_position_sizing(opening_equity)
    logger.info(f"🎯  Per-trade notional: ${per_trade_notional:.2f}")
    
    # Display trading parameters
    logger.info(f"⚙️  Trading configuration:")
    logger.info(f"    Symbol: {SYMBOL}")
    logger.info(f"    Risk per trade: {RISK_FRACTION:.1%}")
    logger.info(f"    Max drawdown: {MAX_DRAWDOWN:.1%}")
    logger.info(f"    MA Windows: {SHORT_WINDOW}/{LONG_WINDOW} minutes")
    logger.info(f"    PDT Rule enforced: {PDT_RULE}")
    logger.info(f"    Multi-indicator: {MULTI_INDICATOR}")
    logger.info(f"    Trailing stop: {USE_TRAILING_STOP}")
    logger.info(f"    Profit targets: {[f'{t:.1%}' for t in PROFIT_TARGETS]}")
    logger.info(f"    Volatility adjustment: {VOLATILITY_ADJUSTMENT}")
    logger.info(f"    Market hours filter: {MARKET_HOURS_FILTER}")
    
    # Main trading loop variables
    trade_count = 0
    entry_price = 0
    position_active = False
    
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
            
            # Enhanced market hours filter
            if not should_trade_based_on_market_hours():
                time.sleep(60)
                continue
            
            # Check market trend
            market_trend = get_market_trend()
            if market_trend == "bearish":
                logger.info("📉  Bearish market detected - reducing activity")
                time.sleep(POLL_INTERVAL * 2)  # Longer wait
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
            
            # Update dynamic position sizing based on current equity
            per_trade_notional = dynamic_position_sizing(current_equity)
            
            # Manage existing position
            if position_active:
                # Check profit taking
                if take_profit_check(SYMBOL, entry_price, current_price):
                    position_active = False
                    trade_count += 1
                    time.sleep(POLL_INTERVAL)
                    continue
                
                # Check trailing stop loss
                if trailing_stop_loss(SYMBOL, entry_price, current_price):
                    position_active = False
                    trade_count += 1
                    time.sleep(POLL_INTERVAL)
                    continue
            
            # Generate trading signal
            signal = enhanced_signal_generator(SYMBOL)
            
            # Execute trades based on signal
            if signal == "buy" and not position_active:
                buying_power = fetch_buying_power()
                if buying_power >= per_trade_notional:
                    if submit_buy(SYMBOL, per_trade_notional):
                        trade_count += 1
                        entry_price = current_price
                        position_active = True
                        logger.info(f"✅  Buy order executed for {SYMBOL} at ${current_price:.2f} (Trade #{trade_count})")
                else:
                    logger.warning(f"⚠️  Insufficient buying power: ${buying_power:.2f}")
            
            elif signal == "sell" and position_active:
                qty = current_position_qty(SYMBOL)
                if qty > 0:
                    if submit_sell(SYMBOL, qty):
                        trade_count += 1
                        position_active = False
                        logger.info(f"✅  Sell order executed for {SYMBOL} at ${current_price:.2f} (Trade #{trade_count})")
                else:
                    logger.info("ℹ️  No position to sell")
            
            # Display current status
            position_status = "LONG" if position_active else "FLAT"
            current_time = clock.timestamp.strftime("%I:%M:%S %p")
            logger.info(f"⏱️  {current_time} - {position_status} - Waiting {POLL_INTERVAL} seconds...")
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
        pnl = final_equity - opening_equity
        pnl_pct = (pnl / opening_equity) * 100 if opening_equity > 0 else 0
        logger.info(f"📊  Session summary: {trade_count} trades executed")
        logger.info(f"💰  Final equity: ${final_equity:.2f} (PNL: ${pnl:.2f}, {pnl_pct:.2f}%)")
        logger.info("✅  daytrader.py finished.")

if __name__ == "__main__":
    main()

