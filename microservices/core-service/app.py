"""
Core Service - Base microservice providing shared models and utilities
Port: 8001
Dependencies: None
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List
from datetime import datetime
import logging
import os
import sys

# Import local models
from models import (
    StockData, OrderSide, OrderType, OrderStatus, 
    SignalType, TradeSignal, TimeSegment, CapitalBucket
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Core Service",
    description="Core data models and shared utilities for the trading platform",
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

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "service": "core-service",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.get("/health/ready")
async def readiness_check():
    """Readiness probe for Kubernetes."""
    return {"status": "ready", "timestamp": datetime.now().isoformat()}

@app.get("/health/live")
async def liveness_check():
    """Liveness probe for Kubernetes."""
    return {"status": "alive", "timestamp": datetime.now().isoformat()}

# Model information endpoints
@app.get("/models/enums")
async def get_enums():
    """Get all available enum types."""
    return {
        "signal_types": [e.value for e in SignalType],
        "order_sides": [e.value for e in OrderSide],
        "order_types": [e.value for e in OrderType],
        "order_statuses": [e.value for e in OrderStatus],
        "time_segments": [e.value for e in TimeSegment],
        "capital_buckets": [e.value for e in CapitalBucket]
    }

@app.get("/models/schemas")
async def get_schemas():
    """Get model schemas for validation."""
    return {
        "StockData": StockData.model_json_schema(),
        "TradeSignal": TradeSignal.model_json_schema()
    }

# Configuration endpoints
@app.get("/config/environment")
async def get_environment():
    """Get environment configuration."""
    return {
        "environment": os.getenv("ENVIRONMENT", "development"),
        "service_name": "core-service",
        "port": 8001,
        "debug": os.getenv("DEBUG", "false").lower() == "true"
    }

# Utility endpoints
@app.post("/utils/validate-signal")
async def validate_signal(signal_data: Dict[str, Any]):
    """Validate a trading signal."""
    try:
        signal = TradeSignal(**signal_data)
        return {
            "valid": True,
            "signal": signal.model_dump(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/utils/validate-stock-data")
async def validate_stock_data(stock_data: Dict[str, Any]):
    """Validate stock data."""
    try:
        stock = StockData(**stock_data)
        return {
            "valid": True,
            "stock_data": stock.model_dump(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Service information
@app.get("/info")
async def service_info():
    """Get detailed service information."""
    return {
        "service": "core-service",
        "description": "Core data models and shared utilities",
        "version": "1.0.0",
        "port": 8001,
        "dependencies": [],
        "endpoints": {
            "health": "/health",
            "models": "/models/enums",
            "schemas": "/models/schemas",
            "config": "/config/environment",
            "validation": ["/utils/validate-signal", "/utils/validate-stock-data"]
        },
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
