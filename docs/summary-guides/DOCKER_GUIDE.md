# 🐳 Docker Deployment Guide

This guide explains how to run the entire Algorithmic Trading Platform using Docker containers.

## 🚀 Quick Start

### Prerequisites
- Docker Desktop installed and running
- At least 4GB RAM available for containers
- Alpaca Trading account (for API keys)

### 1. Setup Environment

```bash
# Clone the repository
git clone <repository-url>
cd algorithmic-trader

# Copy environment template
cp .env.docker.template .env.docker

# Edit the environment file with your API keys
nano .env.docker
```

### 2. Start the Platform

Choose one of these methods:

#### Method 1: Using Docker Setup Script (Recommended)
```bash
# Make the script executable
chmod +x ./docker-setup.sh

# Complete setup and start all services
./docker-setup.sh setup

# Or just start if already built
./docker-setup.sh start
```

#### Method 2: Using Makefile
```bash
# Complete Docker setup
make docker-setup

# Or individual steps
make docker-build
make docker-start
make docker-status
```

#### Method 3: Using Docker Compose Directly
```bash
# Build and start all services
docker-compose --env-file .env.docker up --build -d

# Check status
docker-compose ps
```

### 3. Access the Platform

Once started, you can access:

- **📊 Trading Dashboard**: http://localhost:8501
- **📈 Prometheus Monitoring**: http://localhost:9090
- **📉 Grafana Dashboards**: http://localhost:3000 (admin/admin)
- **🔴 Redis**: localhost:6379
- **🐘 PostgreSQL**: localhost:5432

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Trading Engine  │    │    Dashboard    │    │   PostgreSQL    │
│                 │    │                 │    │                 │
│ • Pipeline      │    │ • Streamlit UI  │    │ • Trade History │
│ • Strategies    │    │ • Monitoring    │    │ • Performance   │
│ • Execution     │    │ • Analytics     │    │ • Metadata      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Redis       │    │   Prometheus    │    │     Grafana     │
│                 │    │                 │    │                 │
│ • Caching       │    │ • Metrics       │    │ • Dashboards    │
│ • Session Data  │    │ • Monitoring    │    │ • Alerting      │
│ • Queue         │    │ • Alerting      │    │ • Visualization │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📦 Container Services

### Core Services

1. **trading-engine**: Main trading application
   - Runs pipeline components (screener, analyzer, strategy, execution)
   - Memory: 1GB, CPU: 0.5 cores
   - Volumes: artifacts, logs, config

2. **dashboard**: Streamlit web interface
   - Real-time monitoring and analytics
   - Memory: 512MB, CPU: 0.25 cores  
   - Port: 8501

3. **postgres**: Database for trade history
   - Stores trades, positions, performance metrics
   - Port: 5432, Volume: postgres-data

4. **redis**: Caching and session storage
   - Cache market data and results
   - Port: 6379, Volume: redis-data

### Specialized Services

5. **pipeline-runner**: Scheduled pipeline execution
   - Runs full trading pipeline
   - Triggered on-demand or scheduled

6. **backtest-runner**: Backtesting engine
   - Historical strategy validation
   - Runs on-demand with custom parameters

### Monitoring Services

7. **prometheus**: Metrics collection
   - System and application metrics
   - Port: 9090

8. **grafana**: Visualization dashboards
   - Performance monitoring
   - Port: 3000, Default: admin/admin

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env.docker`:

```bash
# Trading Configuration
TRADING_MODE=dry_run              # or 'live' for real trading
ENABLE_PAPER_TRADE=true           # Use Alpaca paper trading
MAX_POSITIONS=20                  # Maximum concurrent positions

# API Credentials (REQUIRED)
ALPACA_API_KEY=your_key_here      # Get from Alpaca dashboard
ALPACA_SECRET_KEY=your_secret_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Risk Management
MAX_POSITION_SIZE=0.10            # 10% max per position
MAX_DAILY_LOSS=0.02               # 2% max daily loss
MAX_PORTFOLIO_RISK=0.15           # 15% max portfolio risk
```

### Volume Mounts

The platform uses several volume mounts:

- `./artifacts:/app/artifacts` - Trading results and reports
- `./logs:/app/logs` - Application logs
- `./config:/app/config` - Configuration files
- `postgres-data` - Database storage
- `redis-data` - Cache storage

## 🎯 Common Operations

### Running Trading Operations

```bash
# Run full trading pipeline (dry-run)
./docker-setup.sh pipeline
# OR
make docker-pipeline
# OR
docker-compose --env-file .env.docker run --rm pipeline-runner

