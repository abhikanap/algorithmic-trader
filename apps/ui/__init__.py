"""Streamlit UI Package for Algorithmic Trading Platform.

This package provides web-based user interfaces for monitoring and managing
the algorithmic trading platform using Streamlit.

Modules:
- dashboard: Main trading dashboard with portfolio monitoring, strategy analysis, and more
"""

from .dashboard import TradingDashboard, main

__all__ = ["TradingDashboard", "main"]
