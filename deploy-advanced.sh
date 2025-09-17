#!/bin/bash

# Advanced Deployment Script for Algorithmic Trading Platform v2.0
# Supports multiple deployment modes: development, staging, production

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_MODE="${1:-development}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Logging
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

# Banner
print_banner() {
    echo -e "${BLUE}"
    echo "=========================================="
    echo "🚀 ALGORITHMIC TRADING PLATFORM v2.0"
    echo "   Complete End-to-End Trading System"
    echo "=========================================="
    echo -e "${NC}"
    echo "Deployment Mode: $DEPLOYMENT_MODE"
    echo "Timestamp: $TIMESTAMP"
    echo ""
}

# Environment validation
validate_environment() {
    log "Validating environment..."
    
    # Check required commands
    local required_commands=("docker" "docker-compose" "python3" "git")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            error "Required command '$cmd' not found"
        fi
    done
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running"
    fi
    
    # Check Python version
    local python_version=$(python3 --version | cut -d' ' -f2)
    local required_version="3.11"
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
        warn "Python $required_version+ recommended, found $python_version"
    fi
    
    log "Environment validation completed"
}

# Pre-deployment checks
pre_deployment_checks() {
    log "Running pre-deployment checks..."
    
    cd "$PROJECT_ROOT"
    
    # Check for required files
    local required_files=(
        "main.py"
        "Dockerfile" 
        "docker-compose.yml"
        "requirements.txt"
        "packages/core/config.py"
    )
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            error "Required file '$file' not found"
        fi
    done
    
    # Check for integration components
    local components=(
        "apps/screener"
        "apps/analyzer"
        "apps/strategy"
        "apps/execution"
        "apps/backtesting"
        "integration"
    )
    
    for component in "${components[@]}"; do
        if [[ ! -d "$component" ]]; then
            error "Required component '$component' not found"
        fi
    done
    
    # Validate environment file
    if [[ ! -f ".env" && "$DEPLOYMENT_MODE" != "development" ]]; then
        warn "No .env file found. Using default configuration."
    fi
    
    log "Pre-deployment checks completed"
}

# Setup environment configuration
setup_environment() {
    log "Setting up environment configuration..."
    
    cd "$PROJECT_ROOT"
    
    # Create environment-specific config
    case "$DEPLOYMENT_MODE" in
        "development")
            setup_development_env
            ;;
        "staging")
            setup_staging_env
            ;;
        "production")
            setup_production_env
            ;;
        *)
            error "Invalid deployment mode: $DEPLOYMENT_MODE. Use: development, staging, or production"
            ;;
    esac
    
    # Create required directories
    local directories=(
        "artifacts/screener"
        "artifacts/analyzer"
        "artifacts/strategy"
        "artifacts/execution"
        "artifacts/backtests"
        "artifacts/pipeline_runs"
        "logs"
        "cache"
        "data/historical"
        "config/environments"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
    done
    
    log "Environment configuration completed"
}

setup_development_env() {
    cat > .env << EOF
# Development Environment - Algorithmic Trading Platform v2.0
DEPLOYMENT_MODE=development
TRADING_ENVIRONMENT=development
LOG_LEVEL=DEBUG

# Trading Configuration
TRADING_MODE=paper
ENABLE_PAPER_TRADING=true
ENABLE_LIVE_TRADING=false
MAX_POSITIONS=10
MAX_POSITION_SIZE_PCT=5.0
DAILY_LOSS_LIMIT_PCT=2.0

# Alpaca API (Paper Trading)
ALPACA_BASE_URL=https://paper-api.alpaca.markets
# ALPACA_API_KEY=your_paper_api_key
# ALPACA_SECRET_KEY=your_paper_secret_key

# Platform Features
ENABLE_BACKTESTING=true
ENABLE_WALK_FORWARD=true
ENABLE_UI=true

# Container Resources
PLATFORM_MEMORY=1g
PLATFORM_CPU=0.5

# Ports
TRADING_PORT=8000
STREAMLIT_PORT=8501
MONITORING_PORT=8080

# Paths
ARTIFACTS_PATH=./artifacts
LOGS_PATH=./logs
CACHE_PATH=./cache
DATA_PATH=./data
CONFIG_PATH=./config
EOF
    
    info "Development environment configured"
}

