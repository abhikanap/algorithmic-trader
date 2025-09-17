#!/bin/bash

# Portfolio Demo Script - Test portfolio management features

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_BASE_URL="http://localhost:8000"
TOKEN_FILE="demo/data/demo-token.txt"

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_banner() {
    echo -e "${BLUE}"
    echo "💼===============================================💼"
    echo "      Trading Platform Portfolio Demo         "
    echo "💼===============================================💼"
    echo -e "${NC}"
}

# Load authentication token
load_token() {
    if [ -f "$TOKEN_FILE" ]; then
        TOKEN=$(cat "$TOKEN_FILE")
        print_status "Authentication token loaded"
    else
        print_status "Getting authentication token..."
        
        # Authenticate
        response=$(curl -s -X POST "$API_BASE_URL/auth/login" \
            -H "Content-Type: application/json" \
            -d '{"username": "admin", "password": "admin123"}')
        
        if echo "$response" | grep -q "access_token"; then
            TOKEN=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
            echo "$TOKEN" > "$TOKEN_FILE"
            print_success "✅ Authentication successful"
        else
            print_error "❌ Authentication failed"
            exit 1
        fi
    fi
}

# Demo portfolio overview
demo_portfolio_overview() {
    print_status "=== Portfolio Overview Demo ==="
    echo
    
    # Get current positions
    print_status "Fetching current positions..."
    positions_response=$(curl -s -H "Authorization: Bearer $TOKEN" \
        "$API_BASE_URL/api/v1/portfolio/positions")
    
    echo "$positions_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print('📊 Current Positions:')
    print('=' * 50)
    for pos in data:
        symbol = pos['symbol']
        quantity = pos['quantity']
        market_value = pos['market_value']
        pnl = pos['unrealized_pnl']
        pnl_color = '✅' if pnl >= 0 else '❌'
        print(f'  {symbol:<8} | Qty: {quantity:>8.0f} | Value: \${market_value:>10,.2f} | P&L: {pnl_color} \${pnl:>8,.2f}')
except:
    print('Error parsing positions data')
"
    
    echo
    
    # Get portfolio performance
    print_status "Fetching portfolio performance..."
    performance_response=$(curl -s -H "Authorization: Bearer $TOKEN" \
        "$API_BASE_URL/api/v1/portfolio/performance")
    
    echo "$performance_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print('💰 Portfolio Performance:')
    print('=' * 50)
    print(f'  Total Value:      \${data[\"total_value\"]:>12,.2f}')
    print(f'  Cash Balance:     \${data[\"cash_balance\"]:>12,.2f}')
    print(f'  Day P&L:          \${data[\"day_pnl\"]:>12,.2f} ({data[\"day_pnl_percent\"]:>6.2f}%)')
    print(f'  Total P&L:        \${data[\"total_pnl\"]:>12,.2f} ({data[\"total_pnl_percent\"]:>6.2f}%)')
    print(f'  Positions Count:  {data[\"positions_count\"]:>15d}')
    print(f'  Last Updated:     {data[\"last_updated\"][:19]}')
except:
    print('Error parsing performance data')
"
    
    echo
}

# Demo order management
demo_order_management() {
    print_status "=== Order Management Demo ==="
    echo
    
    # Submit sample orders
    orders_to_submit=(
        '{"symbol": "AAPL", "side": "buy", "quantity": 10, "order_type": "market"}'
        '{"symbol": "GOOGL", "side": "buy", "quantity": 5, "order_type": "limit", "limit_price": 2500.00}'
        '{"symbol": "MSFT", "side": "sell", "quantity": 20, "order_type": "market"}'
        '{"symbol": "TSLA", "side": "buy", "quantity": 15, "order_type": "limit", "limit_price": 200.00}'
    )
    
    order_ids=()
    
    print_status "Submitting sample orders..."
    for order_data in "${orders_to_submit[@]}"; do
        response=$(curl -s -X POST "$API_BASE_URL/api/v1/orders" \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -d "$order_data")
        
        # Extract order details
        echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'  ✅ Order {data[\"order_id\"]}: {data[\"side\"].upper()} {data[\"quantity\"]} {data[\"symbol\"]} ({data[\"status\"]})')
    print(data['order_id'])
except:
    print('  ❌ Order submission failed')
" | {
            read order_info
            read order_id
            echo "$order_info"
            if [ -n "$order_id" ]; then
                order_ids+=("$order_id")
            fi
        }
        
        sleep 0.5  # Small delay between orders
    done
    
    echo
    
    # Get order history
    print_status "Fetching order history..."
    orders_response=$(curl -s -H "Authorization: Bearer $TOKEN" \
        "$API_BASE_URL/api/v1/orders?limit=10")
    
    echo "$orders_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print('📋 Recent Orders:')
    print('=' * 80)
    print(f'{'Order ID':<15} | {'Symbol':<8} | {'Side':<4} | {'Qty':<8} | {'Status':<10} | {'Submitted At':<20}')
    print('-' * 80)
    for order in data[:5]:  # Show last 5 orders
        order_id = order['order_id'][:12] + '...' if len(order['order_id']) > 15 else order['order_id']
        print(f'{order_id:<15} | {order[\"symbol\"]:<8} | {order[\"side\"].upper():<4} | {order[\"quantity\"]:>8.0f} | {order[\"status\"]:<10} | {order[\"submitted_at\"][:19]}')
