"""Order management system for tracking and executing trades."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import pandas as pd

from packages.core import get_logger
from .brokers import AlpacaBroker


class OrderManager:
    """Manages order lifecycle and tracking."""
    
    def __init__(self, broker: AlpacaBroker):
        self.logger = get_logger(__name__)
        self.broker = broker
        
        # Order tracking
        self.pending_orders: Dict[str, Dict[str, Any]] = {}
        self.completed_orders: Dict[str, Dict[str, Any]] = {}
        
        self.logger.info("Initialized order manager")
    
    async def place_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Place an order and track it.
        
        Args:
            order_data: Order parameters
            
        Returns:
            Order result with tracking information
        """
        symbol = order_data.get("symbol", "")
        self.logger.info(f"Placing order for {symbol}: {order_data['side']} {order_data['qty']}")
        
        try:
            # Validate order data
            validation_result = self._validate_order(order_data)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "symbol": symbol,
                    "error": validation_result["error"],
                    "message": f"Order validation failed: {validation_result['error']}"
                }
            
            # Place order with broker
            broker_result = await self.broker.place_order(order_data)
            
            if broker_result.get("success"):
                order_id = broker_result["order_id"]
                
                # Track the order
                self.pending_orders[order_id] = {
                    **order_data,
                    **broker_result,
                    "placed_at": datetime.now(),
                    "last_checked": datetime.now(),
                    "check_count": 0
                }
                
                self.logger.info(f"Order placed successfully: {order_id}")
                
                # Start monitoring the order
                asyncio.create_task(self._monitor_order(order_id))
                
                return broker_result
            else:
                self.logger.error(f"Failed to place order for {symbol}: {broker_result.get('message', 'Unknown error')}")
                return broker_result
                
        except Exception as e:
            error_msg = f"Exception placing order for {symbol}: {e}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "symbol": symbol,
                "error": str(e),
                "message": error_msg
            }
    
    def _validate_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate order parameters."""
        
        # Required fields
        required_fields = ["symbol", "side", "qty"]
        for field in required_fields:
            if field not in order_data or not order_data[field]:
                return {
                    "valid": False,
                    "error": f"Missing required field: {field}"
                }
        
        # Validate symbol format
        symbol = order_data["symbol"]
        if not symbol.replace(".", "").isalnum() or len(symbol) > 10:
            return {
                "valid": False,
                "error": f"Invalid symbol format: {symbol}"
            }
        
        # Validate side
        if order_data["side"] not in ["buy", "sell"]:
            return {
                "valid": False,
                "error": f"Invalid side: {order_data['side']}"
            }
        
        # Validate quantity
        try:
            qty = int(order_data["qty"])
            if qty <= 0:
                return {
                    "valid": False,
                    "error": f"Invalid quantity: {qty}"
                }
        except (ValueError, TypeError):
            return {
                "valid": False,
                "error": f"Invalid quantity format: {order_data['qty']}"
            }
        
        # Validate order type
        order_type = order_data.get("type", "market")
        if order_type not in ["market", "limit", "stop", "stop_limit"]:
            return {
                "valid": False,
                "error": f"Invalid order type: {order_type}"
            }
        
        # Validate limit price if limit order
        if order_type in ["limit", "stop_limit"]:
            if "limit_price" not in order_data:
                return {
                    "valid": False,
                    "error": "Limit price required for limit orders"
                }
            
            try:
                limit_price = float(order_data["limit_price"])
                if limit_price <= 0:
                    return {
                        "valid": False,
                        "error": f"Invalid limit price: {limit_price}"
                    }
            except (ValueError, TypeError):
                return {
                    "valid": False,
                    "error": f"Invalid limit price format: {order_data['limit_price']}"
                }
        
        return {"valid": True}
    
    async def _monitor_order(self, order_id: str):
        """Monitor an order until it's filled or cancelled."""
        
        max_checks = 60  # Check for up to 1 hour (every minute)
        check_interval = 60  # 1 minute
        
        while order_id in self.pending_orders and self.pending_orders[order_id]["check_count"] < max_checks:
            try:
                await asyncio.sleep(check_interval)
                
                # Get order status from broker
                status = await self.broker.get_order_status(order_id)
                
                if status:
                    order_status = status.get("status", "").lower()
                    
                    # Update tracking info
                    self.pending_orders[order_id]["last_checked"] = datetime.now()
                    self.pending_orders[order_id]["check_count"] += 1
                    self.pending_orders[order_id]["current_status"] = order_status
                    
                    # Check if order is complete
                    if order_status in ["filled", "partially_filled", "cancelled", "rejected"]:
                        # Move to completed orders
                        completed_order = self.pending_orders.pop(order_id)
                        completed_order.update(status)
                        completed_order["completed_at"] = datetime.now()
                        self.completed_orders[order_id] = completed_order
                        
                        self.logger.info(f"Order {order_id} completed with status: {order_status}")
                        
                        # Handle partial fills or other special cases
                        if order_status == "partially_filled":
                            await self._handle_partial_fill(order_id, status)
                        
                        break
                else:
                    self.logger.warning(f"Could not get status for order {order_id}")
                    self.pending_orders[order_id]["check_count"] += 1
                    
            except Exception as e:
                self.logger.error(f"Error monitoring order {order_id}: {e}")
                self.pending_orders[order_id]["check_count"] += 1
        
        # If we've exceeded max checks, mark as timed out
        if order_id in self.pending_orders:
            self.logger.warning(f"Order {order_id} monitoring timed out")
            timed_out_order = self.pending_orders.pop(order_id)
            timed_out_order["timed_out"] = True
            timed_out_order["completed_at"] = datetime.now()
            self.completed_orders[order_id] = timed_out_order
    
    async def _handle_partial_fill(self, order_id: str, status: Dict[str, Any]):
        """Handle partially filled orders."""
        
        filled_qty = status.get("filled_qty", 0)
        original_order = self.completed_orders[order_id]
        original_qty = original_order.get("qty", 0)
        
        remaining_qty = original_qty - filled_qty
        
        self.logger.info(f"Order {order_id} partially filled: {filled_qty}/{original_qty}")
        
        if remaining_qty > 0:
            # Could implement logic to handle remaining quantity
            # For now, just log it
            self.logger.info(f"Order {order_id} has {remaining_qty} shares remaining unfilled")
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        
        if order_id not in self.pending_orders:
            self.logger.warning(f"Order {order_id} not found in pending orders")
            return False
        
        try:
            success = await self.broker.cancel_order(order_id)
            
            if success:
                # Move to completed orders with cancelled status
                cancelled_order = self.pending_orders.pop(order_id)
                cancelled_order["status"] = "cancelled"
                cancelled_order["completed_at"] = datetime.now()
                self.completed_orders[order_id] = cancelled_order
                
                self.logger.info(f"Order {order_id} cancelled successfully")
                return True
            else:
                self.logger.error(f"Failed to cancel order {order_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Exception cancelling order {order_id}: {e}")
            return False
    
    async def cancel_all_pending_orders(self) -> Dict[str, bool]:
        """Cancel all pending orders."""
        
        results = {}
        
        # Create a list of order IDs to avoid modifying dict during iteration
        pending_order_ids = list(self.pending_orders.keys())
        
        for order_id in pending_order_ids:
            results[order_id] = await self.cancel_order(order_id)
        
        return results
    
    def get_pending_orders(self) -> Dict[str, Dict[str, Any]]:
        """Get all pending orders."""
        return self.pending_orders.copy()
    
    def get_completed_orders(self) -> Dict[str, Dict[str, Any]]:
        """Get all completed orders."""
        return self.completed_orders.copy()
    
    def get_order_summary(self) -> Dict[str, Any]:
        """Get summary of order activity."""
        
        completed_orders = list(self.completed_orders.values())
        
        if not completed_orders:
            return {
                "total_orders": 0,
                "pending_orders": len(self.pending_orders),
                "completed_orders": 0,
                "filled_orders": 0,
                "cancelled_orders": 0,
                "success_rate": 0.0
            }
        
        filled_count = len([o for o in completed_orders if o.get("status") == "filled"])
        cancelled_count = len([o for o in completed_orders if o.get("status") == "cancelled"])
        
        return {
            "total_orders": len(self.pending_orders) + len(self.completed_orders),
            "pending_orders": len(self.pending_orders),
            "completed_orders": len(self.completed_orders),
            "filled_orders": filled_count,
            "cancelled_orders": cancelled_count,
            "success_rate": (filled_count / len(completed_orders)) * 100 if completed_orders else 0.0
        }
    
    def get_orders_by_symbol(self, symbol: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get all orders for a specific symbol."""
        
        pending = [order for order in self.pending_orders.values() if order.get("symbol") == symbol]
        completed = [order for order in self.completed_orders.values() if order.get("symbol") == symbol]
        
        return {
            "pending": pending,
            "completed": completed
        }
    
    def export_order_history(self) -> pd.DataFrame:
        """Export order history as DataFrame."""
        
        all_orders = []
        
        # Add pending orders
        for order_id, order in self.pending_orders.items():
            order_record = order.copy()
            order_record["order_id"] = order_id
            order_record["is_pending"] = True
            all_orders.append(order_record)
        
        # Add completed orders
        for order_id, order in self.completed_orders.items():
            order_record = order.copy()
            order_record["order_id"] = order_id
            order_record["is_pending"] = False
            all_orders.append(order_record)
        
        if not all_orders:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_orders)
        
        # Clean up columns and format
        if not df.empty:
            # Ensure consistent column types
            for col in ["placed_at", "completed_at", "last_checked"]:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
            
            for col in ["qty", "filled_qty"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            
            # Sort by placement time
            if "placed_at" in df.columns:
                df = df.sort_values("placed_at", ascending=False)
        
        return df
    
    async def cleanup_old_orders(self, days_old: int = 7):
        """Clean up old completed orders to free memory."""
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        old_orders = []
        for order_id, order in self.completed_orders.items():
            completed_at = order.get("completed_at")
            if completed_at and completed_at < cutoff_date:
                old_orders.append(order_id)
        
        for order_id in old_orders:
            del self.completed_orders[order_id]
        
        if old_orders:
            self.logger.info(f"Cleaned up {len(old_orders)} old orders")
    
    def get_status(self) -> Dict[str, Any]:
        """Get order manager status."""
        
        return {
            "broker_connected": self.broker.is_configured(),
            "pending_orders": len(self.pending_orders),
            "completed_orders": len(self.completed_orders),
            "order_summary": self.get_order_summary()
        }
