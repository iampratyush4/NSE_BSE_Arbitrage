import pickle
import os
import time
import configparser
import asyncio
import logging
from login_manager import login, logout_and_login

config = configparser.ConfigParser()

config.read("config.ini", encoding="utf-8-sig")


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
                logging.info("Using existing session.")
                return client
        else:
            logging.info("No active session found. Logging in...")
            return login()  # Synchronous call to login function
    except Exception as e:
        logging.error(f"Error in perform_action: {e}")
        return None


if __name__ == "__main__":
    client =login()
    if not client:
        logging.error("Failed to initialize client session.")
    else:
        req_list = [
            {"Exch": "N", "ExchType": "C", "ScripCode": 1660},
        ]

        # Prepare request data
        req_data = client.Request_Feed('mf', 's', req_list)
        logging.info(req_data)

        # Define message handler
        def on_message(ws, message):
            print(message)

        # Connect to WebSocket
        client.connect(req_data)

        # Receive data with callback for message handling
        client.receive_data(on_message)
