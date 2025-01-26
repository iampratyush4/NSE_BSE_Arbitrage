import pickle
import os
import time
from login_manager import login, logout_and_login, SESSION_FILE

stocks = ["RELIANCE", "TCS", "INFY", "HDFC"]
ARBITRAGE_THRESHOLD = 0.5

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
            client = login()
            return client
    except (FileNotFoundError, pickle.UnpicklingError) as e:
        print(f"Error loading session file: {e}")
    except Exception as e:
        print(f"Unexpected error in perform_action: {e}")
    return None

def get_market_data(client, stock):
    """Fetch bid and ask prices for NSE and BSE."""
    try:
        if not client:
            raise ValueError("Client session is not available.")
        
        market_data = client.fetch_market_depth(stock)
        if market_data:
            return {
                "NSE": {
                    "bid": market_data.get("NSEBidPrice", 0),
                    "ask": market_data.get("NSEAskPrice", 0),
                },
                "BSE": {
                    "bid": market_data.get("BSEBidPrice", 0),
                    "ask": market_data.get("BSEAskPrice", 0),
                },
            }
        else:
            print(f"No market data available for {stock}.")
    except ValueError as ve:
        print(f"ValueError: {ve}")
    except AttributeError as e:
        print(f"Error fetching market data for {stock}: {e}")
    except Exception as e:
        print(f"Unexpected error in get_market_data for {stock}: {e}")
    return None

def calculate_quantity(margin_per_stock, max_price):
    """Calculate the quantity based on the margin for each stock and the maximum price."""
    return max(1, margin_per_stock // max_price)

def check_arbitrage(client, stock, margin_per_stock, executed_orders):
    """Check for arbitrage opportunities and execute trades if found."""
    try:
        data = get_market_data(client, stock)
        if not data:
            return

        nse_bid = data["NSE"]["bid"]
        nse_ask = data["NSE"]["ask"]
        bse_bid = data["BSE"]["bid"]
        bse_ask = data["BSE"]["ask"]

        if bse_bid - nse_ask > ARBITRAGE_THRESHOLD:
            max_price = max(bse_bid, nse_ask)
            quantity = calculate_quantity(margin_per_stock, max_price)
            print(f"Arbitrage Opportunity: Buy {stock} on NSE at {nse_ask}, Sell on BSE at {bse_bid}, Quantity: {quantity}")
            total_amount = execute_trade(client, stock, "NSE", "BUY", nse_ask, quantity) + \
                           execute_trade(client, stock, "BSE", "SELL", bse_bid, quantity)       
            executed_orders.append(total_amount)

        elif nse_bid - bse_ask > ARBITRAGE_THRESHOLD:
            max_price = max(nse_bid, bse_ask)
            quantity = calculate_quantity(margin_per_stock, max_price)
            print(f"Arbitrage Opportunity: Buy {stock} on BSE at {bse_ask}, Sell on NSE at {nse_bid}, Quantity: {quantity}")
            total_amount = execute_trade(client, stock, "BSE", "BUY", bse_ask, quantity) + \
                           execute_trade(client, stock, "NSE", "SELL", nse_bid, quantity)
            executed_orders.append(total_amount)
        else:
            print(f"No arbitrage for {stock}")

    except KeyError as e:
        print(f"Missing data for {stock}: {e}")
    except Exception as e:
        print(f"Unexpected error in check_arbitrage for {stock}: {e}")

def execute_trade(client, stock, exchange, order_type, price, quantity):
    """Execute buy/sell trade."""
    try:
        if not client:
            raise ValueError("Client session is not available.")
        
        order = {
            "Exchange": exchange,
            "OrderType": order_type,
            "ScripName": stock,
            "Price": price,
            "Quantity": quantity,
        }
        response = client.place_order(order)
        print(f"Executed {order_type} order for {stock} on {exchange} at {price} x {quantity}: {response}")
        return price * quantity
    except ValueError as ve:
        print(f"ValueError: {ve}")
    except Exception as e:
        print(f"Unexpected error in execute_trade for {stock}: {e}")
        return 0

if __name__ == "__main__":
    try:
        client = perform_action()
        if not client:
            raise RuntimeError("Failed to initialize client session.")

        margin_per_stock = float(input("Enter the margin for each stock trade: "))
        executed_orders = []

        print(client.holdings())

        while True:
            for stock in stocks:
                check_arbitrage(client, stock, margin_per_stock, executed_orders)
            time.sleep(5)  # Check every 5 seconds

            total_amount = sum(executed_orders)
            print(f"Total amount for executed orders so far: {total_amount}")
    
    except RuntimeError as re:
        print(f"RuntimeError: {re}")
    except KeyboardInterrupt:
        print("Process interrupted by user. Exiting...")
    except Exception as e:
        print(f"Unexpected error in main execution: {e}")
