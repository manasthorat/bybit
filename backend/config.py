import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
    BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
    BYBIT_TESTNET = os.getenv("BYBIT_TESTNET", "True").lower() == "true"
    
    # Webhook Security
    WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./trading_system.db")
    
    # Server
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    
    # Trading Settings
    DEFAULT_POSITION_SIZE = 100  # USDT
    MAX_POSITIONS = 5
    
    # Risk Management
    DEFAULT_STOP_LOSS_PERCENT = 2.0  # 2% stop loss
    DEFAULT_TAKE_PROFIT_PERCENT = 4.0  # 4% take profit

config = Config()