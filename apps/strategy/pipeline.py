"""Strategy engine pipeline for capital allocation and signal generation."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np

from packages.core import get_logger
from packages.core.config import settings
from packages.core.models import CapitalBucket, TimeSegment, TradeSignal

from .allocators import BucketAllocator
from .signals import SignalGenerator


class StrategyPipeline:
    """Main strategy pipeline that allocates capital and generates trade signals."""
    
    def __init__(
        self,
        bucket_allocator: Optional[BucketAllocator] = None,
        signal_generator: Optional[SignalGenerator] = None
    ):
        self.logger = get_logger(__name__)
        
        # Initialize components
        self.bucket_allocator = bucket_allocator or BucketAllocator()
        self.signal_generator = signal_generator or SignalGenerator()
        
        self.logger.info("Initialized strategy pipeline")
    
    async def run(
        self,
        analyzer_data: Optional[pd.DataFrame] = None,
        date: Optional[str] = None,
        total_capital: float = 100000.0,
        max_positions: int = 20,
        save_artifacts: bool = True
    ) -> Dict[str, Any]:
        """
        Run the complete strategy pipeline.
        
        Args:
            analyzer_data: DataFrame from analyzer pipeline
            date: Date string (YYYY-MM-DD). If None, uses today
            total_capital: Total capital to allocate
            max_positions: Maximum number of positions
            save_artifacts: Whether to save results to artifacts
            
        Returns:
            Dictionary containing results and metadata
        """
        start_time = datetime.now()
        
        if date is None:
            date = start_time.strftime("%Y-%m-%d")
        
        self.logger.info(f"Starting strategy pipeline for date: {date}")
        self.logger.info(f"Total capital: ${total_capital:,.2f}, Max positions: {max_positions}")
        
        try:
            # Load analyzer data if not provided
            if analyzer_data is None:
                analyzer_data = self._load_analyzer_data(date)
            
            if analyzer_data.empty:
                raise ValueError("No analyzer data available")
            
            self.logger.info(f"Processing {len(analyzer_data)} symbols")
            
            # Stage 1: Capital bucket allocation
            self.logger.info("Allocating capital to buckets...")
            bucket_allocations = self.bucket_allocator.allocate_to_buckets(
                analyzer_data, 
                total_capital
            )
            
            # Stage 2: Generate trade signals
            self.logger.info("Generating trade signals...")
            trade_signals = await self.signal_generator.generate_signals(
                analyzer_data,
                bucket_allocations,
                max_positions
            )
            
            # Stage 3: Position sizing and risk management
            self.logger.info("Calculating position sizes...")
            final_signals = self._calculate_position_sizes(
                trade_signals,
                bucket_allocations,
                total_capital
            )
            
            # Stage 4: Time segment recommendations
            final_signals = self._add_time_segments(final_signals)
            
            # Prepare results
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Generate metadata
            metadata = {
                "date": date,
                "duration_seconds": round(duration, 2),
                "total_capital": total_capital,
                "max_positions": max_positions,
                "total_signals": len(final_signals),
                "bucket_allocations": bucket_allocations,
                "signal_statistics": self._generate_signal_statistics(final_signals)
            }
            
            # Save artifacts if requested
            saved_files = {}
            if save_artifacts and not final_signals.empty:
                self.logger.info("Saving strategy artifacts...")
                saved_files = self._save_artifacts(final_signals, date, metadata)
                metadata["saved_files"] = saved_files
            
            result = {
                "success": True,
                "data": final_signals,
                "metadata": metadata,
                "saved_files": saved_files
            }
            
            self.logger.info(
                f"Strategy pipeline completed successfully in {duration:.1f}s. "
                f"Generated {len(final_signals)} trade signals"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Strategy pipeline failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return {
                "success": False,
                "error": error_msg,
                "data": pd.DataFrame(),
                "metadata": {
                    "date": date,
                    "error": str(e),
                    "duration_seconds": (datetime.now() - start_time).total_seconds()
                },
                "saved_files": {}
            }
    
    def _load_analyzer_data(self, date: str) -> pd.DataFrame:
        """Load analyzer data from artifacts."""
        try:
            from apps.analyzer.artifacts import ArtifactManager
            
            artifact_manager = ArtifactManager()
            results = artifact_manager.load_analyzer_results(date)
            return results.get("dataframe", pd.DataFrame())
            
        except Exception as e:
            self.logger.warning(f"Could not load analyzer data for {date}: {e}")
            return pd.DataFrame()
    
    def _calculate_position_sizes(
        self, 
        signals_df: pd.DataFrame, 
        bucket_allocations: Dict[str, float],
        total_capital: float
    ) -> pd.DataFrame:
        """Calculate position sizes based on bucket allocations and risk."""
        result_df = signals_df.copy()
        
        for idx, row in result_df.iterrows():
            bucket = row.get("bucket", "BUCKET_B")
            bucket_capital = bucket_allocations.get(bucket, 0)
            
            # Base position size (equal weight within bucket)
            symbols_in_bucket = len(result_df[result_df["bucket"] == bucket])
            base_position_size = bucket_capital / max(symbols_in_bucket, 1)
            
            # Adjust for volatility (ATR-based)
            atr_pct = row.get("atrp_14", 2.0)
            volatility_adjustment = min(2.0 / max(atr_pct, 0.5), 2.0)
            
            # Adjust for confidence
            confidence = row.get("pattern_confidence", 0.5)
            confidence_adjustment = 0.5 + (confidence * 0.5)
            
            # Final position size
            position_size = base_position_size * volatility_adjustment * confidence_adjustment
            position_size = min(position_size, total_capital * 0.1)  # Max 10% per position
            
            result_df.at[idx, "position_size"] = round(position_size, 2)
            result_df.at[idx, "shares"] = int(position_size / row.get("last", 1))
        
        return result_df
    
    def _add_time_segments(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add recommended time segments for each signal."""
        result_df = df.copy()
        
        for idx, row in result_df.iterrows():
            pattern = row.get("pattern_intraday", "")
            bucket = row.get("bucket", "BUCKET_B")
            
            # Determine optimal time segment
            time_segment = self._determine_time_segment(pattern, bucket)
            result_df.at[idx, "time_segment"] = time_segment.value if time_segment else "MARKET_OPEN"
            
            # Add entry and exit hints
            entry_hints, exit_hints = self._get_timing_hints(pattern)
            result_df.at[idx, "entry_hints"] = "; ".join(entry_hints)
            result_df.at[idx, "exit_hints"] = "; ".join(exit_hints)
        
        return result_df
    
    def _determine_time_segment(self, pattern: str, bucket: str) -> Optional[TimeSegment]:
        """Determine optimal time segment based on pattern and bucket."""
        
        # Morning patterns - best in early hours
        if pattern in ["MORNING_SPIKE_FADE", "MORNING_SURGE_UPTREND"]:
            return TimeSegment.MARKET_OPEN
        
        # Recovery patterns - better in late morning/midday
        if pattern == "MORNING_PLUNGE_RECOVERY":
            return TimeSegment.LATE_MORNING
            
        # Trend patterns - can work throughout day
        if pattern in ["MORNING_SURGE_UPTREND", "MORNING_SELLOFF_DOWNTREND"]:
            return TimeSegment.MIDDAY
        
        # Penny stocks (Bucket A) - best in high volume periods
        if bucket == "BUCKET_A":
            return TimeSegment.MARKET_OPEN
            
        # Large cap (Bucket B) - good throughout day
        if bucket == "BUCKET_B":
            return TimeSegment.MIDDAY
            
        # Multi-day (Bucket C) - less time sensitive
        if bucket == "BUCKET_C":
            return TimeSegment.AFTERNOON
        
        # Default
        return TimeSegment.MIDDAY
    
    def _get_timing_hints(self, pattern: str) -> tuple[List[str], List[str]]:
        """Get entry and exit timing hints for pattern."""
        
        if pattern == "MORNING_SPIKE_FADE":
            entry_hints = ["wait_for_fade", "short_bias", "volume_confirmation"]
            exit_hints = ["target_previous_support", "time_stop_by_noon"]
            
        elif pattern == "MORNING_SURGE_UPTREND":
            entry_hints = ["buy_pullbacks", "confirm_volume", "break_of_highs"]
            exit_hints = ["trail_stop", "end_of_day_exit"]
            
        elif pattern == "MORNING_PLUNGE_RECOVERY":
            entry_hints = ["wait_for_bounce", "oversold_levels", "volume_drying_up"]
            exit_hints = ["resistance_levels", "midday_profit_take"]
            
        elif pattern == "MORNING_SELLOFF_DOWNTREND":
            entry_hints = ["short_rallies", "break_of_lows", "weak_volume_on_bounces"]
            exit_hints = ["support_levels", "cover_before_close"]
            
        else:  # CHOPPY_RANGE_BOUND
            entry_hints = ["range_trading", "support_resistance", "smaller_size"]
            exit_hints = ["quick_profits", "avoid_overnight"]
        
        return entry_hints, exit_hints
    
    def _generate_signal_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate statistics about the signals."""
        if df.empty:
            return {}
        
        return {
            "total_signals": len(df),
            "bucket_distribution": df["bucket"].value_counts().to_dict(),
            "pattern_distribution": df.get("pattern_intraday", pd.Series()).value_counts().to_dict(),
            "time_segment_distribution": df.get("time_segment", pd.Series()).value_counts().to_dict(),
            "total_capital_allocated": df["position_size"].sum(),
            "average_position_size": df["position_size"].mean(),
            "confidence_stats": {
                "mean": df.get("pattern_confidence", pd.Series()).mean(),
                "min": df.get("pattern_confidence", pd.Series()).min(),
                "max": df.get("pattern_confidence", pd.Series()).max()
            }
        }
    
    def _save_artifacts(
        self, 
        df: pd.DataFrame, 
        date: str, 
        metadata: Dict[str, Any]
    ) -> Dict[str, str]:
        """Save strategy artifacts to disk."""
        
        # Create artifacts directory
        artifacts_dir = Path(settings.ARTIFACTS_PATH) / "strategy" / date
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = {}
        
        try:
            # Save as Parquet
            parquet_path = artifacts_dir / f"strategy_signals_{date}.parquet"
            df.to_parquet(parquet_path, index=False)
            saved_files["parquet"] = str(parquet_path)
            
            # Save as CSV for readability
            csv_path = artifacts_dir / f"strategy_signals_{date}.csv"
            df.to_csv(csv_path, index=False)
            saved_files["csv"] = str(csv_path)
            
            # Save metadata as JSON
            import json
            metadata_path = artifacts_dir / f"strategy_metadata_{date}.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2, default=str)
            saved_files["metadata"] = str(metadata_path)
            
            # Generate summary report
            report_path = artifacts_dir / f"strategy_report_{date}.md"
            self._generate_report(df, metadata, report_path)
            saved_files["report"] = str(report_path)
            
            self.logger.info(f"Saved strategy artifacts to {artifacts_dir}")
            
        except Exception as e:
            self.logger.error(f"Failed to save artifacts: {e}")
        
        return saved_files
    
    def _generate_report(
        self, 
        df: pd.DataFrame, 
        metadata: Dict[str, Any], 
        output_path: Path
    ):
        """Generate a markdown report of strategy results."""
        
        with open(output_path, "w") as f:
            f.write(f"# Strategy Report - {metadata['date']}\n\n")
            
            # Summary stats
            f.write("## Summary\n\n")
            f.write(f"- **Total Capital**: ${metadata['total_capital']:,.2f}\n")
            f.write(f"- **Total Signals**: {metadata['total_signals']}\n")
            f.write(f"- **Capital Allocated**: ${metadata['signal_statistics']['total_capital_allocated']:,.2f}\n")
            f.write(f"- **Average Position**: ${metadata['signal_statistics']['average_position_size']:,.2f}\n")
            f.write(f"- **Processing Time**: {metadata['duration_seconds']:.1f}s\n\n")
            
            # Bucket allocation
            f.write("## Capital Bucket Allocation\n\n")
            for bucket, amount in metadata['bucket_allocations'].items():
                percentage = (amount / metadata['total_capital']) * 100
                f.write(f"- **{bucket}**: ${amount:,.2f} ({percentage:.1f}%)\n")
            f.write("\n")
            
            # Pattern distribution
            f.write("## Pattern Distribution\n\n")
            pattern_dist = metadata['signal_statistics']['pattern_distribution']
            for pattern, count in pattern_dist.items():
                f.write(f"- **{pattern}**: {count} signals\n")
            f.write("\n")
            
            # Top signals
            f.write("## Top 10 Trade Signals\n\n")
            f.write("| Symbol | Pattern | Bucket | Position Size | Confidence | Time Segment |\n")
            f.write("|--------|---------|--------|---------------|------------|-------------|\n")
            
            top_signals = df.nlargest(10, "position_size")
            for _, row in top_signals.iterrows():
                f.write(f"| {row['symbol']} | {row.get('pattern_intraday', 'N/A')} | "
                       f"{row.get('bucket', 'N/A')} | ${row.get('position_size', 0):,.2f} | "
                       f"{row.get('pattern_confidence', 0):.2f} | {row.get('time_segment', 'N/A')} |\n")
    
    def get_bucket_configurations(self) -> Dict[str, Dict[str, Any]]:
        """Get current bucket configurations."""
        return self.bucket_allocator.get_bucket_configs()
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get pipeline status information."""
        return {
            "strategy": {
                "bucket_allocator": self.bucket_allocator.__class__.__name__,
                "signal_generator": self.signal_generator.__class__.__name__
            },
            "settings": {
                "artifacts_path": str(settings.ARTIFACTS_PATH),
                "debug": settings.DEBUG
            }
        }
