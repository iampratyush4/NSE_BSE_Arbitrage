import pickle
import os
from py5paisa import FivePaisaClient
import Cred

SESSION_FILE = "session.pkl"


def create_client():
    """Create a new FivePaisaClient instance."""
    client = FivePaisaClient(cred=Cred.cred)
    return client


def login():
    """Logs in the user and saves the session if not already logged in."""
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "rb") as f:
            client = pickle.load(f)
            print("Loaded existing session.")
            return client

    # Create a new session if no session exists
    client = create_client()
    client.get_totp_session(
        client_code=Cred.client_code,
        pin=Cred.pin,
        totp=input('Enter your TOTP'),
        
    )
    with open(SESSION_FILE, "wb") as f:
        pickle.dump(client, f)
    print("Logged in and session saved.")
    return client


def logout_and_login():
    """Logs out the existing session and logs in again."""
    client = login()  # Load existing session or create a new one
    client.logout()  # Log out from the current session
    os.remove(SESSION_FILE)  # Delete the existing session file
    print("Logged out from the current session. Logging in again...")
    return login()


if __name__ == "__main__":
    client = login()
