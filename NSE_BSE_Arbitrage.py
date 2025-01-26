import pickle
import os
import time
from login_manager import login, logout_and_login, SESSION_FILE

import configparser

# Read configuration
config = configparser.ConfigParser()
config.read("config.ini")

# Access values
ARBITRAGE_THRESHOLD = float(config["TRADE"]["ArbitrageThreshold"])
SESSION_FILE = config["FILES"]["SessionFile"]
stocks = config["STOCKS"]["StockList"].split(", ")


def perform_action():
    """Performs actions using the logged-in session."""
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, "rb") as f:
                client = pickle.load(f)
                print("Using existing session.")
                return client
        else:
            print("No active session found. Logging in...")
            return login()
    except Exception as e:
        print(f"Error in perform_action: {e}")
        return None

def get_market_data(client, stock):
    """Fetch bid and ask prices for NSE and BSE."""
    try:
        market_data = client.fetch_market_depth(stock)
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
            print(f"No market data available for {stock}.")
    except Exception as e:
        print(f"Error in get_market_data for {stock}: {e}")
    return None

def calculate_quantity(margin_per_stock, max_price):
    """Calculate the quantity based on the margin for each stock and the maximum price."""
    return max(1, margin_per_stock // max_price)

def verify_order_execution(client, order_id):
    """Verify if the order has been executed successfully."""
    try:
        status = client.check_order_status(order_id)
        if status == "EXECUTED":
            print(f"Order {order_id} successfully executed.")
            return True
        else:
            print(f"Order {order_id} not executed yet. Status: {status}")
            return False
    except Exception as e:
        print(f"Error verifying order {order_id}: {e}")
        return False

def execute_trade(client, stock, exchange, order_type, price, quantity):
    """Execute buy/sell trade and verify its execution."""
    try:
        order = {
            "Exchange": exchange,
            "OrderType": order_type,
            "ScripName": stock,
            "Price": price,
            "Quantity": quantity,
        }
        response = client.place_order(order)
        order_id = response.get("OrderID")
        print(f"Placed {order_type} order for {stock} on {exchange} at {price} x {quantity}: {response}")

        # Verify order execution
        if order_id:
            if verify_order_execution(client, order_id):
                return price * quantity
            else:
                print(f"Order {order_id} for {stock} on {exchange} failed to execute.")
                return 0
        else:
            print("No OrderID returned in response.")
            return 0
    except Exception as e:
        print(f"Error in execute_trade for {stock}: {e}")
        return 0

def check_arbitrage(client, stock, margin_per_stock, executed_orders):
    """Check for arbitrage opportunities and execute trades if found."""
    data = get_market_data(client, stock)
    if not data:
        return

    nse_bid = data["NSE"]["bid"]
    nse_ask = data["NSE"]["ask"]
    bse_bid = data["BSE"]["bid"]
    bse_ask = data["BSE"]["ask"]
    nse_bid_volume = data["NSE"]["bid_volume"]
    nse_ask_volume = data["NSE"]["ask_volume"]
    bse_bid_volume = data["BSE"]["bid_volume"]
    bse_ask_volume = data["BSE"]["ask_volume"]

    max_price = max(nse_ask, bse_bid, nse_bid, bse_ask)
    quantity = calculate_quantity(margin_per_stock, max_price)

    if bse_bid - nse_ask > ARBITRAGE_THRESHOLD and \
       nse_ask_volume >= 5 * quantity and bse_bid_volume >= 5 * quantity:
        total_amount = execute_trade(client, stock, "NSE", "BUY", nse_ask, quantity) + \
                       execute_trade(client, stock, "BSE", "SELL", bse_bid, quantity)
        executed_orders.append(total_amount)
    elif nse_bid - bse_ask > ARBITRAGE_THRESHOLD and \
         bse_ask_volume >= 5 * quantity and nse_bid_volume >= 5 * quantity:
        total_amount = execute_trade(client, stock, "BSE", "BUY", bse_ask, quantity) + \
                       execute_trade(client, stock, "NSE", "SELL", nse_bid, quantity)
        executed_orders.append(total_amount)

def main():
    client = perform_action()
    if not client:
        print("Failed to initialize client session.")
        return

    margin_per_stock = float(input("Enter the margin for each stock trade: "))
    executed_orders = []

    while True:
        start_time = time.time()
        for stock in stocks:
            check_arbitrage(client, stock, margin_per_stock, executed_orders)
        total_amount = sum(executed_orders)
        print(f"Total amount for executed orders so far: {total_amount}")

        # Adjust sleep time dynamically to minimize latency
        elapsed_time = time.time() - start_time
        sleep_time = max(0, 5 - elapsed_time)  # Maintain 5-second cycles
        time.sleep(sleep_time)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Process interrupted by user. Exiting...")
    except Exception as e:
        print(f"Error in main execution: {e}")
