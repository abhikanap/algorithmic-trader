"""Main screener pipeline orchestration."""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
import pandas as pd

from packages.core import get_logger
from packages.core.config import settings

from .providers import YahooProvider, DataProvider
from .features import FeatureEngine
from .filters import FilterEngine
from .ranking import RankingEngine
from .artifacts import ArtifactManager


class ScreenerPipeline:
    """Main screener pipeline that orchestrates all components."""
    
    def __init__(
        self,
        provider: Optional[DataProvider] = None,
        feature_engine: Optional[FeatureEngine] = None,
        filter_engine: Optional[FilterEngine] = None,
        ranking_engine: Optional[RankingEngine] = None,
        artifact_manager: Optional[ArtifactManager] = None
    ):
        self.logger = get_logger(__name__)
        
        # Initialize components
        self.provider = provider or YahooProvider()
        self.feature_engine = feature_engine or FeatureEngine()
        self.filter_engine = filter_engine or FilterEngine()
        self.ranking_engine = ranking_engine or RankingEngine()
        self.artifact_manager = artifact_manager or ArtifactManager()
        
        self.logger.info(f"Initialized screener pipeline with provider: {self.provider.name}")
    
    async def run(
        self,
        date: Optional[str] = None,
        symbols: Optional[List[str]] = None,
        save_artifacts: bool = True
    ) -> Dict[str, Any]:
        """
        Run the complete screener pipeline.
        
        Args:
            date: Date string (YYYY-MM-DD). If None, uses today
            symbols: List of symbols to screen. If None, fetches universe
            save_artifacts: Whether to save results to artifacts
            
        Returns:
            Dictionary containing results and metadata
        """
        start_time = datetime.now()
        
        if date is None:
            date = start_time.strftime("%Y-%m-%d")
        
        self.logger.info(f"Starting screener pipeline for date: {date}")
        
        try:
            # Stage 1: Fetch universe/symbols
            if symbols is None:
                self.logger.info("Fetching symbol universe...")
                universe_df = await self.provider.fetch_universe()
                symbols = universe_df["symbol"].tolist()
                self.logger.info(f"Fetched {len(symbols)} symbols from universe")
            else:
                self.logger.info(f"Using provided {len(symbols)} symbols")
            
            if not symbols:
                raise ValueError("No symbols to screen")
            
            # Stage 2: Fetch market data
            self.logger.info("Fetching market snapshot...")
            snapshot_df = await self.provider.fetch_snapshot(symbols)
            
            if snapshot_df.empty:
                raise ValueError("No market data fetched")
            
            self.logger.info(f"Fetched snapshot for {len(snapshot_df)} symbols")
            
            # Stage 3: Fetch historical data for technical analysis
            self.logger.info("Fetching historical data...")
            available_symbols = snapshot_df["symbol"].tolist()
            historical_df = await self.provider.fetch_historical(
                available_symbols, 
                period="1y", 
                interval="1d"
            )
            
            self.logger.info(f"Fetched historical data: {len(historical_df)} records")
            
            # Stage 4: Feature engineering
            self.logger.info("Adding technical features...")
            enriched_df = await self.feature_engine.add_features(snapshot_df, historical_df)
            
            # Stage 5: Filtering
            self.logger.info("Applying filters...")
            filtered_df = await self.filter_engine.apply_filters(enriched_df)
            
            if filtered_df.empty:
                self.logger.warning("All symbols filtered out - consider relaxing criteria")
                filtered_df = enriched_df.head(10)  # Keep top 10 at least
            
            # Stage 6: Ranking
            self.logger.info("Ranking symbols...")
            ranked_df = await self.ranking_engine.rank_symbols(filtered_df)
            
            # Prepare results
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Generate metadata
            metadata = {
                "date": date,
                "provider": self.provider.name,
                "duration_seconds": round(duration, 2),
                "original_count": len(symbols),
                "snapshot_count": len(snapshot_df),
                "filtered_count": len(filtered_df),
                "final_count": len(ranked_df),
                "filter_summary": self.filter_engine.get_filter_summary(enriched_df, filtered_df),
                "ranking_summary": self.ranking_engine.get_ranking_summary(ranked_df),
                "pipeline_stages": {
                    "universe_fetch": len(symbols),
                    "snapshot_fetch": len(snapshot_df),
                    "historical_fetch": len(historical_df),
                    "feature_engineering": len(enriched_df),
                    "filtering": len(filtered_df),
                    "ranking": len(ranked_df)
                }
            }
            
            # Save artifacts if requested
            saved_files = {}
            if save_artifacts and not ranked_df.empty:
                self.logger.info("Saving artifacts...")
                saved_files = self.artifact_manager.save_screener_results(
                    ranked_df, date, metadata
                )
                metadata["saved_files"] = saved_files
            
            result = {
                "success": True,
                "data": ranked_df,
                "metadata": metadata,
                "saved_files": saved_files
            }
            
            self.logger.info(
                f"Screener pipeline completed successfully in {duration:.1f}s. "
                f"Final results: {len(ranked_df)} symbols"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Screener pipeline failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return {
                "success": False,
                "error": error_msg,
                "data": pd.DataFrame(),
                "metadata": {
                    "date": date,
                    "provider": self.provider.name,
                    "error": str(e),
                    "duration_seconds": (datetime.now() - start_time).total_seconds()
                },
                "saved_files": {}
            }
    
    async def run_quick_screen(self, symbols: List[str]) -> pd.DataFrame:
        """
        Run a quick screen on specific symbols without full pipeline.
        
        Args:
            symbols: List of symbols to screen
            
        Returns:
            DataFrame with basic screening results
        """
        self.logger.info(f"Running quick screen for {len(symbols)} symbols")
        
        try:
            # Fetch snapshot only
            snapshot_df = await self.provider.fetch_snapshot(symbols)
            
            if snapshot_df.empty:
                return pd.DataFrame()
            
            # Add basic features (without historical data)
            enriched_df = await self.feature_engine.add_features(
                snapshot_df, 
                pd.DataFrame()  # Empty historical data
            )
            
            # Light filtering
            filtered_df = await self.filter_engine.apply_filters(enriched_df)
            
            # Simple ranking by volume
            if "volume" in filtered_df.columns:
                filtered_df = filtered_df.sort_values("volume", ascending=False)
                filtered_df["rank"] = range(1, len(filtered_df) + 1)
            
            self.logger.info(f"Quick screen completed: {len(filtered_df)} symbols")
            return filtered_df
            
        except Exception as e:
            self.logger.error(f"Quick screen failed: {e}")
            return pd.DataFrame()
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status and configuration."""
        return {
            "provider": {
                "name": self.provider.name,
                "rate_limit": self.provider.rate_limit
            },
            "configuration": {
                "feature_engine": "FeatureEngine",
                "filter_engine": type(self.filter_engine).__name__,
                "ranking_engine": type(self.ranking_engine).__name__,
                "artifact_manager": type(self.artifact_manager).__name__
            },
            "settings": {
                "artifacts_path": str(settings.artifacts_path),
                "debug": settings.debug
            }
        }
