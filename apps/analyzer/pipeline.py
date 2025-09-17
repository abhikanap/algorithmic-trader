"""Analyzer pipeline orchestration."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import pandas as pd

from packages.core import get_logger
from packages.core.config import settings

from .classify_intraday import IntradayClassifier
from .classify_multiday import MultidayClassifier


class AnalyzerPipeline:
    """Main analyzer pipeline that orchestrates pattern classification."""
    
    def __init__(
        self,
        intraday_classifier: Optional[IntradayClassifier] = None,
        multiday_classifier: Optional[MultidayClassifier] = None
    ):
        self.logger = get_logger(__name__)
        
        # Initialize classifiers
        self.intraday_classifier = intraday_classifier or IntradayClassifier()
        self.multiday_classifier = multiday_classifier or MultidayClassifier()
        
        self.logger.info("Initialized analyzer pipeline")
    
    async def run(
        self,
        screener_data: Optional[pd.DataFrame] = None,
        date: Optional[str] = None,
        save_artifacts: bool = True
    ) -> Dict[str, Any]:
        """
        Run the complete analyzer pipeline.
        
        Args:
            screener_data: DataFrame from screener pipeline
            date: Date string (YYYY-MM-DD). If None, uses today
            save_artifacts: Whether to save results to artifacts
            
        Returns:
            Dictionary containing results and metadata
        """
        start_time = datetime.now()
        
        if date is None:
            date = start_time.strftime("%Y-%m-%d")
        
        self.logger.info(f"Starting analyzer pipeline for date: {date}")
        
        try:
            # Load screener data if not provided
            if screener_data is None:
                screener_data = self._load_screener_data(date)
            
            if screener_data.empty:
                raise ValueError("No screener data available")
            
            self.logger.info(f"Analyzing {len(screener_data)} symbols")
            
            # Load historical data (would normally come from data provider)
            # For now, create empty DataFrame as placeholder
            historical_df = pd.DataFrame()
            
            # Stage 1: Intraday pattern classification
            self.logger.info("Classifying intraday patterns...")
            intraday_results = await self.intraday_classifier.classify(
                screener_data, 
                historical_df
            )
            
            # Stage 2: Multi-day pattern classification
            self.logger.info("Classifying multi-day patterns...")
            multiday_results = await self.multiday_classifier.classify(
                intraday_results,
                historical_df
            )
            
            # Stage 3: Generate bucket and time slot hints
            final_results = self._add_strategy_hints(multiday_results)
            
            # Prepare results
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Generate metadata
            metadata = {
                "date": date,
                "duration_seconds": round(duration, 2),
                "total_symbols": len(final_results),
                "pattern_statistics": self._generate_pattern_statistics(final_results)
            }
            
            # Save artifacts if requested
            saved_files = {}
            if save_artifacts and not final_results.empty:
                self.logger.info("Saving analyzer artifacts...")
                saved_files = self._save_artifacts(final_results, date, metadata)
                metadata["saved_files"] = saved_files
            
            result = {
                "success": True,
                "data": final_results,
                "metadata": metadata,
                "saved_files": saved_files
            }
            
            self.logger.info(
                f"Analyzer pipeline completed successfully in {duration:.1f}s. "
                f"Analyzed {len(final_results)} symbols"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Analyzer pipeline failed: {str(e)}"
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
    
    def _load_screener_data(self, date: str) -> pd.DataFrame:
        """Load screener data from artifacts."""
        try:
            from apps.screener.artifacts import ArtifactManager
            
            artifact_manager = ArtifactManager()
            results = artifact_manager.load_screener_results(date)
            return results.get("dataframe", pd.DataFrame())
            
        except Exception as e:
            self.logger.warning(f"Could not load screener data for {date}: {e}")
            return pd.DataFrame()
    
    def _add_strategy_hints(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add bucket and time slot hints based on patterns."""
        result_df = df.copy()
        
        # Initialize hint columns
        result_df["bucket_suggestion"] = None
        result_df["timeslot_suggestion"] = None
        
        for idx, row in result_df.iterrows():
            intraday_pattern = row.get("pattern_intraday")
            multiday_pattern = row.get("pattern_multiday")
            
            # Bucket suggestions based on patterns
            bucket_hint = self._suggest_bucket(intraday_pattern, multiday_pattern, row)
            timeslot_hint = self._suggest_timeslot(intraday_pattern, multiday_pattern, row)
            
            result_df.at[idx, "bucket_suggestion"] = bucket_hint
            result_df.at[idx, "timeslot_suggestion"] = timeslot_hint
        
        return result_df
    
    def _suggest_bucket(self, intraday_pattern: str, multiday_pattern: str, row: pd.Series) -> str:
        """Suggest capital bucket based on patterns and characteristics."""
        # Get stock characteristics
        price = row.get("last", 0)
        atr_pct = row.get("atrp_14", 0)
        dollar_volume = row.get("avg_dollar_volume_20d", 0)
        
        # Bucket A: Penny stocks & microcap movers
        if price < 10.0 and atr_pct > 8.0:
            return "A"
        
        # Bucket D: Catalyst-driven market movers  
        if intraday_pattern in ["morning_spike_fade", "morning_surge_uptrend"] and atr_pct > 10.0:
            return "D"
        
        # Bucket C: Multi-day swing trades
        if multiday_pattern in ["sustained_uptrend", "sustained_downtrend", "downtrend_reversal"]:
            return "C"
        
        # Bucket B: Large-cap intraday trends
        if price > 50.0 and dollar_volume > 100_000_000:
            return "B"
        
        # Bucket E: Defensive hedges (default for low volatility)
        if atr_pct < 3.0:
            return "E"
        
        return "B"  # Default to B
    
    def _suggest_timeslot(self, intraday_pattern: str, multiday_pattern: str, row: pd.Series) -> str:
        """Suggest time slot based on patterns."""
        gap_pct = abs(row.get("gap_pct", 0))
        
        # Morning patterns
        if intraday_pattern in ["morning_spike_fade", "morning_surge_uptrend"]:
            return "open" if gap_pct > 3.0 else "late_morning"
        
        # Recovery patterns
        if intraday_pattern == "morning_plunge_recovery":
            return "midday"
        
        # Trend continuation
        if multiday_pattern in ["sustained_uptrend", "sustained_downtrend"]:
            return "afternoon"
        
        # Default to open for high volatility
        if row.get("atrp_14", 0) > 8.0:
            return "open"
        
        return "midday"  # Conservative default
    
    def _generate_pattern_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate statistics about pattern distribution."""
        stats = {}
        
        # Intraday pattern distribution
        if "pattern_intraday" in df.columns:
            intraday_counts = df["pattern_intraday"].value_counts().to_dict()
            stats["intraday_patterns"] = intraday_counts
        
        # Multi-day pattern distribution
        if "pattern_multiday" in df.columns:
            multiday_counts = df["pattern_multiday"].value_counts().to_dict()
            stats["multiday_patterns"] = multiday_counts
        
        # Bucket suggestions
        if "bucket_suggestion" in df.columns:
            bucket_counts = df["bucket_suggestion"].value_counts().to_dict()
            stats["bucket_suggestions"] = bucket_counts
        
        # Confidence statistics
        if "pattern_confidence" in df.columns:
            stats["confidence_stats"] = {
                "mean": round(df["pattern_confidence"].mean(), 3),
                "median": round(df["pattern_confidence"].median(), 3),
                "min": round(df["pattern_confidence"].min(), 3),
                "max": round(df["pattern_confidence"].max(), 3)
            }
        
        return stats
    
    def _save_artifacts(self, df: pd.DataFrame, date: str, metadata: Dict[str, Any]) -> Dict[str, str]:
        """Save analyzer artifacts."""
        # Create date-specific directory
        artifacts_dir = settings.artifacts_path / "analyzer" / date
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = {}
        
        try:
            # Save full results as parquet
            parquet_path = artifacts_dir / "analyzer.parquet"
            df.to_parquet(parquet_path, index=False)
            saved_files["parquet"] = str(parquet_path)
            
            # Save top results as JSONL
            if not df.empty:
                jsonl_path = artifacts_dir / "analyzer_top.jsonl"
                self._save_top_as_jsonl(df.head(50), jsonl_path)
                saved_files["jsonl"] = str(jsonl_path)
            
            # Save markdown report
            report_path = artifacts_dir / "REPORT.md"
            self._generate_markdown_report(df, metadata, report_path)
            saved_files["report"] = str(report_path)
            
            self.logger.info(f"Analyzer artifacts saved to: {artifacts_dir}")
            
        except Exception as e:
            self.logger.error(f"Error saving analyzer artifacts: {e}")
        
        return saved_files
    
    def _save_top_as_jsonl(self, df: pd.DataFrame, path: Path) -> None:
        """Save top results as JSONL."""
        import json
        
        records = []
        for _, row in df.iterrows():
            record = {
                "symbol": row["symbol"],
                "pattern_intraday": row.get("pattern_intraday"),
                "pattern_multiday": row.get("pattern_multiday"),
                "confidence": round(row.get("pattern_confidence", 0.0), 3),
                "hints": {
                    "bucket_suggestion": row.get("bucket_suggestion"),
                    "timeslot_suggestion": row.get("timeslot_suggestion")
                },
                "asof": datetime.now().isoformat()
            }
            records.append(record)
        
        with open(path, "w") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")
    
    def _generate_markdown_report(self, df: pd.DataFrame, metadata: Dict[str, Any], path: Path) -> None:
        """Generate markdown report."""
        report_lines = [
            f"# Analyzer Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            f"- **Total Symbols Analyzed**: {len(df)}",
            f"- **Duration**: {metadata['duration_seconds']:.1f} seconds",
            ""
        ]
        
        # Pattern statistics
        pattern_stats = metadata.get("pattern_statistics", {})
        
        if "intraday_patterns" in pattern_stats:
            report_lines.extend([
                "## Intraday Pattern Distribution",
                ""
            ])
            for pattern, count in pattern_stats["intraday_patterns"].items():
                pct = (count / len(df)) * 100
                report_lines.append(f"- **{pattern}**: {count} ({pct:.1f}%)")
            report_lines.append("")
        
        if "multiday_patterns" in pattern_stats:
            report_lines.extend([
                "## Multi-day Pattern Distribution",
                ""
            ])
            for pattern, count in pattern_stats["multiday_patterns"].items():
                pct = (count / len(df)) * 100
                report_lines.append(f"- **{pattern}**: {count} ({pct:.1f}%)")
            report_lines.append("")
        
        if "bucket_suggestions" in pattern_stats:
            report_lines.extend([
                "## Bucket Allocation Suggestions",
                ""
            ])
            for bucket, count in pattern_stats["bucket_suggestions"].items():
                pct = (count / len(df)) * 100
                report_lines.append(f"- **Bucket {bucket}**: {count} symbols ({pct:.1f}%)")
            report_lines.append("")
        
        # Write report
        with open(path, "w") as f:
            f.write("\n".join(report_lines))
