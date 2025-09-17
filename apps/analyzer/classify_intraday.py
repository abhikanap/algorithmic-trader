"""Intraday pattern classification engine."""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from packages.core import get_logger
from packages.core.models import IntradayPattern


class IntradayClassifier:
    """Classifies stocks into intraday patterns based on price action."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    async def classify(self, df: pd.DataFrame, historical_df: pd.DataFrame) -> pd.DataFrame:
        """
        Classify stocks into intraday patterns.
        
        Args:
            df: Current market data with features
            historical_df: Historical price data
            
        Returns:
            DataFrame with added pattern classification columns
        """
        self.logger.info(f"Classifying intraday patterns for {len(df)} symbols")
        
        result_df = df.copy()
        
        # Initialize pattern columns
        result_df["pattern_intraday"] = None
        result_df["pattern_confidence"] = 0.0
        result_df["pattern_signals"] = ""
        
        # Classify each symbol
        for idx, row in result_df.iterrows():
            symbol = row["symbol"]
            pattern, confidence, signals = self._classify_symbol(row, historical_df)
            
            result_df.at[idx, "pattern_intraday"] = pattern.value if pattern else None
            result_df.at[idx, "pattern_confidence"] = confidence
            result_df.at[idx, "pattern_signals"] = "; ".join(signals)
        
        pattern_counts = result_df["pattern_intraday"].value_counts()
        self.logger.info(f"Pattern distribution: {dict(pattern_counts)}")
        
        return result_df
    
    def _classify_symbol(
        self, 
        row: pd.Series, 
        historical_df: pd.DataFrame
    ) -> tuple[Optional[IntradayPattern], float, list[str]]:
        """
        Classify a single symbol into intraday pattern.
        
        Returns:
            (pattern, confidence, signals)
        """
        symbol = row["symbol"]
        signals = []
        
        # Get current price action
        last = row.get("last", 0)
        open_price = row.get("open", 0)
        high = row.get("high", 0)
        low = row.get("low", 0)
        prev_close = row.get("close", 0)  # Previous close
        gap_pct = row.get("gap_pct", 0)
        range_pct = row.get("range_pct_day", 0)
        volume_ratio = row.get("volume_ratio", 1.0)
        
        # Get historical context if available
        symbol_hist = historical_df[historical_df["symbol"] == symbol] if not historical_df.empty else pd.DataFrame()
        
        # Safety checks
        if last <= 0 or open_price <= 0:
            return None, 0.0, ["insufficient_data"]
        
        # Pattern classification logic
        
        # 1. Morning Spike → Fade (Pump & Fade)
        if self._is_morning_spike_fade(row, symbol_hist):
            signals.extend(self._get_spike_fade_signals(row))
            confidence = self._calculate_spike_fade_confidence(row, signals)
            return IntradayPattern.MORNING_SPIKE_FADE, confidence, signals
        
        # 2. Morning Surge → All-Day Uptrend
        if self._is_morning_surge_uptrend(row, symbol_hist):
            signals.extend(self._get_surge_uptrend_signals(row))
            confidence = self._calculate_surge_confidence(row, signals)
            return IntradayPattern.MORNING_SURGE_UPTREND, confidence, signals
        
        # 3. Morning Plunge → Midday Recovery
        if self._is_morning_plunge_recovery(row, symbol_hist):
            signals.extend(self._get_plunge_recovery_signals(row))
            confidence = self._calculate_recovery_confidence(row, signals)
            return IntradayPattern.MORNING_PLUNGE_RECOVERY, confidence, signals
        
        # 4. Morning Sell-Off → All-Day Downtrend
        if self._is_morning_selloff_downtrend(row, symbol_hist):
            signals.extend(self._get_selloff_signals(row))
            confidence = self._calculate_selloff_confidence(row, signals)
            return IntradayPattern.MORNING_SELLOFF_DOWNTREND, confidence, signals
        
        # 5. Choppy/Range-Bound Day (default for unclear patterns)
        signals.extend(self._get_choppy_signals(row))
        confidence = self._calculate_choppy_confidence(row, signals)
        return IntradayPattern.CHOPPY_RANGE_BOUND, confidence, signals
    
    def _is_morning_spike_fade(self, row: pd.Series, hist_df: pd.DataFrame) -> bool:
        """Check for morning spike → fade pattern."""
        gap_pct = row.get("gap_pct", 0)
        last = row.get("last", 0)
        open_price = row.get("open", 0)
        high = row.get("high", 0)
        volume_ratio = row.get("volume_ratio", 1.0)
        
        # Criteria: Gap up, high volume, but fading from highs
        return (
            gap_pct > 3.0 and  # Significant gap up
            volume_ratio > 1.5 and  # High volume
            last < (high * 0.85) and  # Fading from highs
            last < (open_price * 1.05)  # Not holding gains
        )
    
    def _is_morning_surge_uptrend(self, row: pd.Series, hist_df: pd.DataFrame) -> bool:
        """Check for morning surge → all-day uptrend pattern."""
        gap_pct = row.get("gap_pct", 0)
        last = row.get("last", 0)
        open_price = row.get("open", 0)
        high = row.get("high", 0)
        volume_ratio = row.get("volume_ratio", 1.0)
        
        # Criteria: Strong open, holding near highs
        return (
            (gap_pct > 2.0 or (last / open_price - 1) * 100 > 3.0) and  # Gap or strong move
            last > (high * 0.9) and  # Holding near highs
            volume_ratio > 1.2 and  # Above average volume
            last > open_price * 1.02  # Holding gains
        )
    
    def _is_morning_plunge_recovery(self, row: pd.Series, hist_df: pd.DataFrame) -> bool:
        """Check for morning plunge → recovery pattern."""
        gap_pct = row.get("gap_pct", 0)
        last = row.get("last", 0)
        open_price = row.get("open", 0)
        low = row.get("low", 0)
        volume_ratio = row.get("volume_ratio", 1.0)
        
        # Criteria: Gap down or weak open, but recovering
        return (
            (gap_pct < -2.0 or low < open_price * 0.95) and  # Gap down or weakness
            last > low * 1.03 and  # Recovering from lows
            last > open_price * 0.98 and  # Back near open
            volume_ratio > 1.1  # Some volume
        )
    
    def _is_morning_selloff_downtrend(self, row: pd.Series, hist_df: pd.DataFrame) -> bool:
        """Check for morning sell-off → downtrend pattern."""
        gap_pct = row.get("gap_pct", 0)
        last = row.get("last", 0)
        open_price = row.get("open", 0)
        low = row.get("low", 0)
        volume_ratio = row.get("volume_ratio", 1.0)
        
        # Criteria: Weakness and staying weak
        return (
            (gap_pct < -1.0 or last < open_price * 0.97) and  # Gap down or weakness
            last < (low * 1.05) and  # Near lows
            volume_ratio > 1.0  # Some selling pressure
        )
    
    # Signal extraction methods
    def _get_spike_fade_signals(self, row: pd.Series) -> list[str]:
        signals = ["gap_up", "high_volume", "fading_from_highs"]
        if row.get("volume_ratio", 1.0) > 2.0:
            signals.append("very_high_volume")
        return signals
    
    def _get_surge_uptrend_signals(self, row: pd.Series) -> list[str]:
        signals = ["strong_open", "holding_gains", "near_highs"]
        if row.get("gap_pct", 0) > 5.0:
            signals.append("large_gap")
        return signals
    
    def _get_plunge_recovery_signals(self, row: pd.Series) -> list[str]:
        signals = ["gap_down", "recovering", "bouncing_from_lows"]
        return signals
    
    def _get_selloff_signals(self, row: pd.Series) -> list[str]:
        signals = ["weak_open", "selling_pressure", "near_lows"]
        return signals
    
    def _get_choppy_signals(self, row: pd.Series) -> list[str]:
        signals = ["mixed_signals", "range_bound"]
        return signals
    
    # Confidence calculation methods
    def _calculate_spike_fade_confidence(self, row: pd.Series, signals: list[str]) -> float:
        base_confidence = 0.6
        if "very_high_volume" in signals:
            base_confidence += 0.2
        if row.get("gap_pct", 0) > 10.0:
            base_confidence += 0.1
        return min(base_confidence, 0.95)
    
    def _calculate_surge_confidence(self, row: pd.Series, signals: list[str]) -> float:
        base_confidence = 0.7
        if "large_gap" in signals:
            base_confidence += 0.1
        if row.get("volume_ratio", 1.0) > 2.0:
            base_confidence += 0.1
        return min(base_confidence, 0.95)
    
    def _calculate_recovery_confidence(self, row: pd.Series, signals: list[str]) -> float:
        return 0.6  # Moderate confidence for recovery patterns
    
    def _calculate_selloff_confidence(self, row: pd.Series, signals: list[str]) -> float:
        return 0.65
    
    def _calculate_choppy_confidence(self, row: pd.Series, signals: list[str]) -> float:
        return 0.4  # Lower confidence for unclear patterns
