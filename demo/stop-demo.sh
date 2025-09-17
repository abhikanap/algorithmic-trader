#!/bin/bash

# Stop Demo Script - Clean shutdown of the trading platform demo

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEMO_COMPOSE_FILE="demo-docker-compose.yml"

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_banner() {
    echo -e "${BLUE}"
    echo "🛑===============================================🛑"
    echo "       Stopping Trading Platform Demo         "
    echo "🛑===============================================🛑"
    echo -e "${NC}"
}

main() {
    print_banner
    
    if [ -f "$DEMO_COMPOSE_FILE" ]; then
        print_status "Stopping demo containers..."
        docker-compose -f $DEMO_COMPOSE_FILE down
        
        print_status "Removing demo networks..."
        docker network prune -f
        
        print_status "✅ Demo environment stopped"
        
        echo
        echo -e "${YELLOW}📋 To completely clean up:${NC}"
        echo -e "  🧹 Clean all:     ${GREEN}./demo/start-demo.sh clean${NC}"
        echo -e "  🔄 Restart:       ${GREEN}./demo/start-demo.sh start${NC}"
        echo
    else
        print_warning "Demo compose file not found. Nothing to stop."
    fi
}

main "$@"
