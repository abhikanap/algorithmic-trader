"""Execution Engine for trade execution and portfolio management."""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any, Optional, List
import pandas as pd

from packages.core import get_logger
from packages.core.config import settings
from packages.core.models import TradeSignal, Order, OrderSide, OrderType, OrderStatus, Position

try:
    import alpaca_trade_api as tradeapi
    from alpaca_trade_api.rest import APIError
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False


class ExecutionEngine:
    """
    Main execution engine that handles trade execution, order management,
    and portfolio rebalancing using Alpaca API.
    """
    
    def __init__(self, paper_trading: bool = True):
        self.logger = get_logger(__name__)
        self.paper_trading = paper_trading
        
        if not ALPACA_AVAILABLE:
            self.logger.warning("Alpaca API not available. Install alpaca-trade-api to enable live trading.")
            self.api = None
        else:
            # Initialize Alpaca API
            self.api = self._initialize_alpaca_api()
        
        self.logger.info(f"Initialized execution engine (paper_trading: {paper_trading})")
    
    def _initialize_alpaca_api(self):
        """Initialize Alpaca API connection."""
        try:
            api = tradeapi.REST(
                key_id=settings.alpaca.api_key,
                secret_key=settings.alpaca.secret_key,
                base_url=settings.alpaca.base_url,
                api_version='v2'
            )
            
            # Test connection
            account = api.get_account()
            self.logger.info(f"Connected to Alpaca API. Account: {account.status}")
            
            return api
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Alpaca API: {e}")
            return None
    
    async def execute_signals(
        self,
        signals: List[TradeSignal],
        date: Optional[str] = None,
        save_artifacts: bool = True
    ) -> Dict[str, Any]:
        """
        Execute trade signals by placing orders and managing positions.
        
        Args:
            signals: List of trade signals from strategy engine
            date: Date string (YYYY-MM-DD). If None, uses today
            save_artifacts: Whether to save execution results
            
        Returns:
            Dictionary containing execution results and metadata
        """
        start_time = datetime.now()
        
        if date is None:
            date = start_time.strftime("%Y-%m-%d")
        
        self.logger.info(f"Starting execution for {len(signals)} signals on {date}")
        
        try:
            if not self.api:
                raise ValueError("Alpaca API not available")
            
            # Stage 1: Validate signals and check market status
            validated_signals = await self._validate_signals(signals)
            
            # Stage 2: Check current positions and calculate position changes
            position_changes = await self._calculate_position_changes(validated_signals)
            
            # Stage 3: Execute orders
            orders_results = await self._execute_orders(position_changes)
            
            # Stage 4: Monitor order fills and update positions
            fill_results = await self._monitor_order_fills(orders_results)
            
            # Stage 5: Generate portfolio snapshot
            portfolio_snapshot = await self._generate_portfolio_snapshot()
            
            # Prepare results
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            metadata = {
                "date": date,
                "duration_seconds": round(duration, 2),
                "signals_received": len(signals),
                "signals_validated": len(validated_signals),
                "orders_placed": len([o for o in orders_results if o.get("success")]),
                "orders_filled": len([f for f in fill_results if f.get("filled")]),
                "execution_statistics": self._generate_execution_statistics(orders_results, fill_results)
            }
            
            # Save artifacts if requested
            saved_files = {}
            if save_artifacts:
                self.logger.info("Saving execution artifacts...")
                saved_files = self._save_artifacts(
                    signals, orders_results, fill_results, portfolio_snapshot, date, metadata
                )
                metadata["saved_files"] = saved_files
            
            result = {
                "success": True,
                "orders": orders_results,
                "fills": fill_results,
                "portfolio": portfolio_snapshot,
                "metadata": metadata,
                "saved_files": saved_files
            }
            
            self.logger.info(
                f"Execution completed successfully in {duration:.1f}s. "
                f"Placed {metadata['orders_placed']} orders, {metadata['orders_filled']} filled"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Execution failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return {
                "success": False,
                "error": error_msg,
                "orders": [],
                "fills": [],
                "portfolio": None,
                "metadata": {
                    "date": date,
                    "error": str(e),
                    "duration_seconds": (datetime.now() - start_time).total_seconds()
                },
                "saved_files": {}
            }
    
    async def _validate_signals(self, signals: List[TradeSignal]) -> List[TradeSignal]:
        """Validate trade signals before execution."""
        validated = []
        
        # Check market status
        clock = self.api.get_clock()
        if not clock.is_open and not self.paper_trading:
            self.logger.warning("Market is closed, limiting execution to paper trading")
        
        for signal in signals:
            try:
                # Validate symbol exists and is tradable
                asset = self.api.get_asset(signal.symbol)
                if not asset.tradable:
                    self.logger.warning(f"Symbol {signal.symbol} is not tradable, skipping")
                    continue
                
                # Validate position size
                if signal.position_size <= 0:
                    self.logger.warning(f"Invalid position size for {signal.symbol}: {signal.position_size}")
                    continue
                
                # Check if we have sufficient buying power
                account = self.api.get_account()
                if float(account.buying_power) < signal.position_size:
                    self.logger.warning(f"Insufficient buying power for {signal.symbol}")
                    continue
                
                validated.append(signal)
                
            except Exception as e:
                self.logger.warning(f"Failed to validate signal for {signal.symbol}: {e}")
                continue
        
        self.logger.info(f"Validated {len(validated)}/{len(signals)} signals")
        return validated
    
    async def _calculate_position_changes(self, signals: List[TradeSignal]) -> List[Dict[str, Any]]:
        """Calculate position changes needed to match target allocations."""
        position_changes = []
        
        # Get current positions
        positions = self.api.list_positions()
        current_positions = {pos.symbol: float(pos.qty) for pos in positions}
        
        for signal in signals:
            symbol = signal.symbol
            current_qty = current_positions.get(symbol, 0.0)
            
            # Calculate target quantity based on position size and current price
            try:
                # Get current price
                latest_trade = self.api.get_latest_trade(symbol)
                current_price = float(latest_trade.price)
                
                # Calculate target quantity
                target_qty = int(signal.position_size / current_price)
                
                # Calculate quantity change needed
                qty_change = target_qty - current_qty
                
                if abs(qty_change) >= 1:  # Only execute if change is at least 1 share
                    position_changes.append({
                        "signal": signal,
                        "symbol": symbol,
                        "current_qty": current_qty,
                        "target_qty": target_qty,
                        "qty_change": qty_change,
                        "current_price": current_price,
                        "order_side": "buy" if qty_change > 0 else "sell",
                        "order_qty": abs(qty_change)
                    })
                
            except Exception as e:
                self.logger.warning(f"Failed to calculate position change for {symbol}: {e}")
                continue
        
        self.logger.info(f"Calculated {len(position_changes)} position changes")
        return position_changes
    
    async def _execute_orders(self, position_changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute orders for position changes."""
        orders_results = []
        
        for change in position_changes:
            try:
                symbol = change["symbol"]
                side = change["order_side"]
                qty = change["order_qty"]
                signal = change["signal"]
                
                # Determine order type based on bucket and time segment  
                order_type = self._determine_order_type(signal)
                
                # Calculate limit price if needed
                limit_price = None
                if order_type == "limit":
                    limit_price = self._calculate_limit_price(change["current_price"], side)
                
                # Place order
                order_request = {
                    "symbol": symbol,
                    "qty": qty,
                    "side": side,
                    "type": order_type,
                    "time_in_force": "day"
                }
                
                if limit_price:
                    order_request["limit_price"] = limit_price
                
                # Add stop loss if configured
                if settings.trading.stop_loss_atr_multiplier > 0:
                    stop_loss_price = self._calculate_stop_loss_price(
                        change["current_price"], side, signal
                    )
                    if stop_loss_price:
                        order_request["stop_loss"] = {"stop_price": stop_loss_price}
                
                # Place the order
                order = self.api.submit_order(**order_request)
                
                orders_results.append({
                    "success": True,
                    "order_id": order.id,
                    "symbol": symbol,
                    "side": side,
                    "qty": qty,
                    "type": order_type,
                    "limit_price": limit_price,
                    "status": order.status,
                    "signal": signal,
                    "submitted_at": datetime.now().isoformat()
                })
                
                self.logger.info(f"Placed {side} order for {qty} shares of {symbol} (Order ID: {order.id})")
                
            except Exception as e:
                self.logger.error(f"Failed to place order for {change['symbol']}: {e}")
                orders_results.append({
                    "success": False,
                    "symbol": change["symbol"],
                    "error": str(e),
                    "signal": change["signal"]
                })
        
        return orders_results
    
    def _determine_order_type(self, signal: TradeSignal) -> str:
        """Determine order type based on signal characteristics."""
        # High volatility or gap plays use limit orders
        atr_pct = signal.metadata.get("atr_pct", 0)
        gap_pct = abs(signal.metadata.get("gap_pct", 0))
        
        if atr_pct > 8.0 or gap_pct > 5.0:
            return "limit"
        
        # Market open time segment use limit orders
        if signal.time_segment == "open":
            return "limit"
        
        # Default to market orders for liquid stocks
        return "market"
    
    def _calculate_limit_price(self, current_price: float, side: str, buffer_pct: float = 0.5) -> float:
        """Calculate limit price with buffer."""
        buffer = current_price * (buffer_pct / 100)
        
        if side == "buy":
            return round(current_price + buffer, 2)
        else:
            return round(current_price - buffer, 2)
    
    def _calculate_stop_loss_price(self, current_price: float, side: str, signal: TradeSignal) -> Optional[float]:
        """Calculate stop loss price based on ATR."""
        try:
            atr_pct = signal.metadata.get("atr_pct", 0)
            if atr_pct <= 0:
                return None
            
            atr_multiplier = settings.trading.stop_loss_atr_multiplier
            stop_distance = current_price * (atr_pct / 100) * atr_multiplier
            
            if side == "buy":
                return round(current_price - stop_distance, 2)
            else:
                return round(current_price + stop_distance, 2)
                
        except Exception:
            return None
    
    async def _monitor_order_fills(self, orders_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Monitor order fills and update status."""
        fill_results = []
        
        # Wait a bit for orders to potentially fill
        await asyncio.sleep(2)
        
        for order_result in orders_results:
            if not order_result.get("success"):
                continue
            
            try:
                order_id = order_result["order_id"]
                order = self.api.get_order(order_id)
                
                fill_results.append({
                    "order_id": order_id,
                    "symbol": order_result["symbol"],
                    "status": order.status,
                    "filled": order.status in ["filled", "partially_filled"],
                    "filled_qty": float(order.filled_qty or 0),
                    "filled_avg_price": float(order.filled_avg_price or 0),
                    "updated_at": datetime.now().isoformat()
                })
                
            except Exception as e:
                self.logger.error(f"Failed to check order status for {order_result['order_id']}: {e}")
                fill_results.append({
                    "order_id": order_result["order_id"],
                    "symbol": order_result["symbol"],
                    "status": "unknown",
                    "filled": False,
                    "error": str(e)
                })
        
        return fill_results
    
    async def _generate_portfolio_snapshot(self) -> Dict[str, Any]:
        """Generate current portfolio snapshot."""
        try:
            account = self.api.get_account()
            positions = self.api.list_positions()
            orders = self.api.list_orders(status='open')
            
            portfolio = {
                "account": {
                    "total_equity": float(account.equity),
                    "buying_power": float(account.buying_power),
                    "day_pnl": float(account.unrealized_pl),
                    "total_pnl": float(account.unrealized_pl),
                    "day_pnl_pct": float(account.unrealized_plpc) * 100
                },
                "positions": [
                    {
                        "symbol": pos.symbol,
                        "qty": float(pos.qty),
                        "market_value": float(pos.market_value),
                        "unrealized_pl": float(pos.unrealized_pl),
                        "unrealized_plpc": float(pos.unrealized_plpc) * 100
                    }
                    for pos in positions
                ],
                "open_orders": [
                    {
                        "id": order.id,
                        "symbol": order.symbol,
                        "side": order.side,
                        "qty": float(order.qty),
                        "type": order.order_type,
                        "status": order.status
                    }
                    for order in orders
                ],
                "timestamp": datetime.now().isoformat()
            }
            
            return portfolio
            
        except Exception as e:
            self.logger.error(f"Failed to generate portfolio snapshot: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def _generate_execution_statistics(self, orders_results: List[Dict], fill_results: List[Dict]) -> Dict[str, Any]:
        """Generate execution statistics."""
        successful_orders = [o for o in orders_results if o.get("success")]
        filled_orders = [f for f in fill_results if f.get("filled")]
        
        stats = {
            "order_success_rate": len(successful_orders) / len(orders_results) if orders_results else 0,
            "fill_rate": len(filled_orders) / len(successful_orders) if successful_orders else 0,
            "order_types": {},
            "bucket_distribution": {},
            "avg_position_size": 0
        }
        
        # Order type distribution
        for order in successful_orders:
            order_type = order.get("type", "unknown")
            stats["order_types"][order_type] = stats["order_types"].get(order_type, 0) + 1
        
        # Bucket distribution
        for order in successful_orders:
            bucket = order.get("signal", {}).get("bucket", "unknown")
            stats["bucket_distribution"][bucket] = stats["bucket_distribution"].get(bucket, 0) + 1
        
        # Average position size
        position_sizes = [order.get("signal", {}).get("position_size", 0) for order in successful_orders]
        stats["avg_position_size"] = sum(position_sizes) / len(position_sizes) if position_sizes else 0
        
        return stats
    
    def _save_artifacts(self, signals, orders_results, fill_results, portfolio, date, metadata) -> Dict[str, str]:
        """Save execution artifacts."""
        artifacts_dir = settings.artifacts_path / "execution" / date
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = {}
        
        try:
            # Save execution summary as JSONL
            jsonl_path = artifacts_dir / "execution.jsonl"
            self._save_execution_as_jsonl(orders_results, fill_results, jsonl_path)
            saved_files["jsonl"] = str(jsonl_path)
            
            # Save portfolio snapshot
            import json
            portfolio_path = artifacts_dir / "portfolio.json"
            with open(portfolio_path, "w") as f:
                json.dump(portfolio, f, indent=2)
            saved_files["portfolio"] = str(portfolio_path)
            
            # Save markdown report
            report_path = artifacts_dir / "REPORT.md"
            self._generate_markdown_report(orders_results, fill_results, portfolio, metadata, report_path)
            saved_files["report"] = str(report_path)
            
            self.logger.info(f"Execution artifacts saved to: {artifacts_dir}")
            
        except Exception as e:
            self.logger.error(f"Error saving execution artifacts: {e}")
        
        return saved_files
    
    def _save_execution_as_jsonl(self, orders_results, fill_results, path: Path) -> None:
        """Save execution results as JSONL."""
        import json
        
        # Create fill lookup
        fills_by_order = {f.get("order_id"): f for f in fill_results}
        
        with open(path, "w") as f:
            for order in orders_results:
                if not order.get("success"):
                    continue
                
                order_id = order.get("order_id")
                fill_info = fills_by_order.get(order_id, {})
                
                record = {
                    "order_id": order_id,
                    "symbol": order["symbol"],
                    "side": order["side"],
                    "qty": order["qty"],
                    "type": order["type"],
                    "status": fill_info.get("status", "unknown"),
                    "filled": fill_info.get("filled", False),
                    "filled_qty": fill_info.get("filled_qty", 0),
                    "filled_avg_price": fill_info.get("filled_avg_price", 0),
                    "bucket": order.get("signal", {}).get("bucket"),
                    "time_segment": order.get("signal", {}).get("time_segment"),
                    "asof": datetime.now().isoformat()
                }
                f.write(json.dumps(record) + "\n")
    
    def _generate_markdown_report(self, orders_results, fill_results, portfolio, metadata, path: Path) -> None:
        """Generate markdown execution report."""
        exec_stats = metadata.get("execution_statistics", {})
        
        report_lines = [
            f"# Execution Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            f"- **Orders Placed**: {metadata['orders_placed']}",
            f"- **Orders Filled**: {metadata['orders_filled']}",
            f"- **Success Rate**: {exec_stats.get('order_success_rate', 0):.1%}",
            f"- **Fill Rate**: {exec_stats.get('fill_rate', 0):.1%}",
            f"- **Duration**: {metadata['duration_seconds']:.1f} seconds",
            ""
        ]
        
        # Portfolio summary
        if portfolio and "account" in portfolio:
            account = portfolio["account"]
            report_lines.extend([
                "## Portfolio Status",
                f"- **Total Equity**: ${account.get('total_equity', 0):,.2f}",
                f"- **Buying Power**: ${account.get('buying_power', 0):,.2f}",
                f"- **Day P&L**: ${account.get('day_pnl', 0):,.2f} ({account.get('day_pnl_pct', 0):.2f}%)",
                f"- **Open Positions**: {len(portfolio.get('positions', []))}",
                f"- **Open Orders**: {len(portfolio.get('open_orders', []))}",
                ""
            ])
        
        # Order type distribution
        order_types = exec_stats.get("order_types", {})
        if order_types:
            report_lines.extend([
                "## Order Type Distribution",
                ""
            ])
            for order_type, count in order_types.items():
                report_lines.append(f"- **{order_type}**: {count}")
            report_lines.append("")
        
        # Recent fills
        filled_orders = [f for f in fill_results if f.get("filled")]
        if filled_orders:
            report_lines.extend([
                "## Recent Fills",
                ""
            ])
            for fill in filled_orders[:10]:  # Show top 10
                report_lines.append(
                    f"- **{fill['symbol']}**: {fill.get('filled_qty', 0)} shares @ "
                    f"${fill.get('filled_avg_price', 0):.2f}"
                )
        
        # Write report
        with open(path, "w") as f:
            f.write("\n".join(report_lines))
