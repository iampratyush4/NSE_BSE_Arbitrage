# place_order.py
import aiohttp
import asyncio
import orjson
import uuid
import gc

from zmq_logger import info, error, warning, debug

# Load configuration using orjson
with open("config.json", "rb") as file:
    config = orjson.loads(file.read())

access_token = config["AUTH"]["access_token"]
client_code  = config["AUTH"]["client_code"]
user_key     = config["AUTH"]["user_key"]
pin          = config["AUTH"]["pin"]
scrip_codes  = config["STOCK"]["scrip_codes"]
fieldnames   = config["STOCK"]["fieldnames"]

# ✅ Proper session initialization
session = None  # Initially set to None

async def get_session():
    global session
    if session is None:
        session = aiohttp.ClientSession()
    return session

async def place_order(exchange, scrip_code, price, order_type, qty=1):
    session = await get_session()  # Ensure session is created inside an event loop
    url = "https://Openapi.5paisa.com/VendorsAPI/Service1.svc/V1/PlaceOrderRequest"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    data = {
        "head": {"key": user_key},
        "body": {
            "Exchange": exchange,
            "ExchangeType": "C",
            "ScripCode": str(scrip_code),
            "Price": str(price),
            "StopLossPrice": "0",
            "OrderType": "B" if order_type.lower() == "buy" else "S",
            "Qty": qty,
            "DisQty": "0",
            "IsIntraday": True,
            "AHPlaced": "N",
            "RemoteOrderID": str(uuid.uuid4())
        }
    }
    try:
        async with session.post(url, headers=headers, json=data) as response:
            response.raise_for_status()
            return await response.json()
    except Exception as e:
        error(f"Place order failed: {str(e)}")
        return None

async def cancel_order(exchange, scrip_code, order_id):
    session = await get_session()
    cancel_url = "https://Openapi.5paisa.com/VendorsAPI/Service1.svc/V1/CancelOrderRequest"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    cancel_data = {
        "head": {"key": user_key},
        "body": {
            "Exchange": exchange,
            "ExchangeType": "C",
            "ScripCode": scrip_code,
            "RemoteOrderID": order_id
        }
    }
    try:
        async with session.post(cancel_url, headers=headers, json=cancel_data) as response:
            response.raise_for_status()
            return await response.json()
    except Exception as e:
        error(f"Cancel order failed: {str(e)}")
        return None

# ✅ Proper shutdown handling
async def shutdown():
    global session
    if session:
        await session.close()
        session = None