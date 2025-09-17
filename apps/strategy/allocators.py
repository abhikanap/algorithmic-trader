"""Capital bucket allocation system."""

from typing import Dict, Any, List
import pandas as pd
import numpy as np

from packages.core import get_logger
from packages.core.models import CapitalBucket


class BucketAllocator:
    """Allocates symbols to capital buckets based on patterns and characteristics."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Default bucket configurations
        self.bucket_configs = {
            "BUCKET_A": {
                "name": "Penny Stocks & Microcap Movers",
                "allocation_pct": 0.15,
                "description": "Sub-$5 stocks with high volatility potential",
                "criteria": {
                    "max_price": 5.0,
                    "min_volume_ratio": 1.5,
                    "min_atr_pct": 3.0
                }
            },
            "BUCKET_B": {
                "name": "Large-Cap Intraday Trends",
                "allocation_pct": 0.35,
                "description": "Established stocks with clear intraday trends",
                "criteria": {
                    "min_price": 10.0,
                    "min_market_cap": 1_000_000_000,  # $1B+
                    "patterns": ["MORNING_SURGE_UPTREND", "MORNING_SELLOFF_DOWNTREND"]
                }
            },
            "BUCKET_C": {
                "name": "Multi-Day Swing Trades",
                "allocation_pct": 0.30,
                "description": "Stocks with multi-day pattern potential",
                "criteria": {
                    "min_price": 5.0,
                    "patterns": ["SUSTAINED_UPTREND", "SUSTAINED_DOWNTREND", "REVERSAL_UP"]
                }
            },
            "BUCKET_D": {
                "name": "Catalyst-Driven Movers",
                "allocation_pct": 0.15,
                "description": "News, earnings, or event-driven opportunities",
                "criteria": {
                    "min_volume_ratio": 2.0,
                    "min_gap_pct": 5.0
                }
            },
            "BUCKET_E": {
                "name": "Defensive Hedges",
                "allocation_pct": 0.05,
                "description": "ETFs and defensive positions",
                "criteria": {
                    "symbols": ["SPY", "QQQ", "IWM", "VIX"]  # Can be expanded
                }
            }
        }
        
        self.logger.info("Initialized bucket allocator with 5 buckets")
    
    def allocate_to_buckets(
        self, 
        df: pd.DataFrame, 
        total_capital: float
    ) -> Dict[str, float]:
        """
        Allocate symbols to buckets and calculate capital allocation.
        
        Args:
            df: DataFrame with symbol data and patterns
            total_capital: Total capital to allocate
            
        Returns:
            Dictionary with bucket -> capital amount mapping
        """
        self.logger.info(f"Allocating {len(df)} symbols to buckets")
        
        # Calculate base capital allocations
        allocations = {}
        for bucket_id, config in self.bucket_configs.items():
            allocations[bucket_id] = total_capital * config["allocation_pct"]
        
        # Assign symbols to buckets
        df_with_buckets = self._assign_symbols_to_buckets(df.copy())
        
        # Log allocation results
        bucket_counts = df_with_buckets["bucket"].value_counts()
        self.logger.info(f"Bucket assignments: {dict(bucket_counts)}")
        
        for bucket_id, capital in allocations.items():
            count = bucket_counts.get(bucket_id, 0)
            self.logger.info(f"{bucket_id}: ${capital:,.2f} ({count} symbols)")
        
        return allocations
    
    def _assign_symbols_to_buckets(self, df: pd.DataFrame) -> pd.DataFrame:
        """Assign each symbol to the most appropriate bucket."""
        
        df["bucket"] = "BUCKET_B"  # Default to large-cap bucket
        df["bucket_reason"] = ""
        
        for idx, row in df.iterrows():
            bucket, reason = self._determine_bucket(row)
            df.at[idx, "bucket"] = bucket
            df.at[idx, "bucket_reason"] = reason
        
        return df
    
    def _determine_bucket(self, row: pd.Series) -> tuple[str, str]:
        """
        Determine the most appropriate bucket for a symbol.
        
        Returns:
            (bucket_id, reason)
        """
        symbol = row.get("symbol", "")
        price = row.get("last", 0)
        volume_ratio = row.get("volume_ratio", 1.0)
        atr_pct = row.get("atrp_14", 0)
        gap_pct = abs(row.get("gap_pct", 0))
        pattern_intraday = row.get("pattern_intraday", "")
        pattern_multiday = row.get("pattern_multiday", "")
        
        # Bucket E: Defensive Hedges (ETFs, specific symbols)
        if symbol in self.bucket_configs["BUCKET_E"]["criteria"]["symbols"]:
            return "BUCKET_E", "defensive_etf"
        
        # Bucket A: Penny Stocks & Microcap Movers
        if (price <= self.bucket_configs["BUCKET_A"]["criteria"]["max_price"] and
            volume_ratio >= self.bucket_configs["BUCKET_A"]["criteria"]["min_volume_ratio"] and
            atr_pct >= self.bucket_configs["BUCKET_A"]["criteria"]["min_atr_pct"]):
            return "BUCKET_A", "penny_stock_mover"
        
        # Bucket D: Catalyst-Driven Movers (high volume + gap)
        if (volume_ratio >= self.bucket_configs["BUCKET_D"]["criteria"]["min_volume_ratio"] and
            gap_pct >= self.bucket_configs["BUCKET_D"]["criteria"]["min_gap_pct"]):
            return "BUCKET_D", "catalyst_driven"
        
        # Bucket C: Multi-Day Swing Trades
        if (pattern_multiday in self.bucket_configs["BUCKET_C"]["criteria"]["patterns"] and
            price >= self.bucket_configs["BUCKET_C"]["criteria"]["min_price"]):
            return "BUCKET_C", "multiday_pattern"
        
        # Bucket B: Large-Cap Intraday Trends (default for quality stocks)
        if (price >= self.bucket_configs["BUCKET_B"]["criteria"]["min_price"] and
            pattern_intraday in self.bucket_configs["BUCKET_B"]["criteria"]["patterns"]):
            return "BUCKET_B", "intraday_trend"
        
        # Default to Bucket B for stocks that don't fit specific criteria
        return "BUCKET_B", "default_largecap"
    
    def get_bucket_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get current bucket configurations."""
        return self.bucket_configs.copy()
    
    def update_bucket_config(
        self, 
        bucket_id: str, 
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update bucket configuration.
        
        Args:
            bucket_id: Bucket to update
            updates: Dictionary of updates to apply
            
        Returns:
            True if successful, False otherwise
        """
        if bucket_id not in self.bucket_configs:
            self.logger.error(f"Unknown bucket: {bucket_id}")
            return False
        
        try:
            self.bucket_configs[bucket_id].update(updates)
            self.logger.info(f"Updated bucket {bucket_id}: {updates}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update bucket {bucket_id}: {e}")
            return False
    
    def get_bucket_summary(self, df_with_buckets: pd.DataFrame) -> Dict[str, Any]:
        """Generate summary statistics for bucket allocations."""
        
        summary = {}
        
        for bucket_id, config in self.bucket_configs.items():
            bucket_symbols = df_with_buckets[df_with_buckets["bucket"] == bucket_id]
            
            summary[bucket_id] = {
                "name": config["name"],
                "allocation_pct": config["allocation_pct"],
                "symbol_count": len(bucket_symbols),
                "symbols": bucket_symbols["symbol"].tolist() if len(bucket_symbols) <= 10 else bucket_symbols["symbol"].head(10).tolist(),
                "avg_price": bucket_symbols["last"].mean() if not bucket_symbols.empty else 0,
                "avg_volume_ratio": bucket_symbols.get("volume_ratio", pd.Series()).mean() if not bucket_symbols.empty else 0,
                "avg_atr_pct": bucket_symbols.get("atrp_14", pd.Series()).mean() if not bucket_symbols.empty else 0
            }
        
        return summary
    
    def validate_allocation(self, allocations: Dict[str, float]) -> bool:
        """Validate that bucket allocations sum to reasonable total."""
        
        total_pct = sum(config["allocation_pct"] for config in self.bucket_configs.values())
        
        if abs(total_pct - 1.0) > 0.01:  # Allow 1% tolerance
            self.logger.warning(f"Bucket allocations sum to {total_pct:.2%}, not 100%")
            return False
        
        return True
    
    def rebalance_buckets(
        self, 
        df: pd.DataFrame, 
        target_counts: Dict[str, int] = None
    ) -> pd.DataFrame:
        """
        Rebalance bucket assignments to target symbol counts.
        
        Args:
            df: DataFrame with current bucket assignments
            target_counts: Optional target symbol counts per bucket
            
        Returns:
            DataFrame with rebalanced bucket assignments
        """
        if target_counts is None:
            # Default targets based on allocation percentages
            total_symbols = len(df)
            target_counts = {
                bucket_id: int(total_symbols * config["allocation_pct"])
                for bucket_id, config in self.bucket_configs.items()
            }
        
        self.logger.info(f"Rebalancing buckets to targets: {target_counts}")
        
        # TODO: Implement sophisticated rebalancing logic
        # For now, return original assignments
        return df
