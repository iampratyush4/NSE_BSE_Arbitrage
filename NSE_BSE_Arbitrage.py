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
SCRIP_CODES = [int(code.strip()) for code in config["STOCKS"]["StockList"].split(",")]
MAX_VERIFY_RETRIES = int(config.get("TRADE", "MaxVerifyRetries", fallback=5))
VERIFY_DELAY = int(config.get("TRADE", "VerifyDelay", fallback=2))

# Global variable to store real-time market data
real_time_data = {}

async def websocket_listener(client, scrip_codes):
    """Listen to WebSocket for real-time feed."""
    ws = WebSocket(client)
    async with ws as socket:
        await ws.subscribe(scrip_codes)
        logging.info(f"Subscribed to scrip codes: {scrip_codes}")

        async for data in ws.listen():
            if data and "Data" in data:
                for entry in data["Data"]:
                    scrip_code = entry.get("Token")
                    real_time_data[scrip_code] = {
                        "NSE": {
                            "bid": entry.get("NSEBidPrice", 0),
                            "ask": entry.get("NSEAskPrice", 0),
                        },
                        "BSE": {
                            "bid": entry.get("BSEBidPrice", 0),
                            "ask": entry.get("BSEAskPrice", 0),
                        },
                    }

async def verify_order(client, order_id):
    """Verify order execution status with retries."""
    for _ in range(MAX_VERIFY_RETRIES):
        await asyncio.sleep(VERIFY_DELAY)
        try:
            order_book = await asyncio.to_thread(client.order_book)
            for order in order_book:
                if str(order["OrderID"]) == str(order_id):
                    status = order["Status"]
                    if status in ["Fully Executed", "Completed"]:
                        logging.info(f"Order {order_id} executed successfully")
                        return True
                    elif status in ["Rejected", "Cancelled"]:
                        logging.warning(f"Order {order_id} failed with status: {status}")
                        return False
            logging.info(f"Order {order_id} still pending...")
        except Exception as e:
            logging.error(f"Order verification failed: {e}")
    logging.warning(f"Order {order_id} not confirmed after {MAX_VERIFY_RETRIES} retries")
    return False

async def execute_trade(client, scrip_code, exchange, order_type, price, qty):
    """Execute and verify trade."""
    try:
        order = Order(
            exchange="N" if exchange == "NSE" else "B",
            exchange_type="C",
            scrip_code=scrip_code,
            quantity=qty,
            price=round(price, 1),
            order_type=OrderType.BUY if order_type == "BUY" else OrderType.SELL
        )
        response = await asyncio.to_thread(client.place_order, order)
        order_id = response.get("OrderID")

        if order_id and await verify_order(client, order_id):
            return True
        return False
    except Exception as e:
        logging.error(f"Trade execution failed: {e}")
        return False

async def check_arbitrage(client, scrip_code, margin):
    """Arbitrage logic with verified execution."""
    data = real_time_data.get(scrip_code)
    if not data: return

    nse_bid, nse_ask = data["NSE"]["bid"], data["NSE"]["ask"]
    bse_bid, bse_ask = data["BSE"]["bid"], data["BSE"]["ask"]

    if nse_ask == 0 or bse_ask == 0: return

    spread_bse_bid_nse_ask = (bse_bid - nse_ask) / nse_ask
    spread_nse_bid_bse_ask = (nse_bid - bse_ask) / bse_ask

    max_price = max(nse_ask, bse_bid, nse_bid, bse_ask)
    qty = max(1, int(margin // max_price))

    executed = False
    if spread_bse_bid_nse_ask > ARBITRAGE_THRESHOLD:
        buy_success = await execute_trade(client, scrip_code, "NSE", "BUY", nse_ask, qty)
        sell_success = await execute_trade(client, scrip_code, "BSE", "SELL", bse_bid, qty)
        executed = buy_success and sell_success

    elif spread_nse_bid_bse_ask > ARBITRAGE_THRESHOLD:
        buy_success = await execute_trade(client, scrip_code, "BSE", "BUY", bse_ask, qty)
        sell_success = await execute_trade(client, scrip_code, "NSE", "SELL", nse_bid, qty)
        executed = buy_success and sell_success

    if executed:
        logging.info(f"Arbitrage executed successfully for {scrip_code}")
    else:
        logging.warning(f"Arbitrage failed for {scrip_code}")

async def main():
    client = login()
    if client is None or not client.margin():
        logging.error("Failed to initialize client session.")
        return

    logging.info(f"Total Margin available for this client is: {client.margin()}")

    margin_per_stock = float(input("Enter the margin for each stock trade: "))

    # Start WebSocket listener
    asyncio.create_task(websocket_listener(client, SCRIP_CODES))

    while True:
        start_time = time.time()
        tasks = [
            check_arbitrage(client, stock, margin_per_stock)
            for stock in SCRIP_CODES
        ]
        await asyncio.gather(*tasks)

        elapsed_time = time.time() - start_time
        sleep_time = max(0, 5 - elapsed_time)
        await asyncio.sleep(sleep_time)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Process interrupted by user. Exiting...")
    except Exception as e:
        logging.error(f"Error in main execution: {e}")
