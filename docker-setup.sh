#!/bin/bash

# Algorithmic Trading Platform - Docker Setup Script
# This script sets up and runs the entire trading platform in Docker containers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env.docker"

echo -e "${BLUE}🐳 Algorithmic Trading Platform - Docker Setup${NC}"
echo "=================================================="

# Function to print status
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    print_status "Prerequisites check passed ✅"
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    # Create directories if they don't exist
    mkdir -p artifacts/{screener,analyzer,strategy,execution,backtest}
    mkdir -p logs
    mkdir -p config
    
    # Ensure proper permissions
    chmod 755 artifacts logs config
    
    print_status "Directories created ✅"
}

# Setup environment configuration
setup_environment() {
    print_status "Setting up environment configuration..."
    
    # Create .env.docker file if it doesn't exist
    if [[ ! -f "$ENV_FILE" ]]; then
        cat > "$ENV_FILE" << 'EOF'
# Docker Environment Configuration for Algorithmic Trading Platform

# Trading Configuration
TRADING_MODE=dry_run
ENABLE_PAPER_TRADE=true
MAX_POSITIONS=20
DEFAULT_STOP_LOSS=0.05
DEFAULT_TAKE_PROFIT=0.10

# Risk Management
MAX_POSITION_SIZE=0.10
MAX_DAILY_LOSS=0.02
MAX_PORTFOLIO_RISK=0.15

# Alpaca API (replace with your actual keys)
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Database Configuration
POSTGRES_DB=trading
POSTGRES_USER=trader
POSTGRES_PASSWORD=trading123
REDIS_URL=redis://redis:6379/0

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Monitoring
ENABLE_METRICS=true
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000

# Dashboard
DASHBOARD_PORT=8501
DASHBOARD_HOST=0.0.0.0
EOF
        print_status "Created environment file: $ENV_FILE"
        print_warning "Please edit $ENV_FILE and add your Alpaca API keys for live trading"
    else
        print_status "Environment file already exists: $ENV_FILE"
    fi
}

# Create default configuration
setup_config() {
    print_status "Setting up configuration files..."
    
    # Create default config if it doesn't exist
    if [[ ! -f "config/config.yaml" ]]; then
        cat > "config/config.yaml" << 'EOF'
# Algorithmic Trading Platform Configuration

# Trading settings
trading:
  dry_run: true
  enable_paper_trade: true
  max_positions: 20
  default_stop_loss: 0.05
  default_take_profit: 0.10
  position_sizing_method: "volatility_adjusted"

# Risk management
risk:
  max_position_size: 0.10
  max_daily_loss: 0.02
  max_portfolio_risk: 0.15
  volatility_lookback_days: 20
  correlation_threshold: 0.7

# Data sources
data:
  primary_source: "yfinance"
  cache_duration_minutes: 15
  retry_attempts: 3
  timeout_seconds: 30

# Screening criteria
screener:
  min_volume: 1000000
  min_price: 5.0
  max_price: 500.0
  min_market_cap: 1000000000
  exclude_sectors: ["Utilities", "Real Estate"]

# Strategy parameters
strategy:
  momentum_lookback: 20
  rsi_period: 14
  rsi_oversold: 30
  rsi_overbought: 70
  bollinger_period: 20
  bollinger_std: 2

# Execution settings
execution:
  order_timeout_minutes: 5
  max_slippage_percent: 0.5
  commission_per_share: 0.005
  fill_rate_threshold: 0.95

# Backtesting
backtest:
  initial_capital: 100000
  commission_per_trade: 5.0
  slippage_basis_points: 5
  benchmark_symbol: "SPY"

# Logging
logging:
  level: "INFO"
  format: "structured"
  file_rotation: "daily"
  max_file_size_mb: 100

# Artifacts
artifacts:
  save_enabled: true
  compression: true
  retention_days: 30
EOF
        print_status "Created default configuration: config/config.yaml"
    else
        print_status "Configuration file already exists: config/config.yaml"
    fi
}

# Build Docker images
build_images() {
    print_status "Building Docker images..."
    
    # Build images with docker-compose
    if command -v docker-compose &> /dev/null; then
        docker-compose build --no-cache
    else
        docker compose build --no-cache
    fi
    
    print_status "Docker images built successfully ✅"
}

# Start services
start_services() {
    print_status "Starting services..."
    
    # Start all services
    if command -v docker-compose &> /dev/null; then
        docker-compose --env-file "$ENV_FILE" up -d
    else
        docker compose --env-file "$ENV_FILE" up -d
    fi
    
    print_status "Services started successfully ✅"
}

# Wait for services to be healthy
wait_for_services() {
    print_status "Waiting for services to be healthy..."
    
    # Wait for dashboard to be ready
    print_status "Waiting for dashboard to be ready..."
    timeout=60
    counter=0
    
    while [ $counter -lt $timeout ]; do
        if curl -s http://localhost:8501/_stcore/health > /dev/null 2>&1; then
            break
        fi
        sleep 2
        counter=$((counter + 2))
        echo -n "."
    done
    
    if [ $counter -ge $timeout ]; then
        print_warning "Dashboard health check timed out, but container may still be starting"
    else
        print_status "Dashboard is ready ✅"
    fi
    
    # Wait for other services
    sleep 5
    print_status "All services should now be ready ✅"
}

