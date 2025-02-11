# login.py file
import json
import logging
import time
from py5paisa import FivePaisaClient
from datetime import datetime, timedelta
import pickle

import requests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with open("config.json", "r") as file:
    config = json.load(file)

access_token = config["AUTH"]["access_token"]
client_code = config["AUTH"]["client_code"]
user_key = config["AUTH"]["user_key"]
pin = config["AUTH"]["pin"]


def check_login_exists():
    if check_session_status() == 9:
        logger.info("Session is not valid try to login")
        login()
    else:
        logger.info("Session is valid")
        return

def login():
    totp_secret = input("Enter the TOTP - ")
    client = FivePaisaClient(cred=config["AUTH"]["cred"])

    client.get_totp_session(client_code,totp_secret,pin)

    New_Access_Token = client.get_access_token() 

    config["AUTH"]["access_token"] =str(New_Access_Token)
    config["AUTH"]["last_updated"] = str(time.time()) 
    
    with open("client.pkl", "wb") as file:
        pickle.dump(client, file)

    with open("config.json", "w") as file:
        json.dump(config, file, indent=4)
    


def check_session_status():
    # Define the request URL
    url = "https://Openapi.5paisa.com/VendorsAPI/Service1.svc/V4/Margin"
    
    # Set up headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"bearer {access_token}"
    }

    # Define the body with app_key and client_code
    body = {
        "head": {
            "key": user_key
        },
        "body": {
            "ClientCode": client_code
        }
    }

    # Send POST request to the API
    response = requests.post(url, headers=headers, json=body)
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        response_data = response.json()
        
        # Check if the status is 0 (success)
        if response_data.get("head", {}).get("status") == "0":
            logger.info(response_data.get("head", {}).get("statusDescription"))
            return 0
        else:
            logger.error("Session is not valid")
            return 9
    else:
        logger.error("Failed to check session status")
        return 9



if __name__ == "__main__":
    check_login_exists()

# login.py file Ends