"""Advanced analytics and reporting system for the trading platform."""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

from packages.core import get_logger


class PerformanceAnalyzer:
    """Advanced performance analysis and reporting."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)
        
        # Configure plotting style
        plt.style.use('seaborn-v0_8-darkgrid')
        sns.set_palette("husl")
    
    def analyze_strategy_performance(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
        strategy_name: str = "Strategy"
    ) -> Dict[str, Any]:
        """Comprehensive strategy performance analysis."""
        
        results = {
            "strategy_name": strategy_name,
            "analysis_date": datetime.now().isoformat(),
            "period": {
                "start_date": returns.index[0].strftime("%Y-%m-%d"),
                "end_date": returns.index[-1].strftime("%Y-%m-%d"),
                "total_days": len(returns)
            }
        }
        
        # Basic performance metrics
        total_return = (1 + returns).prod() - 1
        annual_return = (1 + total_return) ** (252 / len(returns)) - 1
        volatility = returns.std() * np.sqrt(252)
        
        # Risk metrics
        sharpe_ratio = self._calculate_sharpe_ratio(returns)
        sortino_ratio = self._calculate_sortino_ratio(returns)
        max_drawdown, max_dd_duration = self._calculate_max_drawdown(returns)
        var_95 = self._calculate_var(returns, confidence=0.95)
        cvar_95 = self._calculate_cvar(returns, confidence=0.95)
        
        # Trade statistics (if available)
        winning_days = (returns > 0).sum()
        losing_days = (returns < 0).sum()
        win_rate = winning_days / len(returns) if len(returns) > 0 else 0
        
        results["performance"] = {
            "total_return": float(total_return),
            "annual_return": float(annual_return),
            "volatility": float(volatility),
            "sharpe_ratio": float(sharpe_ratio),
            "sortino_ratio": float(sortino_ratio),
            "max_drawdown": float(max_drawdown),
            "max_drawdown_duration": int(max_dd_duration),
            "var_95": float(var_95),
            "cvar_95": float(cvar_95),
            "win_rate": float(win_rate),
            "best_day": float(returns.max()),
            "worst_day": float(returns.min()),
            "avg_daily_return": float(returns.mean()),
            "skewness": float(returns.skew()),
            "kurtosis": float(returns.kurtosis())
        }
        
        # Benchmark comparison
        if benchmark_returns is not None:
            benchmark_analysis = self._analyze_benchmark_comparison(returns, benchmark_returns)
            results["benchmark_comparison"] = benchmark_analysis
        
        # Rolling metrics
        rolling_analysis = self._analyze_rolling_metrics(returns)
        results["rolling_metrics"] = rolling_analysis
        
        # Monthly/yearly breakdown
        monthly_returns = self._calculate_monthly_returns(returns)
        yearly_returns = self._calculate_yearly_returns(returns)
        
        results["periodic_returns"] = {
            "monthly": monthly_returns,
            "yearly": yearly_returns
        }
        
        return results
    
    def _calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio."""
        excess_returns = returns - risk_free_rate / 252
        return excess_returns.mean() / excess_returns.std() * np.sqrt(252) if excess_returns.std() != 0 else 0
    
    def _calculate_sortino_ratio(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate Sortino ratio."""
        excess_returns = returns - risk_free_rate / 252
        downside_returns = excess_returns[excess_returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(252)
        return excess_returns.mean() * np.sqrt(252) / downside_deviation if downside_deviation != 0 else 0
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> Tuple[float, int]:
        """Calculate maximum drawdown and duration."""
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        
        max_drawdown = drawdown.min()
        
        # Calculate max drawdown duration
        is_drawdown = drawdown < 0
        drawdown_periods = []
        current_period = 0
        
        for is_dd in is_drawdown:
            if is_dd:
                current_period += 1
            else:
                if current_period > 0:
                    drawdown_periods.append(current_period)
                current_period = 0
        
        if current_period > 0:
            drawdown_periods.append(current_period)
        
        max_dd_duration = max(drawdown_periods) if drawdown_periods else 0
        
        return max_drawdown, max_dd_duration
    
    def _calculate_var(self, returns: pd.Series, confidence: float = 0.95) -> float:
        """Calculate Value at Risk."""
        return returns.quantile(1 - confidence)
    
    def _calculate_cvar(self, returns: pd.Series, confidence: float = 0.95) -> float:
        """Calculate Conditional Value at Risk."""
        var = self._calculate_var(returns, confidence)
        return returns[returns <= var].mean()
    
    def _analyze_benchmark_comparison(
        self,
        returns: pd.Series,
        benchmark_returns: pd.Series
    ) -> Dict[str, Any]:
        """Analyze performance vs benchmark."""
        
        # Align series
        aligned_returns, aligned_benchmark = returns.align(benchmark_returns, join='inner')
        
        if len(aligned_returns) == 0:
            return {"error": "No overlapping data with benchmark"}
        
        # Calculate metrics
        excess_returns = aligned_returns - aligned_benchmark
        tracking_error = excess_returns.std() * np.sqrt(252)
        information_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252) if excess_returns.std() != 0 else 0
        
        # Beta calculation
        covariance = np.cov(aligned_returns, aligned_benchmark)[0, 1]
        benchmark_variance = aligned_benchmark.var()
        beta = covariance / benchmark_variance if benchmark_variance != 0 else 0
        
        # Alpha calculation
        risk_free_rate = 0.02 / 252  # Daily risk-free rate
        alpha = (aligned_returns.mean() - risk_free_rate) - beta * (aligned_benchmark.mean() - risk_free_rate)
        alpha_annualized = alpha * 252
        
        # Correlation
        correlation = aligned_returns.corr(aligned_benchmark)
        
        return {
            "beta": float(beta),
            "alpha": float(alpha_annualized),
            "correlation": float(correlation),
            "tracking_error": float(tracking_error),
            "information_ratio": float(information_ratio),
            "excess_return": float(excess_returns.sum()),
            "outperformance_days": int((excess_returns > 0).sum()),
            "underperformance_days": int((excess_returns < 0).sum())
        }
    
    def _analyze_rolling_metrics(self, returns: pd.Series, window: int = 252) -> Dict[str, List]:
        """Calculate rolling performance metrics."""
        
        if len(returns) < window:
            return {"error": f"Insufficient data for {window}-day rolling analysis"}
        
        rolling_returns = returns.rolling(window=window)
        rolling_sharpe = rolling_returns.apply(lambda x: self._calculate_sharpe_ratio(x))
        rolling_volatility = rolling_returns.std() * np.sqrt(252)
        rolling_max_dd = rolling_returns.apply(lambda x: self._calculate_max_drawdown(x)[0])
        
        return {
            "dates": [d.strftime("%Y-%m-%d") for d in rolling_sharpe.dropna().index],
            "sharpe_ratio": rolling_sharpe.dropna().tolist(),
            "volatility": rolling_volatility.dropna().tolist(),
            "max_drawdown": rolling_max_dd.dropna().tolist()
        }
    
    def _calculate_monthly_returns(self, returns: pd.Series) -> List[Dict]:
        """Calculate monthly returns."""
        monthly = returns.resample('M').apply(lambda x: (1 + x).prod() - 1)
        
        return [
            {
                "month": date.strftime("%Y-%m"),
                "return": float(ret)
            }
            for date, ret in monthly.items()
        ]
    
    def _calculate_yearly_returns(self, returns: pd.Series) -> List[Dict]:
        """Calculate yearly returns."""
        yearly = returns.resample('Y').apply(lambda x: (1 + x).prod() - 1)
        
        return [
            {
                "year": date.year,
                "return": float(ret)
            }
            for date, ret in yearly.items()
        ]
    
    def generate_performance_report(
        self,
        analysis_results: Dict[str, Any],
        output_format: str = "html"
    ) -> str:
        """Generate comprehensive performance report."""
        
        strategy_name = analysis_results.get("strategy_name", "Strategy")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if output_format == "html":
            return self._generate_html_report(analysis_results, strategy_name, timestamp)
        elif output_format == "pdf":
            return self._generate_pdf_report(analysis_results, strategy_name, timestamp)
        elif output_format == "json":
            return self._generate_json_report(analysis_results, strategy_name, timestamp)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    def _generate_html_report(self, results: Dict[str, Any], strategy_name: str, timestamp: str) -> str:
        """Generate HTML performance report."""
        
        filename = f"performance_report_{strategy_name}_{timestamp}.html"
        filepath = self.reports_dir / filename
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Performance Report - {strategy_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }}
                .metric-card {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; border-left: 4px solid #007acc; }}
                .metric-title {{ font-weight: bold; color: #333; }}
                .metric-value {{ font-size: 1.2em; color: #007acc; }}
                .section {{ margin: 30px 0; }}
                .section h2 {{ color: #333; border-bottom: 2px solid #007acc; padding-bottom: 5px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f0f0f0; }}
                .positive {{ color: #28a745; }}
                .negative {{ color: #dc3545; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Performance Report: {strategy_name}</h1>
                <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Period: {results['period']['start_date']} to {results['period']['end_date']} ({results['period']['total_days']} days)</p>
            </div>
            
            <div class="section">
                <h2>Key Performance Metrics</h2>
                <div class="metric-grid">
        """
        
        # Add key metrics
        perf = results['performance']
        key_metrics = [
            ("Total Return", f"{perf['total_return']:.2%}"),
            ("Annual Return", f"{perf['annual_return']:.2%}"),
            ("Volatility", f"{perf['volatility']:.2%}"),
            ("Sharpe Ratio", f"{perf['sharpe_ratio']:.2f}"),
            ("Sortino Ratio", f"{perf['sortino_ratio']:.2f}"),
            ("Max Drawdown", f"{perf['max_drawdown']:.2%}"),
            ("Win Rate", f"{perf['win_rate']:.1%}"),
            ("VaR (95%)", f"{perf['var_95']:.2%}")
        ]
        
        for title, value in key_metrics:
            color_class = "positive" if any(term in title.lower() for term in ["return", "ratio", "win"]) and not value.startswith("-") else ""
            if "drawdown" in title.lower() or "var" in title.lower():
                color_class = "negative" if value.startswith("-") else ""
            
            html_content += f"""
                    <div class="metric-card">
                        <div class="metric-title">{title}</div>
                        <div class="metric-value {color_class}">{value}</div>
                    </div>
            """
        
        html_content += """
                </div>
            </div>
        """
        
        # Add monthly returns table
        if 'periodic_returns' in results and results['periodic_returns']['monthly']:
            html_content += """
            <div class="section">
                <h2>Monthly Returns</h2>
                <table>
                    <tr><th>Month</th><th>Return</th></tr>
            """
            
            for month_data in results['periodic_returns']['monthly'][-12:]:  # Last 12 months
                return_val = month_data['return']
                color_class = "positive" if return_val > 0 else "negative" if return_val < 0 else ""
                html_content += f"""
                    <tr>
                        <td>{month_data['month']}</td>
                        <td class="{color_class}">{return_val:.2%}</td>
                    </tr>
                """
            
            html_content += """
                </table>
            </div>
            """
        
        # Add benchmark comparison if available
        if 'benchmark_comparison' in results:
            bench = results['benchmark_comparison']
            html_content += f"""
            <div class="section">
                <h2>Benchmark Comparison</h2>
                <div class="metric-grid">
                    <div class="metric-card">
                        <div class="metric-title">Alpha</div>
                        <div class="metric-value {'positive' if bench['alpha'] > 0 else 'negative'}">{bench['alpha']:.2%}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-title">Beta</div>
                        <div class="metric-value">{bench['beta']:.2f}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-title">Correlation</div>
                        <div class="metric-value">{bench['correlation']:.3f}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-title">Information Ratio</div>
                        <div class="metric-value">{bench['information_ratio']:.2f}</div>
                    </div>
                </div>
            </div>
            """
        
        html_content += """
        </body>
        </html>
        """
        
        with open(filepath, 'w') as f:
            f.write(html_content)
        
        self.logger.info(f"HTML report generated: {filepath}")
        return str(filepath)
    
    def _generate_json_report(self, results: Dict[str, Any], strategy_name: str, timestamp: str) -> str:
        """Generate JSON performance report."""
        
        filename = f"performance_report_{strategy_name}_{timestamp}.json"
        filepath = self.reports_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        
        self.logger.info(f"JSON report generated: {filepath}")
        return str(filepath)
    
    def _generate_pdf_report(self, results: Dict[str, Any], strategy_name: str, timestamp: str) -> str:
        """Generate PDF performance report (placeholder)."""
        # This would require additional libraries like reportlab or weasyprint
        self.logger.warning("PDF generation not implemented. Use HTML format instead.")
        return self._generate_html_report(results, strategy_name, timestamp)
    
    def create_performance_charts(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
        strategy_name: str = "Strategy"
    ) -> List[str]:
        """Create comprehensive performance charts."""
        
        chart_files = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Cumulative returns chart
        plt.figure(figsize=(12, 6))
        cumulative_returns = (1 + returns).cumprod()
        plt.plot(cumulative_returns.index, cumulative_returns.values, label=strategy_name, linewidth=2)
        
        if benchmark_returns is not None:
            aligned_returns, aligned_benchmark = returns.align(benchmark_returns, join='inner')
            cumulative_benchmark = (1 + aligned_benchmark).cumprod()
            plt.plot(cumulative_benchmark.index, cumulative_benchmark.values, label='Benchmark', linewidth=2, alpha=0.8)
        
        plt.title(f'Cumulative Returns - {strategy_name}', fontsize=14, fontweight='bold')
        plt.xlabel('Date')
        plt.ylabel('Cumulative Return')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        chart_file = self.reports_dir / f"cumulative_returns_{strategy_name}_{timestamp}.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        plt.close()
        chart_files.append(str(chart_file))
        
        # 2. Drawdown chart
        plt.figure(figsize=(12, 6))
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        
        plt.fill_between(drawdown.index, drawdown.values, 0, alpha=0.3, color='red')
        plt.plot(drawdown.index, drawdown.values, color='red', linewidth=1)
        plt.title(f'Drawdown - {strategy_name}', fontsize=14, fontweight='bold')
        plt.xlabel('Date')
        plt.ylabel('Drawdown')
        plt.grid(True, alpha=0.3)
        plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.1%}'.format(y)))
        plt.tight_layout()
        
        chart_file = self.reports_dir / f"drawdown_{strategy_name}_{timestamp}.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        plt.close()
        chart_files.append(str(chart_file))
        
        # 3. Rolling Sharpe ratio
        if len(returns) >= 252:
            plt.figure(figsize=(12, 6))
            rolling_sharpe = returns.rolling(window=252).apply(lambda x: self._calculate_sharpe_ratio(x))
            
            plt.plot(rolling_sharpe.index, rolling_sharpe.values, linewidth=2)
            plt.axhline(y=0, color='r', linestyle='--', alpha=0.5)
            plt.title(f'Rolling Sharpe Ratio (1 Year) - {strategy_name}', fontsize=14, fontweight='bold')
            plt.xlabel('Date')
            plt.ylabel('Sharpe Ratio')
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            chart_file = self.reports_dir / f"rolling_sharpe_{strategy_name}_{timestamp}.png"
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            chart_files.append(str(chart_file))
        
        # 4. Returns distribution
        plt.figure(figsize=(10, 6))
        plt.hist(returns.values, bins=50, alpha=0.7, density=True, edgecolor='black')
        plt.axvline(returns.mean(), color='red', linestyle='--', label=f'Mean: {returns.mean():.3f}')
        plt.axvline(returns.median(), color='green', linestyle='--', label=f'Median: {returns.median():.3f}')
        plt.title(f'Daily Returns Distribution - {strategy_name}', fontsize=14, fontweight='bold')
        plt.xlabel('Daily Return')
        plt.ylabel('Density')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.gca().xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: '{:.1%}'.format(x)))
        plt.tight_layout()
        
        chart_file = self.reports_dir / f"returns_distribution_{strategy_name}_{timestamp}.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        plt.close()
        chart_files.append(str(chart_file))
        
        # 5. Monthly returns heatmap
        if len(returns) > 365:
            monthly_returns = returns.resample('M').apply(lambda x: (1 + x).prod() - 1)
            monthly_returns.index = monthly_returns.index.to_period('M')
            
            # Create pivot table for heatmap
            monthly_returns_df = monthly_returns.to_frame('return')
            monthly_returns_df['year'] = monthly_returns_df.index.year
            monthly_returns_df['month'] = monthly_returns_df.index.month
            
            pivot = monthly_returns_df.pivot(index='year', columns='month', values='return')
            
            plt.figure(figsize=(12, 8))
            sns.heatmap(
                pivot * 100,  # Convert to percentage
                annot=True,
                fmt='.1f',
                center=0,
                cmap='RdYlGn',
                cbar_kws={'label': 'Monthly Return (%)'}
            )
            plt.title(f'Monthly Returns Heatmap - {strategy_name}', fontsize=14, fontweight='bold')
            plt.xlabel('Month')
            plt.ylabel('Year')
            plt.tight_layout()
            
            chart_file = self.reports_dir / f"monthly_heatmap_{strategy_name}_{timestamp}.png"
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            chart_files.append(str(chart_file))
        
        self.logger.info(f"Generated {len(chart_files)} performance charts")
        return chart_files


