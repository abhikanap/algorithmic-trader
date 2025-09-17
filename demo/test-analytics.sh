#!/bin/bash

# Analytics Demo Script - Test the performance analytics system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_banner() {
    echo -e "${BLUE}"
    echo "📊===============================================📊"
    echo "     Trading Platform Analytics Demo          "
    echo "📊===============================================📊"
    echo -e "${NC}"
}

# Generate comprehensive analytics demo
generate_analytics_demo() {
    print_status "Generating comprehensive analytics demo..."
    
    python3 << 'EOF'
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.append('/Users/abhikanap/Documents/Repositories/algorithmic-trader')

try:
    from analytics.performance import performance_analyzer, generate_mock_returns
    
    print("🚀 Starting Analytics Demo...")
    print("=" * 50)
    
    # Create demo directory
    demo_dir = Path("demo/data")
    demo_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate multiple strategy scenarios
    strategies = {
        "Conservative_Strategy": {
            "annual_return": 0.08,
            "volatility": 0.12,
            "description": "Low risk, steady growth strategy"
        },
        "Aggressive_Growth": {
            "annual_return": 0.18,
            "volatility": 0.25,
            "description": "High growth potential with higher risk"
        },
        "Market_Neutral": {
            "annual_return": 0.05,
            "volatility": 0.08,
            "description": "Market neutral long/short strategy"
        },
        "Momentum_Strategy": {
            "annual_return": 0.15,
            "volatility": 0.20,
            "description": "Trend following momentum strategy"
        }
    }
    
    # Generate benchmark (S&P 500 proxy)
    benchmark_returns = generate_mock_returns(
        days=500, 
        annual_return=0.10, 
        volatility=0.16
    )
    
    print(f"📈 Generated benchmark returns ({len(benchmark_returns)} days)")
    
    # Analyze each strategy
    results_summary = []
    
    for strategy_name, params in strategies.items():
        print(f"\n🔍 Analyzing {strategy_name}...")
        
        # Generate strategy returns
        strategy_returns = generate_mock_returns(
            days=500,
            annual_return=params["annual_return"],
            volatility=params["volatility"]
        )
        
        # Perform comprehensive analysis
        analysis = performance_analyzer.analyze_strategy_performance(
            strategy_returns,
            benchmark_returns,
            strategy_name
        )
        
        # Generate reports
        html_report = performance_analyzer.generate_performance_report(
            analysis, "html"
        )
        json_report = performance_analyzer.generate_performance_report(
            analysis, "json"
        )
        
        # Create charts
        chart_files = performance_analyzer.create_performance_charts(
            strategy_returns,
            benchmark_returns,
            strategy_name
        )
        
        # Store results summary
        perf = analysis["performance"]
        results_summary.append({
            "Strategy": strategy_name,
            "Description": params["description"],
            "Total Return": f"{perf['total_return']:.2%}",
            "Annual Return": f"{perf['annual_return']:.2%}",
            "Sharpe Ratio": f"{perf['sharpe_ratio']:.2f}",
            "Max Drawdown": f"{perf['max_drawdown']:.2%}",
            "Win Rate": f"{perf['win_rate']:.1%}",
            "VaR (95%)": f"{perf['var_95']:.2%}",
            "HTML Report": html_report,
            "Charts": len(chart_files)
        })
        
        print(f"  ✅ Total Return: {perf['total_return']:.2%}")
        print(f"  ✅ Sharpe Ratio: {perf['sharpe_ratio']:.2f}")
        print(f"  ✅ Max Drawdown: {perf['max_drawdown']:.2%}")
        print(f"  ✅ Reports: {html_report}")
        print(f"  ✅ Charts: {len(chart_files)} files generated")
    
    # Create comparison DataFrame
    comparison_df = pd.DataFrame(results_summary)
    
    print("\n📊 Strategy Comparison Summary:")
    print("=" * 80)
    for _, row in comparison_df.iterrows():
        print(f"{row['Strategy']:<20} | {row['Total Return']:<10} | {row['Sharpe Ratio']:<10} | {row['Max Drawdown']:<12}")
    
    # Save comparison to CSV
    comparison_file = demo_dir / "strategy_comparison.csv"
    comparison_df.to_csv(comparison_file, index=False)
    print(f"\n📄 Strategy comparison saved to: {comparison_file}")
    
    # Create summary statistics
    print("\n📈 Portfolio Analytics Summary:")
    print("=" * 50)
    
    # Calculate portfolio-level statistics
    total_returns = [float(row['Total Return'].strip('%')) for row in results_summary]
    sharpe_ratios = [float(row['Sharpe Ratio']) for row in results_summary]
    
    print(f"📊 Average Total Return: {np.mean(total_returns):.2f}%")
    print(f"📊 Best Performing Strategy: {comparison_df.loc[comparison_df['Total Return'].str.replace('%', '').astype(float).idxmax(), 'Strategy']}")
    print(f"📊 Highest Sharpe Ratio: {comparison_df.loc[comparison_df['Sharpe Ratio'].astype(float).idxmax(), 'Strategy']}")
    print(f"📊 Most Conservative: {comparison_df.loc[comparison_df['Max Drawdown'].str.replace('%', '').str.replace('-', '').astype(float).idxmin(), 'Strategy']}")
    
    # List all generated files
    print("\n📁 Generated Files:")
    print("=" * 50)
    
    # Count generated files
    reports_dir = Path("reports")
    if reports_dir.exists():
        html_reports = list(reports_dir.glob("*.html"))
        json_reports = list(reports_dir.glob("*.json")) 
        chart_files = list(reports_dir.glob("*.png"))
        
        print(f"📄 HTML Reports: {len(html_reports)}")
        print(f"📄 JSON Reports: {len(json_reports)}")
        print(f"📊 Chart Files: {len(chart_files)}")
        
        # Show recent files
        all_files = html_reports + json_reports + chart_files
        recent_files = sorted(all_files, key=lambda x: x.stat().st_mtime, reverse=True)[:10]
        
        print(f"\n📋 Recent Files (last 10):")
        for i, file_path in enumerate(recent_files, 1):
            file_size = file_path.stat().st_size
            print(f"  {i:2d}. {file_path.name} ({file_size:,} bytes)")
    
    print("\n🎉 Analytics Demo Completed Successfully!")
    print("🌐 View HTML reports by opening them in a web browser")
    print("📊 All charts are saved as high-resolution PNG files")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error generating analytics demo: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF
}

