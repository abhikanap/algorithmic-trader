"""
Core Service Models - Self-contained data models for microservice
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field


class TimeSegment(str, Enum):
    """Intraday time segments."""
    PREMARKET = "premarket"
    OPEN = "open"
    LATE_MORNING = "late_morning"
    MIDDAY = "midday"
    AFTERNOON = "afternoon"
    POWER_HOUR = "power_hour"
    OVERNIGHT = "overnight"


class CapitalBucket(str, Enum):
    """Capital allocation buckets."""
    A = "A"  # Penny stocks & microcap movers
    B = "B"  # Large-cap intraday trends
    C = "C"  # Multi-day swing trades
    D = "D"  # Catalyst-driven market movers
    E = "E"  # Defensive hedges


class OrderSide(str, Enum):
    """Order side."""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    """Order status."""
    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class SignalType(str, Enum):
    """Trading signal types."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    EXIT = "exit"


class TradeSignal(BaseModel):
    """Trading signal model."""
    symbol: str
    signal_type: SignalType
    timestamp: datetime
    price: float
    confidence: float = Field(ge=0.0, le=1.0)
    strategy: str
    reason: Optional[str] = None
    metadata: Optional[Dict] = None


class StockData(BaseModel):
    """Stock market data."""
    symbol: str
    name: Optional[str] = None
    exchange: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    
    # Price data
    last: float
    open: float
    high: float
    low: float
    close: float
    prev_close: float
    
    # Volume
    volume: int
    avg_volume_20d: Optional[int] = None
    avg_dollar_volume_20d: Optional[float] = None
    
    # Technical indicators
    atr_14: Optional[float] = None
    atrp_14: Optional[float] = None  # ATR as percentage
    hv_10: Optional[float] = None  # Historical volatility 10d
    hv_20: Optional[float] = None  # Historical volatility 20d
    rsi_14: Optional[float] = None
    
    # SMAs
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
