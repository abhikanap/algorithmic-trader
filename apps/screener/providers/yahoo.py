"""Yahoo Finance data provider implementation."""

import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging

import pandas as pd
import yfinance as yf
from yfinance import Ticker

from packages.core import get_logger
from .base import DataProvider


class YahooProvider(DataProvider):
    """Yahoo Finance data provider with rate limiting and caching."""
    
    def __init__(self, rate_limit: float = 1.0, cache_ttl: int = 300):
        """
        Initialize Yahoo provider.
        
        Args:
            rate_limit: Maximum requests per second
            cache_ttl: Cache TTL in seconds
        """
        self.logger = get_logger(__name__)
        self._rate_limit = rate_limit
        self._cache_ttl = cache_ttl
        self._last_request = 0.0
        self._cache: Dict[str, Any] = {}
        
        # Popular exchanges and their tickers
        self._exchanges = {
            "NYSE": [],
            "NASDAQ": [],
            "AMEX": []
        }
    
    @property 
    def name(self) -> str:
        return "yahoo"
    
    @property
    def rate_limit(self) -> float:
        return self._rate_limit
    
    async def _rate_limit_wait(self) -> None:
        """Enforce rate limiting."""
        now = time.time()
        time_since_last = now - self._last_request
        min_interval = 1.0 / self._rate_limit
        
        if time_since_last < min_interval:
            wait_time = min_interval - time_since_last
            await asyncio.sleep(wait_time)
        
        self._last_request = time.time()
    
    def _get_cache_key(self, method: str, **kwargs) -> str:
        """Generate cache key."""
        key_parts = [method] + [f"{k}:{v}" for k, v in sorted(kwargs.items())]
        return "|".join(key_parts)
    
    def _is_cache_valid(self, cache_entry: Dict) -> bool:
        """Check if cache entry is still valid."""
        if not cache_entry:
            return False
        
        timestamp = cache_entry.get("timestamp", 0)
        return time.time() - timestamp < self._cache_ttl
    
    async def fetch_universe(self, exchanges: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Fetch universe of symbols from predefined lists.
        Note: Yahoo doesn't provide a direct universe API, so we use popular indices.
        """
        cache_key = self._get_cache_key("universe", exchanges=exchanges or [])
        
        # Check cache
        if cache_key in self._cache and self._is_cache_valid(self._cache[cache_key]):
            self.logger.info("Using cached universe data")
            return self._cache[cache_key]["data"]
        
        self.logger.info("Fetching universe from Yahoo Finance")
        
        # Get symbols from major indices
        universe_symbols = []
        
        try:
            # S&P 500
            await self._rate_limit_wait()
            sp500_data = yf.download("^GSPC", period="1d", progress=False)
            if not sp500_data.empty:
                # For demo, use a subset of popular S&P 500 stocks
                popular_sp500 = [
                    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "BRK-B", 
                    "UNH", "JNJ", "V", "PG", "JPM", "HD", "MA", "DIS", "NFLX", "BAC",
                    "ADBE", "CRM", "XOM", "ABBV", "KO", "AVGO", "PFE", "TMO", "COST",
                    "WMT", "MRK", "CSCO", "ORCL", "DHR", "LLY", "AMD", "TXN", "QCOM"
                ]
                universe_symbols.extend(popular_sp500)
            
            # Add some popular small/mid caps
            popular_small_mid = [
                "PLTR", "ROKU", "SQ", "BYND", "SPCE", "COIN", "HOOD", "RBLX", 
                "RIVN", "LCID", "GME", "AMC", "BB", "NOK", "SNDL", "MVIS"
            ]
            universe_symbols.extend(popular_small_mid)
            
            # Create DataFrame
            df = pd.DataFrame({
                "symbol": universe_symbols,
                "name": "",  # Will be populated if needed
                "exchange": "NASDAQ",  # Default
                "sector": "",
                "industry": ""
            })
            
            # Remove duplicates
            df = df.drop_duplicates(subset=["symbol"])
            
            # Cache the result
            self._cache[cache_key] = {
                "data": df,
                "timestamp": time.time()
            }
            
            self.logger.info(f"Fetched universe with {len(df)} symbols")
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching universe: {e}")
            # Return empty DataFrame on error
            return pd.DataFrame(columns=["symbol", "name", "exchange", "sector", "industry"])
    
    async def fetch_snapshot(self, symbols: List[str]) -> pd.DataFrame:
        """Fetch current market snapshot for symbols."""
        cache_key = self._get_cache_key("snapshot", symbols=sorted(symbols))
        
        # Check cache
        if cache_key in self._cache and self._is_cache_valid(self._cache[cache_key]):
            self.logger.info(f"Using cached snapshot for {len(symbols)} symbols")
            return self._cache[cache_key]["data"]
        
        self.logger.info(f"Fetching snapshot for {len(symbols)} symbols")
        
        try:
            await self._rate_limit_wait()
            
            # Batch download with yfinance
            tickers_str = " ".join(symbols)
            data = yf.download(
                tickers_str,
                period="2d",  # Need previous close
                interval="1d",
                group_by="ticker",
                auto_adjust=True,
                prepost=True,
                threads=True,
                progress=False
            )
            
            if data.empty:
                self.logger.warning("No data returned from Yahoo Finance")
                return pd.DataFrame(columns=[
                    "symbol", "last", "open", "high", "low", "close", "volume", "timestamp"
                ])
            
            results = []
            now = datetime.now()
            
            for symbol in symbols:
                try:
                    if len(symbols) == 1:
                        symbol_data = data
                    else:
                        symbol_data = data[symbol] if symbol in data.columns.get_level_values(0) else None
                    
                    if symbol_data is None or symbol_data.empty:
                        self.logger.warning(f"No data for symbol {symbol}")
                        continue
                    
                    # Get latest data
                    latest = symbol_data.iloc[-1]
                    prev = symbol_data.iloc[-2] if len(symbol_data) > 1 else latest
                    
                    result = {
                        "symbol": symbol,
                        "last": latest["Close"] if pd.notna(latest["Close"]) else 0.0,
                        "open": latest["Open"] if pd.notna(latest["Open"]) else 0.0,
                        "high": latest["High"] if pd.notna(latest["High"]) else 0.0,
                        "low": latest["Low"] if pd.notna(latest["Low"]) else 0.0,
                        "close": prev["Close"] if pd.notna(prev["Close"]) else 0.0,  # Previous close
                        "volume": int(latest["Volume"]) if pd.notna(latest["Volume"]) else 0,
                        "timestamp": now
                    }
                    results.append(result)
                    
                except Exception as e:
                    self.logger.warning(f"Error processing {symbol}: {e}")
                    continue
            
            df = pd.DataFrame(results)
            
            # Cache the result
            self._cache[cache_key] = {
                "data": df,
                "timestamp": time.time()
            }
            
            self.logger.info(f"Fetched snapshot for {len(df)} symbols")
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching snapshot: {e}")
            return pd.DataFrame(columns=[
                "symbol", "last", "open", "high", "low", "close", "volume", "timestamp"
            ])
    
    async def fetch_historical(
        self, 
        symbols: List[str], 
        period: str = "1y",
        interval: str = "1d"
    ) -> pd.DataFrame:
        """Fetch historical data for technical analysis."""
        cache_key = self._get_cache_key(
            "historical", 
            symbols=sorted(symbols), 
            period=period, 
            interval=interval
        )
        
        # Check cache
        if cache_key in self._cache and self._is_cache_valid(self._cache[cache_key]):
            self.logger.info(f"Using cached historical data for {len(symbols)} symbols")
            return self._cache[cache_key]["data"]
        
        self.logger.info(f"Fetching historical data for {len(symbols)} symbols")
        
        try:
            await self._rate_limit_wait()
            
            tickers_str = " ".join(symbols)
            data = yf.download(
                tickers_str,
                period=period,
                interval=interval,
                group_by="ticker",
                auto_adjust=True,
                prepost=True,
                threads=True,
                progress=False
            )
            
            if data.empty:
                self.logger.warning("No historical data returned")
                return pd.DataFrame(columns=[
                    "symbol", "date", "open", "high", "low", "close", "volume"
                ])
            
            results = []
            
            for symbol in symbols:
                try:
                    if len(symbols) == 1:
                        symbol_data = data
                    else:
                        symbol_data = data[symbol] if symbol in data.columns.get_level_values(0) else None
                    
                    if symbol_data is None or symbol_data.empty:
                        continue
                    
                    # Reset index to get dates as column
                    symbol_df = symbol_data.reset_index()
                    symbol_df["symbol"] = symbol
                    
                    # Rename columns to match expected schema
                    column_mapping = {
                        "Date": "date",
                        "Open": "open", 
                        "High": "high",
                        "Low": "low",
                        "Close": "close",
                        "Volume": "volume"
                    }
                    
                    symbol_df = symbol_df.rename(columns=column_mapping)
                    
                    # Select only required columns
                    required_cols = ["symbol", "date", "open", "high", "low", "close", "volume"]
                    symbol_df = symbol_df[required_cols]
                    
                    results.append(symbol_df)
                    
                except Exception as e:
                    self.logger.warning(f"Error processing historical data for {symbol}: {e}")
                    continue
            
            if results:
                df = pd.concat(results, ignore_index=True)
            else:
                df = pd.DataFrame(columns=[
                    "symbol", "date", "open", "high", "low", "close", "volume"
                ])
            
            # Cache the result
            self._cache[cache_key] = {
                "data": df,
                "timestamp": time.time()
            }
            
            self.logger.info(f"Fetched historical data: {len(df)} records")
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching historical data: {e}")
            return pd.DataFrame(columns=[
                "symbol", "date", "open", "high", "low", "close", "volume"
            ])
    
    async def get_info(self, symbol: str) -> Dict[str, Any]:
        """Get additional info for a symbol."""
        try:
            await self._rate_limit_wait()
            ticker = Ticker(symbol)
            info = ticker.info
            return {
                "name": info.get("longName", ""),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "exchange": info.get("exchange", ""),
                "market_cap": info.get("marketCap", 0),
                "float_shares": info.get("floatShares", 0),
                "avg_volume": info.get("averageVolume", 0)
            }
        except Exception as e:
            self.logger.warning(f"Error getting info for {symbol}: {e}")
            return {}
