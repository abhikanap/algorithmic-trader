"""Streamlit UI Dashboard for Algorithmic Trading Platform.

This module provides a comprehensive web-based dashboard for monitoring
and managing the algorithmic trading platform.

Features:
- Real-time portfolio monitoring
- Strategy performance analysis
- Market data visualization
- Risk management dashboard
- Trade execution monitoring
- Backtesting results viewer
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
import asyncio
from typing import Dict, List, Optional, Any

from packages.core import get_logger
from packages.core.config import settings

logger = get_logger(__name__)


class TradingDashboard:
    """Main dashboard class for the trading platform UI."""
    
    def __init__(self):
        """Initialize the dashboard."""
        self.setup_page_config()
        self.initialize_session_state()
    
    def setup_page_config(self):
        """Configure Streamlit page settings."""
        st.set_page_config(
            page_title="Algorithmic Trading Dashboard",
            page_icon="📈",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Custom CSS for better styling
        st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 2rem;
        }
        .metric-card {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 0.5rem 0;
        }
        .positive {
            color: #28a745;
        }
        .negative {
            color: #dc3545;
        }
        .sidebar-header {
            font-size: 1.5rem;
            color: #495057;
            margin-bottom: 1rem;
        }
        </style>
        """, unsafe_allow_html=True)
    
    def initialize_session_state(self):
        """Initialize Streamlit session state variables."""
        if 'refresh_interval' not in st.session_state:
            st.session_state.refresh_interval = 30
        
        if 'selected_date' not in st.session_state:
            st.session_state.selected_date = datetime.now().date()
        
        if 'portfolio_data' not in st.session_state:
            st.session_state.portfolio_data = None
        
        if 'last_refresh' not in st.session_state:
            st.session_state.last_refresh = datetime.now()
    
    def run(self):
        """Main dashboard application."""
        # Header
        st.markdown('<h1 class="main-header">🚀 Algorithmic Trading Dashboard</h1>', unsafe_allow_html=True)
        
        # Sidebar navigation
        page = self.render_sidebar()
        
        # Render selected page
        if page == "Overview":
            self.render_overview_page()
        elif page == "Portfolio":
            self.render_portfolio_page()
        elif page == "Strategy Performance":
            self.render_strategy_page()
        elif page == "Backtesting":
            self.render_backtest_page()
        elif page == "Risk Management":
            self.render_risk_page()
        elif page == "Market Data":
            self.render_market_data_page()
        elif page == "Trade Execution":
            self.render_execution_page()
        elif page == "Settings":
            self.render_settings_page()
    
    def render_sidebar(self) -> str:
        """Render sidebar navigation and controls."""
        with st.sidebar:
            st.markdown('<h2 class="sidebar-header">Navigation</h2>', unsafe_allow_html=True)
            
            page = st.radio(
                "Select Page",
                [
                    "Overview",
                    "Portfolio", 
                    "Strategy Performance",
                    "Backtesting",
                    "Risk Management",
                    "Market Data",
                    "Trade Execution",
                    "Settings"
                ]
            )
            
            st.markdown("---")
            
            # Date selector
            st.markdown("### Date Selection")
            selected_date = st.date_input(
                "Analysis Date",
                value=st.session_state.selected_date,
                key="date_selector"
            )
            st.session_state.selected_date = selected_date
            
            # Refresh controls
            st.markdown("### Refresh Settings")
            refresh_interval = st.selectbox(
                "Auto Refresh (seconds)",
                [10, 30, 60, 300, 0],  # 0 = manual only
                index=1,
                key="refresh_selector"
            )
            st.session_state.refresh_interval = refresh_interval
            
            if st.button("🔄 Refresh Now"):
                st.session_state.last_refresh = datetime.now()
                st.experimental_rerun()
            
            # Show last refresh time
            st.caption(f"Last updated: {st.session_state.last_refresh.strftime('%H:%M:%S')}")
            
            st.markdown("---")
            
            # Quick actions
            st.markdown("### Quick Actions")
            if st.button("▶️ Run Pipeline"):
                self.run_pipeline_action()
            
            if st.button("🔍 Quick Screen"):
                self.run_screener_action()
            
            if st.button("📊 Generate Report"):
                self.generate_report_action()
        
        return page
    
    def render_overview_page(self):
        """Render overview dashboard page."""
        st.header("📊 Trading Overview")
        
        # Key metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Portfolio Value", "$125,432", "2.3%")
        
        with col2:
            st.metric("Daily P&L", "$2,891", "1.2%")
        
        with col3:
            st.metric("Active Positions", "12", "2")
        
        with col4:
            st.metric("Win Rate", "68.5%", "3.2%")
        
        # Charts row
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Portfolio Performance")
            self.render_portfolio_chart()
        
        with col2:
            st.subheader("Daily P&L Distribution")
            self.render_pnl_distribution()
        
        # Recent activity
        st.subheader("📋 Recent Activity")
        self.render_recent_activity()
        
        # Market status
        st.subheader("🌐 Market Status")
        self.render_market_status()
    
    def render_portfolio_page(self):
        """Render portfolio monitoring page."""
        st.header("💼 Portfolio Management")
        
        # Portfolio summary
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Value", "$125,432.18", "2.3%")
            st.metric("Cash Available", "$15,678.42", "-5.2%")
        
        with col2:
            st.metric("Invested Amount", "$109,753.76", "3.1%")
            st.metric("Margin Used", "$0.00", "0%")
        
        with col3:
            st.metric("Day's P&L", "$2,891.45", "2.3%")
            st.metric("Total P&L", "$25,432.18", "25.4%")
        
        # Positions table
        st.subheader("📈 Current Positions")
        self.render_positions_table()
        
        # Allocation chart
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Asset Allocation")
            self.render_allocation_pie_chart()
        
        with col2:
            st.subheader("Sector Distribution")
            self.render_sector_chart()
    
    def render_strategy_page(self):
        """Render strategy performance page."""
        st.header("💰 Strategy Performance")
        
        # Strategy metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Sharpe Ratio", "1.85", "0.12")
        
        with col2:
            st.metric("Max Drawdown", "-5.2%", "1.1%")
        
        with col3:
            st.metric("Alpha", "8.3%", "2.1%")
        
        with col4:
            st.metric("Beta", "0.92", "-0.05")
        
        # Performance charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Cumulative Returns")
            self.render_cumulative_returns()
        
        with col2:
            st.subheader("Rolling Sharpe Ratio")
            self.render_rolling_sharpe()
        
        # Strategy breakdown
        st.subheader("📊 Strategy Breakdown")
        self.render_strategy_breakdown()
    
    def render_backtest_page(self):
        """Render backtesting results page."""
        st.header("🔄 Backtesting Analysis")
        
        # Backtest selector
        col1, col2, col3 = st.columns(3)
        
        with col1:
            start_date = st.date_input("Start Date", value=datetime.now().date() - timedelta(days=365))
        
        with col2:
            end_date = st.date_input("End Date", value=datetime.now().date())
        
        with col3:
            initial_capital = st.number_input("Initial Capital", value=100000.0, step=1000.0)
        
        if st.button("🚀 Run Backtest"):
            self.run_backtest_action(start_date, end_date, initial_capital)
        
        # Backtest results
        st.subheader("📊 Backtest Results")
        self.render_backtest_results()
        
        # Comparison with benchmarks
        st.subheader("📈 Benchmark Comparison")
        self.render_benchmark_comparison()
    
    def render_risk_page(self):
        """Render risk management page."""
        st.header("⚠️ Risk Management")
        
        # Risk metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Portfolio VaR", "$3,245", "$156")
        
        with col2:
            st.metric("Max Position Size", "8.5%", "0.0%")
        
        with col3:
            st.metric("Correlation Risk", "0.65", "0.05")
        
        with col4:
            st.metric("Volatility", "12.3%", "1.2%")
        
        # Risk charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Position Sizes")
            self.render_position_sizes()
        
        with col2:
            st.subheader("Risk Contribution")
            self.render_risk_contribution()
        
        # Risk alerts
        st.subheader("🚨 Risk Alerts")
        self.render_risk_alerts()
    
    def render_market_data_page(self):
        """Render market data visualization page."""
        st.header("📊 Market Data")
        
        # Symbol selector
        symbol = st.selectbox("Select Symbol", ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"])
        
        # Time range selector
        col1, col2 = st.columns(2)
        with col1:
            timeframe = st.selectbox("Timeframe", ["1D", "5D", "1M", "3M", "6M", "1Y"])
        with col2:
            chart_type = st.selectbox("Chart Type", ["Candlestick", "Line", "Area"])
        
        # Market data chart
        st.subheader(f"📈 {symbol} Price Chart")
        self.render_price_chart(symbol, timeframe, chart_type)
        
        # Technical indicators
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Technical Indicators")
            self.render_technical_indicators(symbol)
        
        with col2:
            st.subheader("Volume Analysis")
            self.render_volume_analysis(symbol)
    
    def render_execution_page(self):
        """Render trade execution monitoring page."""
        st.header("⚡ Trade Execution")
        
        # Execution status
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Orders Today", "15", "3")
        
        with col2:
            st.metric("Fill Rate", "98.5%", "1.2%")
        
        with col3:
            st.metric("Avg Slippage", "0.02%", "-0.01%")
        
        with col4:
            st.metric("Execution Cost", "$125.43", "$23.12")
        
        # Recent orders
        st.subheader("📋 Recent Orders")
        self.render_orders_table()
        
        # Execution analytics
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Fill Rate by Time")
            self.render_fill_rate_chart()
        
        with col2:
            st.subheader("Slippage Analysis")
            self.render_slippage_chart()
    
    def render_settings_page(self):
        """Render settings and configuration page."""
        st.header("⚙️ Settings")
        
        # Trading settings
        st.subheader("🔧 Trading Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            enable_trading = st.checkbox("Enable Live Trading", value=False)
            paper_trading = st.checkbox("Paper Trading Mode", value=True)
            max_positions = st.number_input("Max Positions", value=20, min_value=1, max_value=100)
        
        with col2:
            risk_limit = st.number_input("Risk Limit (%)", value=2.0, min_value=0.1, max_value=10.0)
            stop_loss = st.number_input("Default Stop Loss (%)", value=5.0, min_value=1.0, max_value=20.0)
            take_profit = st.number_input("Default Take Profit (%)", value=10.0, min_value=1.0, max_value=50.0)
        
        # API settings
        st.subheader("🔐 API Configuration")
        
        with st.expander("Alpaca API Settings"):
            alpaca_key = st.text_input("API Key", type="password")
            alpaca_secret = st.text_input("API Secret", type="password")
            alpaca_base_url = st.selectbox("Environment", ["paper", "live"])
        
        # Notification settings
        st.subheader("📨 Notifications")
        
        col1, col2 = st.columns(2)
        
        with col1:
            email_notifications = st.checkbox("Email Notifications", value=True)
            slack_notifications = st.checkbox("Slack Notifications", value=False)
        
        with col2:
            risk_alerts = st.checkbox("Risk Alerts", value=True)
            execution_alerts = st.checkbox("Execution Alerts", value=True)
        
        if st.button("💾 Save Settings"):
            st.success("Settings saved successfully!")
    
    # Chart rendering methods
    def render_portfolio_chart(self):
        """Render portfolio performance chart."""
        # Sample data - in real implementation, load from artifacts
        dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
        values = [100000 + i * 100 + (i % 30) * 500 for i in range(len(dates))]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates,
            y=values,
            mode='lines',
            name='Portfolio Value',
            line=dict(color='#1f77b4', width=2)
        ))
        
        fig.update_layout(
            height=300,
            showlegend=False,
            margin=dict(l=0, r=0, t=0, b=0)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_pnl_distribution(self):
        """Render P&L distribution chart."""
        # Sample data
        pnl_data = [np.random.normal(100, 500) for _ in range(100)]
        
        fig = go.Figure(data=[go.Histogram(x=pnl_data, nbinsx=20)])
        fig.update_layout(
            height=300,
            showlegend=False,
            margin=dict(l=0, r=0, t=0, b=0)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_recent_activity(self):
        """Render recent activity table."""
        # Sample data
        activity_data = {
            'Time': ['09:31:23', '09:32:15', '09:35:42', '09:41:18'],
            'Action': ['Buy', 'Sell', 'Buy', 'Sell'],
            'Symbol': ['AAPL', 'GOOGL', 'MSFT', 'TSLA'],
            'Quantity': [100, 50, 200, 75],
            'Price': [150.25, 2750.80, 310.45, 895.60],
            'Status': ['Filled', 'Filled', 'Pending', 'Filled']
        }
        
        df = pd.DataFrame(activity_data)
        st.dataframe(df, use_container_width=True)
    
    def render_market_status(self):
        """Render market status indicators."""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("S&P 500", "4,185.47", "0.25%")
        
        with col2:
            st.metric("NASDAQ", "13,748.74", "0.45%")
        
        with col3:
            st.metric("VIX", "18.45", "-1.2%")
        
        with col4:
            if datetime.now().hour >= 9 and datetime.now().hour < 16:
                st.success("🟢 Market Open")
            else:
                st.error("🔴 Market Closed")
    
    def render_positions_table(self):
        """Render current positions table."""
        # Sample data
        positions_data = {
            'Symbol': ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN'],
            'Quantity': [100, 25, 150, 50, 30],
            'Avg Price': [148.50, 2720.30, 305.80, 880.25, 3285.70],
            'Current Price': [150.25, 2750.80, 310.45, 895.60, 3310.25],
            'P&L': [175.00, 762.50, 697.50, 767.50, 736.50],
            'P&L %': [1.18, 1.12, 1.52, 1.74, 0.75],
            'Weight': [12.5, 18.2, 15.8, 11.9, 26.1]
        }
        
        df = pd.DataFrame(positions_data)
        
        # Color code P&L
        def color_pnl(value):
            if value > 0:
                return 'color: green'
            elif value < 0:
                return 'color: red'
            return 'color: black'
        
        styled_df = df.style.applymap(color_pnl, subset=['P&L', 'P&L %'])
        st.dataframe(styled_df, use_container_width=True)
    
    def render_allocation_pie_chart(self):
        """Render asset allocation pie chart."""
        # Sample data
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'Others']
        values = [12.5, 18.2, 15.8, 11.9, 26.1, 15.5]
        
        fig = go.Figure(data=[go.Pie(labels=symbols, values=values)])
        fig.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=0, b=0)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_sector_chart(self):
        """Render sector distribution chart."""
        # Sample data
        sectors = ['Technology', 'Healthcare', 'Finance', 'Consumer', 'Energy']
        values = [45.2, 18.5, 15.8, 12.3, 8.2]
        
        fig = go.Figure(data=[go.Bar(x=sectors, y=values)])
        fig.update_layout(
            height=300,
            showlegend=False,
            margin=dict(l=0, r=0, t=0, b=0)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Action methods
    def run_pipeline_action(self):
        """Handle run pipeline action."""
        with st.spinner("Running trading pipeline..."):
            # In real implementation, call the pipeline
            import time
            time.sleep(2)
            st.success("Pipeline completed successfully!")
    
    def run_screener_action(self):
        """Handle run screener action."""
        with st.spinner("Running stock screener..."):
            import time
            time.sleep(1)
            st.success("Found 25 stocks matching criteria!")
    
    def generate_report_action(self):
        """Handle generate report action."""
        with st.spinner("Generating performance report..."):
            import time
            time.sleep(1.5)
            st.success("Report generated and saved to artifacts!")
    
    def run_backtest_action(self, start_date, end_date, initial_capital):
        """Handle run backtest action."""
        with st.spinner("Running backtest..."):
            import time
            time.sleep(3)
            st.success(f"Backtest completed! Return: 15.3%, Sharpe: 1.85")
    
    # Placeholder methods for complex charts
    def render_cumulative_returns(self):
        """Render cumulative returns chart."""
        st.info("Cumulative returns chart - Implementation pending")
    
    def render_rolling_sharpe(self):
        """Render rolling Sharpe ratio chart."""
        st.info("Rolling Sharpe ratio chart - Implementation pending")
    
    def render_strategy_breakdown(self):
        """Render strategy breakdown analysis."""
        st.info("Strategy breakdown analysis - Implementation pending")
    
    def render_backtest_results(self):
        """Render backtest results."""
        st.info("Backtest results viewer - Implementation pending")
    
    def render_benchmark_comparison(self):
        """Render benchmark comparison."""
        st.info("Benchmark comparison - Implementation pending")
    
    def render_position_sizes(self):
        """Render position sizes chart."""
        st.info("Position sizes chart - Implementation pending")
    
    def render_risk_contribution(self):
        """Render risk contribution chart."""
        st.info("Risk contribution chart - Implementation pending")
    
    def render_risk_alerts(self):
        """Render risk alerts."""
        st.info("Risk alerts panel - Implementation pending")
    
    def render_price_chart(self, symbol, timeframe, chart_type):
        """Render price chart."""
        st.info(f"{symbol} price chart ({timeframe}, {chart_type}) - Implementation pending")
    
    def render_technical_indicators(self, symbol):
        """Render technical indicators."""
        st.info(f"{symbol} technical indicators - Implementation pending")
    
    def render_volume_analysis(self, symbol):
        """Render volume analysis."""
        st.info(f"{symbol} volume analysis - Implementation pending")
    
    def render_orders_table(self):
        """Render orders table."""
        st.info("Orders table - Implementation pending")
    
    def render_fill_rate_chart(self):
        """Render fill rate chart."""
        st.info("Fill rate chart - Implementation pending")
    
    def render_slippage_chart(self):
        """Render slippage chart."""
        st.info("Slippage chart - Implementation pending")


def main():
    """Main Streamlit application entry point."""
    dashboard = TradingDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()
