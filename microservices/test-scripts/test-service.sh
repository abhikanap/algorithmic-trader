#!/bin/bash

# Microservice Individual Testing Script
# Tests a specific microservice independently

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SERVICE_NAME="${1:-core-service}"
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${BLUE}🧪 Testing Microservice: ${SERVICE_NAME}${NC}"
echo "=============================================="

# Service configuration
case $SERVICE_NAME in
    "core-service")
        PORT=8001
        ENDPOINTS=(
            "/health"
            "/health/ready"
            "/health/live"
            "/models/enums"
            "/models/schemas"
            "/config/environment"
            "/info"
        )
        ;;
    "market-service")
        PORT=8002
        ENDPOINTS=(
            "/health"
            "/quote/AAPL"
            "/quotes?symbols=AAPL,GOOGL,MSFT"
            "/historical/AAPL?days=30"
            "/search?query=APP"
            "/watchlist"
            "/stats"
            "/info"
        )
        ;;
    *)
        echo -e "${RED}❌ Unknown service: $SERVICE_NAME${NC}"
        echo "Available services: core-service, market-service"
        exit 1
        ;;
esac

# Function to check if service is running
check_service_health() {
    local url="http://localhost:$PORT/health"
    echo -e "${YELLOW}🔍 Checking service health at $url...${NC}"
    
    for i in {1..30}; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Service is healthy${NC}"
            return 0
        fi
        
        if [ $i -eq 30 ]; then
            echo -e "${RED}❌ Service health check failed after 5 minutes${NC}"
            return 1
        fi
        
        echo -n "."
        sleep 10
    done
}

# Function to test endpoints
test_endpoints() {
    echo -e "${YELLOW}🔌 Testing service endpoints...${NC}"
    
    local passed=0
    local total=${#ENDPOINTS[@]}
    
    for endpoint in "${ENDPOINTS[@]}"; do
        local url="http://localhost:$PORT$endpoint"
        echo -e "  ${BLUE}Testing: $endpoint${NC}"
        
        local response=$(curl -s -w "%{http_code}" "$url" 2>/dev/null || echo "000")
        local http_code="${response: -3}"
        local body="${response%???}"
        
        if [ "$http_code" = "200" ]; then
            echo -e "    ${GREEN}✅ $endpoint - OK${NC}"
            ((passed++))
            
            # Show sample response for info endpoints
            if [[ "$endpoint" == *"/info"* ]]; then
                echo -e "    ${BLUE}Sample response:${NC}"
                echo "$body" | python3 -m json.tool 2>/dev/null | head -10 || echo "$body"
            fi
        else
            echo -e "    ${RED}❌ $endpoint - HTTP $http_code${NC}"
            if [ "$http_code" != "000" ]; then
                echo -e "    ${YELLOW}Response: $body${NC}"
            fi
        fi
    done
    
    echo -e "${BLUE}Endpoint Test Results: $passed/$total passed${NC}"
    
    if [ $passed -eq $total ]; then
        echo -e "${GREEN}🎉 All endpoints working!${NC}"
        return 0
    else
        echo -e "${RED}⚠️  Some endpoints failed${NC}"
        return 1
    fi
}

# Function to start service
start_service() {
    echo -e "${YELLOW}🚀 Starting $SERVICE_NAME...${NC}"
    
    cd "$BASE_DIR"
    
    # Stop any existing containers
    docker-compose -f core.yml stop $SERVICE_NAME 2>/dev/null || true
    docker-compose -f core.yml rm -f $SERVICE_NAME 2>/dev/null || true
    
    # Start the service
    docker-compose -f core.yml up -d $SERVICE_NAME
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Service started successfully${NC}"
        sleep 5  # Give service time to initialize
        return 0
    else
        echo -e "${RED}❌ Failed to start service${NC}"
        return 1
    fi
}

# Function to show service logs
show_logs() {
    echo -e "${YELLOW}📋 Recent service logs:${NC}"
    cd "$BASE_DIR"
    docker-compose -f core.yml logs --tail=20 $SERVICE_NAME
}

# Function to stop service
stop_service() {
    echo -e "${YELLOW}🛑 Stopping $SERVICE_NAME...${NC}"
    cd "$BASE_DIR"
    docker-compose -f core.yml stop $SERVICE_NAME
    echo -e "${GREEN}✅ Service stopped${NC}"
}

# Main testing flow
main() {
    echo -e "${BLUE}Service: $SERVICE_NAME${NC}"
    echo -e "${BLUE}Port: $PORT${NC}"
    echo -e "${BLUE}Endpoints: ${#ENDPOINTS[@]}${NC}"
    echo ""
    
    # Start service
    if ! start_service; then
        echo -e "${RED}❌ Failed to start service${NC}"
        show_logs
        exit 1
    fi
    
    # Check health
    if ! check_service_health; then
        echo -e "${RED}❌ Service health check failed${NC}"
        show_logs
        stop_service
        exit 1
    fi
    
    # Test endpoints
    if ! test_endpoints; then
        echo -e "${RED}❌ Endpoint tests failed${NC}"
        show_logs
        stop_service
        exit 1
    fi
    
    # Show service info
    echo -e "${YELLOW}📊 Service Information:${NC}"
    curl -s "http://localhost:$PORT/info" | python3 -m json.tool 2>/dev/null || echo "Could not fetch service info"
    
    echo ""
    echo -e "${GREEN}🎉 All tests passed for $SERVICE_NAME!${NC}"
    echo ""
    echo -e "${BLUE}Service is running at: http://localhost:$PORT${NC}"
    echo -e "${BLUE}To stop: docker-compose -f core.yml stop $SERVICE_NAME${NC}"
    echo -e "${BLUE}To view logs: docker-compose -f core.yml logs -f $SERVICE_NAME${NC}"
}

# Handle script arguments
case "${2:-test}" in
    "test")
        main
        ;;
    "start")
        start_service
        ;;
    "stop")
        stop_service
        ;;
    "logs")
        show_logs
        ;;
    "health")
        check_service_health
        ;;
    *)
        echo "Usage: $0 <service-name> [test|start|stop|logs|health]"
        echo "Services: core-service, market-service"
        exit 1
        ;;
esac
