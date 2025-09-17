"""Alpaca broker integration for trade execution."""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import aiohttp
import json

from packages.core import get_logger
from packages.core.config import settings


class AlpacaBroker:
    """Alpaca API broker integration."""
    
    def __init__(self, paper_trading: bool = True):
        self.logger = get_logger(__name__)
        self.paper_trading = paper_trading
        
        # API configuration
        self.api_key = settings.ALPACA_API_KEY
        self.secret_key = settings.ALPACA_SECRET_KEY
        
        if not self.api_key or not self.secret_key:
            self.logger.warning("Alpaca API keys not configured")
        
        # API endpoints
        if paper_trading:
            self.base_url = "https://paper-api.alpaca.markets"
            self.data_url = "https://data.alpaca.markets"
        else:
            self.base_url = "https://api.alpaca.markets"
            self.data_url = "https://data.alpaca.markets"
        
        self.headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
            "Content-Type": "application/json"
        }
        
        self.logger.info(f"Initialized Alpaca broker (paper: {paper_trading})")
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/v2/account",
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "account_id": data.get("id"),
                            "buying_power": float(data.get("buying_power", 0)),
                            "portfolio_value": float(data.get("portfolio_value", 0)),
                            "cash": float(data.get("cash", 0)),
                            "day_pnl": float(data.get("unrealized_pl", 0)),
                            "status": data.get("status"),
                            "pattern_day_trader": data.get("pattern_day_trader", False)
                        }
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Failed to get account info: {response.status} - {error_text}")
                        return {}
                        
        except Exception as e:
            self.logger.error(f"Exception getting account info: {e}")
            return {}
    
    async def get_market_status(self) -> Dict[str, Any]:
        """Get market status (open/closed)."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/v2/clock",
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "is_open": data.get("is_open", False),
                            "next_open": data.get("next_open"),
                            "next_close": data.get("next_close"),
                            "timestamp": data.get("timestamp")
                        }
                    else:
                        self.logger.error(f"Failed to get market status: {response.status}")
                        return {"is_open": False}
                        
        except Exception as e:
            self.logger.error(f"Exception getting market status: {e}")
            return {"is_open": False}
    
    async def place_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Place an order with Alpaca.
        
        Args:
            order_data: Order parameters
            
        Returns:
            Order result with status and details
        """
        try:
            # Prepare order payload
            payload = {
                "symbol": order_data["symbol"],
                "qty": str(order_data["qty"]),
                "side": order_data["side"],
                "type": order_data.get("type", "market"),
                "time_in_force": order_data.get("time_in_force", "day")
            }
            
            # Add limit price if specified
            if order_data.get("type") == "limit" and "limit_price" in order_data:
                payload["limit_price"] = str(order_data["limit_price"])
            
            # Add stop price if specified
            if "stop_price" in order_data:
                payload["stop_price"] = str(order_data["stop_price"])
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/v2/orders",
                    headers=self.headers,
                    json=payload
                ) as response:
                    
                    response_data = await response.json()
                    
                    if response.status == 201:  # Created
                        return {
                            "success": True,
                            "order_id": response_data.get("id"),
                            "symbol": response_data.get("symbol"),
                            "side": response_data.get("side"),
                            "qty": int(response_data.get("qty", 0)),
                            "type": response_data.get("type"),
                            "status": response_data.get("status"),
                            "created_at": response_data.get("created_at"),
                            "filled_price": float(response_data.get("filled_avg_price", 0)) if response_data.get("filled_avg_price") else None,
                            "message": "Order placed successfully"
                        }
                    else:
                        error_msg = response_data.get("message", f"HTTP {response.status}")
                        return {
                            "success": False,
                            "symbol": order_data["symbol"],
                            "error": error_msg,
                            "message": f"Failed to place order: {error_msg}"
                        }
                        
        except Exception as e:
            return {
                "success": False,
                "symbol": order_data.get("symbol", ""),
                "error": str(e),
                "message": f"Exception placing order: {e}"
            }
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get status of a specific order."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/v2/orders/{order_id}",
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "order_id": data.get("id"),
                            "symbol": data.get("symbol"),
                            "status": data.get("status"),
                            "filled_qty": int(data.get("filled_qty", 0)),
                            "filled_price": float(data.get("filled_avg_price", 0)) if data.get("filled_avg_price") else None,
                            "created_at": data.get("created_at"),
                            "updated_at": data.get("updated_at")
                        }
                    else:
                        self.logger.error(f"Failed to get order status: {response.status}")
                        return {}
                        
        except Exception as e:
            self.logger.error(f"Exception getting order status: {e}")
            return {}
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a specific order."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{self.base_url}/v2/orders/{order_id}",
                    headers=self.headers
                ) as response:
                    if response.status == 204:  # No content (success)
                        self.logger.info(f"Order {order_id} cancelled successfully")
                        return True
                    else:
                        self.logger.error(f"Failed to cancel order: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Exception cancelling order: {e}")
            return False
    
    async def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """Get all current positions."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/v2/positions",
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        positions_data = await response.json()
                        
                        positions = {}
                        for pos in positions_data:
                            symbol = pos.get("symbol")
                            positions[symbol] = {
                                "symbol": symbol,
                                "qty": int(pos.get("qty", 0)),
                                "side": "long" if int(pos.get("qty", 0)) > 0 else "short",
                                "market_value": float(pos.get("market_value", 0)),
                                "current_price": float(pos.get("current_price", 0)),
                                "avg_fill_price": float(pos.get("avg_entry_price", 0)),
                                "unrealized_pl": float(pos.get("unrealized_pl", 0)),
                                "unrealized_plpc": float(pos.get("unrealized_plpc", 0)),
                                "cost_basis": float(pos.get("cost_basis", 0))
                            }
                        
                        return positions
                    else:
                        self.logger.error(f"Failed to get positions: {response.status}")
                        return {}
                        
        except Exception as e:
            self.logger.error(f"Exception getting positions: {e}")
            return {}
    
    async def close_position(self, symbol: str, qty: Optional[int] = None) -> Dict[str, Any]:
        """Close a position (all or partial)."""
        try:
            url = f"{self.base_url}/v2/positions/{symbol}"
            params = {}
            if qty:
                params["qty"] = str(qty)
            
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    url,
                    headers=self.headers,
                    params=params
                ) as response:
                    if response.status == 207:  # Multi-status (success)
                        data = await response.json()
                        return {
                            "success": True,
                            "symbol": symbol,
                            "order_id": data.get("id"),
                            "message": "Position close order placed"
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "symbol": symbol,
                            "message": f"Failed to close position: {error_text}"
                        }
                        
        except Exception as e:
            return {
                "success": False,
                "symbol": symbol,
                "message": f"Exception closing position: {e}"
            }
    
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get real-time quote for a symbol."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.data_url}/v2/stocks/{symbol}/quotes/latest",
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        quote_data = data.get("quote", {})
                        return {
                            "symbol": symbol,
                            "bid": float(quote_data.get("bp", 0)),
                            "ask": float(quote_data.get("ap", 0)),
                            "bid_size": int(quote_data.get("bs", 0)),
                            "ask_size": int(quote_data.get("as", 0)),
                            "timestamp": quote_data.get("t")
                        }
                    else:
                        self.logger.error(f"Failed to get quote for {symbol}: {response.status}")
                        return {}
                        
        except Exception as e:
            self.logger.error(f"Exception getting quote for {symbol}: {e}")
            return {}
    
    async def get_bars(
        self, 
        symbol: str, 
        timeframe: str = "1Day", 
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get historical bars for a symbol."""
        try:
            params = {
                "symbols": symbol,
                "timeframe": timeframe,
                "limit": str(limit)
            }
            
            if start:
                params["start"] = start
            if end:
                params["end"] = end
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.data_url}/v2/stocks/bars",
                    headers=self.headers,
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        bars_data = data.get("bars", {}).get(symbol, [])
                        
                        bars = []
                        for bar in bars_data:
                            bars.append({
                                "timestamp": bar.get("t"),
                                "open": float(bar.get("o", 0)),
                                "high": float(bar.get("h", 0)),
                                "low": float(bar.get("l", 0)),
                                "close": float(bar.get("c", 0)),
                                "volume": int(bar.get("v", 0))
                            })
                        
                        return bars
                    else:
                        self.logger.error(f"Failed to get bars for {symbol}: {response.status}")
                        return []
                        
        except Exception as e:
            self.logger.error(f"Exception getting bars for {symbol}: {e}")
            return []
    
    def is_configured(self) -> bool:
        """Check if broker is properly configured."""
        return bool(self.api_key and self.secret_key)
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information."""
        return {
            "broker": "Alpaca",
            "paper_trading": self.paper_trading,
            "base_url": self.base_url,
            "configured": self.is_configured()
        }
