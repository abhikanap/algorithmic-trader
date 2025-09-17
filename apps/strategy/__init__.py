"""Strategy Engine for capital allocation and position sizing."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd

from packages.core import get_logger
from packages.core.config import settings
from packages.core.models import CapitalBucket, TimeSegment, TradeSignal


class StrategyEngine:
    """
    Main strategy engine that allocates capital and sizes positions
    based on pattern classification and bucket configuration.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Load bucket configurations
        self.bucket_configs = self._load_bucket_configs()
        self.time_segments = self._load_time_segments()
        
        self.logger.info("Initialized strategy engine")
    
    async def allocate_positions(
        self,
        analyzer_data: Optional[pd.DataFrame] = None,
        date: Optional[str] = None,
        total_capital: Optional[float] = None,
        save_artifacts: bool = True
    ) -> Dict[str, Any]:
        """
        Allocate capital and size positions based on analyzer output.
        
        Args:
            analyzer_data: DataFrame from analyzer pipeline
            date: Date string (YYYY-MM-DD). If None, uses today
            total_capital: Total capital to allocate. If None, uses config
            save_artifacts: Whether to save results to artifacts
            
        Returns:
            Dictionary containing allocation results and metadata
        """
        start_time = datetime.now()
        
        if date is None:
            date = start_time.strftime("%Y-%m-%d")
        
        if total_capital is None:
            total_capital = settings.strategy.total_capital
        
        self.logger.info(f"Starting strategy allocation for date: {date}")
        self.logger.info(f"Total capital to allocate: ${total_capital:,.2f}")
        
        try:
            # Load analyzer data if not provided
            if analyzer_data is None:
                analyzer_data = self._load_analyzer_data(date)
            
            if analyzer_data.empty:
                raise ValueError("No analyzer data available")
            
            self.logger.info(f"Processing {len(analyzer_data)} classified symbols")
            
            # Stage 1: Filter signals by confidence threshold
            filtered_signals = self._filter_signals(analyzer_data)
            
            # Stage 2: Group by bucket allocation
            bucket_allocations = self._allocate_to_buckets(filtered_signals, total_capital)
            
            # Stage 3: Size positions within each bucket
            positioned_allocations = self._size_positions(bucket_allocations)
            
            # Stage 4: Map to time segments
            time_scheduled = self._schedule_time_segments(positioned_allocations)
            
            # Stage 5: Generate final trade signals
            trade_signals = self._generate_trade_signals(time_scheduled)
            
            # Prepare results
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Generate metadata
            metadata = {
                "date": date,
                "duration_seconds": round(duration, 2),
                "total_capital": total_capital,
                "symbols_analyzed": len(analyzer_data),
                "signals_generated": len(trade_signals),
                "allocation_statistics": self._generate_allocation_statistics(trade_signals)
            }
            
            # Save artifacts if requested
            saved_files = {}
            if save_artifacts and trade_signals:
                self.logger.info("Saving strategy artifacts...")
                saved_files = self._save_artifacts(trade_signals, date, metadata)
                metadata["saved_files"] = saved_files
            
            result = {
                "success": True,
                "signals": trade_signals,
                "metadata": metadata,
                "saved_files": saved_files
            }
            
            self.logger.info(
                f"Strategy allocation completed successfully in {duration:.1f}s. "
                f"Generated {len(trade_signals)} trade signals"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Strategy allocation failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return {
                "success": False,
                "error": error_msg,
                "signals": [],
                "metadata": {
                    "date": date,
                    "error": str(e),
                    "duration_seconds": (datetime.now() - start_time).total_seconds()
                },
                "saved_files": {}
            }
    
    def _load_bucket_configs(self) -> Dict[str, Dict[str, Any]]:
        """Load bucket configurations from settings."""
        return {
            "A": {
                "name": "Penny Stocks & Microcap Movers",
                "capital_pct": 0.15,  # 15% of total capital
                "max_position_pct": 0.03,  # 3% max per position
                "max_positions": 8,
                "risk_tolerance": "high",
                "patterns": ["morning_spike_fade", "morning_surge_uptrend"]
            },
            "B": {
                "name": "Large-cap Intraday Trends",
                "capital_pct": 0.35,  # 35% of total capital
                "max_position_pct": 0.05,  # 5% max per position
                "max_positions": 10,
                "risk_tolerance": "medium",
                "patterns": ["morning_surge_uptrend", "midday_choppy_range"]
            },
            "C": {
                "name": "Multi-day Swing Trades",
                "capital_pct": 0.30,  # 30% of total capital
                "max_position_pct": 0.08,  # 8% max per position
                "max_positions": 6,
                "risk_tolerance": "medium",
                "patterns": ["sustained_uptrend", "downtrend_reversal"]
            },
            "D": {
                "name": "Catalyst-driven Market Movers",
                "capital_pct": 0.15,  # 15% of total capital
                "max_position_pct": 0.04,  # 4% max per position
                "max_positions": 5,
                "risk_tolerance": "high",
                "patterns": ["morning_spike_fade", "blowoff_top"]
            },
            "E": {
                "name": "Defensive Hedges",
                "capital_pct": 0.05,  # 5% of total capital
                "max_position_pct": 0.02,  # 2% max per position
                "max_positions": 3,
                "risk_tolerance": "low",
                "patterns": ["consolidation_range", "midday_choppy_range"]
            }
        }
    
    def _load_time_segments(self) -> Dict[str, Dict[str, Any]]:
        """Load time segment configurations."""
        return {
            "open": {
                "name": "Market Open",
                "start_time": "09:30",
                "end_time": "10:00",
                "priority": 1,
                "patterns": ["morning_spike_fade", "morning_surge_uptrend", "morning_plunge_recovery"]
            },
            "late_morning": {
                "name": "Late Morning",
                "start_time": "10:00", 
                "end_time": "11:30",
                "priority": 2,
                "patterns": ["morning_surge_uptrend", "sustained_uptrend"]
            },
            "midday": {
                "name": "Midday",
                "start_time": "11:30",
                "end_time": "14:00", 
                "priority": 3,
                "patterns": ["midday_choppy_range", "morning_plunge_recovery"]
            },
            "afternoon": {
                "name": "Afternoon",
                "start_time": "14:00",
                "end_time": "15:30",
                "priority": 4,
                "patterns": ["afternoon_selloff_downtrend", "sustained_downtrend"]
            },
            "close": {
                "name": "Market Close",
                "start_time": "15:30",
                "end_time": "16:00",
                "priority": 5,
                "patterns": ["afternoon_selloff_downtrend", "blowoff_top"]
            }
        }
    
    def _load_analyzer_data(self, date: str) -> pd.DataFrame:
        """Load analyzer data from artifacts."""
        try:
            artifacts_dir = settings.artifacts_path / "analyzer" / date
            parquet_path = artifacts_dir / "analyzer.parquet"
            
            if parquet_path.exists():
                return pd.read_parquet(parquet_path)
            else:
                self.logger.warning(f"No analyzer data found for {date}")
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.warning(f"Could not load analyzer data for {date}: {e}")
            return pd.DataFrame()
    
    def _filter_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter signals by confidence threshold and other criteria."""
        # Minimum confidence threshold
        min_confidence = settings.strategy.min_confidence_threshold
        filtered = df[df.get("pattern_confidence", 0) >= min_confidence].copy()
        
        # Filter out symbols with insufficient liquidity
        min_dollar_volume = 5_000_000  # $5M daily volume
        if "avg_dollar_volume_20d" in filtered.columns:
            filtered = filtered[filtered["avg_dollar_volume_20d"] >= min_dollar_volume]
        
        # Filter by price range (avoid extreme penny stocks)
        if "last" in filtered.columns:
            filtered = filtered[
                (filtered["last"] >= 1.0) & (filtered["last"] <= 500.0)
            ]
        
        self.logger.info(f"Filtered to {len(filtered)} high-confidence signals")
        return filtered
    
    def _allocate_to_buckets(self, df: pd.DataFrame, total_capital: float) -> Dict[str, Dict[str, Any]]:
        """Allocate symbols to capital buckets."""
        bucket_allocations = {}
        
        for bucket_id, bucket_config in self.bucket_configs.items():
            bucket_capital = total_capital * bucket_config["capital_pct"]
            
            # Filter symbols suggested for this bucket
            bucket_symbols = df[df.get("bucket_suggestion") == bucket_id].copy()
            
            # Sort by confidence (highest first)
            bucket_symbols = bucket_symbols.sort_values(
                "pattern_confidence", 
                ascending=False
            )
            
            # Limit to max positions for this bucket
            max_positions = bucket_config["max_positions"]
            bucket_symbols = bucket_symbols.head(max_positions)
            
            bucket_allocations[bucket_id] = {
                "config": bucket_config,
                "capital": bucket_capital,
                "symbols": bucket_symbols,
                "count": len(bucket_symbols)
            }
            
            self.logger.info(
                f"Bucket {bucket_id}: ${bucket_capital:,.0f} allocated to {len(bucket_symbols)} symbols"
            )
        
        return bucket_allocations
    
    def _size_positions(self, bucket_allocations: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Size individual positions within each bucket."""
        for bucket_id, allocation in bucket_allocations.items():
            symbols_df = allocation["symbols"]
            bucket_capital = allocation["capital"]
            config = allocation["config"]
            
            if symbols_df.empty:
                continue
            
            max_position_pct = config["max_position_pct"]
            max_position_size = bucket_capital * max_position_pct
            
            # Equal weight allocation with max position cap
            equal_weight = bucket_capital / len(symbols_df)
            
            position_sizes = []
            for _, row in symbols_df.iterrows():
                # Start with equal weight
                position_size = min(equal_weight, max_position_size)
                
                # Adjust based on volatility and confidence
                confidence = row.get("pattern_confidence", 0.5)
                atr_pct = row.get("atrp_14", 5.0)
                
                # Higher confidence gets more allocation
                confidence_multiplier = 0.8 + (confidence * 0.4)  # 0.8 to 1.2
                
                # Lower volatility gets more allocation (inverse relationship)
                volatility_multiplier = max(0.5, min(1.5, 10.0 / max(atr_pct, 2.0)))
                
                adjusted_size = position_size * confidence_multiplier * volatility_multiplier
                final_size = min(adjusted_size, max_position_size)
                
                position_sizes.append(final_size)
            
            # Add position sizes to the dataframe
            allocation["symbols"] = symbols_df.copy()
            allocation["symbols"]["position_size"] = position_sizes
            allocation["total_allocated"] = sum(position_sizes)
        
        return bucket_allocations
    
    def _schedule_time_segments(self, bucket_allocations: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Map positions to time segments."""
        for bucket_id, allocation in bucket_allocations.items():
            symbols_df = allocation["symbols"]
            
            if symbols_df.empty:
                continue
            
            # Add time segment scheduling
            time_slots = []
            for _, row in symbols_df.iterrows():
                suggested_timeslot = row.get("timeslot_suggestion", "midday")
                
                # Validate timeslot exists
                if suggested_timeslot not in self.time_segments:
                    suggested_timeslot = "midday"
                
                time_slots.append(suggested_timeslot)
            
            allocation["symbols"]["time_segment"] = time_slots
        
        return bucket_allocations
    
    def _generate_trade_signals(self, bucket_allocations: Dict[str, Dict[str, Any]]) -> List[TradeSignal]:
        """Generate final trade signals."""
        signals = []
        
        for bucket_id, allocation in bucket_allocations.items():
            symbols_df = allocation["symbols"]
            
            if symbols_df.empty:
                continue
            
            for _, row in symbols_df.iterrows():
                signal = TradeSignal(
                    symbol=row["symbol"],
                    action="BUY",  # Default to long positions
                    quantity=0,  # Will be calculated by execution engine
                    price=row.get("last", 0.0),
                    position_size=row["position_size"],
                    bucket=bucket_id,
                    time_segment=row["time_segment"],
                    pattern_intraday=row.get("pattern_intraday"),
                    pattern_multiday=row.get("pattern_multiday"),
                    confidence=row.get("pattern_confidence", 0.0),
                    metadata={
                        "atr_pct": row.get("atrp_14", 0.0),
                        "dollar_volume": row.get("avg_dollar_volume_20d", 0.0),
                        "gap_pct": row.get("gap_pct", 0.0),
                        "rsi": row.get("rsi_14", 50.0)
                    }
                )
                signals.append(signal)
        
        # Sort signals by time segment priority
        def time_priority(signal):
            return self.time_segments[signal.time_segment]["priority"]
        
        signals.sort(key=time_priority)
        
        return signals
    
    def _generate_allocation_statistics(self, signals: List[TradeSignal]) -> Dict[str, Any]:
        """Generate allocation statistics."""
        stats = {}
        
        # Bucket distribution
        bucket_stats = {}
        for signal in signals:
            bucket = signal.bucket
            if bucket not in bucket_stats:
                bucket_stats[bucket] = {"count": 0, "total_capital": 0.0}
            bucket_stats[bucket]["count"] += 1
            bucket_stats[bucket]["total_capital"] += signal.position_size
        
        stats["bucket_distribution"] = bucket_stats
        
        # Time segment distribution
        time_stats = {}
        for signal in signals:
            timeslot = signal.time_segment
            if timeslot not in time_stats:
                time_stats[timeslot] = {"count": 0, "total_capital": 0.0}
            time_stats[timeslot]["count"] += 1
            time_stats[timeslot]["total_capital"] += signal.position_size
        
        stats["time_distribution"] = time_stats
        
        # Overall statistics
        total_allocated = sum(s.position_size for s in signals)
        stats["total_allocated"] = total_allocated
        stats["average_position_size"] = total_allocated / len(signals) if signals else 0
        stats["confidence_stats"] = {
            "mean": sum(s.confidence for s in signals) / len(signals) if signals else 0,
            "min": min(s.confidence for s in signals) if signals else 0,
            "max": max(s.confidence for s in signals) if signals else 0
        }
        
        return stats
    
    def _save_artifacts(self, signals: List[TradeSignal], date: str, metadata: Dict[str, Any]) -> Dict[str, str]:
        """Save strategy artifacts."""
        # Create date-specific directory
        artifacts_dir = settings.artifacts_path / "strategy" / date
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = {}
        
        try:
            # Convert signals to DataFrame
            signals_data = []
            for signal in signals:
                signals_data.append({
                    "symbol": signal.symbol,
                    "action": signal.action,
                    "position_size": signal.position_size,
                    "price": signal.price,
                    "bucket": signal.bucket,
                    "time_segment": signal.time_segment,
                    "pattern_intraday": signal.pattern_intraday,
                    "pattern_multiday": signal.pattern_multiday,
                    "confidence": signal.confidence,
                    **signal.metadata
                })
            
            signals_df = pd.DataFrame(signals_data)
            
            # Save as parquet
            parquet_path = artifacts_dir / "strategy.parquet"
            signals_df.to_parquet(parquet_path, index=False)
            saved_files["parquet"] = str(parquet_path)
            
            # Save as JSONL for easy consumption
            jsonl_path = artifacts_dir / "strategy.jsonl"
            self._save_signals_as_jsonl(signals, jsonl_path)
            saved_files["jsonl"] = str(jsonl_path)
            
            # Save markdown report
            report_path = artifacts_dir / "REPORT.md"
            self._generate_markdown_report(signals, metadata, report_path)
            saved_files["report"] = str(report_path)
            
            self.logger.info(f"Strategy artifacts saved to: {artifacts_dir}")
            
        except Exception as e:
            self.logger.error(f"Error saving strategy artifacts: {e}")
        
        return saved_files
    
    def _save_signals_as_jsonl(self, signals: List[TradeSignal], path: Path) -> None:
        """Save trade signals as JSONL."""
        import json
        
        with open(path, "w") as f:
            for signal in signals:
                record = {
                    "symbol": signal.symbol,
                    "action": signal.action,
                    "position_size": round(signal.position_size, 2),
                    "price": round(signal.price, 2),
                    "bucket": signal.bucket,
                    "time_segment": signal.time_segment,
                    "patterns": {
                        "intraday": signal.pattern_intraday,
                        "multiday": signal.pattern_multiday
                    },
                    "confidence": round(signal.confidence, 3),
                    "metadata": signal.metadata,
                    "asof": datetime.now().isoformat()
                }
                f.write(json.dumps(record) + "\n")
    
    def _generate_markdown_report(self, signals: List[TradeSignal], metadata: Dict[str, Any], path: Path) -> None:
        """Generate markdown report."""
        report_lines = [
            f"# Strategy Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            f"- **Total Signals Generated**: {len(signals)}",
            f"- **Total Capital Allocated**: ${metadata.get('allocation_statistics', {}).get('total_allocated', 0):,.2f}",
            f"- **Duration**: {metadata['duration_seconds']:.1f} seconds",
            ""
        ]
        
        # Allocation statistics
        alloc_stats = metadata.get("allocation_statistics", {})
        
        if "bucket_distribution" in alloc_stats:
            report_lines.extend([
                "## Bucket Allocation",
                ""
            ])
            for bucket, stats in alloc_stats["bucket_distribution"].items():
                bucket_name = self.bucket_configs[bucket]["name"]
                report_lines.append(
                    f"- **Bucket {bucket} ({bucket_name})**: {stats['count']} signals, "
                    f"${stats['total_capital']:,.2f}"
                )
            report_lines.append("")
        
        if "time_distribution" in alloc_stats:
            report_lines.extend([
                "## Time Segment Distribution",
                ""
            ])
            for timeslot, stats in alloc_stats["time_distribution"].items():
                timeslot_name = self.time_segments[timeslot]["name"]
                report_lines.append(
                    f"- **{timeslot_name}**: {stats['count']} signals, "
                    f"${stats['total_capital']:,.2f}"
                )
            report_lines.append("")
        
        # Top signals
        if signals:
            report_lines.extend([
                "## Top Signals",
                ""
            ])
            top_signals = sorted(signals, key=lambda s: s.confidence, reverse=True)[:10]
            for signal in top_signals:
                report_lines.append(
                    f"- **{signal.symbol}** ({signal.bucket}): "
                    f"${signal.position_size:,.0f} @ {signal.confidence:.3f} confidence"
                )
        
        # Write report
        with open(path, "w") as f:
            f.write("\n".join(report_lines))
