from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
import json
import uvicorn
from fastapi import Query
from datetime import datetime

from database import init_db, get_db
from models import (
    WebhookSignal, TradeResponse, SettingsUpdate, 
    AccountStatus, Position, Trade, Settings
)
from bybit_client import bybit_client
from webhook_handler import webhook_handler
from config import config

app = FastAPI(title="Trading System API")
from pydantic import BaseModel

# Add this class after your imports
class ClosePositionRequest(BaseModel):
    side: str
    size: float
# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event
@app.on_event("startup")
async def startup_event():
    await init_db()
    print("Database initialized")

# Root endpoint
@app.get("/")
async def root():
    return FileResponse("../frontend/index.html")

# Serve static files
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

# API Endpoints

@app.get("/api/account/status", response_model=AccountStatus)
async def get_account_status():
    """Check if Bybit account is connected and get balance"""
    connection = bybit_client.check_connection()
    
    if connection["connected"]:
        account_info = bybit_client.get_account_info()
        ##print(f"Account Status/Info: {account_info}")
        if account_info["success"]:
            return AccountStatus(
                connected=True,
                balance=account_info["balance"],
                equity=account_info["equity"],
                available_balance=account_info["available_balance"]
            )
    
    return AccountStatus(connected=False)

@app.get("/api/settings")
async def get_settings(db: AsyncSession = Depends(get_db)):
    """Get current trading settings"""
    settings = await db.get(Settings, 1)
    if settings:
        return {
            "auto_trading_enabled": settings.auto_trading_enabled,
            "max_position_size": settings.max_position_size,
            "risk_percentage": settings.risk_percentage
        }
    return {"error": "Settings not found"}

@app.put("/api/settings")
async def update_settings(
    settings_update: SettingsUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update trading settings"""
    settings = await db.get(Settings, 1)
    if not settings:
        return {"error": "Settings not found"}
    
    if settings_update.auto_trading_enabled is not None:
        settings.auto_trading_enabled = settings_update.auto_trading_enabled
    if settings_update.max_position_size is not None:
        settings.max_position_size = settings_update.max_position_size
    if settings_update.risk_percentage is not None:
        settings.risk_percentage = settings_update.risk_percentage
    
    await db.commit()
    await db.refresh(settings)
    
    return {
        "success": True,
        "auto_trading_enabled": settings.auto_trading_enabled,
        "max_position_size": settings.max_position_size,
        "risk_percentage": settings.risk_percentage
    }

@app.get("/api/positions", response_model=List[Position])
async def get_open_positions():
    """Get all open positions from Bybit"""
    positions = bybit_client.get_positions()
    return [Position(**pos) for pos in positions]

@app.get("/api/trades", response_model=List[TradeResponse])
async def get_trade_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Get historical trades from database"""
    result = await db.execute(
        select(Trade).order_by(desc(Trade.created_at)).limit(limit)
    )
    
    trades = result.scalars().all()

    return trades

@app.delete("/api/order/{order_id}")
async def cancel_order(
    order_id: str,
    symbol: str,
    db: AsyncSession = Depends(get_db)
):
    """Cancel an open order"""
    result = bybit_client.cancel_order(symbol, order_id)
    
    if result["success"]:
        # Update trade status in database
        stmt = select(Trade).where(Trade.trade_id == order_id)
        result = await db.execute(stmt)
        trade = result.scalar_one_or_none()
        
        if trade:
            trade.status = "cancelled"
            trade.reason = "Cancelled by user"
            await db.commit()
    
    return result



@app.post("/api/positions/{symbol}/close")
async def close_position(
    symbol: str,
    request: ClosePositionRequest,  # Use Pydantic model for request body
    db: AsyncSession = Depends(get_db)
):
    """Close a position by placing an opposite order"""
    # Determine opposite side
    opposite_side = "sell" if request.side.lower() == "buy" else "buy"
    
    # Place market order to close position
    result = bybit_client.place_order(
        symbol=symbol,
        side=opposite_side,
        qty=request.size
    )
    
    print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$4")

    print(result)
    print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
    if result["success"]:
        # Record the closing trade
        trade = Trade(
            trade_id=result["order_id"],
            symbol=symbol,
            side=opposite_side.upper(),
            quantity=request.size,
            status="filled",
            reason="Position closed by user",
            created_at=datetime.utcnow()
        )
        db.add(trade)
        await db.commit()
        
        return {
            "success": True,
            "message": "Position closed successfully",
            "order_id": result["order_id"]
        }
    else:
        return {
            "success": False,
            "error": result.get("error", "Failed to close position")
        }

@app.post("/api/webhook")
async def receive_webhook(
    request: Request,
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    print(f"Received webhook with token: {token}")
    if token != config.WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid token")
    """Receive and process TradingView webhook"""
    # Get raw body for signature verification
    body = await request.body()
    body_str = body.decode()
    
    
    # Parse webhook data
    try:
        data = json.loads(body_str)
        signal = WebhookSignal(**data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid webhook data: {str(e)}")
    
    # Get current settings
    settings = await db.get(Settings, 1)
    if not settings:
        raise HTTPException(status_code=500, detail="Settings not found")
    
    # Process the signal
    result = await webhook_handler.process_signal(
        signal, 
        db, 
        settings.auto_trading_enabled
    )
    
    return result

@app.get("/api/trades/{trade_id}")
async def get_trade_details(
    trade_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get details of a specific trade"""
    trade = await db.get(Trade, trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    return TradeResponse.from_orm(trade)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True
    )