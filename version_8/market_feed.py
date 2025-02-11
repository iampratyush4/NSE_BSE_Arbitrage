#market_data_feed.py starts here
import asyncio
import configparser
import csv
from datetime import datetime
import os
import pickle
from urllib.parse import quote_plus
import websockets
import json
import logging
from arbitrage_finder import check_and_execute_arbitrage
from py5paisa import FivePaisaClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with open("config.json", "r") as file:
    config = json.load(file)

with open("client.pkl", "rb") as file:
    client = pickle.load(file)
logger.info("client",client)

access_token = config["AUTH"]["access_token"]
client_code = config["AUTH"]["client_code"]
user_key = config["AUTH"]["user_key"]
pin = config["AUTH"]["pin"]
scrip_codes = config["STOCK"]["scrip_codes"]
fieldnames = config["STOCK"]["fieldnames"]

print(access_token,type(access_token),client_code,type(client_code))

latest_data = {
    stock: {
        "N": {"bid": None, "ask": None, "bid_quantity": 0, "ask_quantity": 0},
        "B": {"bid": None, "ask": None, "bid_quantity": 0, "ask_quantity": 0}
    } 
    # logger.info(latest_data)
    for stock in scrip_codes.keys()
}
csv_filename = "market_data.csv"



def save_to_csv(data):
    file_exists = os.path.isfile(csv_filename)
    with open(csv_filename, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)

async def update_price(update):
    stock_name = next((name for name, codes in scrip_codes.items() 
                      if codes["N"] == update.get("Token") 
                      or codes["B"] == update.get("Token")), None)
    
    if not stock_name:
        return
        
    exch = update.get("Exch")
    if exch not in ["N", "B"]:
        return
    
    entry = latest_data[stock_name][exch]
    entry["bid"] = update.get("BidRate", entry["bid"])
    entry["ask"] = update.get("OffRate", entry["ask"])
    entry["bid_quantity"] = update.get("BidQty", entry["bid_quantity"])
    entry["ask_quantity"] = update.get("OffQty", entry["ask_quantity"])

    save_to_csv(update)

    await check_and_execute_arbitrage(stock_name, latest_data[stock_name])



async def market_data_feed():
    logger.info("Margin :", client.margin())
    encoded_value = quote_plus(f"{access_token}|{client_code}")
    ws_url = f"wss://openfeed.5paisa.com/feeds/api/chat?Value1={encoded_value}"
    # logger.info(f"Connecting to WebSocket: {ws_url}")

    
    market_feed_data = []
    for stock_name, codes in scrip_codes.items():
        market_feed_data.extend([
            {"Exch": "N", "ExchType": "C", "ScripCode": codes["N"]},
            {"Exch": "B", "ExchType": "C", "ScripCode": codes["B"]}
        ])

    subscription = {
        "Method": "MarketFeedV3",
        "Operation": "Subscribe",
        "ClientCode": client_code,
        "MarketFeedData": market_feed_data
    }

    while True:
        try:
            async with websockets.connect(ws_url) as ws:
                # logger.info("WebSocket connected")
                await ws.send(json.dumps(subscription))
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    if isinstance(data, list):
                        for update in data:
                            await update_price(update)
        except Exception as e:
            # logger.error(f"WebSocket error: {e}, reconnecting...")
            await asyncio.sleep(5)

async def main():
    await market_data_feed()

if __name__ == "__main__":
    
    asyncio.run(main())
        #market_data_feed.py ends here