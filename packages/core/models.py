"""Core data models and schemas."""

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


class IntradayPattern(str, Enum):
    """Intraday stock patterns."""
    MORNING_SPIKE_FADE = "morning_spike_fade"
    MORNING_SURGE_UPTREND = "morning_surge_uptrend"
    MORNING_PLUNGE_RECOVERY = "morning_plunge_recovery"
    MORNING_SELLOFF_DOWNTREND = "morning_selloff_downtrend"
    CHOPPY_RANGE_BOUND = "choppy_range_bound"


class MultidayPattern(str, Enum):
    """Multi-day stock patterns."""
    SUSTAINED_UPTREND = "sustained_uptrend"
    SUSTAINED_DOWNTREND = "sustained_downtrend"
    BLOWOFF_TOP = "blowoff_top"
    DOWNTREND_REVERSAL = "downtrend_reversal"
    SIDEWAYS_CONSOLIDATION = "sideways_consolidation"


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
    
    # Derived metrics
    range_pct_day: Optional[float] = None  # (high-low)/open * 100
    gap_pct: Optional[float] = None  # (open-prev_close)/prev_close * 100
    
    # Metadata
    asof: datetime
    provider: str = "yahoo"


class ScreenerResult(BaseModel):
    """Screener pipeline result."""
    symbol: str
    score: float
    volatility: Dict[str, float]  # atrp_14, hv_20, range_pct_day
    liquidity: Dict[str, float]  # avg_dollar_volume_20d
    technicals: Dict[str, Optional[float]]  # RSI, SMAs, etc.
    flags: Dict[str, bool]  # gap_up, high_volume, etc.
    asof: datetime


class PatternAnalysis(BaseModel):
    """Pattern analysis result."""
    symbol: str
    pattern_intraday: Optional[IntradayPattern] = None
    pattern_multiday: Optional[MultidayPattern] = None
    confidence: float = Field(ge=0.0, le=1.0)
    hints: Dict[str, Union[str, List[str]]] = Field(default_factory=dict)
    asof: datetime


class StrategyAllocation(BaseModel):
    """Strategy allocation for a symbol."""
    symbol: str
    bucket: CapitalBucket
    time_segment: TimeSegment
    target_weight: float = Field(ge=0.0, le=1.0)
    position_size: float  # in USD
    rationale: str
    
    
class Order(BaseModel):
    """Trading order."""
    id: Optional[str] = None
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: int
    price: Optional[float] = None
    stop_price: Optional[float] = None
    
    # Strategy context
    bucket_id: Optional[CapitalBucket] = None
    pattern_id: Optional[str] = None
    time_segment: Optional[TimeSegment] = None
    
    # Status
    status: OrderStatus = OrderStatus.NEW
    filled_quantity: int = 0
    avg_fill_price: Optional[float] = None
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None


class Position(BaseModel):
    """Trading position."""
    symbol: str
    quantity: int
    market_value: float
    cost_basis: float
    unrealized_pnl: float
    
    # Strategy context
    bucket_id: Optional[CapitalBucket] = None
    pattern_id: Optional[str] = None
    entry_time_segment: Optional[TimeSegment] = None
    
    # Risk management
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    
    # Timestamps
    opened_at: datetime
    updated_at: Optional[datetime] = None


class MarketData(BaseModel):
    """Real-time market data."""
    symbol: str
    bid: float
    ask: float
    last: float
    volume: int
    timestamp: datetime


class PortfolioSnapshot(BaseModel):
    """Portfolio snapshot."""
    total_equity: float
    buying_power: float
    day_pnl: float
    total_pnl: float
    
    # Bucket allocations
    bucket_allocations: Dict[CapitalBucket, float]
    
    # Positions
    positions: List[Position]
    open_orders: List[Order]
    
    # Timestamp
    asof: datetime


class TradeSignal(BaseModel):
    """Trade signal from strategy engine."""
    symbol: str
    action: str  # BUY, SELL
    quantity: int = 0
    price: float
    position_size: float  # Dollar amount
    bucket: str  # Capital bucket (A-E)
    time_segment: str  # Time slot
    pattern_intraday: Optional[str] = None
    pattern_multiday: Optional[str] = None
    confidence: float = 0.0
    metadata: Dict[str, float] = Field(default_factory=dict)
