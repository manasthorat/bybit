from pybit.unified_trading import HTTP
from typing import Optional, List, Dict, Any
import os
from dotenv import load_dotenv
import asyncio
from datetime import datetime

load_dotenv()

class BybitClient:
    def __init__(self):
        self.api_key = os.getenv("BYBIT_API_KEY")
        self.api_secret = os.getenv("BYBIT_API_SECRET")
        self.testnet = os.getenv("BYBIT_TESTNET", "True").lower() == "true"
        
        self.session = HTTP(
            testnet=self.testnet,
            api_key=self.api_key,
            api_secret=self.api_secret
        )
        
    def check_connection(self) -> Dict[str, Any]:
        """Check if Bybit connection is active"""
        try:
            # Try to get account info
            result = self.session.get_wallet_balance(
                accountType="UNIFIED",
                coin="USDT"
            )
            if result["retCode"] == 0:
                return {
                    "connected": True,
                    "data": result["result"]
                }
            else:
                return {
                    "connected": False,
                    "error": result.get("retMsg", "Unknown error")
                }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account balance and info"""
        try:
            result = self.session.get_wallet_balance(accountType="UNIFIED")

            if result["retCode"] == 0:
                account_data = result["result"]["list"][0]
                total_equity = float(account_data.get("totalEquity") or 0)
                available_balance = float(account_data.get("totalAvailableBalance") or 0)
                
                # Get USDT balance specifically
                coins = account_data.get("coin", [])
                usdt_balance = 0
                for coin in coins:
                    if coin["coin"] == "USDT":
                        usdt_balance = float(coin.get("walletBalance", 0))
                        break
                
                return {
                    "success": True,
                    "balance": usdt_balance,
                    "equity": total_equity,
                    "available_balance": available_balance
                }
            else:
                return {
                    "success": False,
                    "error": result.get("retMsg", "Failed to get account info")
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def place_order(self, symbol: str, side: str, qty: float, 
                   leverage: Optional[int] = None,
                   stop_loss: Optional[float] = None, 
                   take_profit: Optional[float] = None) -> Dict[str, Any]:
        """Place a market order with optional leverage and SL/TP"""
        try:
            # Set leverage if provided
            if leverage and leverage > 0:
                leverage_result = self.set_leverage(symbol, leverage)
                if not leverage_result["success"]:
                    return leverage_result
            
            # Place market order
            order_params = {
                "category": "linear",
                "symbol": symbol,
                "side": side.capitalize(),
                "orderType": "Market",
                "qty": str(qty),
                "timeInForce": "IOC",
                "positionIdx": 0  # One-way mode
            }
            print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
            print(f"Placing order with params: {order_params}")
            print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")

            # Add SL/TP if provided
            if stop_loss:
                order_params["stopLoss"] = str(stop_loss)
            if take_profit:
                order_params["takeProfit"] = str(take_profit)
            
            result = self.session.place_order(**order_params)
            
            if result["retCode"] == 0:
                return {
                    "success": True,
                    "order_id": result["result"]["orderId"],
                    "data": result["result"]
                }
            else:
                return {
                    "success": False,
                    "error": result.get("retMsg", "Order placement failed")
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def set_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """Set leverage for a symbol"""
        try:
            result = self.session.set_leverage(
                category="linear",
                symbol=symbol,
                buyLeverage=str(leverage),
                sellLeverage=str(leverage)
            )
            
            if result["retCode"] == 0:
                return {
                    "success": True,
                    "message": f"Leverage set to {leverage}x for {symbol}"
                }
            else:
                return {
                    "success": False,
                    "error": result.get("retMsg", "Failed to set leverage")
                }
        except Exception as e:

            if "leverage not modified" in str(e):
            # Handle specific error code for leverage setting
                return {
                    "success": True,
                    "message": "leverage already set to this valuel"
                }
            else:
                return {
                    "success": False,
                    "error": f"Error setting leverage: {str(e)}"
                }
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions"""
        try:
            result = self.session.get_positions(
                category="linear",
                settleCoin="USDT"
            )
            
            if result["retCode"] == 0:
                positions = []
                for pos in result["result"]["list"]:
                    if float(pos.get("size", 0)) > 0:
                        entry_price = float(pos.get("avgPrice"))
                        current_price = float(pos.get("markPrice", entry_price))
                        pnl = float(pos.get("unrealisedPnl", 0))
                        leverage = float(pos.get("leverage", 1))
                        position_value = float(pos.get("positionValue", 0))
                        #calculate margin used
                        margin_used = position_value / leverage if leverage > 0 else position_value
                        # Calculate PnL percentage
                        pnl_percentage = (pnl / margin_used) * 100 if margin_used > 0 else 0

                        positions.append({
                            "symbol": pos["symbol"],
                            "side": pos["side"],
                            "size": float(pos["size"]),
                            "leverage": leverage,
                            "entry_price": entry_price,
                            "current_price": current_price,
                            "pnl": pnl,
                            "pnl_percentage": pnl_percentage,
                        })
                return positions
            return []
        except Exception as e:
            print(f"Error getting positions: {e}")
            return []
    
    def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Cancel an open order"""
        try:
            result = self.session.cancel_order(
                category="linear",
                symbol=symbol,
                orderId=order_id
            )
            
            if result["retCode"] == 0:
                return {
                    "success": True,
                    "message": "Order cancelled successfully"
                }
            else:
                return {
                    "success": False,
                    "error": result.get("retMsg", "Failed to cancel order")
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_order_history(self, symbol: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get order history"""
        try:
            params = {
                "category": "linear",
                "limit": limit
            }
            if symbol:
                params["symbol"] = symbol
                
            result = self.session.get_order_history(**params)
            
            if result["retCode"] == 0:
                return result["result"]["list"]
            return []
        except Exception as e:
            print(f"Error getting order history: {e}")
            return []

# Create a singleton instance
bybit_client = BybitClient()