# Show service status
show_status() {
    print_status "Service Status:"
    echo ""
    
    if command -v docker-compose &> /dev/null; then
        docker-compose ps
    else
        docker compose ps
    fi
    
    echo ""
    print_status "Access URLs:"
    echo "  📊 Trading Dashboard: http://localhost:8501"
    echo "  📈 Prometheus: http://localhost:9090"
    echo "  📉 Grafana: http://localhost:3000 (admin/admin)"
    echo "  🔴 Redis: localhost:6379"
    echo "  🐘 PostgreSQL: localhost:5432"
    
    echo ""
    print_status "Useful Commands:"
    echo "  View logs: docker-compose logs -f [service-name]"
    echo "  Stop services: docker-compose down"
    echo "  Restart services: docker-compose restart"
    echo "  Shell into container: docker-compose exec trading-engine bash"
}

# Run trading pipeline
run_pipeline() {
    print_status "Running trading pipeline..."
    
    if command -v docker-compose &> /dev/null; then
        docker-compose exec trading-engine python main.py pipeline --dry-run --verbose
    else
        docker compose exec trading-engine python main.py pipeline --dry-run --verbose
    fi
}

# Run backtest
run_backtest() {
    print_status "Running sample backtest..."
    
    if command -v docker-compose &> /dev/null; then
        docker-compose exec trading-engine python main.py backtest run \
            --start-date 2024-01-01 \
            --end-date 2024-03-31 \
            --capital 100000 \
            --verbose
    else
        docker compose exec trading-engine python main.py backtest run \
            --start-date 2024-01-01 \
            --end-date 2024-03-31 \
            --capital 100000 \
            --verbose
    fi
}

# Cleanup function
cleanup() {
    print_status "Cleaning up..."
    
    if command -v docker-compose &> /dev/null; then
        docker-compose down --volumes --remove-orphans
    else
        docker compose down --volumes --remove-orphans
    fi
    
    print_status "Cleanup completed ✅"
}

# Main setup function
main_setup() {
    echo -e "\nSetup Configuration:"
    echo "  Environment File: $ENV_FILE"
    echo "  Compose File: $COMPOSE_FILE"
    echo ""
    
    check_prerequisites
    create_directories
    setup_environment
    setup_config
    build_images
    start_services
    wait_for_services
    show_status
    
    echo -e "\n${GREEN}🎉 Docker setup completed successfully!${NC}"
    echo ""
    print_status "Next Steps:"
    echo "  1. Edit $ENV_FILE to add your Alpaca API keys"
    echo "  2. Visit http://localhost:8501 to access the dashboard"
    echo "  3. Run './docker-setup.sh pipeline' to test the trading pipeline"
    echo "  4. Run './docker-setup.sh backtest' to run a sample backtest"
    echo ""
    print_warning "Note: The platform is running in dry-run mode by default for safety"
}

# Handle script arguments
case "${1:-setup}" in
    "setup"|"start")
        main_setup
        ;;
    "stop")
        print_status "Stopping services..."
        if command -v docker-compose &> /dev/null; then
            docker-compose down
        else
            docker compose down
        fi
        print_status "Services stopped ✅"
        ;;
    "restart")
        print_status "Restarting services..."
        if command -v docker-compose &> /dev/null; then
            docker-compose restart
        else
            docker compose restart
        fi
        print_status "Services restarted ✅"
        ;;
    "logs")
        service_name="${2:-}"
        if [[ -n "$service_name" ]]; then
            if command -v docker-compose &> /dev/null; then
                docker-compose logs -f "$service_name"
            else
                docker compose logs -f "$service_name"
            fi
        else
            if command -v docker-compose &> /dev/null; then
                docker-compose logs -f
            else
                docker compose logs -f
            fi
        fi
        ;;
    "status")
        show_status
        ;;
    "pipeline")
        run_pipeline
        ;;
    "backtest")
        run_backtest
        ;;
    "shell")
        service_name="${2:-trading-engine}"
        print_status "Opening shell in $service_name..."
        if command -v docker-compose &> /dev/null; then
            docker-compose exec "$service_name" bash
        else
            docker compose exec "$service_name" bash
        fi
        ;;
    "clean")
        cleanup
        ;;
    "build")
        check_prerequisites
        build_images
        ;;
    "help")
        echo "Usage: $0 {setup|start|stop|restart|logs|status|pipeline|backtest|shell|clean|build|help}"
        echo ""
        echo "Commands:"
        echo "  setup     - Complete setup and start all services (default)"
        echo "  start     - Same as setup"
        echo "  stop      - Stop all services"
        echo "  restart   - Restart all services"
        echo "  logs      - Show logs (optional: specify service name)"
        echo "  status    - Show service status and URLs"
        echo "  pipeline  - Run trading pipeline in container"
        echo "  backtest  - Run sample backtest in container"
        echo "  shell     - Open shell in container (default: trading-engine)"
        echo "  clean     - Stop and remove all containers and volumes"
        echo "  build     - Build Docker images only"
        echo "  help      - Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 setup                    # Complete setup"
        echo "  $0 logs dashboard           # Show dashboard logs"
        echo "  $0 shell trading-engine     # Shell into trading engine"
        echo "  $0 pipeline                 # Run trading pipeline"
        ;;
    *)
        print_error "Unknown command: $1"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;
esac
