# 🐳 Docker Demo Guide

This guide walks you through running the complete Advanced Algorithmic Trading Platform using Docker for easy local testing and demonstration.

## 🚀 Quick Start

### Prerequisites
- Docker Desktop installed and running
- Docker Compose v2.0+
- 4GB+ available RAM
- Ports 8080 and 8000 available

### One-Command Demo
```bash
# Clone and start demo
git clone https://github.com/abhikanap/algorithmic-trader.git
cd algorithmic-trader
./demo/start-demo.sh
```

**That's it!** The demo will:
- ✅ Check prerequisites
- ✅ Build Docker containers  
- ✅ Start all services
- ✅ Create sample data
- ✅ Set up authentication
- ✅ Display access URLs

## 🌐 Access Points

Once the demo is running, access these URLs:

| Service | URL | Credentials |
|---------|-----|-------------|
| **🖥️ Web Dashboard** | http://localhost:8080 | Visual interface |
| **🔌 API Server** | http://localhost:8000 | See auth section |
| **📚 API Documentation** | http://localhost:8000/docs | Interactive docs |
| **❤️ Health Check** | http://localhost:8000/health | Status endpoint |

## 🔐 Authentication

The demo includes three pre-configured users:

```bash
# Admin User (Full Access)
Username: admin
Password: admin123
Permissions: read, write, admin

# Trader User (Trading Access)  
Username: trader
Password: trader123
Permissions: read, write

# Viewer User (Read-Only)
Username: viewer  
Password: viewer123
Permissions: read
```

### Getting API Token
```bash
# Get authentication token
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Use token in API calls
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/system/status"
```

## 🧪 Demo Test Scripts

The demo includes comprehensive test scripts:

### 1. Complete API Test Suite
```bash
./demo/test-api.sh
```
- Tests all API endpoints
- Validates authentication
- Checks error handling
- Generates test report

### 2. Performance Analytics Demo
```bash
./demo/test-analytics.sh
```
- Generates 4 sample strategies
- Creates performance reports
- Builds comparison charts
- Exports HTML/JSON reports

### 3. Portfolio Management Demo
```bash
./demo/test-portfolio.sh
```
- Shows portfolio positions
- Demonstrates order management
- Displays risk analysis
- Portfolio allocation breakdown

## 📊 Sample Data Generated

The demo automatically creates:

### Performance Reports (4 Strategies)
- **Conservative Strategy**: 8% return, 12% volatility
- **Aggressive Growth**: 18% return, 25% volatility  
- **Market Neutral**: 5% return, 8% volatility
- **Momentum Strategy**: 15% return, 20% volatility

### Chart Types (Per Strategy)
1. Cumulative returns vs benchmark
2. Drawdown timeline
3. Rolling Sharpe ratio (1-year)
4. Daily returns distribution  
5. Monthly returns heatmap

### Mock Trading Data
- Portfolio positions (5 stocks + cash)
- Order history with various types
- System metrics (CPU, memory, trading stats)
- Alert examples with different severity levels

## 🛠️ Demo Management

### Start/Stop Commands
```bash
# Start demo
./demo/start-demo.sh

# Stop demo  
./demo/stop-demo.sh

# Restart demo
./demo/start-demo.sh restart

# View logs
./demo/start-demo.sh logs

# Check status
./demo/start-demo.sh status

# Complete cleanup
./demo/start-demo.sh clean
```

### Docker Commands
```bash
# View running containers
docker-compose -f demo-docker-compose.yml ps

# Follow logs
docker-compose -f demo-docker-compose.yml logs -f

# Restart specific service
docker-compose -f demo-docker-compose.yml restart trading-platform-demo

# Access container shell
docker exec -it trading-platform-demo /bin/bash
```

## 📁 Demo File Structure

```
demo/
├── start-demo.sh           # Main demo launcher
├── stop-demo.sh            # Demo shutdown script
├── test-api.sh             # API test suite
├── test-analytics.sh       # Analytics demo
├── test-portfolio.sh       # Portfolio demo
└── data/                   # Generated demo data
    ├── demo-config.json    # Demo configuration
    ├── sample_prices.csv   # Mock market data
    ├── demo-token.txt      # Authentication token
    ├── system-status.json  # System status snapshot
    └── api-test-results.json # API test results
```

