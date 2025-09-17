"""Trade signal generation system."""

import asyncio
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from packages.core import get_logger
from packages.core.models import TradeSignal, SignalType


class SignalGenerator:
    """Generates trade signals based on patterns and bucket allocations."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Signal generation rules
        self.signal_rules = {
            "MORNING_SPIKE_FADE": {
                "signal_type": SignalType.SHORT,
                "confidence_threshold": 0.6,
                "max_hold_hours": 4,
                "stop_loss_pct": 3.0,
                "target_pct": 5.0
            },
            "MORNING_SURGE_UPTREND": {
                "signal_type": SignalType.LONG,
                "confidence_threshold": 0.7,
                "max_hold_hours": 6,
                "stop_loss_pct": 2.5,
                "target_pct": 4.0
            },
            "MORNING_PLUNGE_RECOVERY": {
                "signal_type": SignalType.LONG,
                "confidence_threshold": 0.6,
                "max_hold_hours": 3,
                "stop_loss_pct": 2.0,
                "target_pct": 3.0
            },
            "MORNING_SELLOFF_DOWNTREND": {
                "signal_type": SignalType.SHORT,
                "confidence_threshold": 0.65,
                "max_hold_hours": 5,
                "stop_loss_pct": 2.5,
                "target_pct": 4.0
            },
            "CHOPPY_RANGE_BOUND": {
                "signal_type": SignalType.NEUTRAL,
                "confidence_threshold": 0.8,  # Higher threshold for unclear patterns
                "max_hold_hours": 2,
                "stop_loss_pct": 1.5,
                "target_pct": 2.0
            }
        }
        
        self.logger.info("Initialized signal generator")
    
    async def generate_signals(
        self,
        df: pd.DataFrame,
        bucket_allocations: Dict[str, float],
        max_positions: int = 20
    ) -> pd.DataFrame:
        """
        Generate trade signals from analyzed data.
        
        Args:
            df: DataFrame with analyzer results and bucket assignments
            bucket_allocations: Capital allocated to each bucket
            max_positions: Maximum number of positions to generate
            
        Returns:
            DataFrame with trade signals
        """
        self.logger.info(f"Generating signals for {len(df)} symbols")
        
        # Filter for signal-worthy symbols
        signal_candidates = self._filter_candidates(df)
        
        if signal_candidates.empty:
            self.logger.warning("No signal candidates found")
            return pd.DataFrame()
        
        # Generate raw signals
        signals_df = self._generate_raw_signals(signal_candidates)
        
        # Rank and prioritize signals
        ranked_signals = self._rank_signals(signals_df)
        
        # Apply position limits
        final_signals = self._apply_position_limits(ranked_signals, max_positions)
        
        # Add risk management parameters
        final_signals = self._add_risk_parameters(final_signals)
        
        self.logger.info(f"Generated {len(final_signals)} trade signals")
        
        return final_signals
    
    def _filter_candidates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter symbols that are candidates for signals."""
        
        candidates = df.copy()
        
        # Remove symbols with insufficient data
        candidates = candidates[candidates["last"] > 0]
        candidates = candidates[candidates["volume"] > 0]
        
        # Remove symbols with very low confidence
        min_confidence = 0.4
        candidates = candidates[
            candidates.get("pattern_confidence", 0) >= min_confidence
        ]
        
        # Remove symbols that are too volatile or illiquid
        max_atr = 15.0  # Max 15% daily ATR
        min_volume = 100000  # Min $100k daily volume
        
        candidates = candidates[
            (candidates.get("atrp_14", 0) <= max_atr) &
            (candidates.get("avg_dollar_volume_20d", 0) >= min_volume)
        ]
        
        self.logger.info(f"Filtered to {len(candidates)} signal candidates")
        
        return candidates
    
    def _generate_raw_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate raw trade signals for each candidate."""
        
        signals = []
        
        for idx, row in df.iterrows():
            signal_data = self._create_signal(row)
            if signal_data:
                signals.append(signal_data)
        
        if not signals:
            return pd.DataFrame()
        
        return pd.DataFrame(signals)
    
    def _create_signal(self, row: pd.Series) -> Optional[Dict[str, Any]]:
        """Create a trade signal for a single symbol."""
        
        symbol = row.get("symbol", "")
        pattern = row.get("pattern_intraday", "")
        confidence = row.get("pattern_confidence", 0)
        price = row.get("last", 0)
        
        # Get signal rules for this pattern
        rules = self.signal_rules.get(pattern)
        if not rules:
            return None
        
        # Check confidence threshold
        if confidence < rules["confidence_threshold"]:
            return None
        
        # Create signal
        signal = {
            "symbol": symbol,
            "signal_type": rules["signal_type"].value,
            "pattern": pattern,
            "confidence": confidence,
            "entry_price": price,
            "current_price": price,
            "bucket": row.get("bucket", "BUCKET_B"),
            "time_segment": row.get("time_segment", "MIDDAY"),
            
            # Risk parameters (will be refined later)
            "stop_loss_pct": rules["stop_loss_pct"],
            "target_pct": rules["target_pct"],
            "max_hold_hours": rules["max_hold_hours"],
            
            # Technical indicators
            "atr_pct": row.get("atrp_14", 0),
            "volume_ratio": row.get("volume_ratio", 1.0),
            "gap_pct": row.get("gap_pct", 0),
            
            # Strategy hints
            "entry_hints": row.get("entry_hints", ""),
            "exit_hints": row.get("exit_hints", ""),
            
            # Timestamps
            "signal_generated_at": pd.Timestamp.now(),
            "valid_until": pd.Timestamp.now() + pd.Timedelta(hours=rules["max_hold_hours"])
        }
        
        return signal
    
    def _rank_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rank signals by attractiveness score."""
        
        if df.empty:
            return df
        
        result_df = df.copy()
        
        # Calculate composite score
        scores = []
        for idx, row in result_df.iterrows():
            score = self._calculate_signal_score(row)
            scores.append(score)
        
        result_df["signal_score"] = scores
        
        # Sort by score (descending)
        result_df = result_df.sort_values("signal_score", ascending=False).reset_index(drop=True)
        
        # Add rank
        result_df["rank"] = range(1, len(result_df) + 1)
        
        return result_df
    
    def _calculate_signal_score(self, row: pd.Series) -> float:
        """Calculate composite attractiveness score for a signal."""
        
        # Base score from pattern confidence
        score = row.get("confidence", 0) * 100
        
        # Adjust for volume (higher is better)
        volume_ratio = row.get("volume_ratio", 1.0)
        volume_boost = min(volume_ratio - 1.0, 2.0) * 10  # Max +20 points
        score += volume_boost
        
        # Adjust for volatility (moderate levels preferred)
        atr_pct = row.get("atr_pct", 2.0)
        if 2.0 <= atr_pct <= 6.0:  # Sweet spot
            volatility_boost = 10
        elif atr_pct > 10.0:  # Too volatile
            volatility_boost = -20
        else:
            volatility_boost = 0
        score += volatility_boost
        
        # Pattern-specific adjustments
        pattern = row.get("pattern", "")
        if pattern == "MORNING_SURGE_UPTREND":
            score += 15  # Preferred pattern
        elif pattern == "MORNING_SPIKE_FADE":
            score += 10  # Good for shorting
        elif pattern == "CHOPPY_RANGE_BOUND":
            score -= 10  # Less preferred
        
        # Bucket adjustments
        bucket = row.get("bucket", "")
        if bucket == "BUCKET_A":  # Penny stocks - higher risk/reward
            score += 5
        elif bucket == "BUCKET_B":  # Large cap - more reliable
            score += 10
        elif bucket == "BUCKET_D":  # Catalyst driven - high potential
            score += 8
        
        return max(score, 0)  # No negative scores
    
    def _apply_position_limits(
        self, 
        df: pd.DataFrame, 
        max_positions: int
    ) -> pd.DataFrame:
        """Apply position limits and diversification rules."""
        
        if df.empty or len(df) <= max_positions:
            return df
        
        # Take top signals by score
        limited_df = df.head(max_positions).copy()
        
        # Ensure diversification across buckets
        limited_df = self._ensure_bucket_diversification(limited_df)
        
        # Ensure no more than 2 positions per symbol (edge case)
        limited_df = limited_df.drop_duplicates(subset=["symbol"], keep="first")
        
        return limited_df
    
    def _ensure_bucket_diversification(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure reasonable diversification across buckets."""
        
        if df.empty:
            return df
        
        # Max positions per bucket
        max_per_bucket = {
            "BUCKET_A": 3,  # Penny stocks - limit exposure
            "BUCKET_B": 8,  # Large cap - can have more
            "BUCKET_C": 6,  # Multi-day - moderate
            "BUCKET_D": 2,  # Catalyst - high risk, limit exposure
            "BUCKET_E": 1   # Defensive - just one hedge
        }
        
        diversified = []
        bucket_counts = {}
        
        for _, row in df.iterrows():
            bucket = row.get("bucket", "BUCKET_B")
            current_count = bucket_counts.get(bucket, 0)
            max_allowed = max_per_bucket.get(bucket, 5)
            
            if current_count < max_allowed:
                diversified.append(row)
                bucket_counts[bucket] = current_count + 1
        
        return pd.DataFrame(diversified) if diversified else df
    
    def _add_risk_parameters(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add detailed risk management parameters to signals."""
        
        if df.empty:
            return df
        
        result_df = df.copy()
        
        for idx, row in result_df.iterrows():
            # Calculate dynamic stop loss based on ATR
            atr_pct = row.get("atr_pct", 2.0)
            base_stop = row.get("stop_loss_pct", 2.5)
            
            # Adjust stop loss for volatility
            if atr_pct > 8.0:  # High volatility
                adjusted_stop = base_stop * 1.5
            elif atr_pct < 2.0:  # Low volatility
                adjusted_stop = base_stop * 0.8
            else:
                adjusted_stop = base_stop
            
            result_df.at[idx, "stop_loss_pct"] = round(adjusted_stop, 2)
            
            # Calculate position-specific targets
            confidence = row.get("confidence", 0.5)
            base_target = row.get("target_pct", 3.0)
            
            # Adjust target for confidence
            adjusted_target = base_target * (0.5 + confidence)
            result_df.at[idx, "target_pct"] = round(adjusted_target, 2)
            
            # Calculate actual stop/target prices
            entry_price = row.get("entry_price", 0)
            signal_type = row.get("signal_type", "LONG")
            
            if signal_type == "LONG":
                stop_price = entry_price * (1 - adjusted_stop / 100)
                target_price = entry_price * (1 + adjusted_target / 100)
            else:  # SHORT
                stop_price = entry_price * (1 + adjusted_stop / 100)
                target_price = entry_price * (1 - adjusted_target / 100)
            
            result_df.at[idx, "stop_loss_price"] = round(stop_price, 2)
            result_df.at[idx, "target_price"] = round(target_price, 2)
        
        return result_df
    
    def get_signal_rules(self) -> Dict[str, Any]:
        """Get current signal generation rules."""
        return self.signal_rules.copy()
    
    def update_signal_rules(
        self, 
        pattern: str, 
        updates: Dict[str, Any]
    ) -> bool:
        """Update signal rules for a pattern."""
        
        if pattern not in self.signal_rules:
            self.logger.error(f"Unknown pattern: {pattern}")
            return False
        
        try:
            self.signal_rules[pattern].update(updates)
            self.logger.info(f"Updated signal rules for {pattern}: {updates}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update signal rules: {e}")
            return False
    
    def get_signal_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate statistics about generated signals."""
        
        if df.empty:
            return {}
        
        return {
            "total_signals": len(df),
            "signal_type_distribution": df.get("signal_type", pd.Series()).value_counts().to_dict(),
            "pattern_distribution": df.get("pattern", pd.Series()).value_counts().to_dict(),
            "bucket_distribution": df.get("bucket", pd.Series()).value_counts().to_dict(),
            "avg_confidence": df.get("confidence", pd.Series()).mean(),
            "avg_score": df.get("signal_score", pd.Series()).mean(),
            "score_range": {
                "min": df.get("signal_score", pd.Series()).min(),
                "max": df.get("signal_score", pd.Series()).max()
            }
        }