# Show report browser commands
show_browser_commands() {
    echo
    print_status "=== Viewing Generated Reports ==="
    echo
    
    # Find recent HTML reports
    if [ -d "reports" ]; then
        recent_html=$(find reports -name "*.html" -type f -exec ls -t {} + | head -5)
        
        if [ -n "$recent_html" ]; then
            echo -e "${YELLOW}📄 Recent HTML Reports:${NC}"
            echo "$recent_html" | while read -r report; do
                echo "  🌐 open $report"
            done
            echo
            
            echo -e "${YELLOW}🖥️  View in browser:${NC}"
            latest_report=$(echo "$recent_html" | head -1)
            if [[ "$OSTYPE" == "darwin"* ]]; then
                echo "  open \"$latest_report\""
            elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
                echo "  xdg-open \"$latest_report\""
            else
                echo "  Open file: $latest_report"
            fi
        fi
    fi
    
    echo
    print_status "=== Chart Files Location ==="
    echo -e "${YELLOW}📊 Chart files are saved in: ${NC}reports/"
    echo -e "${YELLOW}📈 Supported chart types:${NC}"
    echo "   • Cumulative Returns vs Benchmark"
    echo "   • Drawdown Timeline"  
    echo "   • Rolling Sharpe Ratio"
    echo "   • Returns Distribution"
    echo "   • Monthly Returns Heatmap"
}

# Performance metrics explanation
explain_metrics() {
    echo
    print_status "=== Performance Metrics Explanation ==="
    echo
    
    echo -e "${YELLOW}📊 Key Metrics:${NC}"
    echo "   • Total Return:    Cumulative return over the period"
    echo "   • Annual Return:   Annualized return rate"
    echo "   • Sharpe Ratio:    Risk-adjusted return (>1.0 is good)"
    echo "   • Sortino Ratio:   Downside risk-adjusted return"
    echo "   • Max Drawdown:    Largest peak-to-trough decline"
    echo "   • Win Rate:        Percentage of profitable periods"
    echo "   • VaR (95%):       Value at Risk at 95% confidence"
    echo "   • CVaR:            Conditional Value at Risk"
    echo
    
    echo -e "${YELLOW}🎯 Benchmark Comparison:${NC}"
    echo "   • Alpha:           Excess return vs benchmark"
    echo "   • Beta:            Correlation with market movements"
    echo "   • Information Ratio: Risk-adjusted alpha"
    echo "   • Tracking Error:  Volatility of excess returns"
    echo
}

# Main execution
main() {
    print_banner
    
    # Check if we're in the right directory
    if [ ! -f "analytics/performance.py" ]; then
        print_error "❌ Please run this script from the project root directory"
        exit 1
    fi
    
    generate_analytics_demo
    show_browser_commands
    explain_metrics
    
    echo
    print_success "🎉 Analytics Demo Completed!"
    echo -e "${GREEN}📁 All reports and charts saved to: ${NC}reports/"
    echo -e "${GREEN}📄 Strategy comparison saved to: ${NC}demo/data/strategy_comparison.csv"
    echo
}

# Handle script arguments
case "${1:-demo}" in
    demo)
        main
        ;;
    explain)
        explain_metrics
        ;;
    browse)
        show_browser_commands
        ;;
    *)
        echo "Usage: $0 {demo|explain|browse}"
        echo
        echo "Commands:"
        echo "  demo     - Run complete analytics demo (default)"
        echo "  explain  - Explain performance metrics"
        echo "  browse   - Show commands to view reports"
        exit 1
        ;;
esac
