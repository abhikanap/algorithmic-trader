#!/bin/bash

# Demo Start Script - Launch the complete trading platform demo
# This script provides an easy way to test the platform locally

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEMO_COMPOSE_FILE="demo-docker-compose.yml"
DASHBOARD_PORT=8080
API_PORT=8000

# Print banner
print_banner() {
    echo -e "${BLUE}"
    echo "🚀===============================================🚀"
    echo "  Advanced Algorithmic Trading Platform Demo  "
    echo "🚀===============================================🚀"
    echo -e "${NC}"
}

# Print status message
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

# Print warning message
print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Print error message
print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        print_error "Please install Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed or not in PATH"
        print_error "Please install Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        print_error "Please start Docker and try again"
        exit 1
    fi
    
    print_status "✅ All prerequisites met"
}

# Check if ports are available
check_ports() {
    print_status "Checking port availability..."
    
    if lsof -Pi :$DASHBOARD_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port $DASHBOARD_PORT is already in use"
        print_warning "The dashboard might not be accessible"
    fi
    
    if lsof -Pi :$API_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port $API_PORT is already in use"
        print_warning "The API server might not be accessible"
    fi
}

# Create demo docker-compose file
create_demo_compose() {
    print_status "Creating demo Docker Compose configuration..."
    
    cat > $DEMO_COMPOSE_FILE << 'EOF'
version: '3.8'

services:
  trading-platform-demo:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: trading-platform-demo
    ports:
      - "8080:8080"  # Web Dashboard
      - "8000:8000"  # API Server
    environment:
      - ENVIRONMENT=demo
      - SECRET_KEY=demo-secret-key-change-in-production
      - JWT_EXPIRATION=3600
      - MONITORING_INTERVAL=15
      - GENERATE_SAMPLE_REPORTS=true
    volumes:
      - ./logs:/app/logs
      - ./reports:/app/reports
      - ./demo/data:/app/demo/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  redis-demo:
    image: redis:7-alpine
    container_name: trading-platform-redis-demo
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  redis_data:
EOF

    print_status "✅ Demo Docker Compose file created"
}

# Create sample data
create_sample_data() {
    print_status "Creating sample data..."
    
    mkdir -p demo/data
    
    # Create sample configuration
    cat > demo/data/demo-config.json << 'EOF'
{
  "demo_mode": true,
  "sample_symbols": ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"],
  "initial_capital": 100000,
  "risk_limits": {
    "max_position_size": 0.1,
    "daily_loss_limit": 0.05,
    "max_drawdown": 0.15
  },
  "strategies": {
    "mean_reversion": {
      "enabled": true,
      "lookback_period": 20,
      "threshold": 2.0
    },
    "momentum": {
      "enabled": true,
      "lookback_period": 10,
      "threshold": 1.5
    }
  }
}
EOF

    # Create sample market data (CSV format)
    cat > demo/data/sample_prices.csv << 'EOF'
date,symbol,open,high,low,close,volume
2024-01-01,AAPL,150.00,152.50,149.50,151.20,1000000
2024-01-01,GOOGL,2500.00,2520.00,2480.00,2510.00,500000
2024-01-01,MSFT,300.00,305.00,298.00,302.50,800000
2024-01-02,AAPL,151.20,153.00,150.00,152.80,1100000
2024-01-02,GOOGL,2510.00,2530.00,2500.00,2525.00,520000
2024-01-02,MSFT,302.50,308.00,301.00,306.20,850000
EOF

    print_status "✅ Sample data created"
}

# Build and start containers
start_demo() {
    print_status "Building and starting demo containers..."
    
    # Stop any existing containers
    docker-compose -f $DEMO_COMPOSE_FILE down --remove-orphans 2>/dev/null || true
    
    # Build and start
    docker-compose -f $DEMO_COMPOSE_FILE up --build -d
    
    print_status "✅ Demo containers started"
}