except:
    print('Error parsing orders data')
"
    
    echo
}

# Demo risk analysis
demo_risk_analysis() {
    print_status "=== Risk Analysis Demo ==="
    echo
    
    # Get system metrics for risk analysis
    metrics_response=$(curl -s -H "Authorization: Bearer $TOKEN" \
        "$API_BASE_URL/api/v1/system/metrics?hours=24")
    
    echo "$metrics_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print('⚠️  Risk Metrics (Last 24 Hours):')
    print('=' * 50)
    
    if 'daily_pnl' in data:
        current_pnl = data['daily_pnl']['current']
        max_pnl = data['daily_pnl']['max'] 
        min_pnl = data['daily_pnl']['min']
        
        print(f'  Current Daily P&L:    \${current_pnl:>10,.2f}')
        print(f'  Max Daily P&L:        \${max_pnl:>10,.2f}')
        print(f'  Min Daily P&L:        \${min_pnl:>10,.2f}')
        print(f'  P&L Range:            \${max_pnl - min_pnl:>10,.2f}')
        
        # Risk indicators
        if current_pnl < -1000:
            print('  🔴 Risk Level: HIGH (Significant losses)')
        elif current_pnl < 0:
            print('  🟡 Risk Level: MEDIUM (Minor losses)')
        else:
            print('  🟢 Risk Level: LOW (Profitable)')
    
    if 'avg_error_rate' in data:
        error_rate = data['avg_error_rate']
        print(f'  Average Error Rate:   {error_rate:>10.2f}%')
        
        if error_rate > 5:
            print('  🔴 Error Rate: HIGH (System issues detected)')
        elif error_rate > 2:
            print('  🟡 Error Rate: MEDIUM (Monitor closely)')
        else:
            print('  🟢 Error Rate: LOW (System stable)')

except Exception as e:
    print(f'Mock Risk Analysis:')
    print('=' * 50)
    print('  Current Portfolio Value:  \$125,000.00')
    print('  Daily P&L:               \$1,250.50')
    print('  Risk Level:              🟢 LOW')
    print('  Position Concentration:   15% (within limits)')
    print('  Volatility Exposure:      Medium')
"
    
    echo
}

# Demo strategy performance
demo_strategy_performance() {
    print_status "=== Strategy Performance Demo ==="
    echo
    
    # Get strategies list
    strategies_response=$(curl -s -H "Authorization: Bearer $TOKEN" \
        "$API_BASE_URL/api/v1/strategies")
    
    echo "$strategies_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print('🎯 Active Strategies:')
    print('=' * 70)
    print(f'{'Strategy':<20} | {'Status':<10} | {'Return':<8} | {'Sharpe':<6} | {'Drawdown':<10}')
    print('-' * 70)
    
    for strategy in data:
        name = strategy['name'][:18]
        status = strategy['status']
        perf = strategy.get('performance', {})
        total_return = perf.get('total_return', 0)
        sharpe = perf.get('sharpe_ratio', 0)
        drawdown = perf.get('max_drawdown', 0)
        
        print(f'{name:<20} | {status:<10} | {total_return:>6.1f}% | {sharpe:>5.2f} | {drawdown:>8.1f}%')
        
except:
    print('Mock Strategy Performance:')
    print('=' * 70)
    print(f'{'Strategy':<20} | {'Status':<10} | {'Return':<8} | {'Sharpe':<6} | {'Drawdown':<10}')
    print('-' * 70)
    print(f'{'Mean Reversion':<20} | {'Active':<10} | {'8.5%':>8} | {'1.2':>6} | {'-3.2%':>10}')
    print(f'{'Momentum':<20} | {'Active':<10} | {'12.3%':>8} | {'1.8':>6} | {'-5.1%':>10}')
    print(f'{'Market Neutral':<20} | {'Stopped':<10} | {'4.2%':>8} | {'0.9':>6} | {'-1.8%':>10}')
"
    
    echo
}

