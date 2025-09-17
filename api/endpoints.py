"""API endpoints for external integrations and third-party access."""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Depends, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import jwt
from passlib.context import CryptContext

from apps.strategy.pipeline import StrategyPipeline
from apps.execution.pipeline import ExecutionPipeline
from apps.execution.portfolio import PortfolioManager
from monitoring.system import monitoring_system


# Security configuration
SECRET_KEY = "your-secret-key-here"  # Should be in environment variables
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


# API Models
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserLogin(BaseModel):
    username: str
    password: str


class PositionResponse(BaseModel):
    symbol: str
    quantity: float
    market_value: float
    unrealized_pnl: float
    avg_entry_price: float
    current_price: float


class OrderRequest(BaseModel):
    symbol: str
    side: str = Field(..., description="'buy' or 'sell'")
    quantity: float = Field(..., gt=0, description="Number of shares")
    order_type: str = Field(default="market", description="'market' or 'limit'")
    limit_price: Optional[float] = Field(None, description="Required for limit orders")
    time_in_force: str = Field(default="day", description="'day', 'gtc', 'ioc', 'fok'")


class OrderResponse(BaseModel):
    order_id: str
    symbol: str
    side: str
    quantity: float
    status: str
    submitted_at: datetime


class StrategyRequest(BaseModel):
    name: str
    parameters: Dict[str, Any]
    symbols: List[str]
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class StrategyResponse(BaseModel):
    strategy_id: str
    name: str
    status: str
    created_at: datetime
    parameters: Dict[str, Any]


class BacktestRequest(BaseModel):
    strategy_name: str
    symbols: List[str]
    start_date: str
    end_date: str
    initial_capital: float = 100000.0
    parameters: Optional[Dict[str, Any]] = None


class BacktestResponse(BaseModel):
    backtest_id: str
    status: str
    total_return: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    total_trades: Optional[int] = None
    win_rate: Optional[float] = None
    results_url: Optional[str] = None