# Run backtesting
./docker-setup.sh backtest
# OR
make docker-backtest

# Run individual components
docker-compose exec trading-engine python main.py screener run
docker-compose exec trading-engine python main.py analyzer run
docker-compose exec trading-engine python main.py strategy run
```

### Viewing Logs

```bash
# All service logs
./docker-setup.sh logs
# OR
make docker-logs

# Specific service logs
./docker-setup.sh logs dashboard
# OR
make docker-logs SERVICE=dashboard
# OR
docker-compose logs -f dashboard
```

### Database Operations

```bash
# PostgreSQL shell
make docker-shell SERVICE=postgres
# Then: psql -U trader -d trading

# Redis CLI
docker-compose exec redis redis-cli

# Database backup
docker-compose exec postgres pg_dump -U trader trading > backup.sql

# Database restore
docker-compose exec -T postgres psql -U trader trading < backup.sql
```

### Container Management

```bash
# Check service status
./docker-setup.sh status
# OR
make docker-status

# Restart services
./docker-setup.sh restart
# OR
make docker-restart

# Open shell in trading engine
./docker-setup.sh shell
# OR
make docker-shell

# Resource usage
docker stats
```

## 🛡️ Security Considerations

### API Keys
- Never commit API keys to version control
- Use `.env.docker` for local development
- Use proper secrets management in production
- Start with paper trading (`TRADING_MODE=dry_run`)

### Network Security
- Services communicate over internal Docker network
- Only necessary ports exposed to host
- Consider using Docker secrets in production

### Data Protection
- Database passwords should be changed in production
- Regular backups of trading data
- Encrypted storage for sensitive data

## 🚨 Troubleshooting

### Common Issues

#### 1. Services won't start
```bash
# Check Docker daemon
docker info

# Check available resources
docker system df

# View detailed logs
docker-compose logs trading-engine
```

#### 2. Database connection errors
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Test connection
docker-compose exec postgres pg_isready -U trader

# Check logs
docker-compose logs postgres
```

#### 3. API connection errors
```bash
# Verify API keys in environment
docker-compose exec trading-engine env | grep ALPACA

# Test API connection
docker-compose exec trading-engine python -c "
import os
from alpaca_trade_api import REST
api = REST(os.getenv('ALPACA_API_KEY'), os.getenv('ALPACA_SECRET_KEY'), base_url=os.getenv('ALPACA_BASE_URL'))
print(api.get_account())
"
```

#### 4. Dashboard not accessible
```bash
# Check dashboard service
docker-compose ps dashboard

# Check health endpoint
curl http://localhost:8501/_stcore/health

# View dashboard logs
docker-compose logs dashboard
```

### Resource Issues

If you encounter memory or CPU issues:

```bash
# Check resource usage
docker stats

# Adjust resource limits in docker-compose.yml
# Or increase Docker Desktop memory allocation
```

## 📈 Performance Optimization

### Resource Allocation
- Adjust memory limits based on your system
- Use SSD storage for database volumes
- Consider using Docker BuildKit for faster builds

### Database Optimization
- Regular VACUUM and ANALYZE operations
- Proper indexing for query performance
- Connection pooling for high-throughput scenarios

### Caching Strategy
- Redis for market data caching
- Application-level caching for expensive calculations
- Optimize artifact storage and retrieval

## 🔄 Production Deployment

For production deployment:

1. **Environment Configuration**
   - Use proper secrets management
   - Set resource limits appropriately
   - Configure monitoring and alerting

2. **Database Setup**
   - Use managed database services
   - Implement backup strategies
   - Set up read replicas if needed

3. **Monitoring**
   - Configure Prometheus data retention
   - Set up Grafana alerting
   - Implement log aggregation

4. **Security**
   - Use HTTPS for web interfaces
   - Implement proper authentication
   - Regular security updates

See `k8s/` directory for Kubernetes deployment manifests.

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/)
- [Alpaca API Documentation](https://alpaca.markets/docs/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## 🆘 Getting Help

If you encounter issues:

1. Check the troubleshooting section above
2. Review service logs for error messages
3. Verify environment configuration
4. Test individual components
5. Check Docker resources and permissions

For additional support:
- Create GitHub issues for bugs
- Join the community Discord for discussions
- Check the main README.md for general platform information