setup_staging_env() {
    cat > .env << EOF
# Staging Environment - Algorithmic Trading Platform v2.0
DEPLOYMENT_MODE=staging
TRADING_ENVIRONMENT=staging
LOG_LEVEL=INFO

# Trading Configuration
TRADING_MODE=paper
ENABLE_PAPER_TRADING=true
ENABLE_LIVE_TRADING=false
MAX_POSITIONS=15
MAX_POSITION_SIZE_PCT=8.0
DAILY_LOSS_LIMIT_PCT=3.0

# Alpaca API (Paper Trading)
ALPACA_BASE_URL=https://paper-api.alpaca.markets
# ALPACA_API_KEY=your_paper_api_key
# ALPACA_SECRET_KEY=your_paper_secret_key

# Platform Features
ENABLE_BACKTESTING=true
ENABLE_WALK_FORWARD=true
ENABLE_UI=true

# Container Resources
PLATFORM_MEMORY=1.5g
PLATFORM_CPU=0.75

# Ports
TRADING_PORT=8000
STREAMLIT_PORT=8501
MONITORING_PORT=8080

# Paths
ARTIFACTS_PATH=./artifacts
LOGS_PATH=./logs
CACHE_PATH=./cache
DATA_PATH=./data
CONFIG_PATH=./config
EOF
    
    info "Staging environment configured"
}

setup_production_env() {
    cat > .env << EOF
# Production Environment - Algorithmic Trading Platform v2.0
DEPLOYMENT_MODE=production
TRADING_ENVIRONMENT=production
LOG_LEVEL=INFO

# Trading Configuration (CAREFUL: This can trade real money!)
TRADING_MODE=live
ENABLE_PAPER_TRADING=true
ENABLE_LIVE_TRADING=false  # Set to true when ready for live trading
MAX_POSITIONS=20
MAX_POSITION_SIZE_PCT=10.0
DAILY_LOSS_LIMIT_PCT=5.0

# Alpaca API (LIVE TRADING - Use with caution!)
ALPACA_BASE_URL=https://api.alpaca.markets  # LIVE API
# ALPACA_API_KEY=your_live_api_key
# ALPACA_SECRET_KEY=your_live_secret_key

# Platform Features
ENABLE_BACKTESTING=true
ENABLE_WALK_FORWARD=true
ENABLE_UI=true

# Container Resources
PLATFORM_MEMORY=2g
PLATFORM_CPU=1.0

# Ports
TRADING_PORT=8000
STREAMLIT_PORT=8501
MONITORING_PORT=8080

# Production Paths
ARTIFACTS_PATH=./artifacts
LOGS_PATH=./logs
CACHE_PATH=./cache
DATA_PATH=./data
CONFIG_PATH=./config

# Security (Add your own values)
# SSL_CERT_PATH=./certs/cert.pem
# SSL_KEY_PATH=./certs/key.pem
EOF
    
    warn "Production environment configured - Review settings carefully!"
    warn "Set ALPACA_API_KEY and ALPACA_SECRET_KEY before deploying!"
    if [[ "$DEPLOYMENT_MODE" == "production" ]]; then
        warn "LIVE TRADING is DISABLED by default. Enable with caution!"
    fi
}

# Build and deploy
build_and_deploy() {
    log "Building and deploying platform..."
    
    cd "$PROJECT_ROOT"
    
    # Build the Docker image
    log "Building Docker image..."
    docker-compose build --no-cache --parallel
    
    # Stop existing containers
    log "Stopping existing containers..."
    docker-compose down --remove-orphans
    
    # Start the platform
    log "Starting Algorithmic Trading Platform v2.0..."
    docker-compose up -d
    
    # Wait for services to be ready
    log "Waiting for services to start..."
    sleep 10
    
    # Check service health
    check_service_health
    
    log "Deployment completed successfully!"
}

