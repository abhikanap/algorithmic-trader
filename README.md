# 🚀 Advanced Algorithmic Trading Platform

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)]()

A comprehensive, production-ready algorithmic trading platform with advanced monitoring, web dashboard, RESTful API, and analytics capabilities.

## 🌟 Key Features

### 🎯 Core Trading Platform
- **Multi-Strategy Engine**: Mean reversion, momentum, breakout strategies
- **Real-Time Execution**: Alpaca broker integration with live trading
- **Advanced Risk Management**: Position limits, stop-loss, volatility controls  
- **Comprehensive Backtesting**: Historical strategy validation with detailed analytics
- **Data Pipeline**: Real-time and historical market data processing

### 🖥️ Advanced Web Interface
- **Real-Time Dashboard**: Live system monitoring with interactive charts
- **Alert Management**: Intelligent alerting with multiple severity levels
- **Performance Analytics**: Professional reports with risk metrics
- **Responsive Design**: Desktop and mobile-friendly interface

### 🔌 RESTful API
- **JWT Authentication**: Role-based access control (admin/trader/viewer)
- **Trading Operations**: Portfolio management, order execution, strategy control
- **Market Data**: Real-time quotes and historical data access
- **Backtesting API**: Programmatic strategy testing and results

### 📊 Advanced Analytics
- **Performance Metrics**: Sharpe ratio, Sortino ratio, VaR, CVaR
- **Risk Analysis**: Maximum drawdown, volatility analysis
- **Benchmark Comparison**: Alpha/beta calculations vs market indices
- **Professional Reports**: HTML/JSON export with comprehensive charts

### 🐳 Production Ready
- **Docker Integration**: Complete containerization with multi-environment support
- **Monitoring System**: Real-time system health and trading metrics
- **Scalable Architecture**: Modular design for easy extension
- **Security**: Authentication, authorization, and secure API endpoints

## 🚀 Quick Start

### Option 1: Docker Demo (Recommended)
```bash
# Clone repository
git clone https://github.com/abhikanap/algorithmic-trader.git
cd algorithmic-trader

# Start demo environment
./demo/start-demo.sh

# Access services
# Web Dashboard: http://localhost:8080
# API Documentation: http://localhost:8000/docs
```

### Option 2: Local Development
```bash
# Clone and setup
git clone https://github.com/abhikanap/algorithmic-trader.git
cd algorithmic-trader

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start platform
./launch_advanced.py
```

## 🌐 Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **Web Dashboard** | http://localhost:8080 | Real-time monitoring interface |
| **API Server** | http://localhost:8000 | RESTful API endpoints |
| **API Documentation** | http://localhost:8000/docs | Interactive API documentation |
| **Health Check** | http://localhost:8000/health | Service health status |

## 🔐 Authentication

The platform uses JWT-based authentication with three default user roles:

| Username | Password | Permissions | Description |
|----------|----------|-------------|-------------|
| `admin` | `admin123` | read, write, admin | Full platform access |
| `trader` | `trader123` | read, write | Trading operations |
| `viewer` | `viewer123` | read | Read-only access |

### API Authentication Example
```bash
# Get access token
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Use token in requests
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/system/status"
```

## 📊 Platform Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Dashboard │    │   API Server    │    │  Analytics      │
│   (Port 8080)   │    │   (Port 8000)   │    │  Engine         │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                     │                      │
          └──────────┬──────────┴──────────────────────┘
                     │
          ┌─────────────────┐
          │  Monitoring     │
          │  System         │
          │  (Background)   │
          └─────────┬───────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
┌───▼────┐    ┌────▼────┐    ┌────▼────┐
│Strategy │    │Execution│    │   Data  │
│Engine   │    │Engine   │    │Pipeline │
└────────┘    └─────────┘    └─────────┘
```

## 🎮 Demo Scenarios

### 1. System Monitoring Demo
```bash
# Start monitoring only
./launch_advanced.py --monitoring-only

# View real-time metrics
curl "http://localhost:8000/api/v1/system/status"
```

### 2. Trading API Demo
```bash
# Run complete API test suite
./demo/test-api.sh

# Test specific endpoints
./demo/test-portfolio.sh
./demo/test-orders.sh
```

### 3. Performance Analytics Demo
```bash
# Generate sample performance reports
python -c "
from analytics.performance import performance_analyzer, generate_mock_returns
import pandas as pd

# Generate mock strategy returns
returns = generate_mock_returns(days=252, annual_return=0.15, volatility=0.20)
benchmark = generate_mock_returns(days=252, annual_return=0.10, volatility=0.15)

# Analyze performance
analysis = performance_analyzer.analyze_strategy_performance(returns, benchmark, 'Demo_Strategy')

# Generate reports
html_report = performance_analyzer.generate_performance_report(analysis, 'html')
charts = performance_analyzer.create_performance_charts(returns, benchmark, 'Demo_Strategy')

print(f'Report: {html_report}')
print(f'Charts: {len(charts)} generated')
"
```

## 📈 Sample Performance Metrics

| Metric | Value | Description |
|--------|-------|-------------|
| **Total Return** | 15.2% | Cumulative strategy return |
| **Annual Return** | 12.8% | Annualized return rate |
| **Sharpe Ratio** | 1.42 | Risk-adjusted return |
| **Sortino Ratio** | 1.89 | Downside risk-adjusted return |
| **Max Drawdown** | -5.3% | Largest peak-to-trough decline |
| **Win Rate** | 58.7% | Percentage of profitable periods |
| **VaR (95%)** | -1.8% | Value at Risk (95% confidence) |

## 🛠️ Configuration

### Environment Variables
```bash
# Security
export SECRET_KEY="your-secret-key-here"
export JWT_EXPIRATION=3600

