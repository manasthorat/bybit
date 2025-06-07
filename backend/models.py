from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any

Base = declarative_base()

# SQLAlchemy Models (Database Tables)
class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(String, unique=True, index=True)  # Bybit order ID
    symbol = Column(String, index=True)
    side = Column(String)  # Buy/Sell
    quantity = Column(Float)
    leverage = Column(Integer, nullable=True)  # Add leverage field
    entry_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    status = Column(String)  # pending, filled, cancelled, rejected
    reason = Column(Text, nullable=True)  # Reason for execution or rejection
    pnl = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    webhook_data = Column(Text, nullable=True)  # Store original webhook JSON

class Settings(Base):
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True)
    auto_trading_enabled = Column(Boolean, default=True)
    max_position_size = Column(Float, default=1000.0)
    risk_percentage = Column(Float, default=1.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Pydantic Models (API Request/Response)
class WebhookSignal(BaseModel):
    action: str  # "buy" or "sell"
    symbol: str
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    quantity: Optional[float] = None
    leverage: Optional[int] = 1  # Add leverage with default value
    alert_message: Optional[str] = None
    
class TradeResponse(BaseModel):
    id: int
    trade_id: Optional[str] = None  # Make this optional
    symbol: str
    side: str
    quantity: float
    leverage: Optional[int] = None  # Add leverage field
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: str
    reason: Optional[str] = None
    pnl: Optional[float] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class SettingsUpdate(BaseModel):
    auto_trading_enabled: Optional[bool] = None
    max_position_size: Optional[float] = None
    risk_percentage: Optional[float] = None

class AccountStatus(BaseModel):
    connected: bool
    balance: Optional[float] = None
    equity: Optional[float] = None
    available_balance: Optional[float] = None
    
class Position(BaseModel):
    symbol: str
    side: str
    size: float
    leverage: float
    entry_price: float
    current_price: float
    pnl: float
    pnl_percentage: float
    trade_id: Optional[str] = None