# Health checks
check_service_health() {
    log "Checking service health..."
    
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if docker-compose ps | grep -q "Up"; then
            log "Services are running"
            break
        fi
        
        if [[ $attempt -eq $max_attempts ]]; then
            error "Services failed to start after $max_attempts attempts"
        fi
        
        info "Attempt $attempt/$max_attempts - Waiting for services..."
        sleep 5
        ((attempt++))
    done
    
    # Show service status
    info "Service status:"
    docker-compose ps
}

# Post-deployment verification
post_deployment_verification() {
    log "Running post-deployment verification..."
    
    cd "$PROJECT_ROOT"
    
    # Test platform CLI
    log "Testing platform CLI..."
    if docker-compose exec -T trading-platform python main.py status; then
        log "Platform CLI test passed"
    else
        error "Platform CLI test failed"
    fi
    
    # Test individual components
    local components=("screener" "analyzer" "strategy" "execution" "backtesting")
    for component in "${components[@]}"; do
        info "Testing $component component..."
        if docker-compose exec -T trading-platform python main.py "$component" --help &>/dev/null; then
            info "$component component test passed"
        else
            warn "$component component test failed"
        fi
    done
    
    log "Post-deployment verification completed"
}

# Deployment summary
print_deployment_summary() {
    echo -e "${GREEN}"
    echo "=========================================="
    echo "🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!"
    echo "=========================================="
    echo -e "${NC}"
    
    echo "Platform Status:"
    echo "  - Mode: $DEPLOYMENT_MODE"
    echo "  - Container: algorithmic-trader-v2"
    echo "  - Health: $(docker-compose ps -q | wc -l) services running"
    echo ""
    
    echo "Available Interfaces:"
    echo "  - Main CLI: docker-compose exec trading-platform python main.py --help"
    echo "  - Live Pipeline: docker-compose exec trading-platform python main.py run-live"
    echo "  - Backtesting: docker-compose exec trading-platform python main.py backtest"
    echo "  - System Status: docker-compose exec trading-platform python main.py status"
    echo ""
    
    if [[ -f ".env" ]]; then
        local streamlit_port=$(grep "STREAMLIT_PORT" .env | cut -d'=' -f2)
        echo "Web Interfaces:"
        echo "  - Streamlit UI: http://localhost:${streamlit_port:-8501}"
        echo ""
    fi
    
    echo "Useful Commands:"  
    echo "  - View logs: docker-compose logs -f trading-platform"
    echo "  - Stop platform: docker-compose down"
    echo "  - Restart platform: docker-compose restart"
    echo "  - Scale resources: docker-compose up -d --scale trading-platform=2"
    echo ""
    
    if [[ "$DEPLOYMENT_MODE" == "production" ]]; then
        warn "Production deployment - Monitor carefully!"
        warn "Verify Alpaca API keys are set correctly"
        warn "Live trading is disabled by default"
    fi
}

# Cleanup function
cleanup() {
    log "Cleaning up..."
    # Add any cleanup tasks here
}

# Error handling
trap cleanup EXIT

# Main execution
main() {
    print_banner
    validate_environment
    pre_deployment_checks
    setup_environment
    build_and_deploy
    post_deployment_verification
    print_deployment_summary
}

# Help message
show_help() {
    echo "Advanced Deployment Script for Algorithmic Trading Platform v2.0"
    echo ""
    echo "Usage: $0 [MODE]"
    echo ""
    echo "Deployment Modes:"
    echo "  development  - Development environment (default)"
    echo "  staging      - Staging environment for testing"
    echo "  production   - Production environment (use with caution)"
    echo ""
    echo "Examples:"
    echo "  $0                    # Deploy in development mode"
    echo "  $0 development        # Deploy in development mode"
    echo "  $0 staging           # Deploy in staging mode"
    echo "  $0 production        # Deploy in production mode"
    echo ""
    echo "Features:"
    echo "  ✅ Complete end-to-end trading platform"
    echo "  ✅ All 5 phases: Screener → Analyzer → Strategy → Execution → Backtesting"
    echo "  ✅ Live and paper trading support"
    echo "  ✅ Historical backtesting and walk-forward analysis"
    echo "  ✅ Comprehensive performance metrics"
    echo "  ✅ Docker containerization"
    echo "  ✅ Environment-specific configuration"
    echo ""
}

# Handle help flag
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    show_help
    exit 0
fi

# Run main function
main "$@"
