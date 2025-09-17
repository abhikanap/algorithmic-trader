"""Filtering engine for stock screening."""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from packages.core import get_logger
from packages.core.config import screening_config


class FilterEngine:
    """Stock filtering based on configurable criteria."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.logger = get_logger(__name__)
        self.config = config or self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default filtering configuration."""
        return {
            "min_price": screening_config.min_price,
            "max_price": screening_config.max_price,
            "min_dollar_volume": screening_config.min_dollar_volume,
            "min_atr_percent": screening_config.min_atr_percent,
            "max_symbols_per_sector": screening_config.max_symbols_per_sector,
            "exclude_penny_threshold": 1.0,
            "min_volume": 100_000,
            "max_gap_pct": 50.0,  # Exclude extreme gaps
            "min_market_hours_volume": 10_000,
        }
    
    async def apply_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply filtering criteria to remove unwanted stocks.
        
        Args:
            df: DataFrame with stock data and features
            
        Returns:
            Filtered DataFrame
        """
        if df.empty:
            return df
        
        initial_count = len(df)
        self.logger.info(f"Applying filters to {initial_count} symbols")
        
        # Apply individual filters
        df = self._filter_by_price(df)
        df = self._filter_by_volume(df)
        df = self._filter_by_volatility(df)
        df = self._filter_by_data_quality(df)
        df = self._filter_extreme_movers(df)
        
        # Apply sector limits
        df = self._apply_sector_limits(df)
        
        final_count = len(df)
        filtered_count = initial_count - final_count
        
        self.logger.info(
            f"Filtering complete: {final_count} symbols remaining "
            f"({filtered_count} filtered out)"
        )
        
        return df
    
    def _filter_by_price(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter by price range."""
        initial_count = len(df)
        
        # Price range filter
        price_mask = (
            (df["last"] >= self.config["min_price"]) &
            (df["last"] <= self.config["max_price"]) &
            (df["last"] > 0)  # Exclude zero/negative prices
        )
        
        df = df[price_mask].copy()
        
        filtered_count = initial_count - len(df)
        if filtered_count > 0:
            self.logger.info(f"Price filter: removed {filtered_count} symbols")
        
        return df
    
    def _filter_by_volume(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter by volume criteria."""
        initial_count = len(df)
        
        # Volume filters
        volume_mask = (
            (df["volume"] >= self.config["min_volume"]) &
            (df["avg_dollar_volume_20d"].fillna(0) >= self.config["min_dollar_volume"])
        )
        
        df = df[volume_mask].copy()
        
        filtered_count = initial_count - len(df)
        if filtered_count > 0:
            self.logger.info(f"Volume filter: removed {filtered_count} symbols")
        
        return df
    
    def _filter_by_volatility(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter by volatility requirements."""
        initial_count = len(df)
        
        # Volatility filter - need minimum ATR% for trading opportunities
        volatility_mask = (
            (df["atrp_14"].fillna(0) >= self.config["min_atr_percent"]) |
            (df["hv_20"].fillna(0) >= self.config["min_atr_percent"])
        )
        
        df = df[volatility_mask].copy()
        
        filtered_count = initial_count - len(df)
        if filtered_count > 0:
            self.logger.info(f"Volatility filter: removed {filtered_count} symbols")
        
        return df
    
    def _filter_by_data_quality(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter out symbols with poor data quality."""
        initial_count = len(df)
        
        # Data quality filters
        quality_mask = (
            # Basic price sanity checks
            (df["last"] > 0) &
            (df["high"] >= df["low"]) &
            (df["high"] >= df["open"]) &
            (df["low"] <= df["open"]) &
            # Volume sanity check
            (df["volume"] >= 0) &
            # No extreme price ratios
            (df["high"] / df["low"] <= 10) &  # Max 10x intraday range
            # Open price reasonable vs close
            (abs(df["gap_pct"].fillna(0)) <= self.config["max_gap_pct"])
        )
        
        df = df[quality_mask].copy()
        
        filtered_count = initial_count - len(df)
        if filtered_count > 0:
            self.logger.info(f"Data quality filter: removed {filtered_count} symbols")
        
        return df
    
    def _filter_extreme_movers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter out extreme price movements that might be errors."""
        initial_count = len(df)
        
        # Filter extreme gaps (might be stock splits, errors, etc.)
        gap_filter = abs(df["gap_pct"].fillna(0)) <= self.config["max_gap_pct"]
        
        # Filter extreme intraday ranges
        range_filter = df["range_pct_day"].fillna(0) <= 100  # Max 100% intraday range
        
        # Combine filters
        extreme_filter = gap_filter & range_filter
        
        df = df[extreme_filter].copy()
        
        filtered_count = initial_count - len(df)
        if filtered_count > 0:
            self.logger.info(f"Extreme movers filter: removed {filtered_count} symbols")
        
        return df
    
    def _apply_sector_limits(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply per-sector symbol limits for diversification."""
        if "sector" not in df.columns or df["sector"].isna().all():
            return df
        
        max_per_sector = self.config["max_symbols_per_sector"]
        if max_per_sector <= 0:
            return df
        
        initial_count = len(df)
        
        # Group by sector and take top symbols by a ranking criteria
        # Use ATR% as the ranking criteria (higher volatility preferred)
        ranking_col = "atrp_14"
        if ranking_col not in df.columns:
            ranking_col = "volume"  # Fallback to volume
        
        # Apply sector limits
        result_dfs = []
        for sector, sector_df in df.groupby("sector"):
            if len(sector_df) > max_per_sector:
                # Sort by ranking criteria descending and take top N
                sector_df = sector_df.nlargest(max_per_sector, ranking_col)
                self.logger.info(
                    f"Sector '{sector}': limited to {max_per_sector} symbols "
                    f"(was {len(sector_df)} symbols)"
                )
            
            result_dfs.append(sector_df)
        
        df = pd.concat(result_dfs, ignore_index=True) if result_dfs else df
        
        final_count = len(df)
        filtered_count = initial_count - final_count
        
        if filtered_count > 0:
            self.logger.info(f"Sector limits: removed {filtered_count} symbols")
        
        return df
    
    def get_filter_summary(self, original_df: pd.DataFrame, filtered_df: pd.DataFrame) -> Dict[str, Any]:
        """Generate summary of filtering results."""
        original_count = len(original_df)
        final_count = len(filtered_df)
        filtered_count = original_count - final_count
        filter_rate = (filtered_count / original_count) * 100 if original_count > 0 else 0
        
        summary = {
            "original_count": original_count,
            "final_count": final_count,
            "filtered_count": filtered_count,
            "filter_rate_pct": round(filter_rate, 2),
            "config": self.config.copy()
        }
        
        # Add sector breakdown if available
        if "sector" in filtered_df.columns:
            sector_counts = filtered_df["sector"].value_counts().to_dict()
            summary["sector_breakdown"] = sector_counts
        
        return summary
