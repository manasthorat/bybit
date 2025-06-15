from pybit.unified_trading import HTTP
from typing import Optional, List, Dict, Any
import os
from dotenv import load_dotenv
import asyncio
from datetime import datetime
from decimal import Decimal, ROUND_DOWN

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
        
        # Cache for instrument info
        self._instrument_cache = {}
        
    def get_instrument_info(self, symbol: str) -> Dict[str, Any]:
        """Get trading rules for a symbol (min order qty, tick size, etc.)"""
        # Check cache first
        if symbol in self._instrument_cache:
            return self._instrument_cache[symbol]
            
        try:
            result = self.session.get_instruments_info(
                category="linear",
                symbol=symbol
            )
            
            if result["retCode"] == 0 and result["result"]["list"]:
                instrument = result["result"]["list"][0]
                
                # Extract important trading rules
                lot_size_filter = instrument.get("lotSizeFilter", {})
                price_filter = instrument.get("priceFilter", {})
                
                info = {
                    "min_order_qty": float(lot_size_filter.get("minOrderQty", 0.001)),
                    "max_order_qty": float(lot_size_filter.get("maxOrderQty", 10000)),
                    "qty_step": float(lot_size_filter.get("qtyStep", 0.001)),
                    "tick_size": float(price_filter.get("tickSize", 0.01)),
                    "min_price": float(price_filter.get("minPrice", 0.01)),
                    "max_price": float(price_filter.get("maxPrice", 999999)),
                }
                
                # Cache the result
                self._instrument_cache[symbol] = info
                return info
            else:
                # Return default values if can't get info
                return {
                    "min_order_qty": 0.001,
                    "max_order_qty": 10000,
                    "qty_step": 0.001,
                    "tick_size": 0.01,
                    "min_price": 0.01,
                    "max_price": 999999,
                }
        except Exception as e:
            print(f"Error getting instrument info: {e}")
            # Return default values
            return {
                "min_order_qty": 0.001,
                "max_order_qty": 10000,
                "qty_step": 0.001,
                "tick_size": 0.01,
                "min_price": 0.01,
                "max_price": 999999,
            }
    
    def adjust_quantity(self, symbol: str, quantity: float) -> float:
        """Adjust quantity to meet symbol's trading rules"""
        info = self.get_instrument_info(symbol)
        
        # Use Decimal for precise calculations
        qty_decimal = Decimal(str(quantity))
        qty_step = Decimal(str(info["qty_step"]))
        min_qty = Decimal(str(info["min_order_qty"]))
        max_qty = Decimal(str(info["max_order_qty"]))
        
        # Round down to nearest step
        adjusted_qty = (qty_decimal // qty_step) * qty_step
        
        # Ensure within limits
        if adjusted_qty < min_qty:
            adjusted_qty = min_qty
        elif adjusted_qty > max_qty:
            adjusted_qty = max_qty
            
        # Return as float with appropriate precision
        return float(adjusted_qty)
    
    def adjust_price(self, symbol: str, price: float) -> float:
        """Adjust price to meet symbol's tick size"""
        info = self.get_instrument_info(symbol)
        
        # Use Decimal for precise calculations
        price_decimal = Decimal(str(price))
        tick_size = Decimal(str(info["tick_size"]))
        
        # Round to nearest tick
        adjusted_price = round(price_decimal / tick_size) * tick_size
        
        return float(adjusted_price)
        
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
            # Adjust quantity to meet trading rules
            adjusted_qty = self.adjust_quantity(symbol, qty)
            
            print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
            print(f"Original qty: {qty}, Adjusted qty: {adjusted_qty}")
            print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
            
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
                "qty": str(adjusted_qty),
                "timeInForce": "IOC",
                "positionIdx": 0  # One-way mode
            }
            
            # Add SL/TP if provided (adjust prices to tick size)
            if stop_loss:
                adjusted_sl = self.adjust_price(symbol, stop_loss)
                order_params["stopLoss"] = str(adjusted_sl)
            if take_profit:
                adjusted_tp = self.adjust_price(symbol, take_profit)
                order_params["takeProfit"] = str(adjusted_tp)
            
            print(f"Placing order with params: {order_params}")
            
            result = self.session.place_order(**order_params)
            
            if result["retCode"] == 0:
                return {
                    "success": True,
                    "order_id": result["result"]["orderId"],
                    "data": result["result"],
                    "adjusted_qty": adjusted_qty
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
                    "message": "leverage already set to this value"
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
