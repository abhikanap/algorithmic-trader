"""
Market Data Service - Real-time and historical market data
Port: 8002
Dependencies: Core Service
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import asyncio
import aiohttp
import json
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Market Data Service",
    description="Real-time and historical market data provider",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache for demo
price_cache: Dict[str, Dict[str, Any]] = {}
historical_cache: Dict[str, List[Dict[str, Any]]] = {}

# Mock data generator
def generate_mock_price_data(symbol: str) -> Dict[str, Any]:
    """Generate realistic mock price data."""
    base_prices = {
        "AAPL": 150.0,
        "GOOGL": 2500.0,
        "MSFT": 300.0,
        "TSLA": 200.0,
        "AMZN": 3000.0,
        "NVDA": 400.0,
        "META": 250.0,
        "SPY": 420.0
    }
    
    base_price = base_prices.get(symbol, 100.0)
    current_price = base_price * (1 + random.uniform(-0.05, 0.05))
    
    return {
        "symbol": symbol,
        "price": round(current_price, 2),
        "open": round(current_price * 0.99, 2),
        "high": round(current_price * 1.02, 2),
        "low": round(current_price * 0.97, 2),
        "close": round(current_price, 2),
        "volume": random.randint(1000000, 10000000),
        "timestamp": datetime.now().isoformat(),
        "change": round(random.uniform(-5.0, 5.0), 2),
        "change_percent": round(random.uniform(-3.0, 3.0), 2)
    }

def generate_historical_data(symbol: str, days: int = 30) -> List[Dict[str, Any]]:
    """Generate mock historical data."""
    data = []
    base_price = 100.0
    
    for i in range(days):
        date = datetime.now() - timedelta(days=days-i)
        price_change = random.uniform(-0.03, 0.03)
        base_price *= (1 + price_change)
        
        data.append({
            "symbol": symbol,
            "date": date.strftime("%Y-%m-%d"),
            "open": round(base_price * 0.99, 2),
            "high": round(base_price * 1.02, 2),
            "low": round(base_price * 0.98, 2),
            "close": round(base_price, 2),
            "volume": random.randint(1000000, 5000000),
            "timestamp": date.isoformat()
        })
    
    return data

# Health check endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "service": "market-service",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "cache_size": len(price_cache)
    }

@app.get("/health/ready")
async def readiness_check():
    """Readiness probe."""
    return {"status": "ready", "timestamp": datetime.now().isoformat()}

@app.get("/health/live")
async def liveness_check():
    """Liveness probe."""
    return {"status": "alive", "timestamp": datetime.now().isoformat()}

# Market data endpoints
@app.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """Get current quote for a symbol."""
    try:
        # Check cache first
        if symbol in price_cache:
            cached_data = price_cache[symbol]
            # Use cache if less than 30 seconds old
            if (datetime.now() - datetime.fromisoformat(cached_data["timestamp"])).seconds < 30:
                return cached_data
        
        # Generate new data (in production, this would fetch from real API)
        quote_data = generate_mock_price_data(symbol)
        price_cache[symbol] = quote_data
        
        logger.info(f"Generated quote for {symbol}: ${quote_data['price']}")
        return quote_data
        
    except Exception as e:
        logger.error(f"Error getting quote for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get quote for {symbol}")

@app.get("/quotes")
async def get_multiple_quotes(symbols: str):
    """Get quotes for multiple symbols (comma-separated)."""
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        quotes = {}
        
        for symbol in symbol_list:
            quotes[symbol] = await get_quote(symbol)
        
        return {
            "quotes": quotes,
            "timestamp": datetime.now().isoformat(),
            "count": len(quotes)
        }
        
    except Exception as e:
        logger.error(f"Error getting multiple quotes: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get quotes")

@app.get("/historical/{symbol}")
async def get_historical_data(symbol: str, days: int = 30):
    """Get historical data for a symbol."""
    try:
        cache_key = f"{symbol}_{days}"
        
        # Check cache
        if cache_key in historical_cache:
            return {
                "symbol": symbol,
                "data": historical_cache[cache_key],
                "days": days,
                "cached": True,
                "timestamp": datetime.now().isoformat()
            }
        
        # Generate historical data
        historical_data = generate_historical_data(symbol, days)
        historical_cache[cache_key] = historical_data
        
        logger.info(f"Generated {days} days of historical data for {symbol}")
        
        return {
            "symbol": symbol,
            "data": historical_data,
            "days": days,
            "cached": False,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting historical data for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get historical data for {symbol}")

@app.get("/search")
async def search_symbols(query: str):
    """Search for symbols matching query."""
    mock_symbols = [
        {"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ"},
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "exchange": "NASDAQ"},
        {"symbol": "MSFT", "name": "Microsoft Corporation", "exchange": "NASDAQ"},
        {"symbol": "TSLA", "name": "Tesla, Inc.", "exchange": "NASDAQ"},
        {"symbol": "AMZN", "name": "Amazon.com, Inc.", "exchange": "NASDAQ"},
        {"symbol": "NVDA", "name": "NVIDIA Corporation", "exchange": "NASDAQ"},
        {"symbol": "META", "name": "Meta Platforms, Inc.", "exchange": "NASDAQ"},
        {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust", "exchange": "NYSE"}
    ]
    
    # Filter symbols matching query
    results = [
        sym for sym in mock_symbols 
        if query.upper() in sym["symbol"] or query.upper() in sym["name"].upper()
    ]
    
    return {
        "query": query,
        "results": results,
        "count": len(results),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/watchlist")
async def get_watchlist():
    """Get default watchlist with current prices."""
    watchlist_symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
    quotes = {}
    
    for symbol in watchlist_symbols:
        quotes[symbol] = generate_mock_price_data(symbol)
    
    return {
        "watchlist": quotes,
        "timestamp": datetime.now().isoformat(),
        "count": len(quotes)
    }

@app.post("/cache/clear")
async def clear_cache():
    """Clear price cache."""
    global price_cache, historical_cache
    cache_size = len(price_cache) + len(historical_cache)
    price_cache.clear()
    historical_cache.clear()
    
    return {
        "message": "Cache cleared",
        "previous_size": cache_size,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/stats")
async def get_service_stats():
    """Get service statistics."""
    return {
        "service": "market-service",
        "cache_stats": {
            "price_cache_size": len(price_cache),
            "historical_cache_size": len(historical_cache),
            "total_symbols_cached": len(set(list(price_cache.keys()) + [k.split('_')[0] for k in historical_cache.keys()]))
        },
        "timestamp": datetime.now().isoformat()
    }

# Service information
@app.get("/info")
async def service_info():
    """Get detailed service information."""
    return {
        "service": "market-service",
        "description": "Real-time and historical market data provider",
        "version": "1.0.0",
        "port": 8002,
        "dependencies": ["core-service"],
        "endpoints": {
            "health": "/health",
            "quote": "/quote/{symbol}",
            "quotes": "/quotes?symbols=AAPL,GOOGL",
            "historical": "/historical/{symbol}?days=30",
            "search": "/search?query=AAPL",
            "watchlist": "/watchlist",
            "stats": "/stats"
        },
        "features": [
            "Real-time price quotes",
            "Historical data",
            "Symbol search",
            "Price caching",
            "Watchlist management"
        ],
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )
