import csv

def get_scripcodes_from_csv(csv_filepath, nifty_symbols):
    """
    Extract scripcodes for Nifty 50 symbols from a CSV file, filtering by Exch (B/N) and ExchType (C).
    
    Args:
        csv_filepath (str): Path to CSV file with symbol-scripcode mapping
        nifty_symbols (list): List of Nifty 50 stock symbols
        
    Returns:
        list: Scripcodes in the same order as input symbols
    """
    symbol_to_scrip = {}
    
    # Read CSV file with validation
    with open(csv_filepath, 'r') as file:
        csv_reader = csv.DictReader(file)
        
        # Check required columns
        required_columns = ['Name', 'ScripCode', 'Exch', 'ExchType']
        missing_columns = [col for col in required_columns if col not in csv_reader.fieldnames]
        if missing_columns:
            raise ValueError(f"CSV missing required columns: {missing_columns}")

        # Process rows
        for row in csv_reader:
            # Check exchange filters
            exch = row['Exch'].strip().upper()
            exch_type = row['ExchType'].strip().upper()
            
            if exch not in ['B'] or exch_type != 'C':
                continue  # Skip rows not matching exchange criteria

            # Normalize symbol (uppercase + remove hyphens)
            symbol = row['Name'].strip().upper().replace('-', '')
            scripcode = row['ScripCode'].strip()
            
            # Store in dictionary (last occurrence in CSV wins)
            symbol_to_scrip[symbol] = scripcode

    # Match scripcodes with Nifty symbols
    scripcodes = []
    for symbol in nifty_symbols:
        # Normalize symbol for matching
        normalized_symbol = symbol.upper().replace('-', '')
        scripcode = symbol_to_scrip.get(normalized_symbol, None)
        
        if scripcode is None:
            print(f"Warning: Scripcode not found for {symbol} (Normalized: {normalized_symbol})")
            
        scripcodes.append(scripcode)
    
    return scripcodes

# Your Nifty 50 symbols list (same as before)

nifty_50_symbols = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
    "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BHARTIARTL", "BRITANNIA",
    "CIPLA", "COALINDIA", "DIVISLAB", "DRREDDY", "EICHERMOT", "GRASIM",
    "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDUNILVR",
    "ICICIBANK", "ITC", "INDUSINDBK", "INFY", "JSWSTEEL", "KOTAKBANK", "LT",
    "M&M", "MARUTI", "NESTLEIND", "NTPC", "ONGC", "POWERGRID", "RELIANCE",
    "SBIN", "SBILIFE", "SUNPHARMA", "TCS", "TATACONSUM", "TATAMOTORS",
    "TATASTEEL", "TECHM", "TITAN", "ULTRACEMCO", "UPL", "WIPRO", "BPCL", "SHREECEM"
]

# Example usage
csv_path = "ScripMaster.csv"  # Replace with your CSV path
try:
    scripcode_list = get_scripcodes_from_csv(csv_path, nifty_50_symbols)
    print("Scripcodes for Nifty 50:", scripcode_list)
except ValueError as e:
    print(f"Error reading CSV: {e}")