"""Historical data loader for backtesting."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import pandas as pd
import yfinance as yf
from pathlib import Path

from packages.core import get_logger
from packages.core.config import settings


class HistoricalDataLoader:
    """Loads historical market data for backtesting."""
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.logger = get_logger(__name__)
        self.cache_dir = Path(cache_dir or settings.CACHE_PATH) / "historical_data"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Initialized data loader with cache: {self.cache_dir}")
    
    async def load_data_range(
        self,
        start_date: str,
        end_date: str,
        symbols: Optional[List[str]] = None,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Load historical data for date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)  
            symbols: List of symbols (None = use default set)
            use_cache: Whether to use cached data
            
        Returns:
            DataFrame with historical market data
        """
        self.logger.info(f"Loading data from {start_date} to {end_date}")
        
        # Use default symbol universe if none provided
        if symbols is None:
            symbols = self._get_default_symbols()
        
        self.logger.info(f"Loading data for {len(symbols)} symbols")
        
        all_data = []
        
        # Load data in batches to avoid rate limits
        batch_size = 50
        for i in range(0, len(symbols), batch_size):
            batch_symbols = symbols[i:i + batch_size]
            
            self.logger.info(f"Loading batch {i//batch_size + 1}: {len(batch_symbols)} symbols")
            
            batch_data = await self._load_batch_data(
                batch_symbols, start_date, end_date, use_cache
            )
            
            if not batch_data.empty:
                all_data.append(batch_data)
            
            # Rate limiting
            await asyncio.sleep(1)
        
        if all_data:
            result = pd.concat(all_data, ignore_index=True)
            
            # Add calculated fields
            result = self._enrich_data(result)
            
            self.logger.info(f"Loaded {len(result)} data points for {result['symbol'].nunique()} symbols")
            return result
        else:
            self.logger.warning("No data loaded")
            return pd.DataFrame()
    
    async def _load_batch_data(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        use_cache: bool
    ) -> pd.DataFrame:
        """Load data for a batch of symbols."""
        
        batch_data = []
        
        for symbol in symbols:
            try:
                symbol_data = await self._load_symbol_data(
                    symbol, start_date, end_date, use_cache
                )
                
                if not symbol_data.empty:
                    symbol_data['symbol'] = symbol
                    batch_data.append(symbol_data)
                    
            except Exception as e:
                self.logger.error(f"Failed to load data for {symbol}: {e}")
                continue
        
        if batch_data:
            return pd.concat(batch_data, ignore_index=True)
        else:
            return pd.DataFrame()
    
    async def _load_symbol_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        use_cache: bool
    ) -> pd.DataFrame:
        """Load data for a single symbol."""
        
        # Check cache first
        if use_cache:
            cached_data = self._load_from_cache(symbol, start_date, end_date)
            if cached_data is not None:
                return cached_data
        
        # Load from API
        try:
            ticker = yf.Ticker(symbol)
            
            # Get historical data
            hist_data = ticker.history(
                start=start_date,
                end=end_date,
                interval="1d",
                actions=False,
                auto_adjust=True,
                back_adjust=False
            )
            
            if hist_data.empty:
                return pd.DataFrame()
            
            # Convert to our format
            df = pd.DataFrame({
                'date': hist_data.index.strftime('%Y-%m-%d'),
                'open': hist_data['Open'].round(2),
                'high': hist_data['High'].round(2),
                'low': hist_data['Low'].round(2),
                'close': hist_data['Close'].round(2),
                'volume': hist_data['Volume'].astype(int)
            })
            
            # Get additional info
            info = ticker.info
            df['market_cap'] = info.get('marketCap', 0)
            df['avg_volume_20d'] = info.get('averageVolume', df['volume'].mean())
            
            # Cache the data
            if use_cache:
                self._save_to_cache(symbol, df, start_date, end_date)
            
            return df
            
        except Exception as e:
            self.logger.error(f"API error loading {symbol}: {e}")
            return pd.DataFrame()
    
    def _enrich_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add calculated fields to the data."""
        
        if df.empty:
            return df
        
        # Sort by symbol and date
        df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
        
        # Calculate previous close
        df['prev_close'] = df.groupby('symbol')['close'].shift(1)
        
        # Calculate returns
        df['return_1d'] = ((df['close'] - df['prev_close']) / df['prev_close']) * 100
        
        # Calculate gaps
        df['gap_pct'] = ((df['open'] - df['prev_close']) / df['prev_close']) * 100
        
        # Calculate intraday range
        df['range_pct'] = ((df['high'] - df['low']) / df['close']) * 100
        
        # Calculate volume ratio
        df['volume_ratio'] = df['volume'] / df['avg_volume_20d']
        
        # Calculate volatility (5-day rolling)
        df['volatility_5d'] = df.groupby('symbol')['return_1d'].rolling(5).std().reset_index(0, drop=True)
        
        # Calculate price momentum (5-day)
        df['momentum_5d'] = ((df['close'] - df.groupby('symbol')['close'].shift(5)) / 
                            df.groupby('symbol')['close'].shift(5)) * 100
        
        # Fill NaN values
        df['prev_close'] = df['prev_close'].fillna(df['open'])
        df['return_1d'] = df['return_1d'].fillna(0)
        df['gap_pct'] = df['gap_pct'].fillna(0)
        df['volatility_5d'] = df['volatility_5d'].fillna(df['range_pct'])
        df['momentum_5d'] = df['momentum_5d'].fillna(0)
        
        return df
    
    def _get_default_symbols(self) -> List[str]:
        """Get default symbol universe for backtesting."""
        
        # Popular stocks across different sectors and market caps
        symbols = [
            # Large cap tech
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA',
            
            # Financial
            'JPM', 'BAC', 'WFC', 'GS', 'MS',
            
            # Healthcare
            'JNJ', 'PFE', 'UNH', 'ABBV', 'MRK',
            
            # Consumer
            'KO', 'PG', 'WMT', 'HD', 'MCD',
            
            # Industrial
            'BA', 'CAT', 'GE', 'MMM', 'UPS',
            
            # Energy
            'XOM', 'CVX', 'COP', 'SLB', 'EOG',
            
            # Utilities
            'NEE', 'SO', 'DUK', 'AEP', 'SRE',
            
            # Mid cap growth
            'ZM', 'ROKU', 'SQ', 'SHOP', 'TWLO',
            
            # Small cap momentum
            'SPCE', 'PLTR', 'SKLZ', 'SOFI', 'WISH',
            
            # Penny stocks (for testing)
            'SNDL', 'NOK', 'AMC', 'GME', 'BB'
        ]
        
        return symbols
    
    def _load_from_cache(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """Load data from cache if available and valid."""
        
        cache_file = self.cache_dir / f"{symbol}_{start_date}_{end_date}.parquet"
        
        if cache_file.exists():
            try:
                # Check if cache is recent (less than 1 day old for daily data)
                cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                
                if cache_age < timedelta(hours=4):  # Refresh cache every 4 hours
                    df = pd.read_parquet(cache_file)
                    self.logger.debug(f"Loaded {symbol} from cache")
                    return df
                else:
                    self.logger.debug(f"Cache expired for {symbol}")
                    cache_file.unlink()  # Remove expired cache
                    
            except Exception as e:
                self.logger.error(f"Error loading cache for {symbol}: {e}")
                try:
                    cache_file.unlink()  # Remove corrupted cache
                except:
                    pass
        
        return None
    
    def _save_to_cache(self, symbol: str, df: pd.DataFrame, start_date: str, end_date: str):
        """Save data to cache."""
        
        try:
            cache_file = self.cache_dir / f"{symbol}_{start_date}_{end_date}.parquet"
            df.to_parquet(cache_file, index=False)
            self.logger.debug(f"Cached data for {symbol}")
            
        except Exception as e:
            self.logger.error(f"Error caching data for {symbol}: {e}")
    
    def clear_cache(self, symbol: Optional[str] = None):
        """Clear cached data."""
        
        if symbol:
            # Clear specific symbol
            pattern = f"{symbol}_*.parquet"
            for cache_file in self.cache_dir.glob(pattern):
                cache_file.unlink()
            self.logger.info(f"Cleared cache for {symbol}")
        else:
            # Clear all cache
            for cache_file in self.cache_dir.glob("*.parquet"):
                cache_file.unlink()
            self.logger.info("Cleared all cache")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache information."""
        
        cache_files = list(self.cache_dir.glob("*.parquet"))
        
        cache_info = {
            "cache_dir": str(self.cache_dir),
            "total_files": len(cache_files),
            "total_size_mb": sum(f.stat().st_size for f in cache_files) / (1024 * 1024),
            "symbols_cached": len(set(f.stem.split('_')[0] for f in cache_files))
        }
        
        return cache_info
