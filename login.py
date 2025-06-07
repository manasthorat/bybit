from pybit.unified_trading import HTTP
import os
import pandas as pd
from datetime import datetime
import time
import json

# Load configuration from a config.json file
config_file = "config.json"
if not os.path.exists(config_file):
    raise FileNotFoundError(f"Configuration file '{config_file}' not found.")

# Read the configuration file
with open(config_file, "r") as file:
    config = json.load(file)


# Store your API credentials (ideally in environment variables)

api_key = config['testnet']['api_key']
api_secret = config['testnet']['api_secret']

# Specify the network (testnet for testing, mainnet for real trading)
use_testnet = True  # Set to False for real trading
try:
    # Create the session
    session = HTTP(
        testnet=use_testnet,
        api_key=api_key,
        api_secret=api_secret
    )
    print("Successfully connected to Bybit API!")
    
    # Test the connection with a simple request
    server_time = session.get_server_time()
    print(f"Server time: {datetime.fromtimestamp(server_time['time'] / 1000)}")
    
    # Get market data (public endpoint that doesn't require authentication)
    symbol = "BTCUSDT"
    tickers = session.get_tickers(category="spot", symbol=symbol)
    print(f"Current {symbol} price: {tickers['result']['list'][0]['lastPrice']}")
    


    account_info = session.get_account_info()
    print(f"Account info : {account_info}")
    # Try different account types if you're unsure which one you have
    account_types = ["UNIFIED", "CONTRACT", "SPOT"]
    
    for account_type in account_types:
        try:
            print(f"Trying to get balance for account type: {account_type}")
            wallet_balance = session.get_wallet_balance(accountType=account_type)
            print(f"Successfully retrieved {account_type} wallet balance")
            
            # Display available balance
            #print(f"wallet {wallet_balance}")
            for coin in wallet_balance["result"]["list"][0]["coin"]:
                if float(coin["walletBalance"]) > 0:
                    print(f"Asset: {coin['coin']}, Available Balance: {coin['walletBalance']}")
            
            # If we get here, we found a working account type
            
        except Exception as e:
            print(f"Error getting {account_type} wallet balance: {e}")
            
except Exception as e:
    print(f"Error connecting to Bybit API: {e}")



print(session.get_wallet_balance(
    accountType="UNIFIED",
    coin="BTC",))

print(session.place_order(
    category="linear",
    symbol="SOLUSDT",
    side="Buy",
    orderType="MARKET",
    qty="0.1",
    timeInForce="GoodTillCancel",
))

#         Additional information:
print("All Open Positions:")
positions = session.get_positions(
    category="linear",
    settleCoin="USDT"
)

print(positions)
# Print results
for pos in positions['result']['list']:
    if float(pos["size"]) > 0:
        print(f"Symbol: {pos['symbol']}, Side: {pos['side']}, Size: {pos['size']}")