# Wait for services to be ready
wait_for_services() {
    print_status "Waiting for services to be ready..."
    echo -e "${BLUE}🔍 Detailed Service Check Progress:${NC}"
    
    # Check container status first
    print_status "📦 Checking container status..."
    CONTAINER_STATUS=$(docker-compose -f $DEMO_COMPOSE_FILE ps --format "table {{.Name}}\t{{.State}}\t{{.Status}}")
    echo "$CONTAINER_STATUS"
    
    # Check if containers are running
    if ! docker-compose -f $DEMO_COMPOSE_FILE ps | grep -q "Up"; then
        print_error "❌ Containers are not running properly"
        print_error "Container logs:"
        docker-compose -f $DEMO_COMPOSE_FILE logs --tail=50
        exit 1
    fi
    
    print_status "✅ Containers are running, checking application readiness..."
    
    # Wait for Redis first
    print_status "🔴 Checking Redis connection..."
    for i in {1..10}; do
        if docker exec trading-platform-redis-demo redis-cli ping >/dev/null 2>&1; then
            print_status "✅ Redis is ready (attempt $i/10)"
            break
        else
            echo -e "   ${YELLOW}⏳ Redis not ready yet (attempt $i/10), waiting 2 seconds...${NC}"
            sleep 2
        fi
        
        if [ $i -eq 10 ]; then
            print_warning "⚠️  Redis might not be fully ready, continuing..."
        fi
    done
    
    # Wait for API health check with detailed feedback
    print_status "🔌 Checking API server health..."
    for i in {1..30}; do
        echo -e "   ${BLUE}🔍 Health check attempt $i/30...${NC}"
        
        # Check if the health endpoint responds
        HEALTH_RESPONSE=$(curl -s -w "%{http_code}" "http://localhost:$API_PORT/health" 2>/dev/null || echo "connection_failed")
        
        if [ "$HEALTH_RESPONSE" = "connection_failed" ]; then
            echo -e "   ${YELLOW}⏳ Connection failed - API server not accepting connections yet${NC}"
        elif [ "${HEALTH_RESPONSE: -3}" = "200" ]; then
            HEALTH_BODY=$(echo "$HEALTH_RESPONSE" | sed 's/...$//')
            echo -e "   ${GREEN}✅ API server health check passed!${NC}"
            echo -e "   ${GREEN}📊 Health response: $HEALTH_BODY${NC}"
            print_status "✅ API server is ready"
            break
        else
            echo -e "   ${YELLOW}⚠️  HTTP ${HEALTH_RESPONSE: -3} - API server responding but not healthy yet${NC}"
        fi
        
        # Show recent container logs on every 5th attempt
        if [ $((i % 5)) -eq 0 ]; then
            echo -e "   ${BLUE}📋 Recent container logs (last 10 lines):${NC}"
            docker-compose -f $DEMO_COMPOSE_FILE logs --tail=10 trading-platform-demo | head -10
        fi
        
        if [ $i -eq 30 ]; then
            print_error "❌ API server failed to start within 5 minutes"
            echo -e "${RED}🔥 Final container status:${NC}"
            docker-compose -f $DEMO_COMPOSE_FILE ps
            echo -e "${RED}🔥 Recent error logs:${NC}"
            docker-compose -f $DEMO_COMPOSE_FILE logs --tail=50 trading-platform-demo
            print_error "Check logs with: docker-compose -f $DEMO_COMPOSE_FILE logs"
            exit 1
        fi
        
        echo -e "   ${BLUE}⏳ Waiting 10 seconds before next check...${NC}"
        sleep 10
    done
    
    # Check additional API endpoints
    print_status "🔍 Testing additional API endpoints..."
    
    # Test docs endpoint
    DOCS_RESPONSE=$(curl -s -w "%{http_code}" "http://localhost:$API_PORT/docs" 2>/dev/null || echo "failed")
    if [ "${DOCS_RESPONSE: -3}" = "200" ]; then
        print_status "✅ API documentation endpoint ready"
    else
        print_warning "⚠️  API docs endpoint not responding (${DOCS_RESPONSE: -3})"
    fi
    
    # Wait a bit more for dashboard
    print_status "🖥️  Checking web dashboard..."
    sleep 5
    
    DASHBOARD_RESPONSE=$(curl -s -w "%{http_code}" "http://localhost:$DASHBOARD_PORT" 2>/dev/null || echo "failed")
    if [ "${DASHBOARD_RESPONSE: -3}" = "200" ]; then
        print_status "✅ Web dashboard is ready"
    else
        print_warning "⚠️  Web dashboard not responding yet (${DASHBOARD_RESPONSE: -3})"
        print_warning "Dashboard might take additional time to initialize"
    fi
    
    # Final system status
    print_status "📊 Final system status check..."
    echo -e "${BLUE}Container Status:${NC}"
    docker-compose -f $DEMO_COMPOSE_FILE ps
    
    echo -e "${BLUE}Port Status:${NC}"
    netstat -an | grep -E ":(8000|8080|6379)" | head -10 || true
}

