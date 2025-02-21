# NSE-BSE Arbitrage Bot

This script identifies arbitrage opportunities between the NSE (National Stock Exchange) and BSE (Bombay Stock Exchange) for selected stocks and executes trades automatically. The script is designed for real-time monitoring and efficient execution.

---

## Features

1. **Session Management**:
   - Uses an existing session file if available.
   - Logs in automatically if no active session is found.

2. **Market Data Retrieval**:
   - Fetches bid and ask prices for stocks on both NSE and BSE.

3. **Arbitrage Detection**:
   - Checks if the price difference between the two exchanges exceeds a defined threshold.
   - Executes trades when an arbitrage opportunity is detected.

4. **Error Handling**:
   - Comprehensive error handling ensures stability and robustness.
   - Logs meaningful error messages for debugging.

5. **Real-Time Execution**:
   - Monitors selected stocks every 5 seconds for arbitrage opportunities.

---

## Prerequisites

1. **Python**:
   - Ensure you have Python 3.7 or higher installed.

2. **Dependencies**:
   - Required modules: `pickle`, `os`, `time`, and any custom modules like `login_manager`.

3. **Session File**:
   - The script requires a session file (defined as `SESSION_FILE` in `login_manager`). Ensure this file exists or implement the `login()` function in `login_manager`.

4. **Client Object**:
   - The `client` object must have the following methods:
     - `fetch_market_depth(stock)`: Fetch market data for a given stock.
     - `place_order(order)`: Place a buy/sell order.
     - `holdings()`: Display holdings.

---

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/iampratyush4/NSE_BSE_Arbitrage
   ```

2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Ensure the `SESSION_FILE` path is configured in the `login_manager` module.

---

## Configuration

### Arbitrage Threshold
Set the threshold for arbitrage detection by modifying the `ARBITRAGE_THRESHOLD` constant:
```python
ARBITRAGE_THRESHOLD = 0.5  # Adjust this value as needed
```

### Stocks List
Specify the stocks to monitor in the `stocks` list:
```python
stocks = ["RELIANCE", "TCS", "INFY", "HDFC"]
```

### Time Interval
Adjust the monitoring frequency by modifying the sleep interval in the main loop:
```python
time.sleep(5)  # Time in seconds
```

---

## Usage

1. Run the script:
   ```bash
   python NSE_BSE_Arbitrage.py
   ```

2. The script will:
   - Load the session file or log in to initialize a new session.
   - Fetch market data for the specified stocks.
   - Identify arbitrage opportunities and execute trades when detected.
   - Repeat the process every 5 seconds.

---

## File Descriptions

1. **NSE_BSE_Arbitrage.py**:
   - The main script that implements the arbitrage bot logic.
   - Handles session management, market data retrieval, and trade execution.

2. **login_manager.py**:
   - Manages user login/logout for the trading API.
   - Saves and retrieves sessions using a session file (`session.pkl`).

3. **Cred.py**:
   - Stores API credentials required for connecting to the 5Paisa API.
   - Replace placeholder values with your actual credentials:
     ```python
     cred = {
         "APP_NAME": "",
         "APP_SOURCE": "",
         "USER_ID": "",
         "PASSWORD": "",
         "USER_KEY": "",
         "ENCRYPTION_KEY": ""
     }
     client_code = ""
     totp_secret = ""
     pin = ""
     ```

---

## Error Handling

- If the session file is missing or corrupted, the script will attempt to log in again.
- Missing market data for a stock will log a warning and skip to the next stock.
- General errors are caught and logged for debugging purposes.

---

## Example Output

```plaintext
Using existing session.
{'holdings': {...}}
Checking arbitrage for RELIANCE...
Arbitrage Opportunity: Buy RELIANCE on NSE at 2520, Sell on BSE at 2535
Executed BUY order for RELIANCE on NSE at 2520: {'status': 'success'}
Executed SELL order for RELIANCE on BSE at 2535: {'status': 'success'}
Checking arbitrage for TCS...
No arbitrage for TCS
...
```

---

## Contributing

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Commit your changes with clear messages.
4. Submit a pull request.

---

## License

This Project is built by Pratyush upadhyay

---

## Disclaimer

This script is for educational purposes only. Ensure you comply with all regulatory and exchange-specific rules before executing trades in a live environment.
