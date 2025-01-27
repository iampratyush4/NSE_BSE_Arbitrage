import asyncio
import time
import logging
import configparser
from py5paisa import FivePaisaClient, WebSocket
from py5paisa.order import Order, OrderType, Exchange
from login_manager import login

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load config
config = configparser.ConfigParser()
config.read("config.ini")
ARBITRAGE_THRESHOLD = float(config["TRADE"]["ArbitrageThreshold"])
DATA_FRESHNESS_SEC = float(config.get("TRADE", "DataFreshnessSec", fallback=2))  # New config parameter

# Parse stock pairs (NSE:BSE)
stock_pairs = [pair.strip().split(":") for pair in config["STOCKS"]["StockList"].split(",")]
STOCKS = [{"nse": int(nse), "bse": int(bse)} for nse, bse in stock_pairs]

# Create token map and scrip codes list
token_map = {}  # Maps token to (stock_index, exchange)
SCRIP_CODES = []
for idx, stock in enumerate(STOCKS):
    SCRIP_CODES.extend([stock["nse"], stock["bse"]])
    token_map[stock["nse"]] = (idx, "NSE")
    token_map[stock["bse"]] = (idx, "BSE")

MAX_VERIFY_RETRIES = int(config.get("TRADE", "MaxVerifyRetries", fallback=5))
VERIFY_DELAY = int(config.get("TRADE", "VerifyDelay", fallback=2))

# Global variable to store real-time data with timestamps
real_time_data = {}  # Format: {stock_idx: {"NSE": {"bid": x, "ask": y, "ts": t}, "BSE": ...}}

async def websocket_listener(client, scrip_codes):
    """WebSocket listener with exchange-specific updates and timestamps."""
    while True:  # Reconnection loop
        try:
            ws = WebSocket(client)
            async with ws as socket:
                await ws.subscribe(scrip_codes)
                logging.info(f"Subscribed to scrip codes: {scrip_codes}")

                async for data in ws.listen():
                    if data and "Data" in data:
                        current_ts = time.time()
                        for entry in data["Data"]:
                            token = int(entry.get("Token", 0))
                            if token not in token_map:
                                continue

                            stock_idx, exchange = token_map[token]
                            
                            # Initialize if missing
                            if stock_idx not in real_time_data:
                                real_time_data[stock_idx] = {
                                    "NSE": {"bid": 0, "ask": 0, "ts": 0},
                                    "BSE": {"bid": 0, "ask": 0, "ts": 0}
                                }
                            
                            # Update only the relevant exchange's data
                            real_time_data[stock_idx][exchange].update({
                                "bid": entry.get(f"{exchange}BidPrice", 0),
                                "ask": entry.get(f"{exchange}AskPrice", 0),
                                "ts": current_ts
                            })
        except Exception as e:
            logging.error(f"WebSocket error: {e}. Reconnecting...")
            await asyncio.sleep(5)

async def check_arbitrage(client, stock_idx, margin):
    """Arbitrage logic with data freshness check."""
    stock_data = real_time_data.get(stock_idx)
    if not stock_data:
        return

    current_time = time.time()
    nse_data = stock_data["NSE"]
    bse_data = stock_data["BSE"]

    # Check data freshness
    if (current_time - nse_data["ts"] > DATA_FRESHNESS_SEC) or \
       (current_time - bse_data["ts"] > DATA_FRESHNESS_SEC):
        logging.debug(f"Skipping stale data for stock {stock_idx}")
        return

    nse_bid, nse_ask = nse_data["bid"], nse_data["ask"]
    bse_bid, bse_ask = bse_data["bid"], bse_data["ask"]

    if nse_ask == 0 or bse_ask == 0:
        return

    spread_bse_bid_nse_ask = (bse_bid - nse_ask) / nse_ask
    spread_nse_bid_bse_ask = (nse_bid - bse_ask) / bse_ask

    nse_code = STOCKS[stock_idx]["nse"]
    bse_code = STOCKS[stock_idx]["bse"]

    max_price = max(nse_ask, bse_bid, nse_bid, bse_ask)
    qty = max(1, int(margin // max_price))

    executed = False
    try:
        if spread_bse_bid_nse_ask > ARBITRAGE_THRESHOLD:
            buy_success = await execute_trade(client, nse_code, "NSE", "BUY", nse_ask, qty)
            sell_success = await execute_trade(client, bse_code, "BSE", "SELL", bse_bid, qty)
            executed = buy_success and sell_success

        elif spread_nse_bid_bse_ask > ARBITRAGE_THRESHOLD:
            buy_success = await execute_trade(client, bse_code, "BSE", "BUY", bse_ask, qty)
            sell_success = await execute_trade(client, nse_code, "NSE", "SELL", nse_bid, qty)
            executed = buy_success and sell_success
    except Exception as e:
        logging.error(f"Arbitrage execution failed: {e}")
        executed = False

    if executed:
        logging.info(f"Arbitrage executed for stock {stock_idx} (NSE:{nse_code}/BSE:{bse_code})")
    else:
        logging.warning(f"Arbitrage failed for stock {stock_idx}")

# Rest of the code (execute_trade, verify_order, main) remains unchanged from previous version