# Create demo users and data
setup_demo_data() {
    print_status "Setting up demo data..."
    
    # Create demo authentication token
    TOKEN=$(curl -s -X POST "http://localhost:$API_PORT/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"username": "admin", "password": "admin123"}' | \
        python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || echo "")
    
    if [ -n "$TOKEN" ]; then
        print_status "✅ Demo authentication successful"
        
        # Save token for other demo scripts
        echo "$TOKEN" > demo/data/demo-token.txt
        
        # Test API endpoints
        curl -s -H "Authorization: Bearer $TOKEN" \
            "http://localhost:$API_PORT/api/v1/system/status" > demo/data/system-status.json
        
        print_status "✅ Demo API data created"
    else
        print_warning "Could not authenticate with demo API"
    fi
}

# Display access information
show_access_info() {
    echo
    echo -e "${GREEN}🎉 Demo Environment is Ready! 🎉${NC}"
    echo -e "${BLUE}═══════════════════════════════════${NC}"
    echo
    echo -e "${YELLOW}📊 Access Points:${NC}"
    echo -e "  🌐 Web Dashboard:    ${GREEN}http://localhost:$DASHBOARD_PORT${NC}"
    echo -e "  🔌 API Server:       ${GREEN}http://localhost:$API_PORT${NC}"
    echo -e "  📚 API Docs:         ${GREEN}http://localhost:$API_PORT/docs${NC}"
    echo -e "  ❤️  Health Check:     ${GREEN}http://localhost:$API_PORT/health${NC}"
    echo
    echo -e "${YELLOW}🔐 Demo Credentials:${NC}"
    echo -e "  👑 Admin:    ${GREEN}admin${NC} / ${GREEN}admin123${NC}     (Full access)"
    echo -e "  💼 Trader:   ${GREEN}trader${NC} / ${GREEN}trader123${NC}   (Trading access)"
    echo -e "  👀 Viewer:   ${GREEN}viewer${NC} / ${GREEN}viewer123${NC}   (Read-only)"
    echo
    echo -e "${YELLOW}🛠️  Management:${NC}"
    echo -e "  📋 View logs:        ${GREEN}docker-compose -f $DEMO_COMPOSE_FILE logs -f${NC}"
    echo -e "  ⏹️  Stop demo:        ${GREEN}./demo/stop-demo.sh${NC}"
    echo -e "  🔄 Restart:          ${GREEN}docker-compose -f $DEMO_COMPOSE_FILE restart${NC}"
    echo
    echo -e "${YELLOW}🧪 Test Scripts:${NC}"
    echo -e "  🔍 API Tests:        ${GREEN}./demo/test-api.sh${NC}"
    echo -e "  📈 Analytics Demo:   ${GREEN}./demo/test-analytics.sh${NC}"
    echo -e "  📊 Portfolio Demo:   ${GREEN}./demo/test-portfolio.sh${NC}"
    echo
    echo -e "${BLUE}═══════════════════════════════════${NC}"
    echo -e "${GREEN}Happy Trading! 🚀${NC}"
    echo
}

# Main execution
main() {
    print_banner
    
    check_prerequisites
    check_ports
    create_demo_compose
    create_sample_data
    start_demo
    wait_for_services
    setup_demo_data
    show_access_info
}

# Handle script arguments
case "${1:-start}" in
    start)
        main
        ;;
    stop)
        print_status "Stopping demo environment..."
        docker-compose -f $DEMO_COMPOSE_FILE down
        print_status "✅ Demo stopped"
        ;;
    restart)
        print_status "Restarting demo environment..."
        docker-compose -f $DEMO_COMPOSE_FILE restart
        print_status "✅ Demo restarted"
        ;;
    logs)
        docker-compose -f $DEMO_COMPOSE_FILE logs -f
        ;;
    status)
        docker-compose -f $DEMO_COMPOSE_FILE ps
        ;;
    clean)
        print_status "Cleaning up demo environment..."
        docker-compose -f $DEMO_COMPOSE_FILE down -v --remove-orphans
        docker system prune -f
        rm -f $DEMO_COMPOSE_FILE
        rm -rf demo/data
        print_status "✅ Demo environment cleaned"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|logs|status|clean}"
        echo
        echo "Commands:"
        echo "  start    - Start the demo environment (default)"
        echo "  stop     - Stop the demo environment"
        echo "  restart  - Restart the demo environment"
        echo "  logs     - Show demo logs"
        echo "  status   - Show container status"
        echo "  clean    - Clean up everything"
        exit 1
        ;;
esac
