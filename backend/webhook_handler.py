from models import WebhookSignal, Trade
from bybit_client import bybit_client
from sqlalchemy.ext.asyncio import AsyncSession
import json
from datetime import datetime
from typing import Dict, Any
import hashlib
import hmac
from config import config

class WebhookHandler:
    def __init__(self):
        self.client = bybit_client
        
    def verify_webhook(self, payload: str, signature: str) -> bool:
        """Verify webhook signature for security"""
        expected_signature = hmac.new(
            config.WEBHOOK_SECRET.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected_signature, signature)
    
    async def process_signal(self, signal: WebhookSignal, db: AsyncSession, 
                           auto_trading_enabled: bool) -> Dict[str, Any]:
        """Process incoming webhook signal"""
        
        # Create trade record
        trade = Trade(
            symbol=signal.symbol,
            side=signal.action.upper(),
            quantity=signal.quantity or config.DEFAULT_POSITION_SIZE,
            leverage=signal.leverage,  # Add leverage
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            status="pending",
            webhook_data=signal.json()
        )
        
        # Check if auto trading is enabled
        if not auto_trading_enabled:
            trade.status = "rejected"
            trade.reason = "Auto trading is disabled"
            db.add(trade)
            await db.commit()
            return {
                "success": False,
                "message": "Trade recorded but not executed - auto trading disabled",
                "trade_id": trade.id
            }
        
        # Check account connection
        connection = self.client.check_connection()
        if not connection["connected"]:
            trade.status = "rejected"
            trade.reason = f"Bybit connection failed: {connection.get('error', 'Unknown error')}"
            db.add(trade)
            await db.commit()
            return {
                "success": False,
                "message": "Trade rejected - Bybit connection failed",
                "trade_id": trade.id
            }
        
        # Calculate position size based on risk if not provided
        if not signal.quantity:
            account_info = self.client.get_account_info()
            if account_info["success"]:
                # Use 1% of balance as default
                trade.quantity = account_info["balance"] * 0.01
            else:
                trade.quantity = config.DEFAULT_POSITION_SIZE
        
        # Place the order
        order_result = self.client.place_order(
            symbol=signal.symbol,
            side=signal.action,
            qty=trade.quantity,
            leverage=signal.leverage,  # Pass leverage
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit
        )
    
        if order_result["success"]:
            trade.trade_id = order_result["order_id"]
            trade.status = "filled"
            trade.reason = "Order placed successfully"
            
            # Fetch the entry price from the position
            try:
                # Small delay to ensure position is created
                import time
                time.sleep(0.5)
                
                position_result = self.client.session.get_positions(
                    category="linear",
                    symbol=signal.symbol
                )
                
                if position_result["retCode"] == 0 and position_result["result"]["list"]:
                    position_info = position_result["result"]["list"][0]
                    trade.entry_price = float(position_info.get("avgPrice", 0))
                else:
                    # Fallback to data from order result if available
                    trade.entry_price = float(order_result["data"].get("price", 0))
            except:
                # If fetching fails, use the price from order result as fallback
                trade.entry_price = float(order_result["data"].get("price", 0))
        else:
            trade.status = "rejected"
            trade.reason = f"Order failed: {order_result.get('error', 'Unknown error')}"
        
        db.add(trade)
        await db.commit()
        
        return {
            "success": order_result["success"],
            "message": trade.reason,
            "trade_id": trade.id,
            "order_id": trade.trade_id if order_result["success"] else None
        }
    
    async def update_trade_status(self, trade_id: str, db: AsyncSession):
        """Update trade status from Bybit"""
        # This would be called periodically to update trade statuses
        # Implementation depends on specific requirements
        pass

webhook_handler = WebhookHandler()