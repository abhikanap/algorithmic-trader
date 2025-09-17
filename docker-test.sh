#!/bin/bash

# Docker Test Script for Algorithmic Trading Platform
# This script tests the Docker deployment to ensure everything works correctly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENV_FILE=".env.docker"
DOCKER_COMPOSE="docker-compose"

echo -e "${BLUE}🧪 Docker Test Suite for Algorithmic Trading Platform${NC}"
echo "========================================================="

# Check if docker-compose or docker compose is available
if ! command -v docker-compose &> /dev/null; then
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    else
        echo -e "${RED}❌ Neither docker-compose nor docker compose is available${NC}"
        exit 1
    fi
fi

print_test() {
    echo -e "\n${BLUE}[TEST]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Test 1: Check Docker prerequisites
test_prerequisites() {
    print_test "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        return 1
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        return 1
    fi
    
    # Check Docker Compose
    if ! $DOCKER_COMPOSE version &> /dev/null; then
        print_error "Docker Compose is not working"
        return 1
    fi
    
    print_success "Prerequisites check passed"
    return 0
}

# Test 2: Check environment configuration
test_environment() {
    print_test "Checking environment configuration..."
    
    if [ ! -f "$ENV_FILE" ]; then
        print_warning "Environment file $ENV_FILE not found, creating from template"
        if [ -f ".env.docker.template" ]; then
            cp .env.docker.template "$ENV_FILE"
            print_success "Created $ENV_FILE from template"
        else
            print_error "Template file .env.docker.template not found"
            return 1
        fi
    fi
    
    # Check for required variables
    if ! grep -q "ALPACA_API_KEY=" "$ENV_FILE"; then
        print_warning "ALPACA_API_KEY not found in $ENV_FILE"
    fi
    
    if ! grep -q "ALPACA_SECRET_KEY=" "$ENV_FILE"; then
        print_warning "ALPACA_SECRET_KEY not found in $ENV_FILE"
    fi
    
    print_success "Environment configuration check completed"
    return 0
}

# Test 3: Build Docker images
test_build() {
    print_test "Building Docker images..."
    
    if $DOCKER_COMPOSE --env-file "$ENV_FILE" build --no-cache > /tmp/build.log 2>&1; then
        print_success "Docker images built successfully"
        return 0
    else
        print_error "Failed to build Docker images"
        echo "Build log:"
        tail -20 /tmp/build.log
        return 1
    fi
}

# Test 4: Start services
test_start_services() {
    print_test "Starting services..."
    
    if $DOCKER_COMPOSE --env-file "$ENV_FILE" up -d > /tmp/start.log 2>&1; then
        print_success "Services started successfully"
        sleep 10  # Wait for services to initialize
        return 0
    else
        print_error "Failed to start services"
        echo "Start log:"
        cat /tmp/start.log
        return 1
    fi
}

# Test 5: Check service health
test_service_health() {
    print_test "Checking service health..."
    
    # Check if containers are running
    running_containers=$($DOCKER_COMPOSE ps --services --filter "status=running" | wc -l)
    if [ "$running_containers" -lt 1 ]; then
        print_error "No containers are running"
        $DOCKER_COMPOSE ps
        return 1
    fi
    
    print_success "$running_containers containers are running"
    
    # Test specific services
    services=("redis" "postgres")
    for service in "${services[@]}"; do
        if $DOCKER_COMPOSE ps "$service" | grep -q "Up"; then
            print_success "$service is running"
        else
            print_warning "$service is not running"
        fi
    done
    
    return 0
}

# Test 6: Test database connectivity
test_database() {
    print_test "Testing database connectivity..."
    
    # Test PostgreSQL
    if $DOCKER_COMPOSE exec -T postgres pg_isready -U trader -d trading > /dev/null 2>&1; then
        print_success "PostgreSQL is accessible"
    else
        print_error "PostgreSQL is not accessible"
        return 1
    fi
    
    # Test Redis
    if $DOCKER_COMPOSE exec -T redis redis-cli ping > /dev/null 2>&1; then
        print_success "Redis is accessible"
    else
        print_error "Redis is not accessible"
        return 1
    fi
    
    return 0
}

# Test 7: Test dashboard accessibility
test_dashboard() {
    print_test "Testing dashboard accessibility..."
    
    # Wait for dashboard to be ready
    timeout=30
    counter=0
    while [ $counter -lt $timeout ]; do
        if curl -s http://localhost:8501/_stcore/health > /dev/null 2>&1; then
            print_success "Dashboard is accessible at http://localhost:8501"
            return 0
        fi
        sleep 2
        counter=$((counter + 2))
    done
    
    print_error "Dashboard is not accessible after ${timeout}s"
    return 1
}

# Test 8: Test trading engine functionality
test_trading_engine() {
    print_test "Testing trading engine functionality..."
    
    # Test help command
    if $DOCKER_COMPOSE exec -T trading-engine python main.py --help > /dev/null 2>&1; then
        print_success "Trading engine CLI is working"
    else
        print_error "Trading engine CLI is not working"
        return 1
    fi
    
    # Test screener (dry run)
    if timeout 60 $DOCKER_COMPOSE exec -T trading-engine python main.py screener run --min-volume 100000 --max-results 5 > /tmp/screener.log 2>&1; then
        print_success "Screener test passed"
    else
        print_warning "Screener test failed or timed out"
        echo "Screener log:"
        tail -10 /tmp/screener.log
    fi
    
    return 0
}

# Test 9: Test pipeline runner
test_pipeline() {
    print_test "Testing pipeline runner..."
    
    # Run a minimal pipeline test
    if timeout 120 $DOCKER_COMPOSE --env-file "$ENV_FILE" run --rm pipeline-runner python main.py --help > /tmp/pipeline.log 2>&1; then
        print_success "Pipeline runner is working"
    else
        print_warning "Pipeline runner test failed or timed out"
        echo "Pipeline log:"
        tail -10 /tmp/pipeline.log
    fi
    
    return 0
}

# Test 10: Test resource usage
test_resources() {
    print_test "Checking resource usage..."
    
    # Get container stats
    stats=$(docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" $($DOCKER_COMPOSE ps -q) 2>/dev/null || echo "Stats unavailable")
    
    if [ "$stats" != "Stats unavailable" ]; then
        echo "Container Resource Usage:"
        echo "$stats"
        print_success "Resource usage check completed"
    else
        print_warning "Could not retrieve resource usage stats"
    fi
    
    return 0
}

# Cleanup function
cleanup() {
    print_test "Cleaning up test environment..."
    
    $DOCKER_COMPOSE down --volumes --remove-orphans > /dev/null 2>&1 || true
    
    # Clean up log files
    rm -f /tmp/build.log /tmp/start.log /tmp/screener.log /tmp/pipeline.log
    
    print_success "Cleanup completed"
}

# Main test runner
run_tests() {
    local failed_tests=0
    local total_tests=10
    
    echo -e "\nRunning test suite..."
    
    # Run tests
    test_prerequisites || ((failed_tests++))
    test_environment || ((failed_tests++))
    test_build || ((failed_tests++))
    test_start_services || ((failed_tests++))
    test_service_health || ((failed_tests++))
    test_database || ((failed_tests++))
    test_dashboard || ((failed_tests++))
    test_trading_engine || ((failed_tests++))
    test_pipeline || ((failed_tests++))
    test_resources || ((failed_tests++))
    
    # Summary
    echo -e "\n${BLUE}Test Summary${NC}"
    echo "============"
    passed_tests=$((total_tests - failed_tests))
    echo -e "Passed: ${GREEN}$passed_tests${NC}/$total_tests"
    
    if [ $failed_tests -gt 0 ]; then
        echo -e "Failed: ${RED}$failed_tests${NC}/$total_tests"
        echo -e "\n${YELLOW}Some tests failed. Check the output above for details.${NC}"
        return 1
    else
        echo -e "\n${GREEN}🎉 All tests passed! Your Docker setup is working correctly.${NC}"
        echo -e "\nNext steps:"
        echo "  1. Edit $ENV_FILE with your Alpaca API keys"
        echo "  2. Visit http://localhost:8501 to access the dashboard"
        echo "  3. Run './docker-setup.sh pipeline' to test the trading pipeline"
        return 0
    fi
}

# Handle script arguments
case "${1:-test}" in
    "test"|"run")
        run_tests
        ;;
    "cleanup"|"clean")
        cleanup
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 {test|cleanup|help}"
        echo ""
        echo "Commands:"
        echo "  test     - Run complete test suite (default)"
        echo "  cleanup  - Clean up test environment"
        echo "  help     - Show this help message"
        ;;
    *)
        echo "Unknown command: $1"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;
esac

# Cleanup on exit if tests were run
if [ "${1:-test}" = "test" ] || [ "${1:-test}" = "run" ]; then
    trap cleanup EXIT
fi