class TradingAPI:
    """Main API class for the trading platform."""
    
    def __init__(self):
        self.app = FastAPI(
            title="Trading Platform API",
            description="RESTful API for algorithmic trading platform",
            version="1.0.0"
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Mock user database (use proper database in production)
        self.users_db = {
            "admin": {
                "username": "admin",
                "hashed_password": pwd_context.hash("admin123"),
                "permissions": ["read", "write", "admin"]
            },
            "trader": {
                "username": "trader",
                "hashed_password": pwd_context.hash("trader123"),
                "permissions": ["read", "write"]
            },
            "viewer": {
                "username": "viewer",
                "hashed_password": pwd_context.hash("viewer123"),
                "permissions": ["read"]
            }
        }
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes."""
        
        # Authentication
        @self.app.post("/auth/login", response_model=TokenResponse)
        async def login(user_credentials: UserLogin):
            """Authenticate user and return access token."""
            user = self._authenticate_user(user_credentials.username, user_credentials.password)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = self._create_access_token(
                data={"sub": user["username"], "permissions": user["permissions"]},
                expires_delta=access_token_expires
            )
            
            return TokenResponse(
                access_token=access_token,
                expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )
        
        # System Status
        @self.app.get("/api/v1/system/status")
        async def get_system_status(current_user: dict = Depends(self._get_current_user)):
            """Get system status and health metrics."""
            return monitoring_system.get_system_status()
        
        @self.app.get("/api/v1/system/metrics")
        async def get_system_metrics(
            hours: int = 24,
            current_user: dict = Depends(self._get_current_user)
        ):
            """Get system metrics summary."""
            return monitoring_system.get_metrics_summary(hours)
        
        # Portfolio Management
        @self.app.get("/api/v1/portfolio/positions", response_model=List[PositionResponse])
        async def get_positions(current_user: dict = Depends(self._get_current_user)):
            """Get current portfolio positions."""
            # Mock implementation - integrate with actual portfolio manager
            positions = [
                PositionResponse(
                    symbol="AAPL",
                    quantity=100,
                    market_value=15000.0,
                    unrealized_pnl=500.0,
                    avg_entry_price=145.0,
                    current_price=150.0
                ),
                PositionResponse(
                    symbol="GOOGL",
                    quantity=50,
                    market_value=12500.0,
                    unrealized_pnl=-250.0,
                    avg_entry_price=2550.0,
                    current_price=2500.0
                )
            ]
            return positions
        
        @self.app.get("/api/v1/portfolio/performance")
        async def get_portfolio_performance(
            days: int = 30,
            current_user: dict = Depends(self._get_current_user)
        ):
            """Get portfolio performance metrics."""
            # Mock implementation
            return {
                "total_value": 125000.0,
                "cash_balance": 25000.0,
                "day_pnl": 250.0,
                "day_pnl_percent": 0.2,
                "total_pnl": 5000.0,
                "total_pnl_percent": 4.17,
                "period_days": days,
                "positions_count": 15,
                "last_updated": datetime.now().isoformat()
            }
        
        # Order Management
        @self.app.post("/api/v1/orders", response_model=OrderResponse)
        async def submit_order(
            order: OrderRequest,
            current_user: dict = Depends(self._require_write_permission)
        ):
            """Submit a new trading order."""
            # Validate order
            if order.order_type == "limit" and order.limit_price is None:
                raise HTTPException(
                    status_code=400,
                    detail="Limit price required for limit orders"
                )
            
            # Mock order submission
            order_id = f"order_{int(datetime.now().timestamp())}"
            
            # In production, integrate with execution engine
            return OrderResponse(
                order_id=order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                status="submitted",
                submitted_at=datetime.now()
            )
        
        @self.app.get("/api/v1/orders")
        async def get_orders(
            symbol: Optional[str] = None,
            status: Optional[str] = None,
            limit: int = 100,
            current_user: dict = Depends(self._get_current_user)
        ):
            """Get order history with optional filtering."""
            # Mock implementation
            orders = [
                {
                    "order_id": "order_1",
                    "symbol": "AAPL",
                    "side": "buy",
                    "quantity": 100,
                    "order_type": "market",
                    "status": "filled",
                    "filled_quantity": 100,
                    "avg_fill_price": 149.50,
                    "submitted_at": "2024-01-15T10:30:00Z",
                    "filled_at": "2024-01-15T10:30:15Z"
                }
            ]
            
            # Apply filters
            if symbol:
                orders = [o for o in orders if o["symbol"] == symbol]
            if status:
                orders = [o for o in orders if o["status"] == status]
            
            return orders[:limit]
        
        @self.app.delete("/api/v1/orders/{order_id}")
        async def cancel_order(
            order_id: str,
            current_user: dict = Depends(self._require_write_permission)
        ):
            """Cancel an existing order."""
            # Mock implementation
            return {"message": f"Order {order_id} cancellation requested", "status": "pending_cancel"}
        
        # Strategy Management
        @self.app.post("/api/v1/strategies", response_model=StrategyResponse)
        async def create_strategy(
            strategy: StrategyRequest,
            current_user: dict = Depends(self._require_write_permission)
        ):
            """Create a new trading strategy."""
            strategy_id = f"strategy_{int(datetime.now().timestamp())}"
            
            return StrategyResponse(
                strategy_id=strategy_id,
                name=strategy.name,
                status="created",
                created_at=datetime.now(),
                parameters=strategy.parameters
            )
        
        @self.app.get("/api/v1/strategies")
        async def list_strategies(current_user: dict = Depends(self._get_current_user)):
            """List all available strategies."""
            # Mock implementation
            return [
                {
                    "strategy_id": "strategy_1",
                    "name": "Mean Reversion",
                    "status": "active",
                    "created_at": "2024-01-15T09:00:00Z",
                    "performance": {
                        "total_return": 8.5,
                        "sharpe_ratio": 1.2,
                        "max_drawdown": -3.2
                    }
                }
            ]
        
        @self.app.post("/api/v1/strategies/{strategy_id}/start")
        async def start_strategy(
            strategy_id: str,
            current_user: dict = Depends(self._require_write_permission)
        ):
            """Start a trading strategy."""
            return {"message": f"Strategy {strategy_id} started", "status": "running"}
        
        @self.app.post("/api/v1/strategies/{strategy_id}/stop")
        async def stop_strategy(
            strategy_id: str,
            current_user: dict = Depends(self._require_write_permission)
        ):
            """Stop a trading strategy."""
            return {"message": f"Strategy {strategy_id} stopped", "status": "stopped"}
        
        # Backtesting
        @self.app.post("/api/v1/backtest", response_model=BacktestResponse)
        async def run_backtest(
            backtest: BacktestRequest,
            current_user: dict = Depends(self._get_current_user)
        ):
            """Run a strategy backtest."""
            backtest_id = f"backtest_{int(datetime.now().timestamp())}"
            
            # Mock backtest results
            return BacktestResponse(
                backtest_id=backtest_id,
                status="completed",
                total_return=12.5,
                sharpe_ratio=1.4,
                max_drawdown=-5.2,
                total_trades=156,
                win_rate=58.3,
                results_url=f"/api/v1/backtest/{backtest_id}/results"
            )
        
        @self.app.get("/api/v1/backtest/{backtest_id}")
        async def get_backtest_results(
            backtest_id: str,
            current_user: dict = Depends(self._get_current_user)
        ):
            """Get backtest results."""
            # Mock detailed results
            return {
                "backtest_id": backtest_id,
                "status": "completed",
                "strategy_name": "Mean Reversion",
                "period": {
                    "start_date": "2023-01-01",
                    "end_date": "2023-12-31"
                },
                "performance": {
                    "total_return": 12.5,
                    "annual_return": 12.8,
                    "sharpe_ratio": 1.4,
                    "sortino_ratio": 1.8,
                    "max_drawdown": -5.2,
                    "volatility": 9.1,
                    "beta": 0.85,
                    "alpha": 4.2
                },
                "trades": {
                    "total_trades": 156,
                    "winning_trades": 91,
                    "losing_trades": 65,
                    "win_rate": 58.3,
                    "avg_win": 1.8,
                    "avg_loss": -1.2,
                    "profit_factor": 1.37
                },
                "monthly_returns": [
                    {"month": "2023-01", "return": 2.1},
                    {"month": "2023-02", "return": -0.8},
                    # ... more monthly data
                ]
            }
        
        # Market Data
        @self.app.get("/api/v1/market/quote/{symbol}")
        async def get_quote(
            symbol: str,
            current_user: dict = Depends(self._get_current_user)
        ):
            """Get real-time quote for a symbol."""
            # Mock implementation
            import random
            base_price = 150.0
            
            return {
                "symbol": symbol.upper(),
                "price": round(base_price + random.uniform(-5, 5), 2),
                "bid": round(base_price + random.uniform(-5, 5), 2),
                "ask": round(base_price + random.uniform(-5, 5), 2),
                "volume": random.randint(1000000, 10000000),
                "change": round(random.uniform(-3, 3), 2),
                "change_percent": round(random.uniform(-2, 2), 2),
                "timestamp": datetime.now().isoformat()
            }
        
        @self.app.get("/api/v1/market/bars/{symbol}")
        async def get_bars(
            symbol: str,
            timeframe: str = "1D",
            start: Optional[str] = None,
            end: Optional[str] = None,
            limit: int = 100,
            current_user: dict = Depends(self._get_current_user)
        ):
            """Get historical price bars."""
            # Mock implementation
            import random
            bars = []
            base_price = 150.0
            
            for i in range(min(limit, 30)):
                date = datetime.now() - timedelta(days=i)
                bars.append({
                    "timestamp": date.isoformat(),
                    "open": round(base_price + random.uniform(-2, 2), 2),
                    "high": round(base_price + random.uniform(0, 3), 2),
                    "low": round(base_price + random.uniform(-3, 0), 2),
                    "close": round(base_price + random.uniform(-2, 2), 2),
                    "volume": random.randint(1000000, 5000000)
                })
            
            return {
                "symbol": symbol.upper(),
                "timeframe": timeframe,
                "bars": bars[::-1]  # Reverse to get chronological order
            }
        
        # Alerts
        @self.app.get("/api/v1/alerts")
        async def get_alerts(
            level: Optional[str] = None,
            active_only: bool = True,
            current_user: dict = Depends(self._get_current_user)
        ):
            """Get system alerts."""
            alerts = monitoring_system.alerts
            
            if active_only:
                alerts = [a for a in alerts if not a.resolved]
            
            if level:
                from monitoring.system import AlertLevel
                try:
                    alert_level = AlertLevel(level.lower())
                    alerts = [a for a in alerts if a.level == alert_level]
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid alert level: {level}")
            
            # Convert to dict format
            alerts_data = []
            for alert in alerts:
                alerts_data.append({
                    'id': alert.id,
                    'timestamp': alert.timestamp.isoformat(),
                    'level': alert.level.value,
                    'type': alert.type.value,
                    'title': alert.title,
                    'message': alert.message,
                    'component': alert.component,
                    'resolved': alert.resolved,
                    'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
                    'metadata': alert.metadata
                })
            
            return {"alerts": alerts_data}
        
        # Health check
        @self.app.get("/health")
        async def health_check():
            """API health check."""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0"
            }
    
    def _authenticate_user(self, username: str, password: str):
        """Authenticate user credentials."""
        user = self.users_db.get(username)
        if not user:
            return False
        if not pwd_context.verify(password, user["hashed_password"]):
            return False
        return user
    
    def _create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """Create JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    async def _get_current_user(self, credentials: HTTPAuthorizationCredentials = Security(security)):
        """Get current authenticated user."""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            permissions: List[str] = payload.get("permissions", [])
            if username is None:
                raise credentials_exception
        except jwt.PyJWTError:
            raise credentials_exception
        
        user = self.users_db.get(username)
        if user is None:
            raise credentials_exception
        
        return {"username": username, "permissions": permissions}
    
    async def _require_write_permission(self, current_user: dict = Depends(_get_current_user)):
        """Require write permission."""
        if "write" not in current_user["permissions"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    
    async def _require_admin_permission(self, current_user: dict = Depends(_get_current_user)):
        """Require admin permission."""
        if "admin" not in current_user["permissions"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required"
            )
        return current_user


# Global API instance
trading_api = TradingAPI()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(trading_api.app, host="0.0.0.0", port=8000)
