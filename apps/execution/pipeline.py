"""Execution engine pipeline for placing and managing trades."""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np

from packages.core import get_logger
from packages.core.config import settings
from packages.core.models import TradeSignal, OrderStatus, OrderType

from .brokers import AlpacaBroker
from .orders import OrderManager
from .portfolio import PortfolioManager


class ExecutionPipeline:
    """Main execution pipeline that manages trade placement and portfolio."""
    
    def __init__(
        self,
        broker: Optional[AlpacaBroker] = None,
        order_manager: Optional[OrderManager] = None,
        portfolio_manager: Optional[PortfolioManager] = None
    ):
        self.logger = get_logger(__name__)
        
        # Initialize components
        self.broker = broker or AlpacaBroker()
        self.order_manager = order_manager or OrderManager(self.broker)
        self.portfolio_manager = portfolio_manager or PortfolioManager(self.broker)
        
        self.logger.info("Initialized execution pipeline")
    
    async def run(
        self,
        strategy_data: Optional[pd.DataFrame] = None,
        date: Optional[str] = None,
        dry_run: bool = True,
        max_orders: int = 20,
        save_artifacts: bool = True
    ) -> Dict[str, Any]:
        """
        Run the complete execution pipeline.
        
        Args:
            strategy_data: DataFrame from strategy pipeline with trade signals
            date: Date string (YYYY-MM-DD). If None, uses today
            dry_run: If True, simulates orders without placing them
            max_orders: Maximum number of orders to place
            save_artifacts: Whether to save results to artifacts
            
        Returns:
            Dictionary containing results and metadata
        """
        start_time = datetime.now()
        
        if date is None:
            date = start_time.strftime("%Y-%m-%d")
        
        self.logger.info(f"Starting execution pipeline for date: {date}")
        self.logger.info(f"Dry run: {dry_run}, Max orders: {max_orders}")
        
        try:
            # Load strategy data if not provided
            if strategy_data is None:
                strategy_data = self._load_strategy_data(date)
            
            if strategy_data.empty:
                raise ValueError("No strategy data available")
            
            self.logger.info(f"Processing {len(strategy_data)} trade signals")
            
            # Stage 1: Validate market conditions and broker connection
            await self._validate_market_conditions()
            
            # Stage 2: Filter and prepare orders
            self.logger.info("Preparing orders...")
            orders_to_place = self._prepare_orders(strategy_data, max_orders)
            
            # Stage 3: Check portfolio constraints
            orders_to_place = await self._apply_portfolio_constraints(orders_to_place)
            
            # Stage 4: Place orders
            self.logger.info(f"Placing {len(orders_to_place)} orders...")
            order_results = await self._place_orders(orders_to_place, dry_run)
            
            # Stage 5: Monitor existing positions
            portfolio_status = await self._check_portfolio_status()
            
            # Stage 6: Risk management and position adjustments
            risk_actions = await self._apply_risk_management(portfolio_status)
            
            # Prepare results
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Generate metadata
            metadata = {
                "date": date,
                "duration_seconds": round(duration, 2),
                "dry_run": dry_run,
                "max_orders": max_orders,
                "orders_placed": len([r for r in order_results if r.get("success", False)]),
                "orders_failed": len([r for r in order_results if not r.get("success", False)]),
                "portfolio_summary": portfolio_status,
                "risk_actions": len(risk_actions)
            }
            
            # Save artifacts if requested
            saved_files = {}
            if save_artifacts:
                self.logger.info("Saving execution artifacts...")
                saved_files = self._save_artifacts(order_results, risk_actions, date, metadata)
                metadata["saved_files"] = saved_files
            
            result = {
                "success": True,
                "order_results": order_results,
                "portfolio_status": portfolio_status,
                "risk_actions": risk_actions,
                "metadata": metadata,
                "saved_files": saved_files
            }
            
            self.logger.info(
                f"Execution pipeline completed successfully in {duration:.1f}s. "
                f"Placed {metadata['orders_placed']} orders"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Execution pipeline failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return {
                "success": False,
                "error": error_msg,
                "order_results": [],
                "portfolio_status": {},
                "risk_actions": [],
                "metadata": {
                    "date": date,
                    "error": str(e),
                    "duration_seconds": (datetime.now() - start_time).total_seconds()
                },
                "saved_files": {}
            }
    
    def _load_strategy_data(self, date: str) -> pd.DataFrame:
        """Load strategy data from artifacts."""
        try:
            from apps.strategy.artifacts import ArtifactManager
            
            artifact_manager = ArtifactManager()
            results = artifact_manager.load_strategy_results(date)
            return results.get("dataframe", pd.DataFrame())
            
        except Exception as e:
            self.logger.warning(f"Could not load strategy data for {date}: {e}")
            return pd.DataFrame()
    
    async def _validate_market_conditions(self):
        """Validate that markets are open and broker is accessible."""
        
        # Check if market is open
        market_status = await self.broker.get_market_status()
        if not market_status.get("is_open", False):
            self.logger.warning("Market is closed")
            
        # Check broker connection
        account_info = await self.broker.get_account_info()
        if not account_info:
            raise ValueError("Cannot connect to broker")
        
        self.logger.info(f"Market status: {market_status}")
        self.logger.info(f"Account buying power: ${account_info.get('buying_power', 0):,.2f}")
    
    def _prepare_orders(self, df: pd.DataFrame, max_orders: int) -> List[Dict[str, Any]]:
        """Prepare orders from trade signals."""
        
        # Sort by rank/score (best signals first)
        sorted_df = df.sort_values(["rank"], ascending=True).head(max_orders)
        
        orders = []
        for _, row in sorted_df.iterrows():
            order = self._create_order_from_signal(row)
            if order:
                orders.append(order)
        
        self.logger.info(f"Prepared {len(orders)} orders from {len(df)} signals")
        return orders
    
    def _create_order_from_signal(self, row: pd.Series) -> Optional[Dict[str, Any]]:
        """Create an order dictionary from a trade signal."""
        
        try:
            symbol = row.get("symbol", "")
            signal_type = row.get("signal_type", "LONG")
            shares = int(row.get("shares", 0))
            entry_price = float(row.get("entry_price", 0))
            stop_price = float(row.get("stop_loss_price", 0))
            target_price = float(row.get("target_price", 0))
            
            if shares <= 0 or entry_price <= 0:
                return None
            
            # Determine order side
            side = "buy" if signal_type == "LONG" else "sell"
            
            order = {
                "symbol": symbol,
                "side": side,
                "qty": abs(shares),
                "type": "market",  # Could be "limit" with entry_price
                "time_in_force": "day",
                
                # Signal metadata
                "signal_type": signal_type,
                "bucket": row.get("bucket", ""),
                "pattern": row.get("pattern", ""),
                "confidence": float(row.get("confidence", 0)),
                "time_segment": row.get("time_segment", ""),
                
                # Risk management
                "stop_loss_price": stop_price,
                "target_price": target_price,
                "entry_hints": row.get("entry_hints", ""),
                "exit_hints": row.get("exit_hints", ""),
                
                # Timestamps
                "created_at": datetime.now(),
                "valid_until": row.get("valid_until", datetime.now() + timedelta(hours=6))
            }
            
            return order
            
        except Exception as e:
            self.logger.error(f"Failed to create order from signal: {e}")
            return None
    
    async def _apply_portfolio_constraints(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply portfolio-level constraints to orders."""
        
        # Get current portfolio
        positions = await self.portfolio_manager.get_positions()
        account_info = await self.broker.get_account_info()
        
        buying_power = float(account_info.get("buying_power", 0))
        max_position_value = buying_power * 0.1  # Max 10% per position
        
        filtered_orders = []
        total_order_value = 0
        
        for order in orders:
            # Calculate order value
            qty = order["qty"]
            # Use last price as estimate (would get real-time quote in production)
            estimated_price = 50.0  # Placeholder
            order_value = qty * estimated_price
            
            # Check position size limit
            if order_value > max_position_value:
                self.logger.warning(f"Order for {order['symbol']} exceeds position limit")
                continue
                
            # Check total buying power
            if total_order_value + order_value > buying_power * 0.8:
                self.logger.warning("Approaching buying power limit")
                break
            
            # Check for existing position in same symbol
            existing_position = positions.get(order["symbol"])
            if existing_position and existing_position["side"] == order["side"]:
                self.logger.warning(f"Already have {order['side']} position in {order['symbol']}")
                continue
            
            filtered_orders.append(order)
            total_order_value += order_value
        
        self.logger.info(f"Filtered to {len(filtered_orders)} orders after constraints")
        return filtered_orders
    
    async def _place_orders(self, orders: List[Dict[str, Any]], dry_run: bool) -> List[Dict[str, Any]]:
        """Place orders with the broker."""
        
        results = []
        
        for order in orders:
            try:
                if dry_run:
                    # Simulate order placement
                    result = {
                        "success": True,
                        "order_id": f"sim_{order['symbol']}_{datetime.now().strftime('%H%M%S')}",
                        "symbol": order["symbol"],
                        "side": order["side"],
                        "qty": order["qty"],
                        "status": "filled",
                        "filled_price": order.get("entry_price", 50.0),
                        "message": "Simulated order",
                        "dry_run": True
                    }
                else:
                    # Place real order
                    result = await self.order_manager.place_order(order)
                
                results.append(result)
                
                if result.get("success"):
                    self.logger.info(f"Order placed: {order['symbol']} {order['side']} {order['qty']}")
                else:
                    self.logger.error(f"Order failed: {order['symbol']} - {result.get('message', 'Unknown error')}")
                
                # Small delay between orders
                await asyncio.sleep(0.5)
                
            except Exception as e:
                error_result = {
                    "success": False,
                    "symbol": order["symbol"],
                    "error": str(e),
                    "message": f"Failed to place order: {e}"
                }
                results.append(error_result)
                self.logger.error(f"Exception placing order for {order['symbol']}: {e}")
        
        return results
    
    async def _check_portfolio_status(self) -> Dict[str, Any]:
        """Get current portfolio status."""
        
        try:
            positions = await self.portfolio_manager.get_positions()
            account_info = await self.broker.get_account_info()
            
            # Calculate portfolio metrics
            total_value = float(account_info.get("portfolio_value", 0))
            buying_power = float(account_info.get("buying_power", 0))
            day_pnl = float(account_info.get("day_pnl", 0))
            
            return {
                "total_positions": len(positions),
                "total_value": total_value,
                "buying_power": buying_power,
                "day_pnl": day_pnl,
                "positions": positions
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get portfolio status: {e}")
            return {}
    
    async def _apply_risk_management(self, portfolio_status: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply risk management rules to existing positions."""
        
        risk_actions = []
        positions = portfolio_status.get("positions", {})
        
        for symbol, position in positions.items():
            try:
                # Check stop loss conditions
                current_price = float(position.get("current_price", 0))
                entry_price = float(position.get("avg_fill_price", 0))
                side = position.get("side", "")
                
                if side == "long" and current_price > 0 and entry_price > 0:
                    loss_pct = ((current_price - entry_price) / entry_price) * 100
                    if loss_pct < -5.0:  # 5% stop loss
                        action = {
                            "type": "stop_loss",
                            "symbol": symbol,
                            "reason": f"Stop loss triggered: {loss_pct:.1f}%",
                            "recommended_action": "close_position"
                        }
                        risk_actions.append(action)
                
                # Check profit taking
                elif side == "long" and current_price > 0 and entry_price > 0:
                    gain_pct = ((current_price - entry_price) / entry_price) * 100
                    if gain_pct > 10.0:  # 10% profit target
                        action = {
                            "type": "profit_target",
                            "symbol": symbol,
                            "reason": f"Profit target reached: {gain_pct:.1f}%",
                            "recommended_action": "take_partial_profit"
                        }
                        risk_actions.append(action)
                
            except Exception as e:
                self.logger.error(f"Risk management error for {symbol}: {e}")
        
        return risk_actions
    
    def _save_artifacts(
        self, 
        order_results: List[Dict[str, Any]], 
        risk_actions: List[Dict[str, Any]],
        date: str, 
        metadata: Dict[str, Any]
    ) -> Dict[str, str]:
        """Save execution artifacts to disk."""
        
        # Create artifacts directory
        artifacts_dir = Path(settings.ARTIFACTS_PATH) / "execution" / date
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = {}
        
        try:
            # Save order results
            if order_results:
                orders_df = pd.DataFrame(order_results)
                
                # Save as Parquet
                parquet_path = artifacts_dir / f"orders_{date}.parquet"
                orders_df.to_parquet(parquet_path, index=False)
                saved_files["orders_parquet"] = str(parquet_path)
                
                # Save as CSV
                csv_path = artifacts_dir / f"orders_{date}.csv"
                orders_df.to_csv(csv_path, index=False)
                saved_files["orders_csv"] = str(csv_path)
            
            # Save risk actions
            if risk_actions:
                risk_df = pd.DataFrame(risk_actions)
                risk_path = artifacts_dir / f"risk_actions_{date}.csv"
                risk_df.to_csv(risk_path, index=False)
                saved_files["risk_actions"] = str(risk_path)
            
            # Save metadata as JSON
            import json
            metadata_path = artifacts_dir / f"execution_metadata_{date}.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2, default=str)
            saved_files["metadata"] = str(metadata_path)
            
            # Generate summary report
            report_path = artifacts_dir / f"execution_report_{date}.md"
            self._generate_report(order_results, risk_actions, metadata, report_path)
            saved_files["report"] = str(report_path)
            
            self.logger.info(f"Saved execution artifacts to {artifacts_dir}")
            
        except Exception as e:
            self.logger.error(f"Failed to save artifacts: {e}")
        
        return saved_files
    
    def _generate_report(
        self, 
        order_results: List[Dict[str, Any]], 
        risk_actions: List[Dict[str, Any]],
        metadata: Dict[str, Any], 
        output_path: Path
    ):
        """Generate a markdown report of execution results."""
        
        with open(output_path, "w") as f:
            f.write(f"# Execution Report - {metadata['date']}\n\n")
            
            # Summary stats
            f.write("## Summary\n\n")
            f.write(f"- **Date**: {metadata['date']}\n")
            f.write(f"- **Dry Run**: {'Yes' if metadata['dry_run'] else 'No'}\n")
            f.write(f"- **Orders Placed**: {metadata['orders_placed']}\n")
            f.write(f"- **Orders Failed**: {metadata['orders_failed']}\n")
            f.write(f"- **Risk Actions**: {metadata['risk_actions']}\n")
            f.write(f"- **Processing Time**: {metadata['duration_seconds']:.1f}s\n\n")
            
            # Portfolio status
            portfolio = metadata.get("portfolio_summary", {})
            if portfolio:
                f.write("## Portfolio Status\n\n")
                f.write(f"- **Total Positions**: {portfolio.get('total_positions', 0)}\n")
                f.write(f"- **Portfolio Value**: ${portfolio.get('total_value', 0):,.2f}\n")
                f.write(f"- **Buying Power**: ${portfolio.get('buying_power', 0):,.2f}\n")
                f.write(f"- **Day P&L**: ${portfolio.get('day_pnl', 0):,.2f}\n\n")
            
            # Successful orders
            successful_orders = [o for o in order_results if o.get("success", False)]
            if successful_orders:
                f.write("## Successful Orders\n\n")
                f.write("| Symbol | Side | Quantity | Price | Status |\n")
                f.write("|--------|------|----------|-------|--------|\n")
                
                for order in successful_orders[:10]:  # Top 10
                    symbol = order.get("symbol", "N/A")
                    side = order.get("side", "N/A")
                    qty = order.get("qty", 0)
                    price = order.get("filled_price", 0)
                    status = order.get("status", "N/A")
                    
                    f.write(f"| {symbol} | {side} | {qty} | ${price:.2f} | {status} |\n")
                f.write("\n")
            
            # Failed orders
            failed_orders = [o for o in order_results if not o.get("success", False)]
            if failed_orders:
                f.write("## Failed Orders\n\n")
                for order in failed_orders:
                    symbol = order.get("symbol", "N/A")
                    message = order.get("message", "Unknown error")
                    f.write(f"- **{symbol}**: {message}\n")
                f.write("\n")
            
            # Risk actions
            if risk_actions:
                f.write("## Risk Management Actions\n\n")
                for action in risk_actions:
                    symbol = action.get("symbol", "N/A")
                    action_type = action.get("type", "N/A")
                    reason = action.get("reason", "N/A")
                    f.write(f"- **{symbol}** ({action_type}): {reason}\n")
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get pipeline status information."""
        return {
            "execution": {
                "broker": self.broker.__class__.__name__,
                "order_manager": self.order_manager.__class__.__name__,
                "portfolio_manager": self.portfolio_manager.__class__.__name__
            },
            "settings": {
                "artifacts_path": str(settings.ARTIFACTS_PATH),
                "debug": settings.DEBUG
            }
        }