# Mock data generator for testing
def generate_mock_returns(days: int = 252, annual_return: float = 0.10, volatility: float = 0.15) -> pd.Series:
    """Generate mock daily returns for testing."""
    np.random.seed(42)  # For reproducible results
    
    daily_return = annual_return / 252
    daily_vol = volatility / np.sqrt(252)
    
    returns = np.random.normal(daily_return, daily_vol, days)
    dates = pd.date_range(start='2023-01-01', periods=days, freq='D')
    
    return pd.Series(returns, index=dates)


# Global analyzer instance
performance_analyzer = PerformanceAnalyzer()


if __name__ == "__main__":
    # Example usage
    mock_returns = generate_mock_returns(days=500)
    mock_benchmark = generate_mock_returns(days=500, annual_return=0.08, volatility=0.12)
    
    # Analyze performance
    analysis = performance_analyzer.analyze_strategy_performance(
        mock_returns,
        mock_benchmark,
        "Mock Strategy"
    )
    
    # Generate report
    report_path = performance_analyzer.generate_performance_report(analysis, "html")
    print(f"Report generated: {report_path}")
    
    # Create charts
    chart_paths = performance_analyzer.create_performance_charts(
        mock_returns,
        mock_benchmark,
        "Mock Strategy"
    )
    print(f"Charts generated: {chart_paths}")
