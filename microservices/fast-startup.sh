#!/bin/bash

# High-Performance Docker Build and Startup Script
# Uses parallel builds, BuildKit caching, and optimized startup sequence

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="core-optimized.yml"
CACHE_DIR="$HOME/.docker-cache/trading-platform"
BUILD_CACHE_DIR="$CACHE_DIR/buildkit"

# Performance settings
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
export BUILDKIT_PROGRESS=plain

echo -e "${BLUE}🚀 High-Performance Trading Platform Startup${NC}"
echo "==================================================="

# Create cache directories
mkdir -p "$BUILD_CACHE_DIR"

# Function to check if service is healthy
wait_for_service() {
    local service=$1
    local port=$2
    local max_attempts=30
    local attempt=0
    
    echo -e "${YELLOW}⏳ Waiting for $service to be healthy...${NC}"
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -sf "http://localhost:$port/health" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ $service is healthy!${NC}"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 1
        echo -n "."
    done
    
    echo -e "${RED}❌ $service failed to start within $max_attempts seconds${NC}"
    return 1
}

# Function for parallel image builds
build_images_parallel() {
    echo -e "${BLUE}🔨 Building images in parallel with caching...${NC}"
    
    # Build base layers first (can be done in parallel)
    {
        echo -e "${YELLOW}Building core-service...${NC}"
        docker build \
            --cache-from trading-core-service:cache \
            --target production \
            --tag trading-core-service:latest \
            --tag trading-core-service:cache \
            --build-arg BUILDKIT_INLINE_CACHE=1 \
            ./core-service -f ./core-service/Dockerfile.optimized &
        CORE_PID=$!
    }
    
    {
        echo -e "${YELLOW}Building market-service...${NC}"
        docker build \
            --cache-from trading-market-service:cache \
            --target production \
            --tag trading-market-service:latest \
            --tag trading-market-service:cache \
            --build-arg BUILDKIT_INLINE_CACHE=1 \
            ./market-service -f ./market-service/Dockerfile.optimized &
        MARKET_PID=$!
    }
    
    # Pull Redis in parallel
    {
        echo -e "${YELLOW}Pulling Redis image...${NC}"
        docker pull redis:7-alpine &
        REDIS_PID=$!
    }
    
    # Wait for all builds to complete
    echo -e "${YELLOW}⏳ Waiting for parallel builds to complete...${NC}"
    
    if wait $CORE_PID; then
        echo -e "${GREEN}✅ Core service build completed${NC}"
    else
        echo -e "${RED}❌ Core service build failed${NC}"
        exit 1
    fi
    
    if wait $MARKET_PID; then
        echo -e "${GREEN}✅ Market service build completed${NC}"
    else
        echo -e "${RED}❌ Market service build failed${NC}"
        exit 1
    fi
    
    if wait $REDIS_PID; then
        echo -e "${GREEN}✅ Redis image pulled${NC}"
    else
        echo -e "${RED}❌ Redis pull failed${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}🎉 All images built successfully!${NC}"
}

# Function to start services with optimized sequence
start_services_optimized() {
    echo -e "${BLUE}🚀 Starting services with optimized sequence...${NC}"
    
    # Start Redis first (fastest startup)
    echo -e "${YELLOW}Starting Redis...${NC}"
    docker-compose -f $COMPOSE_FILE up -d redis
    
    # Wait for Redis to be ready
    echo -e "${YELLOW}⏳ Waiting for Redis...${NC}"
    timeout=30
    while [ $timeout -gt 0 ]; do
        if docker exec trading-redis redis-cli ping >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Redis is ready!${NC}"
            break
        fi
        timeout=$((timeout - 1))
        sleep 1
    done
    
    # Start core service
    echo -e "${YELLOW}Starting core service...${NC}"
    docker-compose -f $COMPOSE_FILE up -d core-service
    wait_for_service "core-service" "8001"
    
    # Start market service (depends on core)
    echo -e "${YELLOW}Starting market service...${NC}"
    docker-compose -f $COMPOSE_FILE up -d market-service
    wait_for_service "market-service" "8002"
    
    echo -e "${GREEN}🎉 All services started successfully!${NC}"
}

# Function to show performance metrics
show_performance_metrics() {
    echo -e "${BLUE}📊 Performance Metrics${NC}"
    echo "======================"
    
    # Container resource usage
    echo -e "${YELLOW}Resource Usage:${NC}"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" \
        trading-core-service trading-market-service trading-redis
    
    echo ""
    
    # Service response times
    echo -e "${YELLOW}Service Response Times:${NC}"
    for service in "core-service:8001" "market-service:8002"; do
        name=$(echo $service | cut -d: -f1)
        port=$(echo $service | cut -d: -f2)
        time=$(curl -w "%{time_total}" -s -o /dev/null "http://localhost:$port/health")
        echo "  $name: ${time}s"
    done
}

# Function to run comprehensive tests
run_comprehensive_tests() {
    echo -e "${BLUE}🧪 Running comprehensive platform tests...${NC}"
    
    # Test individual services
    echo -e "${YELLOW}Testing individual services...${NC}"
    ./test-scripts/test-service.sh core-service
    ./test-scripts/test-service.sh market-service
    
    # Test integration
    echo -e "${YELLOW}Testing service integration...${NC}"
    ./test-scripts/test-integration.sh
    
    echo -e "${GREEN}✅ All tests completed!${NC}"
}

# Main execution
main() {
    local start_time=$(date +%s)
    
    echo -e "${BLUE}Starting high-performance platform deployment...${NC}"
    
    # Clean up any existing containers
    echo -e "${YELLOW}🧹 Cleaning up existing containers...${NC}"
    docker-compose -f $COMPOSE_FILE down --remove-orphans >/dev/null 2>&1 || true
    
    # Build images in parallel
    build_images_parallel
    
    # Start services with optimization
    start_services_optimized
    
    # Show performance metrics
    show_performance_metrics
    
    # Run tests if requested
    if [[ "${1:-}" == "test" ]]; then
        run_comprehensive_tests
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    echo ""
    echo -e "${GREEN}🎉 Platform startup completed in ${duration} seconds!${NC}"
    echo -e "${GREEN}🌐 Services available at:${NC}"
    echo -e "  ${BLUE}Core Service:${NC}    http://localhost:8001"
    echo -e "  ${BLUE}Market Service:${NC}  http://localhost:8002"
    echo -e "  ${BLUE}Redis:${NC}           localhost:6379"
    echo ""
    echo -e "${YELLOW}💡 Next steps:${NC}"
    echo -e "  ${BLUE}•${NC} View service docs: http://localhost:8001/docs"
    echo -e "  ${BLUE}•${NC} Run tests: ./fast-startup.sh test"
    echo -e "  ${BLUE}•${NC} Monitor services: docker-compose -f $COMPOSE_FILE logs -f"
    echo -e "  ${BLUE}•${NC} Stop services: docker-compose -f $COMPOSE_FILE down"
}

# Handle script arguments
case "${1:-start}" in
    "build")
        build_images_parallel
        ;;
    "start")
        start_services_optimized
        show_performance_metrics
        ;;
    "test")
        main test
        ;;
    "metrics")
        show_performance_metrics
        ;;
    "clean")
        echo -e "${YELLOW}🧹 Cleaning up all containers and images...${NC}"
        docker-compose -f $COMPOSE_FILE down --remove-orphans --volumes
        docker system prune -f
        ;;
    *)
        main "$1"
        ;;
esac
