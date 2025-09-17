"""Multi-day pattern classification engine."""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from packages.core import get_logger
from packages.core.models import MultidayPattern


class MultidayClassifier:
    """Classifies stocks into multi-day patterns based on historical trends."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    async def classify(self, df: pd.DataFrame, historical_df: pd.DataFrame) -> pd.DataFrame:
        """
        Classify stocks into multi-day patterns.
        
        Args:
            df: Current market data with features
            historical_df: Historical price data
            
        Returns:
            DataFrame with added multi-day pattern classification columns
        """
        self.logger.info(f"Classifying multi-day patterns for {len(df)} symbols")
        
        result_df = df.copy()
        
        # Initialize pattern columns
        result_df["pattern_multiday"] = None
        result_df["multiday_confidence"] = 0.0
        result_df["multiday_signals"] = ""
        
        # Classify each symbol
        for idx, row in result_df.iterrows():
            symbol = row["symbol"]
            pattern, confidence, signals = self._classify_symbol(row, historical_df)
            
            result_df.at[idx, "pattern_multiday"] = pattern.value if pattern else None
            result_df.at[idx, "multiday_confidence"] = confidence
            result_df.at[idx, "multiday_signals"] = "; ".join(signals)
        
        pattern_counts = result_df["pattern_multiday"].value_counts()
        self.logger.info(f"Multi-day pattern distribution: {dict(pattern_counts)}")
        
        return result_df
    
    def _classify_symbol(
        self, 
        row: pd.Series, 
        historical_df: pd.DataFrame
    ) -> tuple[Optional[MultidayPattern], float, list[str]]:
        """
        Classify a single symbol into multi-day pattern.
        
        Returns:
            (pattern, confidence, signals)
        """
        symbol = row["symbol"]
        signals = []
        
        # Get historical data for this symbol
        symbol_hist = historical_df[historical_df["symbol"] == symbol] if not historical_df.empty else pd.DataFrame()
        
        if symbol_hist.empty or len(symbol_hist) < 10:
            return MultidayPattern.SIDEWAYS_CONSOLIDATION, 0.3, ["insufficient_data"]
        
        # Sort by date
        symbol_hist = symbol_hist.sort_values("date")
        
        # Calculate trend metrics
        recent_data = symbol_hist.tail(10)  # Last 10 days
        longer_data = symbol_hist.tail(20) if len(symbol_hist) >= 20 else symbol_hist  # Last 20 days
        
        # Pattern classification based on price trends
        
        # 1. Sustained Uptrend (Multi-Day Rally)
        if self._is_sustained_uptrend(recent_data, longer_data):
            signals.extend(self._get_uptrend_signals(recent_data, longer_data))
            confidence = self._calculate_uptrend_confidence(recent_data, signals)
            return MultidayPattern.SUSTAINED_UPTREND, confidence, signals
        
        # 2. Sustained Downtrend (Multi-Day Selloff)
        if self._is_sustained_downtrend(recent_data, longer_data):
            signals.extend(self._get_downtrend_signals(recent_data, longer_data))
            confidence = self._calculate_downtrend_confidence(recent_data, signals)
            return MultidayPattern.SUSTAINED_DOWNTREND, confidence, signals
        
        # 3. Blow-Off Top / First Red Day
        if self._is_blowoff_top(recent_data, longer_data):
            signals.extend(self._get_blowoff_signals(recent_data, longer_data))
            confidence = self._calculate_blowoff_confidence(recent_data, signals)
            return MultidayPattern.BLOWOFF_TOP, confidence, signals
        
        # 4. Downtrend → Reversal Up
        if self._is_downtrend_reversal(recent_data, longer_data):
            signals.extend(self._get_reversal_signals(recent_data, longer_data))
            confidence = self._calculate_reversal_confidence(recent_data, signals)
            return MultidayPattern.DOWNTREND_REVERSAL, confidence, signals
        
        # 5. Sideways Consolidation/Base (default)
        signals.extend(self._get_consolidation_signals(recent_data))
        confidence = self._calculate_consolidation_confidence(recent_data, signals)
        return MultidayPattern.SIDEWAYS_CONSOLIDATION, confidence, signals
    
    def _is_sustained_uptrend(self, recent_data: pd.DataFrame, longer_data: pd.DataFrame) -> bool:
        """Check for sustained uptrend pattern."""
        if len(recent_data) < 5:
            return False
        
        # Calculate recent trend
        recent_returns = recent_data["close"].pct_change().dropna()
        
        # Criteria for uptrend
        positive_days = (recent_returns > 0).sum()
        total_return = (recent_data["close"].iloc[-1] / recent_data["close"].iloc[0] - 1) * 100
        
        return (
            positive_days >= 6 and  # At least 6 positive days out of last 10
            total_return > 15.0 and  # At least 15% gain
            recent_data["close"].iloc[-1] > recent_data["close"].rolling(5).mean().iloc[-1]  # Above 5-day MA
        )
    
    def _is_sustained_downtrend(self, recent_data: pd.DataFrame, longer_data: pd.DataFrame) -> bool:
        """Check for sustained downtrend pattern."""
        if len(recent_data) < 5:
            return False
        
        recent_returns = recent_data["close"].pct_change().dropna()
        
        negative_days = (recent_returns < 0).sum()
        total_return = (recent_data["close"].iloc[-1] / recent_data["close"].iloc[0] - 1) * 100
        
        return (
            negative_days >= 6 and  # At least 6 negative days
            total_return < -10.0 and  # At least 10% decline
            recent_data["close"].iloc[-1] < recent_data["close"].rolling(5).mean().iloc[-1]  # Below 5-day MA
        )
    
    def _is_blowoff_top(self, recent_data: pd.DataFrame, longer_data: pd.DataFrame) -> bool:
        """Check for blow-off top pattern."""
        if len(recent_data) < 5 or len(longer_data) < 15:
            return False
        
        # Look for: strong uptrend followed by recent weakness
        longer_return = (longer_data["close"].iloc[-6] / longer_data["close"].iloc[0] - 1) * 100
        recent_return = (recent_data["close"].iloc[-1] / recent_data["close"].iloc[-5] - 1) * 100
        
        # High volume in recent days (if available)
        volume_surge = False
        if "volume" in recent_data.columns:
            recent_avg_vol = recent_data["volume"].tail(3).mean()
            longer_avg_vol = longer_data["volume"].mean()
            volume_surge = recent_avg_vol > longer_avg_vol * 1.5
        
        return (
            longer_return > 20.0 and  # Strong prior uptrend
            recent_return < -5.0 and  # Recent weakness
            volume_surge  # High volume
        )
    
    def _is_downtrend_reversal(self, recent_data: pd.DataFrame, longer_data: pd.DataFrame) -> bool:
        """Check for downtrend reversal pattern."""
        if len(recent_data) < 5 or len(longer_data) < 15:
            return False
        
        # Look for: prior downtrend followed by recent strength
        longer_return = (longer_data["close"].iloc[-6] / longer_data["close"].iloc[0] - 1) * 100
        recent_return = (recent_data["close"].iloc[-1] / recent_data["close"].iloc[-5] - 1) * 100
        
        return (
            longer_return < -15.0 and  # Prior downtrend
            recent_return > 8.0 and  # Recent strength
            recent_data["close"].iloc[-1] > recent_data["close"].rolling(3).mean().iloc[-1]  # Above recent MA
        )
    
    # Signal extraction methods
    def _get_uptrend_signals(self, recent_data: pd.DataFrame, longer_data: pd.DataFrame) -> list[str]:
        signals = ["multi_day_uptrend", "higher_highs", "higher_lows"]
        
        if len(recent_data) >= 5:
            total_return = (recent_data["close"].iloc[-1] / recent_data["close"].iloc[0] - 1) * 100
            if total_return > 25.0:
                signals.append("strong_momentum")
        
        return signals
    
    def _get_downtrend_signals(self, recent_data: pd.DataFrame, longer_data: pd.DataFrame) -> list[str]:
        signals = ["multi_day_downtrend", "lower_highs", "lower_lows"]
        
        if len(recent_data) >= 5:
            total_return = (recent_data["close"].iloc[-1] / recent_data["close"].iloc[0] - 1) * 100
            if total_return < -20.0:
                signals.append("strong_selling")
        
        return signals
    
    def _get_blowoff_signals(self, recent_data: pd.DataFrame, longer_data: pd.DataFrame) -> list[str]:
        return ["prior_uptrend", "recent_weakness", "potential_exhaustion"]
    
    def _get_reversal_signals(self, recent_data: pd.DataFrame, longer_data: pd.DataFrame) -> list[str]:
        return ["prior_downtrend", "recent_strength", "potential_reversal"]
    
    def _get_consolidation_signals(self, recent_data: pd.DataFrame) -> list[str]:
        return ["sideways_action", "consolidation", "mixed_signals"]
    
    # Confidence calculation methods
    def _calculate_uptrend_confidence(self, recent_data: pd.DataFrame, signals: list[str]) -> float:
        base_confidence = 0.7
        if "strong_momentum" in signals:
            base_confidence += 0.15
        return min(base_confidence, 0.9)
    
    def _calculate_downtrend_confidence(self, recent_data: pd.DataFrame, signals: list[str]) -> float:
        base_confidence = 0.7
        if "strong_selling" in signals:
            base_confidence += 0.15
        return min(base_confidence, 0.9)
    
    def _calculate_blowoff_confidence(self, recent_data: pd.DataFrame, signals: list[str]) -> float:
        return 0.6  # Moderate confidence for reversal patterns
    
    def _calculate_reversal_confidence(self, recent_data: pd.DataFrame, signals: list[str]) -> float:
        return 0.6  # Moderate confidence for reversal patterns
    
    def _calculate_consolidation_confidence(self, recent_data: pd.DataFrame, signals: list[str]) -> float:
        return 0.5  # Neutral confidence for consolidation
