"""Base provider protocol for data sources."""

from abc import ABC, abstractmethod
from typing import List, Optional
import pandas as pd


class DataProvider(ABC):
    """Abstract base class for market data providers."""
    
    @abstractmethod
    async def fetch_universe(self, exchanges: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Fetch the universe of available symbols.
        
        Returns DataFrame with columns:
        - symbol: str
        - name: str 
        - exchange: str
        - sector: str
        - industry: str
        - market_cap: float (optional)
        """
        pass
    
    @abstractmethod
    async def fetch_snapshot(self, symbols: List[str]) -> pd.DataFrame:
        """
        Fetch current market snapshot for given symbols.
        
        Returns DataFrame with columns:
        - symbol: str
        - last: float
        - open: float  
        - high: float
        - low: float
        - close: float (previous close)
        - volume: int
        - timestamp: datetime
        """
        pass
    
    @abstractmethod
    async def fetch_historical(
        self, 
        symbols: List[str], 
        period: str = "1y",
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Fetch historical data for technical analysis.
        
        Returns DataFrame with columns:
        - symbol: str
        - date: datetime
        - open: float
        - high: float
        - low: float
        - close: float
        - volume: int
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass
    
    @property
    @abstractmethod
    def rate_limit(self) -> float:
        """Rate limit in requests per second."""
        pass