## 🎯 Demo Scenarios

### Scenario 1: System Monitoring
```bash
# Start monitoring dashboard
open http://localhost:8080

# Check system health
curl "http://localhost:8000/health"

# View system metrics
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/system/status"
```

### Scenario 2: Trading Operations
```bash
# View portfolio
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/portfolio/positions"

# Submit order
curl -X POST "http://localhost:8000/api/v1/orders" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", "side": "buy", "quantity": 10, "order_type": "market"}'

# Check order status
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/orders"
```

### Scenario 3: Strategy Management
```bash
# List strategies
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/strategies"

# Create new strategy
curl -X POST "http://localhost:8000/api/v1/strategies" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Demo_Strategy",
    "parameters": {"lookback": 20, "threshold": 2.0},
    "symbols": ["AAPL", "GOOGL"]
  }'

# Run backtest
curl -X POST "http://localhost:8000/api/v1/backtest" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "mean_reversion",
    "symbols": ["AAPL"],
    "start_date": "2023-01-01",
    "end_date": "2023-12-31"
  }'
```

## 🔍 Troubleshooting

### Common Issues

**Port Already in Use**
```bash
# Check what's using the ports
lsof -i :8080
lsof -i :8000

# Kill processes if needed
sudo kill -9 $(lsof -t -i:8080)
sudo kill -9 $(lsof -t -i:8000)
```

**Docker Issues**
```bash
# Restart Docker daemon
# On macOS: Docker Desktop -> Restart
# On Linux: sudo systemctl restart docker

# Clean Docker system
docker system prune -a
docker volume prune
```

**API Not Responding**
```bash
# Check container health
docker-compose -f demo-docker-compose.yml ps

# View container logs
docker-compose -f demo-docker-compose.yml logs trading-platform-demo

# Restart containers
docker-compose -f demo-docker-compose.yml restart
```

**Authentication Errors**
```bash
# Get fresh token
./demo/test-api.sh auth

# Check token file
cat demo/data/demo-token.txt

# Manual token generation
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

### Performance Optimization

**Increase Memory Limits**
```yaml
# In demo-docker-compose.yml
services:
  trading-platform-demo:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

**Enable Debug Logging**
```bash
# Set environment variable
docker-compose -f demo-docker-compose.yml exec trading-platform-demo \
  sh -c 'export LOG_LEVEL=DEBUG && python launch_advanced.py'
```

## 📈 Expected Demo Results

### System Status Response
```json
{
  "health_status": "HEALTHY",
  "system_metrics": {
    "cpu_usage": 15.2,
    "memory_usage": 45.8,
    "disk_usage": 32.1
  },
  "trading_metrics": {
    "active_positions": 12,
    "daily_pnl": 1250.50,
    "total_trades": 28,
    "error_rate": 0.5
  },
  "alerts": {
    "total_active": 0
  }
}
```

### Sample Portfolio Response
```json
[
  {
    "symbol": "AAPL",
    "quantity": 100,
    "market_value": 15000.0,
    "unrealized_pnl": 500.0,
    "avg_entry_price": 145.0,
    "current_price": 150.0
  }
]
```

### Analytics Report Metrics
- **Total Return**: 12.5%
- **Sharpe Ratio**: 1.42
- **Max Drawdown**: -5.3%
- **Win Rate**: 58.7%

## 📚 Next Steps

After running the demo:

1. **Explore the Web Dashboard** - Real-time monitoring interface
2. **Review Generated Reports** - Professional analytics in `reports/` folder
3. **Test API Endpoints** - Use the interactive docs at `/docs`
4. **Customize Configuration** - Modify parameters in demo files
5. **Deploy to Production** - Use `./deploy-advanced.sh production`

## 🆘 Support

- 📖 **Documentation**: [README.md](../README.md)
- 🐛 **Issues**: Check container logs first
- 💬 **Questions**: Review API documentation at `/docs`
- 🔧 **Configuration**: Modify `demo-docker-compose.yml`

---

🎉 **Enjoy exploring the Advanced Algorithmic Trading Platform!** 🚀
