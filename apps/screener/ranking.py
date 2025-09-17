"""Ranking engine for stock screening."""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from packages.core import get_logger
from packages.core.config import screening_config


class RankingEngine:
    """Stock ranking and scoring system."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.logger = get_logger(__name__)
        self.config = config or self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default ranking configuration."""
        return {
            "topk_symbols": screening_config.topk_symbols,
            "scoring_weights": {
                "volatility": 0.4,      # ATR%, HV - higher is better
                "liquidity": 0.3,       # Dollar volume - higher is better
                "momentum": 0.2,        # Price momentum - directional
                "technical": 0.1        # Technical indicators
            },
            "volatility_metrics": ["atrp_14", "hv_20", "range_pct_day"],
            "liquidity_metrics": ["avg_dollar_volume_20d", "volume_ratio"],
            "momentum_metrics": ["gap_pct", "change_from_open_pct"],
            "technical_metrics": ["rsi_14"]
        }
    
    async def rank_symbols(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Rank symbols by composite score.
        
        Args:
            df: DataFrame with stock data and features
            
        Returns:
            DataFrame with added score column, sorted by rank
        """
        if df.empty:
            return df
        
        self.logger.info(f"Ranking {len(df)} symbols")
        
        # Calculate component scores
        df = self._calculate_volatility_score(df)
        df = self._calculate_liquidity_score(df)
        df = self._calculate_momentum_score(df)
        df = self._calculate_technical_score(df)
        
        # Calculate composite score
        df = self._calculate_composite_score(df)
        
        # Sort by score (descending)
        df = df.sort_values("score", ascending=False).reset_index(drop=True)
        
        # Add rank
        df["rank"] = range(1, len(df) + 1)
        
        # Take top K
        topk = self.config["topk_symbols"]
        if topk > 0 and len(df) > topk:
            df = df.head(topk).copy()
            self.logger.info(f"Selected top {topk} symbols")
        
        self.logger.info(f"Ranking complete. Top symbol: {df.iloc[0]['symbol']} (score: {df.iloc[0]['score']:.3f})")
        
        return df
    
    def _calculate_volatility_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate volatility-based score (0-1, higher is better)."""
        volatility_scores = []
        
        for metric in self.config["volatility_metrics"]:
            if metric in df.columns:
                # Normalize to 0-1 using percentile ranks
                values = df[metric].fillna(0)
                if values.max() > values.min():
                    scores = values.rank(pct=True)
                else:
                    scores = pd.Series([0.5] * len(values), index=values.index)
                volatility_scores.append(scores)
        
        if volatility_scores:
            # Average of volatility metrics
            df["volatility_score"] = pd.concat(volatility_scores, axis=1).mean(axis=1)
        else:
            df["volatility_score"] = 0.5  # Neutral score
        
        return df
    
    def _calculate_liquidity_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate liquidity-based score (0-1, higher is better)."""
        liquidity_scores = []
        
        for metric in self.config["liquidity_metrics"]:
            if metric in df.columns:
                values = df[metric].fillna(0)
                if values.max() > values.min():
                    scores = values.rank(pct=True)
                else:
                    scores = pd.Series([0.5] * len(values), index=values.index)
                liquidity_scores.append(scores)
        
        if liquidity_scores:
            df["liquidity_score"] = pd.concat(liquidity_scores, axis=1).mean(axis=1)
        else:
            df["liquidity_score"] = 0.5
        
        return df
    
    def _calculate_momentum_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate momentum-based score (0-1, absolute momentum preferred)."""
        momentum_scores = []
        
        for metric in self.config["momentum_metrics"]:
            if metric in df.columns:
                values = df[metric].fillna(0)
                # For momentum, we prefer absolute values (strong moves in either direction)
                abs_values = abs(values)
                if abs_values.max() > abs_values.min():
                    scores = abs_values.rank(pct=True)
                else:
                    scores = pd.Series([0.5] * len(values), index=values.index)
                momentum_scores.append(scores)
        
        if momentum_scores:
            df["momentum_score"] = pd.concat(momentum_scores, axis=1).mean(axis=1)
        else:
            df["momentum_score"] = 0.5
        
        return df
    
    def _calculate_technical_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicator score."""
        technical_scores = []
        
        # RSI score: prefer values away from 50 (overbought/oversold)
        if "rsi_14" in df.columns:
            rsi_values = df["rsi_14"].fillna(50)
            # Distance from neutral (50)
            rsi_distance = abs(rsi_values - 50)
            if rsi_distance.max() > rsi_distance.min():
                rsi_scores = rsi_distance.rank(pct=True)
            else:
                rsi_scores = pd.Series([0.5] * len(rsi_values), index=rsi_values.index)
            technical_scores.append(rsi_scores)
        
        # SMA position score: prefer stocks near SMAs for potential breakouts
        if "sma_20" in df.columns and "last" in df.columns:
            sma_20_values = df["sma_20"].fillna(df["last"])
            price_to_sma = abs(df["last"] - sma_20_values) / sma_20_values
            # Prefer stocks close to SMA (potential breakout candidates)
            proximity_scores = (1 - price_to_sma.clip(0, 1)).rank(pct=True)
            technical_scores.append(proximity_scores)
        
        if technical_scores:
            df["technical_score"] = pd.concat(technical_scores, axis=1).mean(axis=1)
        else:
            df["technical_score"] = 0.5
        
        return df
    
    def _calculate_composite_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate weighted composite score."""
        weights = self.config["scoring_weights"]
        
        df["score"] = (
            df["volatility_score"] * weights["volatility"] +
            df["liquidity_score"] * weights["liquidity"] +
            df["momentum_score"] * weights["momentum"] +
            df["technical_score"] * weights["technical"]
        )
        
        return df
    
    def get_ranking_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate ranking summary statistics."""
        if df.empty:
            return {"error": "No data to summarize"}
        
        summary = {
            "total_symbols": len(df),
            "top_symbol": {
                "symbol": df.iloc[0]["symbol"],
                "score": round(df.iloc[0]["score"], 3),
                "volatility_score": round(df.iloc[0]["volatility_score"], 3),
                "liquidity_score": round(df.iloc[0]["liquidity_score"], 3),
                "momentum_score": round(df.iloc[0]["momentum_score"], 3),
                "technical_score": round(df.iloc[0]["technical_score"], 3)
            },
            "score_distribution": {
                "mean": round(df["score"].mean(), 3),
                "median": round(df["score"].median(), 3),
                "std": round(df["score"].std(), 3),
                "min": round(df["score"].min(), 3),
                "max": round(df["score"].max(), 3)
            },
            "component_correlations": {
                "volatility_liquidity": round(df["volatility_score"].corr(df["liquidity_score"]), 3),
                "volatility_momentum": round(df["volatility_score"].corr(df["momentum_score"]), 3),
                "liquidity_momentum": round(df["liquidity_score"].corr(df["momentum_score"]), 3)
            }
        }
        
        # Top 10 symbols summary
        top_10 = df.head(10)
        summary["top_10"] = [
            {
                "rank": int(row["rank"]),
                "symbol": row["symbol"],
                "score": round(row["score"], 3),
                "atrp_14": round(row.get("atrp_14", 0), 2),
                "avg_dollar_volume_20d": int(row.get("avg_dollar_volume_20d", 0))
            }
            for _, row in top_10.iterrows()
        ]
        
        return summary
    
    def get_sector_distribution(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get distribution of top symbols by sector."""
        if df.empty or "sector" not in df.columns:
            return {}
        
        sector_stats = df.groupby("sector").agg({
            "symbol": "count",
            "score": ["mean", "max"],
            "atrp_14": "mean"
        }).round(3)
        
        # Flatten column names
        sector_stats.columns = ["count", "avg_score", "max_score", "avg_atr_pct"]
        
        return sector_stats.to_dict("index")