# Demo portfolio allocation
demo_portfolio_allocation() {
    print_status "=== Portfolio Allocation Demo ==="
    echo
    
    print_status "Current allocation breakdown..."
    
    # Create mock allocation visualization
    python3 -c "
import random

# Mock portfolio data
positions = [
    ('AAPL', 25.5, 38250.0),
    ('GOOGL', 15.2, 38000.0), 
    ('MSFT', 18.8, 28200.0),
    ('TSLA', 12.3, 18450.0),
    ('AMZN', 8.1, 12150.0),
    ('CASH', 20.1, 30150.0)
]

total_value = sum(pos[2] for pos in positions)

print('💰 Portfolio Allocation:')
print('=' * 60)
print(f'{'Asset':<8} | {'Weight':<8} | {'Value':<12} | {'Allocation Bar':<20}')
print('-' * 60)

for symbol, weight, value in positions:
    bar_length = int(weight / 5)  # Scale bar length
    bar = '█' * bar_length + '░' * (20 - bar_length)
    color = '🟢' if symbol == 'CASH' else '🔵'
    print(f'{symbol:<8} | {weight:>6.1f}% | \${value:>10,.0f} | {bar} {color}')

print('-' * 60)
print(f'{'TOTAL':<8} | {'100.0%':>8} | \${total_value:>10,.0f} |')

print('\n📊 Allocation Analysis:')
print(f'  • Equity Exposure:     {100-20.1:.1f}%')
print(f'  • Cash Position:       20.1%')
print(f'  • Top 3 Holdings:      {25.5+15.2+18.8:.1f}%')
print(f'  • Diversification:     Good (6 positions)')

# Risk metrics
print('\n⚠️  Risk Indicators:')
if 25.5 > 25:
    print('  🟡 AAPL concentration slightly high (25.5% > 25% limit)')
else:
    print('  🟢 Position sizes within limits')
    
print('  🟢 Adequate cash buffer (20.1%)')
print('  🟢 Sector diversification maintained')
"
    
    echo
}

# Show management commands
show_management_commands() {
    echo
    print_status "=== Portfolio Management Commands ==="
    echo
    
    echo -e "${YELLOW}📊 Monitoring Commands:${NC}"
    echo "  curl -H 'Authorization: Bearer \$TOKEN' '$API_BASE_URL/api/v1/portfolio/positions'"
    echo "  curl -H 'Authorization: Bearer \$TOKEN' '$API_BASE_URL/api/v1/portfolio/performance'"
    echo
    
    echo -e "${YELLOW}📋 Order Management:${NC}"
    echo "  # Submit market order"
    echo "  curl -X POST '$API_BASE_URL/api/v1/orders' \\"
    echo "    -H 'Authorization: Bearer \$TOKEN' \\"
    echo "    -d '{\"symbol\": \"AAPL\", \"side\": \"buy\", \"quantity\": 10, \"order_type\": \"market\"}'"
    echo
    echo "  # Submit limit order"
    echo "  curl -X POST '$API_BASE_URL/api/v1/orders' \\"
    echo "    -H 'Authorization: Bearer \$TOKEN' \\"
    echo "    -d '{\"symbol\": \"GOOGL\", \"side\": \"sell\", \"quantity\": 5, \"order_type\": \"limit\", \"limit_price\": 2600.00}'"
    echo
    
    echo -e "${YELLOW}📈 Analysis Commands:${NC}"
    echo "  curl -H 'Authorization: Bearer \$TOKEN' '$API_BASE_URL/api/v1/system/metrics?hours=24'"
    echo "  curl -H 'Authorization: Bearer \$TOKEN' '$API_BASE_URL/api/v1/strategies'"
    echo
}

# Main execution
main() {
    print_banner
    
    # Check API accessibility
    if ! curl -s -f "$API_BASE_URL/health" > /dev/null; then
        print_error "❌ API is not accessible at $API_BASE_URL"
        print_error "Please start the demo: ./demo/start-demo.sh"
        exit 1
    fi
    
    load_token
    
    demo_portfolio_overview
    demo_order_management  
    demo_risk_analysis
    demo_strategy_performance
    demo_portfolio_allocation
    show_management_commands
    
    echo
    print_success "🎉 Portfolio Demo Completed!"
    echo -e "${GREEN}🌐 View real-time data at: ${NC}http://localhost:8080"
    echo -e "${GREEN}📚 API Documentation: ${NC}$API_BASE_URL/docs"
    echo
}

# Handle script arguments
case "${1:-demo}" in
    demo)
        main
        ;;
    positions)
        print_banner
        load_token
        demo_portfolio_overview
        ;;
    orders)
        print_banner
        load_token
        demo_order_management
        ;;
    risk)
        print_banner
        load_token
        demo_risk_analysis
        ;;
    commands)
        show_management_commands
        ;;
    *)
        echo "Usage: $0 {demo|positions|orders|risk|commands}"
        echo
        echo "Commands:"
        echo "  demo      - Run complete portfolio demo (default)"
        echo "  positions - Show positions only"
        echo "  orders    - Demo order management"
        echo "  risk      - Show risk analysis"
        echo "  commands  - Show management commands"
        exit 1
        ;;
esac
