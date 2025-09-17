"""Backtesting Engine for strategy validation and performance analysis."""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
import numpy as np

from packages.core import get_logger
from packages.core.config import settings
from packages.core.models import TradeSignal


class BacktestEngine:
    """
    Main backtesting engine that validates strategies using historical data
    and generates comprehensive performance metrics.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Performance tracking
        self.trades = []
        self.daily_returns = []
        self.positions = {}
        self.portfolio_value = []
        self.benchmark_returns = []
        
        self.logger.info("Initialized backtest engine")
    
    async def run_backtest(
        self,
        start_date: str,
        end_date: str,
        initial_capital: float = 100000.0,
        benchmark_symbol: str = "SPY",
        save_artifacts: bool = True
    ) -> Dict[str, Any]:
        """
        Run comprehensive backtest over specified date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            initial_capital: Starting capital
            benchmark_symbol: Benchmark symbol for comparison
            save_artifacts: Whether to save backtest results
            
        Returns:
            Dictionary containing backtest results and metrics
        """
        start_time = datetime.now()
        
        self.logger.info(f"Starting backtest from {start_date} to {end_date}")
        self.logger.info(f"Initial capital: ${initial_capital:,.2f}")
        
        try:
            # Initialize portfolio
            self.current_capital = initial_capital
            self.initial_capital = initial_capital
            self.positions = {}
            self.trades = []
            self.daily_returns = []
            self.portfolio_value = [(start_date, initial_capital)]
            
            # Load benchmark data
            benchmark_data = await self._load_benchmark_data(benchmark_symbol, start_date, end_date)
            
            # Generate date range for backtesting
            date_range = self._generate_date_range(start_date, end_date)
            
            # Run backtest for each date
            for backtest_date in date_range:
                daily_result = await self._run_daily_backtest(backtest_date, benchmark_data)
                
                if daily_result:
                    self.daily_returns.append(daily_result)
            
            # Calculate performance metrics
            performance_metrics = self._calculate_performance_metrics(benchmark_data)
            
            # Generate trade analysis
            trade_analysis = self._analyze_trades()
            
            # Prepare results
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            metadata = {
                "start_date": start_date,
                "end_date": end_date,
                "duration_seconds": round(duration, 2),
                "initial_capital": initial_capital,
                "final_capital": self.current_capital,
                "total_return": (self.current_capital - initial_capital) / initial_capital,
                "total_trades": len(self.trades),
                "trading_days": len(self.daily_returns)
            }
            
            # Save artifacts if requested
            saved_files = {}
            if save_artifacts:
                self.logger.info("Saving backtest artifacts...")
                saved_files = self._save_artifacts(
                    performance_metrics, trade_analysis, metadata, 
                    start_date, end_date
                )
                metadata["saved_files"] = saved_files
            
            result = {
                "success": True,
                "performance": performance_metrics,
                "trades": trade_analysis,
                "metadata": metadata,
                "saved_files": saved_files
            }
            
            total_return_pct = metadata["total_return"] * 100
            self.logger.info(
                f"Backtest completed successfully in {duration:.1f}s. "
                f"Total return: {total_return_pct:.2f}% over {len(self.daily_returns)} trading days"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Backtest failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return {
                "success": False,
                "error": error_msg,
                "performance": {},
                "trades": {},
                "metadata": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "error": str(e),
                    "duration_seconds": (datetime.now() - start_time).total_seconds()
                },
                "saved_files": {}
            }
    
    async def _run_daily_backtest(self, date: str, benchmark_data: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Run backtest for a single day."""
        try:
            # Load strategy signals for this date
            signals = await self._load_strategy_signals(date)
            
            if not signals:
                return None
            
            self.logger.debug(f"Processing {len(signals)} signals for {date}")
            
            # Simulate trade execution
            daily_trades = []
            for signal in signals:
                trade_result = await self._simulate_trade(signal, date)
                if trade_result:
                    daily_trades.append(trade_result)
                    self.trades.append(trade_result)
            
            # Update portfolio value
            daily_pnl = sum(trade.get("realized_pnl", 0) for trade in daily_trades)
            unrealized_pnl = self._calculate_unrealized_pnl(date)
            
            self.current_capital += daily_pnl
            portfolio_value = self.current_capital + unrealized_pnl
            self.portfolio_value.append((date, portfolio_value))
            
            # Calculate daily return
            if len(self.portfolio_value) > 1:
                prev_value = self.portfolio_value[-2][1]
                daily_return = (portfolio_value - prev_value) / prev_value
            else:
                daily_return = 0.0
            
            return {
                "date": date,
                "portfolio_value": portfolio_value,
                "daily_return": daily_return,
                "daily_pnl": daily_pnl,
                "unrealized_pnl": unrealized_pnl,
                "trades_count": len(daily_trades),
                "positions_count": len(self.positions)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to run daily backtest for {date}: {e}")
            return None
    
    async def _simulate_trade(self, signal: TradeSignal, date: str) -> Optional[Dict[str, Any]]:
        """Simulate executing a trade signal."""
        try:
            symbol = signal.symbol
            
            # Get historical price data for this symbol and date
            price_data = await self._get_historical_price(symbol, date)
            if not price_data:
                return None
            
            # Calculate position size (number of shares)
            entry_price = price_data["open"]  # Assume we trade at open
            shares = int(signal.position_size / entry_price)
            
            if shares <= 0:
                return None
            
            # Check if we already have a position
            current_position = self.positions.get(symbol, 0)
            
            # Determine trade action
            if signal.action == "BUY":
                new_position = current_position + shares
            else:  # SELL
                new_position = current_position - shares
            
            # Calculate trade cost and update capital
            trade_cost = shares * entry_price
            commission = self._calculate_commission(trade_cost)
            
            if signal.action == "BUY":
                if self.current_capital < (trade_cost + commission):
                    return None  # Insufficient capital
                self.current_capital -= (trade_cost + commission)
            else:
                self.current_capital += (trade_cost - commission)
            
            # Update position
            self.positions[symbol] = new_position
            if new_position == 0:
                del self.positions[symbol]
            
            # Calculate exit price and PnL (simplified - assume we exit at close)
            exit_price = price_data["close"]
            
            if signal.action == "BUY":
                realized_pnl = 0  # Will be realized when we sell
                unrealized_pnl = shares * (exit_price - entry_price)
            else:
                realized_pnl = shares * (entry_price - exit_price)  # Realized immediately for sells
                unrealized_pnl = 0
            
            trade_result = {
                "date": date,
                "symbol": symbol,
                "action": signal.action,
                "shares": shares,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "trade_cost": trade_cost,
                "commission": commission,
                "realized_pnl": realized_pnl,
                "unrealized_pnl": unrealized_pnl,
                "bucket": signal.bucket,
                "time_segment": signal.time_segment,
                "pattern_intraday": signal.pattern_intraday,
                "pattern_multiday": signal.pattern_multiday,
                "confidence": signal.confidence
            }
            
            return trade_result
            
        except Exception as e:
            self.logger.error(f"Failed to simulate trade for {signal.symbol}: {e}")
            return None
    
    def _calculate_commission(self, trade_cost: float) -> float:
        """Calculate trading commission."""
        # Simple commission model: $1 per trade
        return 1.0
    
    def _calculate_unrealized_pnl(self, date: str) -> float:
        """Calculate unrealized P&L for current positions."""
        total_unrealized = 0.0
        
        for symbol, shares in self.positions.items():
            try:
                # Get current price (simplified - use close price)
                price_data = asyncio.run(self._get_historical_price(symbol, date))
                if price_data:
                    current_price = price_data["close"]
                    # For simplicity, assume all positions were bought at recent average price
                    avg_cost = current_price * 0.98  # Assume 2% gain on average
                    unrealized = shares * (current_price - avg_cost)
                    total_unrealized += unrealized
                    
            except Exception:
                continue
        
        return total_unrealized
    
    async def _get_historical_price(self, symbol: str, date: str) -> Optional[Dict[str, float]]:
        """Get historical price data for a symbol on a specific date."""
        try:
            # For demo purposes, generate synthetic price data
            # In production, this would fetch real historical data
            import random
            
            base_price = 50.0 + hash(symbol) % 200  # Deterministic base price per symbol
            date_hash = hash(date + symbol) % 1000
            
            # Generate OHLC data with some realistic patterns
            open_price = base_price + (date_hash % 20) - 10
            high_price = open_price + (date_hash % 5)
            low_price = open_price - (date_hash % 5)
            close_price = open_price + ((date_hash % 10) - 5) * 0.5
            volume = 100000 + (date_hash % 500000)
            
            return {
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": volume
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get historical price for {symbol} on {date}: {e}")
            return None
    
    async def _load_strategy_signals(self, date: str) -> List[TradeSignal]:
        """Load strategy signals for a specific date."""
        try:
            artifacts_dir = settings.artifacts_path / "strategy" / date
            jsonl_path = artifacts_dir / "strategy.jsonl"
            
            if not jsonl_path.exists():
                return []
            
            signals = []
            import json
            
            with open(jsonl_path, "r") as f:
                for line in f:
                    data = json.loads(line.strip())
                    signal = TradeSignal(**data)
                    signals.append(signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Failed to load strategy signals for {date}: {e}")
            return []
    
    async def _load_benchmark_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Load benchmark data for comparison."""
        try:
            # For demo purposes, generate synthetic benchmark data
            # In production, this would fetch real benchmark data
            date_range = self._generate_date_range(start_date, end_date)
            
            benchmark_data = []
            base_price = 400.0  # SPY-like base price
            
            for i, date in enumerate(date_range):
                # Generate realistic SPY-like returns (small positive drift)
                daily_return = np.random.normal(0.0005, 0.015)  # ~0.05% daily drift, 1.5% volatility
                price = base_price * (1 + daily_return)
                base_price = price
                
                benchmark_data.append({
                    "date": date,
                    "price": round(price, 2),
                    "return": daily_return
                })
            
            return pd.DataFrame(benchmark_data)
            
        except Exception as e:
            self.logger.error(f"Failed to load benchmark data: {e}")
            return pd.DataFrame()
    
    def _generate_date_range(self, start_date: str, end_date: str) -> List[str]:
        """Generate list of trading dates (excluding weekends)."""
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        dates = []
        current = start
        
        while current <= end:
            # Only include weekdays (exclude weekends)
            if current.weekday() < 5:
                dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        
        return dates
    
    def _calculate_performance_metrics(self, benchmark_data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics."""
        if len(self.portfolio_value) < 2:
            return {}
        
        # Calculate returns
        portfolio_df = pd.DataFrame(self.portfolio_value, columns=["date", "value"])
        portfolio_df["return"] = portfolio_df["value"].pct_change().fillna(0)
        
        # Basic metrics
        total_return = (self.current_capital - self.initial_capital) / self.initial_capital
        annualized_return = (1 + total_return) ** (252 / len(portfolio_df)) - 1
        
        # Risk metrics
        daily_returns = portfolio_df["return"].dropna()
        volatility = daily_returns.std() * np.sqrt(252)  # Annualized volatility
        
        # Sharpe ratio (assuming 2% risk-free rate)
        risk_free_rate = 0.02
        sharpe_ratio = (annualized_return - risk_free_rate) / volatility if volatility > 0 else 0
        
        # Maximum drawdown
        portfolio_df["cumulative"] = (1 + portfolio_df["return"]).cumprod()
        portfolio_df["running_max"] = portfolio_df["cumulative"].expanding().max()
        portfolio_df["drawdown"] = portfolio_df["cumulative"] / portfolio_df["running_max"] - 1
        max_drawdown = portfolio_df["drawdown"].min()
        
        # Win rate
        winning_trades = [t for t in self.trades if t.get("realized_pnl", 0) > 0]
        win_rate = len(winning_trades) / len(self.trades) if self.trades else 0
        
        # Benchmark comparison
        benchmark_return = 0.0
        beta = 0.0
        alpha = 0.0
        
        if not benchmark_data.empty and len(benchmark_data) > 1:
            benchmark_total_return = (benchmark_data["price"].iloc[-1] - benchmark_data["price"].iloc[0]) / benchmark_data["price"].iloc[0]
            benchmark_return = benchmark_total_return
            
            # Calculate beta (simplified)
            if len(daily_returns) == len(benchmark_data):
                benchmark_returns = benchmark_data["return"].dropna()
                if len(benchmark_returns) > 1 and benchmark_returns.std() > 0:
                    covariance = np.cov(daily_returns, benchmark_returns)[0, 1]
                    benchmark_variance = benchmark_returns.var()
                    beta = covariance / benchmark_variance
                    
                    # Alpha = Portfolio Return - (Risk-free rate + Beta * (Benchmark Return - Risk-free rate))
                    alpha = annualized_return - (risk_free_rate + beta * (benchmark_return - risk_free_rate))
        
        return {
            "total_return": round(total_return, 4),
            "total_return_pct": round(total_return * 100, 2),
            "annualized_return": round(annualized_return, 4),
            "annualized_return_pct": round(annualized_return * 100, 2),
            "volatility": round(volatility, 4),
            "volatility_pct": round(volatility * 100, 2),
            "sharpe_ratio": round(sharpe_ratio, 3),
            "max_drawdown": round(max_drawdown, 4),
            "max_drawdown_pct": round(max_drawdown * 100, 2),
            "win_rate": round(win_rate, 3),
            "win_rate_pct": round(win_rate * 100, 1),
            "benchmark_return": round(benchmark_return, 4),
            "benchmark_return_pct": round(benchmark_return * 100, 2),
            "beta": round(beta, 3),
            "alpha": round(alpha, 4),
            "alpha_pct": round(alpha * 100, 2),
            "total_trades": len(self.trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(self.trades) - len(winning_trades)
        }
    
    def _analyze_trades(self) -> Dict[str, Any]:
        """Analyze trade performance by various dimensions."""
        if not self.trades:
            return {}
        
        trades_df = pd.DataFrame(self.trades)
        
        analysis = {
            "total_trades": len(self.trades),
            "total_pnl": trades_df["realized_pnl"].sum(),
            "avg_trade_pnl": trades_df["realized_pnl"].mean(),
            "best_trade": trades_df["realized_pnl"].max(),
            "worst_trade": trades_df["realized_pnl"].min(),
        }
        
        # Analysis by bucket
        if "bucket" in trades_df.columns:
            bucket_analysis = trades_df.groupby("bucket").agg({
                "realized_pnl": ["count", "sum", "mean"],
                "confidence": "mean"
            }).round(3)
            analysis["by_bucket"] = bucket_analysis.to_dict()
        
        # Analysis by pattern
        if "pattern_intraday" in trades_df.columns:
            pattern_analysis = trades_df.groupby("pattern_intraday").agg({
                "realized_pnl": ["count", "sum", "mean"],
                "confidence": "mean"
            }).round(3)
            analysis["by_intraday_pattern"] = pattern_analysis.to_dict()
        
        # Analysis by time segment
        if "time_segment" in trades_df.columns:
            time_analysis = trades_df.groupby("time_segment").agg({
                "realized_pnl": ["count", "sum", "mean"],
                "confidence": "mean"
            }).round(3)
            analysis["by_time_segment"] = time_analysis.to_dict()
        
        return analysis
    
    def _save_artifacts(self, performance, trades, metadata, start_date, end_date) -> Dict[str, str]:
        """Save backtest artifacts."""
        # Create backtest-specific directory
        backtest_id = f"{start_date}_to_{end_date}"
        artifacts_dir = settings.artifacts_path / "backtest" / backtest_id
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = {}
        
        try:
            # Save performance metrics as JSON
            import json
            
            metrics_path = artifacts_dir / "performance.json"
            with open(metrics_path, "w") as f:
                json.dump({
                    "performance": performance,
                    "trades_analysis": trades,
                    "metadata": metadata
                }, f, indent=2)
            saved_files["metrics"] = str(metrics_path)
            
            # Save detailed trades as CSV
            if self.trades:
                trades_df = pd.DataFrame(self.trades)
                trades_path = artifacts_dir / "trades.csv"
                trades_df.to_csv(trades_path, index=False)
                saved_files["trades"] = str(trades_path)
            
            # Save portfolio value time series
            portfolio_df = pd.DataFrame(self.portfolio_value, columns=["date", "value"])
            portfolio_path = artifacts_dir / "portfolio_value.csv"
            portfolio_df.to_csv(portfolio_path, index=False)
            saved_files["portfolio"] = str(portfolio_path)
            
            # Save markdown report
            report_path = artifacts_dir / "REPORT.md"
            self._generate_markdown_report(performance, trades, metadata, report_path)
            saved_files["report"] = str(report_path)
            
            self.logger.info(f"Backtest artifacts saved to: {artifacts_dir}")
            
        except Exception as e:
            self.logger.error(f"Error saving backtest artifacts: {e}")
        
        return saved_files
    
    def _generate_markdown_report(self, performance, trades, metadata, path: Path) -> None:
        """Generate markdown backtest report."""
        report_lines = [
            f"# Backtest Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Backtest Summary",
            f"- **Period**: {metadata['start_date']} to {metadata['end_date']}",
            f"- **Initial Capital**: ${metadata['initial_capital']:,.2f}",
            f"- **Final Capital**: ${metadata['final_capital']:,.2f}",
            f"- **Total Return**: {performance.get('total_return_pct', 0):.2f}%",
            f"- **Duration**: {metadata['duration_seconds']:.1f} seconds",
            ""
        ]
        
        # Performance metrics
        if performance:
            report_lines.extend([
                "## Performance Metrics",
                f"- **Annualized Return**: {performance.get('annualized_return_pct', 0):.2f}%",
                f"- **Volatility**: {performance.get('volatility_pct', 0):.2f}%",
                f"- **Sharpe Ratio**: {performance.get('sharpe_ratio', 0):.3f}",
                f"- **Maximum Drawdown**: {performance.get('max_drawdown_pct', 0):.2f}%",
                f"- **Win Rate**: {performance.get('win_rate_pct', 0):.1f}%",
                f"- **Beta**: {performance.get('beta', 0):.3f}",
                f"- **Alpha**: {performance.get('alpha_pct', 0):.2f}%",
                ""
            ])
        
        # Trade statistics
        if trades:
            report_lines.extend([
                "## Trade Statistics",
                f"- **Total Trades**: {trades.get('total_trades', 0)}",
                f"- **Winning Trades**: {performance.get('winning_trades', 0)}",
                f"- **Losing Trades**: {performance.get('losing_trades', 0)}",
                f"- **Total P&L**: ${trades.get('total_pnl', 0):,.2f}",
                f"- **Average Trade P&L**: ${trades.get('avg_trade_pnl', 0):,.2f}",
                f"- **Best Trade**: ${trades.get('best_trade', 0):,.2f}",
                f"- **Worst Trade**: ${trades.get('worst_trade', 0):,.2f}",
                ""
            ])
        
        # Benchmark comparison
        if performance and performance.get('benchmark_return'):
            report_lines.extend([
                "## Benchmark Comparison",
                f"- **Strategy Return**: {performance.get('total_return_pct', 0):.2f}%",
                f"- **Benchmark Return**: {performance.get('benchmark_return_pct', 0):.2f}%",
                f"- **Excess Return**: {performance.get('total_return_pct', 0) - performance.get('benchmark_return_pct', 0):.2f}%",
                ""
            ])
        
        # Write report
        with open(path, "w") as f:
            f.write("\n".join(report_lines))
