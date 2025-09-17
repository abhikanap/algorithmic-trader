"""Portfolio management system for tracking positions and performance."""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np

from packages.core import get_logger
from .brokers import AlpacaBroker


class PortfolioManager:
    """Manages portfolio positions and performance tracking."""
    
    def __init__(self, broker: AlpacaBroker):
        self.logger = get_logger(__name__)
        self.broker = broker
        
        # Portfolio tracking
        self.positions_cache: Dict[str, Dict[str, Any]] = {}
        self.performance_history: List[Dict[str, Any]] = []
        self.last_update = None
        
        self.logger.info("Initialized portfolio manager")
    
    async def get_positions(self, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Get current portfolio positions.
        
        Args:
            force_refresh: Force refresh from broker (bypass cache)
            
        Returns:
            Dictionary of positions keyed by symbol
        """
        # Use cache if recent and not forcing refresh
        if (not force_refresh and 
            self.last_update and 
            (datetime.now() - self.last_update).seconds < 60):  # 1 minute cache
            return self.positions_cache.copy()
        
        try:
            positions = await self.broker.get_positions()
            
            # Enrich positions with additional metrics
            enriched_positions = {}
            for symbol, position in positions.items():
                enriched_position = position.copy()
                enriched_position.update(self._calculate_position_metrics(position))
                enriched_positions[symbol] = enriched_position
            
            # Update cache
            self.positions_cache = enriched_positions
            self.last_update = datetime.now()
            
            self.logger.info(f"Retrieved {len(positions)} positions")
            return enriched_positions
            
        except Exception as e:
            self.logger.error(f"Failed to get positions: {e}")
            return {}
    
    def _calculate_position_metrics(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate additional metrics for a position."""
        
        try:
            current_price = float(position.get("current_price", 0))
            avg_price = float(position.get("avg_fill_price", 0))
            qty = int(position.get("qty", 0))
            
            if current_price <= 0 or avg_price <= 0:
                return {}
            
            # Calculate percentage return
            if qty > 0:  # Long position
                pct_return = ((current_price - avg_price) / avg_price) * 100
            else:  # Short position
                pct_return = ((avg_price - current_price) / avg_price) * 100
            
            # Calculate position value
            position_value = abs(current_price * qty)
            
            # Risk metrics
            risk_amount = position_value * 0.02  # 2% risk assumption
            
            return {
                "pct_return": round(pct_return, 2),
                "position_value": round(position_value, 2),
                "risk_amount": round(risk_amount, 2),
                "days_held": 1,  # Would calculate from entry date in production
                "position_size_category": self._categorize_position_size(position_value)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating position metrics: {e}")
            return {}
    
    def _categorize_position_size(self, value: float) -> str:
        """Categorize position size."""
        if value < 1000:
            return "small"
        elif value < 5000:
            return "medium"
        elif value < 25000:
            return "large"
        else:
            return "very_large"
    
    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary."""
        
        try:
            # Get account info and positions
            account_info = await self.broker.get_account_info()
            positions = await self.get_positions()
            
            if not account_info:
                return {}
            
            # Basic account metrics
            total_value = float(account_info.get("portfolio_value", 0))
            cash = float(account_info.get("cash", 0))
            buying_power = float(account_info.get("buying_power", 0))
            day_pnl = float(account_info.get("day_pnl", 0))
            
            # Position metrics
            total_positions = len(positions)
            long_positions = len([p for p in positions.values() if int(p.get("qty", 0)) > 0])
            short_positions = len([p for p in positions.values() if int(p.get("qty", 0)) < 0])
            
            # Calculate position values
            total_position_value = sum(
                abs(float(p.get("market_value", 0))) for p in positions.values()
            )
            
            # Calculate unrealized P&L
            total_unrealized_pnl = sum(
                float(p.get("unrealized_pl", 0)) for p in positions.values()
            )
            
            # Risk metrics
            largest_position = max(
                (abs(float(p.get("market_value", 0))) for p in positions.values()), 
                default=0
            )
            
            concentration_risk = (largest_position / total_value * 100) if total_value > 0 else 0
            
            # Performance metrics
            day_return_pct = (day_pnl / total_value * 100) if total_value > 0 else 0
            cash_utilization = ((total_value - cash) / total_value * 100) if total_value > 0 else 0
            
            summary = {
                # Account basics
                "total_value": total_value,
                "cash": cash,
                "buying_power": buying_power,
                "day_pnl": day_pnl,
                "day_return_pct": round(day_return_pct, 2),
                
                # Position metrics
                "total_positions": total_positions,
                "long_positions": long_positions,
                "short_positions": short_positions,
                "total_position_value": total_position_value,
                "total_unrealized_pnl": total_unrealized_pnl,
                
                # Risk metrics
                "largest_position": largest_position,
                "concentration_risk_pct": round(concentration_risk, 2),
                "cash_utilization_pct": round(cash_utilization, 2),
                
                # Status
                "last_updated": datetime.now().isoformat(),
                "market_value_vs_cash": "healthy" if cash_utilization < 90 else "high_utilization"
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get portfolio summary: {e}")
            return {}
    
    async def check_risk_limits(self) -> List[Dict[str, Any]]:
        """Check portfolio against risk limits and return violations."""
        
        violations = []
        
        try:
            summary = await self.get_portfolio_summary()
            positions = await self.get_positions()
            
            if not summary:
                return violations
            
            # Check concentration risk (no single position > 15% of portfolio)
            concentration_limit = 15.0
            if summary.get("concentration_risk_pct", 0) > concentration_limit:
                violations.append({
                    "type": "concentration_risk",
                    "severity": "high",
                    "message": f"Largest position is {summary['concentration_risk_pct']:.1f}% of portfolio (limit: {concentration_limit}%)",
                    "recommended_action": "reduce_largest_position"
                })
            
            # Check cash utilization (should keep some cash buffer)
            cash_utilization_limit = 95.0
            if summary.get("cash_utilization_pct", 0) > cash_utilization_limit:
                violations.append({
                    "type": "cash_utilization",
                    "severity": "medium",
                    "message": f"Cash utilization is {summary['cash_utilization_pct']:.1f}% (limit: {cash_utilization_limit}%)",
                    "recommended_action": "reduce_position_sizes"
                })
            
            # Check individual position losses (stop at -10% per position)
            position_loss_limit = -10.0
            for symbol, position in positions.items():
                pct_return = position.get("pct_return", 0)
                if pct_return < position_loss_limit:
                    violations.append({
                        "type": "position_loss",
                        "severity": "high",
                        "symbol": symbol,
                        "message": f"{symbol} is down {pct_return:.1f}% (stop loss: {position_loss_limit}%)",
                        "recommended_action": "close_position"
                    })
            
            # Check daily P&L limit (stop at -5% daily loss)
            daily_loss_limit = -5.0
            day_return_pct = summary.get("day_return_pct", 0)
            if day_return_pct < daily_loss_limit:
                violations.append({
                    "type": "daily_loss",
                    "severity": "critical",
                    "message": f"Daily loss is {day_return_pct:.1f}% (limit: {daily_loss_limit}%)",
                    "recommended_action": "stop_trading_for_day"
                })
            
            # Check number of positions (max 25 positions)
            max_positions = 25
            if summary.get("total_positions", 0) > max_positions:
                violations.append({
                    "type": "position_count",
                    "severity": "medium",
                    "message": f"Have {summary['total_positions']} positions (limit: {max_positions})",
                    "recommended_action": "reduce_position_count"
                })
            
            if violations:
                self.logger.warning(f"Found {len(violations)} risk violations")
            
            return violations
            
        except Exception as e:
            self.logger.error(f"Failed to check risk limits: {e}")
            return []
    
    async def suggest_rebalancing(self) -> List[Dict[str, Any]]:
        """Suggest portfolio rebalancing actions."""
        
        suggestions = []
        
        try:
            positions = await self.get_positions()
            summary = await self.get_portfolio_summary()
            
            if not positions or not summary:
                return suggestions
            
            total_value = summary.get("total_value", 0)
            
            # Suggest reducing oversized positions
            for symbol, position in positions.items():
                position_value = abs(float(position.get("market_value", 0)))
                position_pct = (position_value / total_value * 100) if total_value > 0 else 0
                
                if position_pct > 10.0:  # Suggest reducing positions > 10%
                    suggestions.append({
                        "type": "reduce_position",
                        "symbol": symbol,
                        "current_pct": round(position_pct, 2),
                        "target_pct": 8.0,
                        "message": f"Consider reducing {symbol} from {position_pct:.1f}% to ~8% of portfolio",
                        "reason": "position_size_management"
                    })
            
            # Suggest taking profits on large winners
            for symbol, position in positions.items():
                pct_return = position.get("pct_return", 0)
                if pct_return > 25.0:  # Large winners
                    suggestions.append({
                        "type": "take_profit",
                        "symbol": symbol,
                        "current_return": pct_return,
                        "message": f"Consider taking partial profits on {symbol} (+{pct_return:.1f}%)",
                        "reason": "profit_taking"
                    })
            
            # Suggest diversification if too concentrated in few positions
            if len(positions) > 0 and len(positions) < 5:
                suggestions.append({
                    "type": "diversify",
                    "message": f"Consider diversifying beyond {len(positions)} positions",
                    "reason": "concentration_risk"
                })
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Failed to generate rebalancing suggestions: {e}")
            return []
    
    def record_performance_snapshot(self, additional_data: Optional[Dict[str, Any]] = None):
        """Record a point-in-time performance snapshot."""
        
        try:
            snapshot = {
                "timestamp": datetime.now(),
                "positions_count": len(self.positions_cache),
                "last_update": self.last_update
            }
            
            if additional_data:
                snapshot.update(additional_data)
            
            self.performance_history.append(snapshot)
            
            # Keep only last 1000 snapshots
            if len(self.performance_history) > 1000:
                self.performance_history = self.performance_history[-1000:]
                
        except Exception as e:
            self.logger.error(f"Failed to record performance snapshot: {e}")
    
    def get_performance_history(self, days: int = 30) -> pd.DataFrame:
        """Get performance history as DataFrame."""
        
        if not self.performance_history:
            return pd.DataFrame()
        
        try:
            # Filter to requested days
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_history = [
                h for h in self.performance_history 
                if h.get("timestamp", datetime.min) >= cutoff_date
            ]
            
            if not recent_history:
                return pd.DataFrame()
            
            df = pd.DataFrame(recent_history)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Failed to get performance history: {e}")
            return pd.DataFrame()
    
    async def close_position(self, symbol: str, qty: Optional[int] = None, reason: str = "") -> Dict[str, Any]:
        """Close a position (all or partial)."""
        
        try:
            self.logger.info(f"Closing position for {symbol}" + (f" ({qty} shares)" if qty else " (full position)"))
            
            result = await self.broker.close_position(symbol, qty)
            
            if result.get("success"):
                # Clear from cache to force refresh
                if symbol in self.positions_cache:
                    del self.positions_cache[symbol]
                
                self.logger.info(f"Position close order placed for {symbol}")
            else:
                self.logger.error(f"Failed to close position for {symbol}: {result.get('message', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            error_msg = f"Exception closing position for {symbol}: {e}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "symbol": symbol,
                "message": error_msg
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get portfolio manager status."""
        
        return {
            "broker_connected": self.broker.is_configured(),
            "positions_cached": len(self.positions_cache),
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "performance_snapshots": len(self.performance_history)
        }
