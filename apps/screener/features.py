"""Feature engineering for stock screening."""

import asyncio
from typing import List, Dict, Any
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from packages.core import get_logger


class FeatureEngine:
    """Feature engineering for stock market data."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    async def add_features(self, snapshot_df: pd.DataFrame, historical_df: pd.DataFrame) -> pd.DataFrame:
        """
        Add technical features to the snapshot data.
        
        Args:
            snapshot_df: Current market snapshot
            historical_df: Historical price data
            
        Returns:
            DataFrame with added features
        """
        self.logger.info(f"Adding features for {len(snapshot_df)} symbols")
        
        # Start with snapshot data
        result_df = snapshot_df.copy()
        
        # Add basic price features
        result_df = self._add_price_features(result_df)
        
        # Add technical indicators from historical data
        result_df = await self._add_technical_features(result_df, historical_df)
        
        # Add volatility features
        result_df = self._add_volatility_features(result_df, historical_df)
        
        # Add volume features
        result_df = self._add_volume_features(result_df, historical_df)
        
        self.logger.info(f"Added features, final shape: {result_df.shape}")
        return result_df
    
    def _add_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add basic price-derived features."""
        # Day range as percentage
        df["range_pct_day"] = np.where(
            df["open"] > 0,
            ((df["high"] - df["low"]) / df["open"]) * 100,
            0.0
        )
        
        # Gap percentage from previous close
        df["gap_pct"] = np.where(
            df["close"] > 0,
            ((df["open"] - df["close"]) / df["close"]) * 100,
            0.0
        )
        
        # Current price change from open
        df["change_from_open_pct"] = np.where(
            df["open"] > 0,
            ((df["last"] - df["open"]) / df["open"]) * 100,
            0.0
        )
        
        # Previous day change
        df["prev_day_change_pct"] = np.where(
            df["close"] > 0,
            ((df["close"] - df.get("prev_close", df["close"])) / df["close"]) * 100,
            0.0
        )
        
        return df
    
    async def _add_technical_features(self, df: pd.DataFrame, historical_df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators."""
        if historical_df.empty:
            # Add empty columns if no historical data
            for col in ["atr_14", "atrp_14", "rsi_14", "sma_20", "sma_50", "sma_200"]:
                df[col] = np.nan
            return df
        
        # Process each symbol
        for symbol in df["symbol"].unique():
            symbol_hist = historical_df[historical_df["symbol"] == symbol].copy()
            
            if len(symbol_hist) < 20:  # Need minimum data for indicators
                continue
            
            # Sort by date
            symbol_hist = symbol_hist.sort_values("date")
            
            # Calculate ATR (Average True Range)
            atr = self._calculate_atr(symbol_hist, period=14)
            current_price = df[df["symbol"] == symbol]["last"].iloc[0] if len(df[df["symbol"] == symbol]) > 0 else 1.0
            atr_pct = (atr / current_price) * 100 if current_price > 0 else 0.0
            
            # Calculate RSI
            rsi = self._calculate_rsi(symbol_hist["close"], period=14)
            
            # Calculate SMAs
            sma_20 = symbol_hist["close"].rolling(window=20).mean().iloc[-1]
            sma_50 = symbol_hist["close"].rolling(window=50).mean().iloc[-1] if len(symbol_hist) >= 50 else np.nan
            sma_200 = symbol_hist["close"].rolling(window=200).mean().iloc[-1] if len(symbol_hist) >= 200 else np.nan
            
            # Update the main DataFrame
            mask = df["symbol"] == symbol
            df.loc[mask, "atr_14"] = atr
            df.loc[mask, "atrp_14"] = atr_pct
            df.loc[mask, "rsi_14"] = rsi
            df.loc[mask, "sma_20"] = sma_20
            df.loc[mask, "sma_50"] = sma_50
            df.loc[mask, "sma_200"] = sma_200
        
        return df
    
    def _add_volatility_features(self, df: pd.DataFrame, historical_df: pd.DataFrame) -> pd.DataFrame:
        """Add volatility-based features."""
        if historical_df.empty:
            df["hv_10"] = np.nan
            df["hv_20"] = np.nan
            return df
        
        # Calculate historical volatility for each symbol
        for symbol in df["symbol"].unique():
            symbol_hist = historical_df[historical_df["symbol"] == symbol].copy()
            
            if len(symbol_hist) < 20:
                continue
            
            # Sort by date
            symbol_hist = symbol_hist.sort_values("date")
            
            # Calculate daily returns
            symbol_hist["returns"] = symbol_hist["close"].pct_change()
            
            # Historical volatility (annualized)
            hv_10 = symbol_hist["returns"].rolling(window=10).std().iloc[-1] * np.sqrt(252) * 100
            hv_20 = symbol_hist["returns"].rolling(window=20).std().iloc[-1] * np.sqrt(252) * 100
            
            # Update main DataFrame
            mask = df["symbol"] == symbol
            df.loc[mask, "hv_10"] = hv_10
            df.loc[mask, "hv_20"] = hv_20
        
        return df
    
    def _add_volume_features(self, df: pd.DataFrame, historical_df: pd.DataFrame) -> pd.DataFrame:
        """Add volume-based features."""
        if historical_df.empty:
            df["avg_volume_20d"] = np.nan
            df["avg_dollar_volume_20d"] = np.nan
            df["volume_ratio"] = np.nan
            return df
        
        # Calculate volume features for each symbol
        for symbol in df["symbol"].unique():
            symbol_hist = historical_df[historical_df["symbol"] == symbol].copy()
            
            if len(symbol_hist) < 20:
                continue
            
            # Sort by date
            symbol_hist = symbol_hist.sort_values("date")
            
            # Average volume
            avg_volume_20d = symbol_hist["volume"].rolling(window=20).mean().iloc[-1]
            
            # Average dollar volume
            symbol_hist["dollar_volume"] = symbol_hist["close"] * symbol_hist["volume"]
            avg_dollar_volume_20d = symbol_hist["dollar_volume"].rolling(window=20).mean().iloc[-1]
            
            # Current volume ratio vs average
            current_volume = df[df["symbol"] == symbol]["volume"].iloc[0] if len(df[df["symbol"] == symbol]) > 0 else 0
            volume_ratio = current_volume / avg_volume_20d if avg_volume_20d > 0 else 0.0
            
            # Update main DataFrame
            mask = df["symbol"] == symbol
            df.loc[mask, "avg_volume_20d"] = int(avg_volume_20d) if not np.isnan(avg_volume_20d) else 0
            df.loc[mask, "avg_dollar_volume_20d"] = avg_dollar_volume_20d
            df.loc[mask, "volume_ratio"] = volume_ratio
        
        return df
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range."""
        if len(df) < period:
            return 0.0
        
        df = df.copy()
        
        # True Range calculation
        df["prev_close"] = df["close"].shift(1)
        df["tr1"] = df["high"] - df["low"]
        df["tr2"] = abs(df["high"] - df["prev_close"])
        df["tr3"] = abs(df["low"] - df["prev_close"])
        df["true_range"] = df[["tr1", "tr2", "tr3"]].max(axis=1)
        
        # ATR is simple moving average of True Range
        atr = df["true_range"].rolling(window=period).mean().iloc[-1]
        return atr if not np.isnan(atr) else 0.0
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate Relative Strength Index."""
        if len(prices) < period + 1:
            return 50.0  # Neutral RSI
        
        # Calculate price changes
        delta = prices.diff()
        
        # Separate gains and losses
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        
        # Calculate exponential moving averages
        avg_gains = gains.rolling(window=period).mean()
        avg_losses = losses.rolling(window=period).mean()
        
        # Calculate RS and RSI
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1] if not np.isnan(rsi.iloc[-1]) else 50.0
