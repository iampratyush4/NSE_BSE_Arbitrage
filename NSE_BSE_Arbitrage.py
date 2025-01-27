# NSE_BSE_Arbitrage.py
import asyncio
import time
import logging
import configparser
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

async def get_market_data(client, stock):
    """Fetch bid and ask prices for NSE and BSE."""
    try:
        market_data = await asyncio.to_thread(client.fetch_market_depth, stock)

        if market_data:
            return {
                "NSE": {
                    "bid": market_data.get("NSEBidPrice", 0),
                    "ask": market_data.get("NSEAskPrice", 0),
                    "bid_volume": market_data.get("NSEBidVolume", 0),
                    "ask_volume": market_data.get("NSEAskVolume", 0),
                },
                "BSE": {
                    "bid": market_data.get("BSEBidPrice", 0),
                    "ask": market_data.get("BSEAskPrice", 0),
                    "bid_volume": market_data.get("BSEBidVolume", 0),
                    "ask_volume": market_data.get("BSEAskVolume", 0),
                },
            }
        else:
            logging.warning(f"No market data available for {stock}.")
    except Exception as e:
        logging.error(f"Error in get_market_data for {stock}: {e}")
    return None



async def verify_order(client, order_id):
    """Verify order execution status with retries"""
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
    """Execute and verify trade"""
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
    """Arbitrage logic with verified execution"""
    data = await get_market_data(client, scrip_code)
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

# Rest of the code (get_market_data, main) remains same as previous version
async def main():
    client =  login()
    if  client is None or not client.margin():
        logging.error("Failed to initialize client session.")
        return
    
    logging.info(f"Total Margin available for this client is: {client.margin()}")

    margin_per_stock = float(input("Enter the margin for each stock trade: "))
    executed_orders = []

    while True:
        start_time = time.time()
        tasks = [
            check_arbitrage(client, stock, margin_per_stock, executed_orders)
            for stock in stocks
        ]
        await asyncio.gather(*tasks)
        total_amount = sum(executed_orders)
        logging.info(f"Total amount for executed orders so far: {total_amount}")

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

nifty_50_symbols = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
    "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BHARTIARTL", "BRITANNIA",
    "CIPLA", "COALINDIA", "DIVISLAB", "DRREDDY", "EICHERMOT", "GRASIM",
    "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDUNILVR",
    "ICICIBANK", "ITC", "INDUSINDBK", "INFY", "JSWSTEEL", "KOTAKBANK", "LT",
    "M&M", "MARUTI", "NESTLEIND", "NTPC", "ONGC", "POWERGRID", "RELIANCE",
    "SBIN", "SBILIFE", "SUNPHARMA", "TCS", "TATACONSUM", "TATAMOTORS",
    "TATASTEEL", "TECHM", "TITAN", "ULTRACEMCO", "UPL", "WIPRO", "BPCL", "SHREECEM"
]