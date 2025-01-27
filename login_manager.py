import logging
import os
import pickle
from py5paisa import FivePaisaClient
import Cred

SESSION_FILE = "session.pkl"

def create_client():
    """Create a new FivePaisaClient instance."""
    return FivePaisaClient(cred=Cred.cred)

def login():
    """Login with TOTP and save session."""
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, "rb") as f:
                client = pickle.load(f)
                if client.fetch_margin()["TotalMargin"] > 0:  # Validate session
                    logging.info("Loaded existing session.")
                    return client
                else:
                    logging.warning("Session expired. Re-authenticating...")
                    os.remove(SESSION_FILE)

        # Fresh login
        client = FivePaisaClient(cred=Cred.cred)
        totp = input("Enter TOTP: ")  # Replace with secure TOTP retrieval if needed
        client.get_totp_session(client_code=Cred.client_code, totp=totp,pin=Cred.pin)
        
        # Save session
        with open(SESSION_FILE, "wb") as f:
            pickle.dump(client, f)
        return client
    except Exception as e:
        logging.error(f"Login failed: {e}")
        return None

def logout_and_login():
    """Logout and force new login."""
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)
    return login()