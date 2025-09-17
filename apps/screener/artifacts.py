"""Artifact management for screener results."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

from packages.core import get_logger
from packages.core.config import settings


class ArtifactManager:
    """Manages saving and loading of screener artifacts."""
    
    def __init__(self, base_path: Optional[str] = None):
        self.logger = get_logger(__name__)
        self.base_path = Path(base_path) if base_path else settings.artifacts_path
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def save_screener_results(
        self, 
        df: pd.DataFrame, 
        date: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Save screener results in multiple formats.
        
        Args:
            df: Screener results DataFrame
            date: Date string (YYYY-MM-DD format)
            metadata: Additional metadata to save
            
        Returns:
            Dictionary of saved file paths
        """
        # Create date-specific directory
        date_dir = self.base_path / "screener" / date
        date_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = {}
        
        try:
            # Save as Parquet (primary format)
            parquet_path = date_dir / "screener.parquet"
            df.to_parquet(parquet_path, index=False)
            saved_files["parquet"] = str(parquet_path)
            self.logger.info(f"Saved parquet: {parquet_path}")
            
            # Save top symbols as JSONL
            if not df.empty:
                top_df = df.head(50)  # Top 50 for JSONL
                jsonl_path = date_dir / "screener_top.jsonl"
                self._save_as_jsonl(top_df, jsonl_path)
                saved_files["jsonl"] = str(jsonl_path)
                self.logger.info(f"Saved JSONL: {jsonl_path}")
            
            # Save markdown report
            report_path = date_dir / "REPORT.md"
            self._generate_markdown_report(df, metadata, report_path)
            saved_files["report"] = str(report_path)
            self.logger.info(f"Saved report: {report_path}")
            
            # Save metadata
            metadata_path = date_dir / "metadata.json"
            full_metadata = {
                **metadata,
                "generated_at": datetime.now().isoformat(),
                "total_symbols": len(df),
                "files": saved_files
            }
            
            with open(metadata_path, "w") as f:
                json.dump(full_metadata, f, indent=2, default=str)
            saved_files["metadata"] = str(metadata_path)
            
            self.logger.info(f"Screener artifacts saved to: {date_dir}")
            
        except Exception as e:
            self.logger.error(f"Error saving screener results: {e}")
            raise
        
        return saved_files
    
    def _save_as_jsonl(self, df: pd.DataFrame, path: Path) -> None:
        """Save DataFrame as JSONL format."""
        records = []
        
        for _, row in df.iterrows():
            record = {
                "symbol": row["symbol"],
                "volatility": {
                    "atrp_14": round(row.get("atrp_14", 0.0), 2),
                    "hv_20": round(row.get("hv_20", 0.0), 2),
                    "range_pct_day": round(row.get("range_pct_day", 0.0), 2)
                },
                "liquidity": {
                    "avg_dollar_volume_20d": int(row.get("avg_dollar_volume_20d", 0))
                },
                "technicals": {
                    "rsi_14": round(row.get("rsi_14", 50.0), 2),
                    "sma_20": round(row.get("sma_20", row.get("last", 0.0)), 2),
                    "sma_50": round(row.get("sma_50", row.get("last", 0.0)), 2)
                },
                "flags": {
                    "gap_up": row.get("gap_pct", 0.0) > 2.0,
                    "high_volume": row.get("volume_ratio", 0.0) > 1.5,
                    "high_volatility": row.get("atrp_14", 0.0) > 5.0
                },
                "score": round(row.get("score", 0.0), 3),
                "rank": int(row.get("rank", 0)),
                "asof": datetime.now().isoformat()
            }
            records.append(record)
        
        # Write JSONL
        with open(path, "w") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")
    
    def _generate_markdown_report(
        self, 
        df: pd.DataFrame, 
        metadata: Dict[str, Any], 
        path: Path
    ) -> None:
        """Generate markdown report."""
        report_content = []
        
        # Header
        report_content.append(f"# Screener Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_content.append("")
        
        # Summary
        report_content.append("## Summary")
        report_content.append(f"- **Total Symbols Screened**: {metadata.get('original_count', 'N/A')}")
        report_content.append(f"- **Symbols After Filtering**: {len(df)}")
        report_content.append(f"- **Filter Rate**: {metadata.get('filter_rate_pct', 0):.1f}%")
        report_content.append(f"- **Provider**: {metadata.get('provider', 'yahoo')}")
        report_content.append("")
        
        if not df.empty:
            # Top 10 symbols
            report_content.append("## Top 10 Symbols")
            report_content.append("")
            report_content.append("| Rank | Symbol | Score | ATR% | HV 20d | Dollar Vol | Gap% |")
            report_content.append("|------|--------|-------|------|--------|------------|------|")
            
            for i, (_, row) in enumerate(df.head(10).iterrows(), 1):
                atr_pct = row.get("atrp_14", 0.0)
                hv_20 = row.get("hv_20", 0.0)
                dollar_vol = row.get("avg_dollar_volume_20d", 0)
                gap_pct = row.get("gap_pct", 0.0)
                score = row.get("score", 0.0)
                
                report_content.append(
                    f"| {i} | {row['symbol']} | {score:.3f} | {atr_pct:.2f}% | "
                    f"{hv_20:.1f}% | ${dollar_vol:,.0f} | {gap_pct:+.1f}% |"
                )
            
            report_content.append("")
            
            # Statistics
            report_content.append("## Statistics")
            report_content.append("")
            
            if "score" in df.columns:
                report_content.append(f"- **Average Score**: {df['score'].mean():.3f}")
                report_content.append(f"- **Score Range**: {df['score'].min():.3f} - {df['score'].max():.3f}")
            
            if "atrp_14" in df.columns:
                report_content.append(f"- **Average ATR%**: {df['atrp_14'].mean():.2f}%")
            
            if "avg_dollar_volume_20d" in df.columns:
                avg_dollar_vol = df["avg_dollar_volume_20d"].mean()
                report_content.append(f"- **Average Dollar Volume**: ${avg_dollar_vol:,.0f}")
            
            # Sector distribution
            if "sector" in df.columns and not df["sector"].isna().all():
                report_content.append("")
                report_content.append("## Sector Distribution")
                report_content.append("")
                sector_counts = df["sector"].value_counts()
                for sector, count in sector_counts.items():
                    pct = (count / len(df)) * 100
                    report_content.append(f"- **{sector}**: {count} symbols ({pct:.1f}%)")
        
        # Configuration
        report_content.append("")
        report_content.append("## Configuration")
        report_content.append("")
        config = metadata.get("config", {})
        for key, value in config.items():
            report_content.append(f"- **{key}**: {value}")
        
        # Write to file
        with open(path, "w") as f:
            f.write("\n".join(report_content))
    
    def load_screener_results(self, date: str) -> Dict[str, Any]:
        """
        Load screener results for a specific date.
        
        Args:
            date: Date string (YYYY-MM-DD format)
            
        Returns:
            Dictionary containing loaded data and metadata
        """
        date_dir = self.base_path / "screener" / date
        
        if not date_dir.exists():
            raise FileNotFoundError(f"No screener results found for date: {date}")
        
        result = {}
        
        try:
            # Load parquet
            parquet_path = date_dir / "screener.parquet"
            if parquet_path.exists():
                result["dataframe"] = pd.read_parquet(parquet_path)
                self.logger.info(f"Loaded parquet: {parquet_path}")
            
            # Load JSONL
            jsonl_path = date_dir / "screener_top.jsonl"
            if jsonl_path.exists():
                result["top_symbols"] = self._load_jsonl(jsonl_path)
                self.logger.info(f"Loaded JSONL: {jsonl_path}")
            
            # Load metadata
            metadata_path = date_dir / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    result["metadata"] = json.load(f)
                self.logger.info(f"Loaded metadata: {metadata_path}")
            
            # Load report
            report_path = date_dir / "REPORT.md"
            if report_path.exists():
                with open(report_path, "r") as f:
                    result["report"] = f.read()
                self.logger.info(f"Loaded report: {report_path}")
        
        except Exception as e:
            self.logger.error(f"Error loading screener results: {e}")
            raise
        
        return result
    
    def _load_jsonl(self, path: Path) -> List[Dict[str, Any]]:
        """Load JSONL file."""
        records = []
        with open(path, "r") as f:
            for line in f:
                records.append(json.loads(line.strip()))
        return records
    
    def list_available_dates(self) -> List[str]:
        """List all available screener result dates."""
        screener_dir = self.base_path / "screener"
        if not screener_dir.exists():
            return []
        
        dates = []
        for item in screener_dir.iterdir():
            if item.is_dir() and item.name.count("-") == 2:  # YYYY-MM-DD format
                dates.append(item.name)
        
        return sorted(dates, reverse=True)  # Most recent first
