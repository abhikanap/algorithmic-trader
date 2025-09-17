"""Performance analysis and metrics calculation for backtesting."""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from packages.core import get_logger


class PerformanceAnalyzer:
    """Calculates comprehensive performance metrics for backtest results."""
    
    def __init__(self, risk_free_rate: float = 0.02):
        self.logger = get_logger(__name__)
        self.risk_free_rate = risk_free_rate  # Annual risk-free rate
        
        self.logger.info(f"Initialized performance analyzer (risk-free rate: {risk_free_rate:.1%})")
    
    def calculate_metrics(self, simulation_results: Dict[str, Any], initial_capital: float) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics.
        
        Args:
            simulation_results: Results from trading simulation
            initial_capital: Starting capital amount
            
        Returns:
            Dictionary of performance metrics
        """
        self.logger.info("Calculating performance metrics")
        
        trades_df = simulation_results.get("trades_df", pd.DataFrame())
        equity_curve = simulation_results.get("equity_curve", pd.DataFrame())
        final_equity = simulation_results.get("final_equity", initial_capital)
        
        metrics = {}
        
        # Basic return metrics
        metrics.update(self._calculate_return_metrics(final_equity, initial_capital))
        
        # Trade-based metrics
        if not trades_df.empty:
            metrics.update(self._calculate_trade_metrics(trades_df))
        
        # Time-series metrics
        if not equity_curve.empty:
            metrics.update(self._calculate_time_series_metrics(equity_curve, initial_capital))
        
        # Risk metrics
        metrics.update(self._calculate_risk_metrics(equity_curve, trades_df))
        
        # Efficiency metrics
        metrics.update(self._calculate_efficiency_metrics(trades_df, equity_curve))
        
        self.logger.info(f"Calculated {len(metrics)} performance metrics")
        return metrics
    
    def _calculate_return_metrics(self, final_equity: float, initial_capital: float) -> Dict[str, Any]:
        """Calculate basic return metrics."""
        
        total_return = final_equity - initial_capital
        total_return_pct = (total_return / initial_capital) * 100
        
        return {
            "initial_capital": initial_capital,
            "final_equity": final_equity,
            "total_return": total_return,
            "total_return_pct": total_return_pct
        }
    
    def _calculate_trade_metrics(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate trade-based performance metrics."""
        
        if trades_df.empty:
            return {}
        
        # Basic trade statistics
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df["pnl"] > 0])
        losing_trades = len(trades_df[trades_df["pnl"] < 0])
        breakeven_trades = total_trades - winning_trades - losing_trades
        
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # P&L statistics
        total_pnl = trades_df["pnl"].sum()
        gross_pnl = trades_df["gross_pnl"].sum() if "gross_pnl" in trades_df.columns else total_pnl
        
        avg_win = trades_df[trades_df["pnl"] > 0]["pnl"].mean() if winning_trades > 0 else 0
        avg_loss = trades_df[trades_df["pnl"] < 0]["pnl"].mean() if losing_trades > 0 else 0
        
        largest_win = trades_df["pnl"].max()
        largest_loss = trades_df["pnl"].min()
        
        # Risk/reward ratio
        risk_reward_ratio = abs(avg_win / avg_loss) if avg_loss < 0 else 0
        
        # Consecutive trades
        consecutive_wins = self._calculate_consecutive_outcomes(trades_df, "win")
        consecutive_losses = self._calculate_consecutive_outcomes(trades_df, "loss")
        
        # Average hold time
        avg_hold_time = trades_df["hold_time_days"].mean() if "hold_time_days" in trades_df.columns else 0
        
        # Profit factor
        total_wins = trades_df[trades_df["pnl"] > 0]["pnl"].sum() if winning_trades > 0 else 0
        total_losses = abs(trades_df[trades_df["pnl"] < 0]["pnl"].sum()) if losing_trades > 0 else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "breakeven_trades": breakeven_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "gross_pnl": gross_pnl,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "largest_win": largest_win,
            "largest_loss": largest_loss,
            "risk_reward_ratio": risk_reward_ratio,
            "consecutive_wins_max": consecutive_wins,
            "consecutive_losses_max": consecutive_losses,
            "avg_hold_time_days": avg_hold_time,
            "profit_factor": profit_factor
        }
    
    def _calculate_time_series_metrics(self, equity_curve: pd.DataFrame, initial_capital: float) -> Dict[str, Any]:
        """Calculate time-series based metrics."""
        
        if equity_curve.empty or "equity" not in equity_curve.columns:
            return {}
        
        equity_series = equity_curve["equity"]
        
        # Calculate daily returns
        returns = equity_series.pct_change().dropna()
        
        # Annualized return
        total_days = len(equity_curve)
        years = total_days / 365.25
        annualized_return = ((equity_series.iloc[-1] / initial_capital) ** (1/years) - 1) * 100 if years > 0 else 0
        
        # Volatility (annualized)
        volatility = returns.std() * np.sqrt(252) * 100 if len(returns) > 1 else 0
        
        # Maximum drawdown
        peak = equity_series.expanding(min_periods=1).max()
        drawdown = (equity_series - peak) / peak
        max_drawdown = drawdown.min() * 100
        
        # Drawdown duration
        drawdown_duration = self._calculate_drawdown_duration(equity_series)
        
        # Calmar ratio
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown < 0 else 0
        
        return {
            "annualized_return": annualized_return,
            "volatility": volatility,
            "max_drawdown": max_drawdown,
            "max_drawdown_duration_days": drawdown_duration,
            "calmar_ratio": calmar_ratio
        }
    
    def _calculate_risk_metrics(self, equity_curve: pd.DataFrame, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate risk-based metrics."""
        
        metrics = {}
        
        # Equity curve risk metrics
        if not equity_curve.empty and "equity" in equity_curve.columns:
            returns = equity_curve["equity"].pct_change().dropna()
            
            if len(returns) > 1:
                # Sharpe ratio
                excess_returns = returns - (self.risk_free_rate / 252)  # Daily risk-free rate
                sharpe_ratio = (excess_returns.mean() / excess_returns.std()) * np.sqrt(252) if excess_returns.std() > 0 else 0
                
                # Sortino ratio (downside deviation)
                downside_returns = returns[returns < 0]
                downside_deviation = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
                sortino_ratio = (returns.mean() * 252) / downside_deviation if downside_deviation > 0 else 0
                
                # Value at Risk (95%)
                var_95 = np.percentile(returns, 5) * 100
                
                metrics.update({
                    "sharpe_ratio": sharpe_ratio,
                    "sortino_ratio": sortino_ratio,
                    "var_95": var_95
                })
        
        # Trade-based risk metrics
        if not trades_df.empty:
            # Expectancy
            win_rate = (trades_df["pnl"] > 0).mean()
            avg_win = trades_df[trades_df["pnl"] > 0]["pnl"].mean() if win_rate > 0 else 0
            avg_loss = trades_df[trades_df["pnl"] < 0]["pnl"].mean() if win_rate < 1 else 0
            
            expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
            
            # Maximum adverse excursion
            max_adverse_excursion = trades_df["max_loss"].min() if "max_loss" in trades_df.columns else 0
            
            # Maximum favorable excursion
            max_favorable_excursion = trades_df["max_profit"].max() if "max_profit" in trades_df.columns else 0
            
            metrics.update({
                "expectancy": expectancy,
                "max_adverse_excursion": max_adverse_excursion,
                "max_favorable_excursion": max_favorable_excursion
            })
        
        return metrics
    
    def _calculate_efficiency_metrics(self, trades_df: pd.DataFrame, equity_curve: pd.DataFrame) -> Dict[str, Any]:
        """Calculate efficiency and consistency metrics."""
        
        metrics = {}
        
        if not trades_df.empty:
            # Trade efficiency
            winning_trades = trades_df[trades_df["pnl"] > 0]
            
            if not winning_trades.empty:
                # Percentage of gains realized vs maximum possible
                realized_gains = winning_trades["pnl"].sum()
                max_possible_gains = winning_trades["max_profit"].sum() if "max_profit" in winning_trades.columns else realized_gains
                
                gain_efficiency = (realized_gains / max_possible_gains) * 100 if max_possible_gains > 0 else 0
                
                metrics["gain_efficiency"] = gain_efficiency
        
        if not equity_curve.empty and "equity" in equity_curve.columns:
            # Consistency metrics
            returns = equity_curve["equity"].pct_change().dropna()
            
            if len(returns) > 0:
                # Percentage of positive periods
                positive_periods = (returns > 0).mean() * 100
                
                # Return consistency (lower standard deviation of returns is better)
                return_consistency = 1 / (1 + returns.std()) if returns.std() > 0 else 1
                
                metrics.update({
                    "positive_periods_pct": positive_periods,
                    "return_consistency": return_consistency
                })
        
        return metrics
    
    def _calculate_consecutive_outcomes(self, trades_df: pd.DataFrame, outcome_type: str) -> int:
        """Calculate maximum consecutive wins or losses."""
        
        if trades_df.empty:
            return 0
        
        if outcome_type == "win":
            outcomes = (trades_df["pnl"] > 0).astype(int)
        else:  # loss
            outcomes = (trades_df["pnl"] < 0).astype(int)
        
        max_consecutive = 0
        current_consecutive = 0
        
        for outcome in outcomes:
            if outcome:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def _calculate_drawdown_duration(self, equity_series: pd.Series) -> int:
        """Calculate maximum drawdown duration in days."""
        
        if len(equity_series) < 2:
            return 0
        
        peak = equity_series.expanding(min_periods=1).max()
        is_drawdown = equity_series < peak
        
        max_duration = 0
        current_duration = 0
        
        for in_drawdown in is_drawdown:
            if in_drawdown:
                current_duration += 1
                max_duration = max(max_duration, current_duration)
            else:
                current_duration = 0
        
        return max_duration
    
    def generate_performance_summary(self, metrics: Dict[str, Any]) -> str:
        """Generate a human-readable performance summary."""
        
        summary_lines = [
            "=== PERFORMANCE SUMMARY ===",
            "",
            f"Total Return: ${metrics.get('total_return', 0):,.2f} ({metrics.get('total_return_pct', 0):.2f}%)",
            f"Annualized Return: {metrics.get('annualized_return', 0):.2f}%",
            f"Max Drawdown: {metrics.get('max_drawdown', 0):.2f}%",
            f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}",
            "",
            f"Total Trades: {metrics.get('total_trades', 0)}",
            f"Win Rate: {metrics.get('win_rate', 0):.1f}%",
            f"Profit Factor: {metrics.get('profit_factor', 0):.2f}",
            f"Risk/Reward Ratio: {metrics.get('risk_reward_ratio', 0):.2f}",
            "",
            f"Average Win: ${metrics.get('avg_win', 0):.2f}",
            f"Average Loss: ${metrics.get('avg_loss', 0):.2f}",
            f"Largest Win: ${metrics.get('largest_win', 0):.2f}",
            f"Largest Loss: ${metrics.get('largest_loss', 0):.2f}",
            "",
            f"Max Consecutive Wins: {metrics.get('consecutive_wins_max', 0)}",
            f"Max Consecutive Losses: {metrics.get('consecutive_losses_max', 0)}",
            f"Average Hold Time: {metrics.get('avg_hold_time_days', 0):.1f} days",
            "",
            "=== END SUMMARY ==="
        ]
        
        return "\n".join(summary_lines)
    
    def create_benchmark_comparison(self, metrics: Dict[str, Any], benchmark_return: float = 10.0) -> Dict[str, Any]:
        """Compare strategy performance to benchmark."""
        
        strategy_return = metrics.get('annualized_return', 0)
        strategy_sharpe = metrics.get('sharpe_ratio', 0)
        strategy_drawdown = metrics.get('max_drawdown', 0)
        
        # Assume benchmark has typical market characteristics
        benchmark_sharpe = benchmark_return / 15.0  # Assume 15% volatility
        benchmark_drawdown = -20.0  # Assume 20% max drawdown
        
        comparison = {
            "strategy_vs_benchmark_return": strategy_return - benchmark_return,
            "strategy_vs_benchmark_sharpe": strategy_sharpe - benchmark_sharpe,
            "strategy_vs_benchmark_drawdown": abs(strategy_drawdown) - abs(benchmark_drawdown),
            "outperformed_benchmark": strategy_return > benchmark_return,
            "better_risk_adjusted": strategy_sharpe > benchmark_sharpe,
            "lower_drawdown": abs(strategy_drawdown) < abs(benchmark_drawdown)
        }
        
        return comparison