# Database (optional)
export DATABASE_URL="postgresql://user:pass@localhost/trading"

# Broker Integration
export ALPACA_API_KEY="your-alpaca-key"
export ALPACA_SECRET_KEY="your-alpaca-secret"
export ALPACA_BASE_URL="https://paper-api.alpaca.markets"

# Monitoring
export MONITORING_INTERVAL=30
export ALERT_EMAIL_HOST="smtp.gmail.com"
export ALERT_EMAIL_PORT=587
```

### Service Configuration
```bash
# Custom ports
./launch_advanced.py --dashboard-port 9090 --api-port 9000

# Selective services
./launch_advanced.py --no-dashboard --no-analytics

# Production mode
./launch_advanced.py --no-sample-reports
```

## 🐳 Docker Deployment

### Development Environment
```bash
# Build and start
docker-compose up --build

# Background mode
docker-compose up -d

# View logs
docker-compose logs -f trading-platform
```

### Production Deployment
```bash
# Deploy to production
./deploy-advanced.sh production

# Deploy to staging
./deploy-advanced.sh staging

# Check deployment status
./deploy-advanced.sh status
```

## 📁 Project Structure

```
algorithmic-trader/
├── 📁 packages/              # Core trading modules
├── 📁 apps/                  # Application interfaces
├── 📁 monitoring/            # System monitoring
├── 📁 api/                   # RESTful API
├── 📁 analytics/             # Performance analytics
├── 📁 demo/                  # Demo scripts and data
├── 📁 tests/                 # Test suites
├── 📁 docs/                  # Documentation
├── 📁 reports/               # Generated reports
├── 🐳 Dockerfile             # Container configuration
├── 🐳 docker-compose.yml     # Service orchestration
├── 🚀 launch_advanced.py     # Platform launcher
├── 🚀 deploy-advanced.sh     # Deployment script
└── 📋 requirements.txt       # Python dependencies
```

## 🧪 Testing

### Run All Tests
```bash
# Unit tests
pytest tests/ -v

# Integration tests
pytest tests/integration/ -v

# API tests
pytest tests/api/ -v

# Coverage report
pytest --cov=packages --cov-report=html
```

### Manual Testing
```bash
# Test monitoring system
python -m monitoring.system

# Test performance analytics
python -m analytics.performance

# Test API endpoints
./demo/test-api.sh
```

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [PHASE_7_ADVANCED_FEATURES.md](docs/phase-updates/PHASE_7_ADVANCED_FEATURES.md) | Phase 7 implementation details |
| [API Documentation](http://localhost:8000/docs) | Interactive API reference (when server is running) |
| [Docker Guide](docs/summary-guides/DOCKER_GUIDE.md) | Docker deployment guide |
| [Testing & Debugging Guide](docs/summary-guides/TESTING_DEBUGGING_GUIDE.md) | Common issues and solutions |

### Additional Documentation

| Document | Category | Description |
|----------|----------|-------------|
| [Project Summary](docs/summary-guides/PROJECT_SUMMARY.md) | Overview | Complete project overview and architecture |
| [Microservices Architecture](docs/summary-guides/MICROSERVICES_ARCHITECTURE.md) | Architecture | Detailed microservices design |
| [Demo Summary](docs/summary-guides/DEMO_SUMMARY.md) | Usage | Demo scenarios and examples |
| [Deployment Complete](docs/phase-updates/DEPLOYMENT_COMPLETE.md) | Deployment | Production deployment status |
| [Project Status](docs/phase-updates/PROJECT_STATUS.md) | Status | Current project status and roadmap |
| [Trading Strategies](docs/strategy/) | Strategy | Strategy documentation and patterns |

## 🚀 Advanced Usage

### Custom Strategy Development
```python
from packages.strategy.base import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    def generate_signals(self, data):
        # Your strategy logic here
        return signals
    
    def calculate_position_size(self, signal, portfolio):
        # Your position sizing logic
        return size
```

### API Integration Example
```python
import requests

# Authenticate
response = requests.post("http://localhost:8000/auth/login", 
                        json={"username": "admin", "password": "admin123"})
token = response.json()["access_token"]

# Get portfolio positions
headers = {"Authorization": f"Bearer {token}"}
positions = requests.get("http://localhost:8000/api/v1/portfolio/positions", 
                        headers=headers)
```

### Custom Monitoring Alerts
```python
from monitoring.system import monitoring_system

async def custom_alert_handler(alert):
    # Send to Slack, email, or custom notification system
    await send_notification(alert.title, alert.message)

monitoring_system.add_alert_handler(custom_alert_handler)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Alpaca Markets** for trading API
- **FastAPI** for high-performance API framework
- **Chart.js** for interactive visualizations
- **Docker** for containerization support

## 🆘 Support

- 📧 Email: [abhishek.data.unicorn@gmail.com](mailto:abhishek.data.unicorn@gmail.com)
- 📚 Documentation: [docs/](docs/)
- 🐛 Issues: [GitHub Issues](https://github.com/abhikanap/algorithmic-trader/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/abhikanap/algorithmic-trader/discussions)

---

⭐ **Star this repository if you find it helpful!** ⭐
