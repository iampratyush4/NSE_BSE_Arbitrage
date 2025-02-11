# arbitrage_finder.py
import logging
import orjson
import asyncio
import gc

from place_order import place_order, cancel_order
from zmq_logger import info, error, debug, warning
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration using orjson
with open("config.json", "rb") as file:
    config = orjson.loads(file.read())

THRESHOLD_PERCENTAGE = 0.004
TRADE_AMOUNT = 100000

scrip_codes = config["STOCK"]["scrip_codes"]

# Thread-safe tracking of open trades
open_trades = {}
open_trades_lock = asyncio.Lock()

def liquidity_check(buy_exchange_data, sell_exchange_data, trade_qty):
    required = trade_qty * 10
    return (
        buy_exchange_data["ask_quantity"] >= required and
        sell_exchange_data["bid_quantity"] >= required
    )

# Try to import the Cython-compiled function
try:
    try:
        from arbitrage_cy import compute_profit
    except ImportError:
        def compute_profit(ask_price, bid_price):
            if ask_price <= 0:
                return 0.0
            return ((bid_price - ask_price) / ask_price) * 100
except ImportError:
    def compute_profit(ask_price, bid_price):
        if ask_price <= 0:
            return 0.0
        return ((bid_price- ask_price) / ask_price) *100

async def process_arbitrage(scenario, stock_name, stock_data, buy_exchange, sell_exchange):
    # logger.info(f"Processing {scenario}")

    async with open_trades_lock:
        if stock_name in open_trades:
            logger.info(f"Skipping {stock_name}, already in open trades")
            return
        
    
    # logger.info(f"Processing arbitrage for {stock_name}")
    buy_data = stock_data[buy_exchange]
    # logger.info(f"buy_data: {buy_data}")
    sell_data = stock_data[sell_exchange]
    # logger.info(f"sell_data: {sell_data}")

    ask_price = buy_data["ask"]
    # logger.info(f"ask_price: {ask_price}")

    bid_price = sell_data["bid"]
    # logger.info(f"Processing arbitrage for {stock_name} | Ask={ask_price} | Bid={bid_price} ")
    
    if not (ask_price and bid_price and ask_price > 0):
        return

    if bid_price <= ask_price:
        return

    profit_percentage = compute_profit(ask_price, bid_price)
    if profit_percentage < THRESHOLD_PERCENTAGE:
        logger.info(f"Stock: {stock_name} | Bad Spread {profit_percentage}")
        return

    highest_price = max(ask_price, bid_price)
    trade_qty = int(TRADE_AMOUNT / highest_price)
    if trade_qty <= 0:
        return

    if liquidity_check(buy_data, sell_data, trade_qty) == False:
        logger.info(f"Skipping {stock_name} due to low liquidity")
        return

    logger.info(f"Arbitrage opportunity: {stock_name} | Spread {profit_percentage}% | Buy {buy_exchange} @ {ask_price} | Sell {sell_exchange} @ {bid_price}")

    # Disable GC for this critical section
    gc.disable()
    try:
        order_buy_task = asyncio.create_task(
            place_order(
                exchange=buy_exchange,
                scrip_code=scrip_codes[stock_name][buy_exchange],
                price=0,
                order_type="Buy",
                qty=trade_qty
            )
        )
        order_sell_task = asyncio.create_task(
            place_order(
                exchange=sell_exchange,
                scrip_code=scrip_codes[stock_name][sell_exchange],
                price=0,
                order_type="Sell",
                qty=trade_qty
            )
        )

        buy_response, sell_response = await asyncio.gather(order_buy_task, order_sell_task)
        await asyncio.sleep(3)  # Allow order processing

        buy_success = buy_response and buy_response.get("Status") == "Success"
        sell_success = sell_response and sell_response.get("Status") == "Success"

        async with open_trades_lock:
            if buy_success and sell_success:
                open_trades[stock_name] = {
                    "buy_exchange": buy_exchange,
                    "sell_exchange": sell_exchange,
                    "trade_qty": trade_qty,
                    "buy_price": ask_price,
                    "sell_price": bid_price,
                    "order_ids": {
                        "buy": buy_response.get("OrderID"),
                        "sell": sell_response.get("OrderID")
                    }
                }
                info(f"Recorded open trade for {stock_name}")
            else:
                if buy_success:
                    warning(f"Cancelling buy order for {stock_name}")
                    await cancel_order(buy_exchange, scrip_codes[stock_name][buy_exchange], buy_response.get("OrderID"))
                if sell_success:
                    warning(f"Cancelling sell order for {stock_name}")
                    await cancel_order(sell_exchange, scrip_codes[stock_name][sell_exchange], sell_response.get("OrderID"))
    except Exception as e:
        error(f"Arbitrage processing failed: {str(e)}")
    finally:
        gc.enable()

async def square_off_trade(stock_name, trade, stock_data):
    buy_exch = trade["buy_exchange"]
    sell_exch = trade["sell_exchange"]
    qty = trade["trade_qty"]
    
    exit_buy_price = stock_data[buy_exch]["bid"]
    exit_sell_price = stock_data[sell_exch]["ask"]
    
    if exit_buy_price is None or exit_sell_price is None:
        error(f"Cannot square off {stock_name}: Missing prices")
        return

    if exit_buy_price >= exit_sell_price:

        logger.info(f"Square off condition met for {stock_name}")
        try:
            exit_buy_task = asyncio.create_task(
                place_order(
                    exchange=buy_exch,
                    scrip_code=scrip_codes[stock_name][buy_exch],
                    price=0,
                    order_type="Sell",
                    qty=qty
                )
            )
            exit_sell_task = asyncio.create_task(
                place_order(
                    exchange=sell_exch,
                    scrip_code=scrip_codes[stock_name][sell_exch],
                    price=0,
                    order_type="Buy",
                    qty=qty
                )
            )

            exit_buy_resp, exit_sell_resp = await asyncio.gather(exit_buy_task, exit_sell_task)
            buy_success = exit_buy_resp and exit_buy_resp.get("Status") == "Success"
            sell_success = exit_sell_resp and exit_sell_resp.get("Status") == "Success"

            async with open_trades_lock:
                if stock_name in open_trades and (buy_success and sell_success):
                    del open_trades[stock_name]
                    info(f"Squared off {stock_name} successfully")
                else:
                    error(f"Failed to square off {stock_name}: Buy={buy_success}, Sell={sell_success}")
        except Exception as e:
            error(f"Square off failed: {str(e)}")

async def check_and_execute_arbitrage(stock_name, stock_data):
    logger.info(f"Checking arbitrage for {stock_name}")
    await asyncio.gather(
        process_arbitrage(1, stock_name, stock_data, "N", "B"),
        process_arbitrage(2, stock_name, stock_data, "B", "N")
    )
    
    async with open_trades_lock:
        if stock_name in open_trades:

            trade = open_trades[stock_name]
            buy_exch = trade["buy_exchange"]
            sell_exch = trade["sell_exchange"]
            current_buy_bid = stock_data[buy_exch]["bid"]
            current_sell_ask = stock_data[sell_exch]["ask"]

            if current_buy_bid is None or current_sell_ask is None:
                logger.info(f"Missing prices for {stock_name}")
                return
            logger.info(f"Checking square off for {stock_name} | Buy={current_buy_bid} | Sell={current_sell_ask}")
            if current_buy_bid >= current_sell_ask:
                logger.info(f"Square off condition met for {stock_name}")
                await square_off_trade(stock_name, trade, stock_data)

        else:
            return
