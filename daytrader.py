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
    "PDT_RULE": True
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

# Initialize Alpaca API
api = tradeapi.REST(
    os.getenv('APCA_API_KEY_ID'),
    os.getenv('APCA_API_SECRET_KEY'),
    os.getenv('APCA_API_BASE_URL'),
    api_version='v2'
)

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
            logger.info(f"🕒 Market opens at {format_market_time(next_open)}")
            logger.info(f"⏱️ Waiting {readable_time}...")
            
            # Sleep in smaller chunks to allow for graceful interruption
            while seconds_until_open > 0:
                sleep_time = min(60, seconds_until_open)  # Check every minute max
                time.sleep(sleep_time)
                seconds_until_open -= sleep_time
                
                # Update remaining time display periodically
                if sleep_time >= 60:
                    remaining_readable = seconds_to_human_readable(seconds_until_open)
                    logger.info(f"⏱️ {remaining_readable} remaining...")
        else:
            logger.info("✅ Market is open!")
    else:
        logger.info("✅ Market is open!")

def fetch_equity():
    """Fetch the current account equity."""
    try:
        account = api.get_account()
        return float(account.equity)
    except Exception as e:
        logger.error(f"❌ Failed to fetch equity: {e}")
        return 0.0

def fetch_buying_power():
    """Fetch the current buying power."""
    try:
        account = api.get_account()
        return float(account.buying_power)
    except Exception as e:
        logger.error(f"❌ Failed to fetch buying power: {e}")
        return 0.0

def get_day_trade_count():
    """Get the current day trade count."""
    try:
        account = api.get_account()
        return int(account.day_trade_count)
    except Exception as e:
        logger.error(f"❌ Failed to fetch day trade count: {e}")
        return 0

def submit_buy(symbol, notional):
    """Submit a buy order."""
    if notional < MIN_NOTIONAL:
        logger.warning(f"⚠️ Notional ${notional:.2f} < minimum ${MIN_NOTIONAL} - skipping.")
        return False
    
    try:
        api.submit_order(
            symbol=symbol,
            notional=round(notional, 2),
            side="buy",
            type="market",
            time_in_force="day"
        )
        logger.info(f"🟢 BUY ${notional:.2f} of {symbol}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to buy {symbol}: {e}")
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
        logger.info(f"🔴 SELL {qty} shares of {symbol}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to sell {symbol}: {e}")
        return False

def close_all_positions():
    """Close all open positions."""
    try:
        positions = api.list_positions()
        if not positions:
            logger.info("✅ No open positions to close.")
            return
        
        logger.warning("⚠️ Closing all open positions...")
        for pos in positions:
            submit_sell(pos.symbol, int(float(pos.qty)))
        logger.info("✅ All positions closed.")
    except Exception as e:
        logger.error(f"❌ Failed to close positions: {e}")

def get_recent_bars(symbol, limit=20):
    """Get recent bar data for a symbol."""
    try:
        bars = api.get_bars(
            symbol,
            "minute",
            limit=limit
        ).df
        return bars
    except Exception as e:
        logger.error(f"❌ Failed to fetch bars for {symbol}: {e}")
        return None

def ma_cross_signal(symbol):
    """Generate a moving average crossover signal."""
    bars = get_recent_bars(symbol, LONG_WINDOW + 5)
    if bars is None or len(bars) < LONG_WINDOW:
        return None
    
    closes = bars['close']
    short_ma = closes.rolling(window=SHORT_WINDOW).mean().iloc[-1]
    long_ma = closes.rolling(window=LONG_WINDOW).mean().iloc[-1]
    
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
        logger.error(f"❌ Failed to fetch positions: {e}")
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
            logger.error(f"🛑 PDT rule triggered: {day_trade_count} day-trades in rolling 5-day window")
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

# -----------------------------------------------------------------------------
# Main Trading Loop
# -----------------------------------------------------------------------------

def main():
    """Main trading function."""
    logger.info("🎯 Starting daytrader.py...")
    
    # Display current market status
    market_info = get_market_status()
    logger.info(f"🏛️ Market is currently {market_info['status'].upper()}")
    
    if market_info['status'] == 'closed':
        logger.info(f"📅 Next market {market_info['event_type']}: {format_market_time(market_info['next_event'])}")
    
    # Wait for market to open
    wait_until_market_open()
    
    # Record opening equity
    opening_equity = fetch_equity()
    if opening_equity == 0:
        logger.error("💥 No equity available. Exiting...")
        return
    
    logger.info(f"💰 Opening equity: ${opening_equity:.2f}")
    
    # Compute per-trade notional
    per_trade_notional = max(MIN_NOTIONAL, opening_equity * RISK_FRACTION)
    logger.info(f"🎯 Per-trade notional: ${per_trade_notional:.2f}")
    
    # Display trading parameters
    logger.info(f"⚙️ Trading configuration:")
    logger.info(f"    Symbol: {SYMBOL}")
    logger.info(f"    Risk per trade: {RISK_FRACTION:.1%}")
    logger.info(f"    Max drawdown: {MAX_DRAWDOWN:.1%}")
    logger.info(f"    MA Windows: {SHORT_WINDOW}/{LONG_WINDOW} minutes")
    logger.info(f"    PDT Rule enforced: {PDT_RULE}")
    
    # Main trading loop
    trade_count = 0
    try:
        while True:
            # Check if market is open
            clock = api.get_clock()
            if not clock.is_open:
                logger.info("❌ Market is closed. Exiting...")
                break
            
            # Check equity drop
            current_equity = fetch_equity()
            drawdown = (opening_equity - current_equity) / opening_equity
            
            if drawdown > MAX_DRAWDOWN:
                logger.error(f"💸 Maximum drawdown exceeded: {drawdown:.2%}. Stopping...")
                break
            
            # Check PDT rule
            if not pdt_allows_new_trade():
                logger.error("🛑 PDT rule violation. Stopping...")
                break
            
            # Generate trading signal
            signal = ma_cross_signal(SYMBOL)
            
            if signal == "buy":
                buying_power = fetch_buying_power()
                if buying_power >= per_trade_notional:
                    if submit_buy(SYMBOL, per_trade_notional):
                        trade_count += 1
                        logger.info(f"✅ Buy order executed for {SYMBOL} (Trade #{trade_count})")
                else:
                    logger.warning(f"⚠️ Insufficient buying power: ${buying_power:.2f}")
            
            elif signal == "sell":
                qty = current_position_qty(SYMBOL)
                if qty > 0:
                    if submit_sell(SYMBOL, qty):
                        trade_count += 1
                        logger.info(f"✅ Sell order executed for {SYMBOL} (Trade #{trade_count})")
                else:
                    logger.info("ℹ️ No position to sell")
            
            # Display current status
            current_time = clock.timestamp.strftime("%I:%M:%S %p")
            logger.info(f"⏱️ {current_time} - Waiting {POLL_INTERVAL} seconds for next check...")
            time.sleep(POLL_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("🛑 Script interrupted by user")
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
    finally:
        logger.info("🔚 Script ending. Closing any remaining positions...")
        close_all_positions()
        logger.info(f"📊 Session summary: {trade_count} trades executed")
        logger.info("✅ daytrader.py finished.")

if __name__ == "__main__":
    main()

