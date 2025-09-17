"""Backtesting engine for historical strategy validation."""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
import numpy as np

from packages.core import get_logger
from packages.core.config import settings
from packages.core.models import TradeSignal, BacktestResult

from .data_loader import HistoricalDataLoader
from .simulator import TradingSimulator
from .metrics import PerformanceAnalyzer


class BacktestPipeline:
    """Main backtesting pipeline for strategy validation."""
    
    def __init__(
        self,
        data_loader: Optional[HistoricalDataLoader] = None,
        simulator: Optional[TradingSimulator] = None,
        analyzer: Optional[PerformanceAnalyzer] = None
    ):
        self.logger = get_logger(__name__)
        
        # Initialize components
        self.data_loader = data_loader or HistoricalDataLoader()
        self.simulator = simulator or TradingSimulator()
        self.analyzer = analyzer or PerformanceAnalyzer()
        
        self.logger.info("Initialized backtesting pipeline")
    
    async def run(
        self,
        start_date: str,
        end_date: str,
        initial_capital: float = 100000.0,
        strategy_config: Optional[Dict[str, Any]] = None,
        symbols: Optional[List[str]] = None,
        save_artifacts: bool = True
    ) -> Dict[str, Any]:
        """
        Run a comprehensive backtest.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            initial_capital: Starting capital
            strategy_config: Strategy parameters
            symbols: List of symbols to test (None = use screener)
            save_artifacts: Whether to save results
            
        Returns:
            Backtest results and performance metrics
        """
        run_start_time = datetime.now()
        
        self.logger.info(f"Starting backtest: {start_date} to {end_date}")
        self.logger.info(f"Initial capital: ${initial_capital:,.2f}")
        
        try:
            # Stage 1: Load historical data
            self.logger.info("Loading historical data...")
            historical_data = await self.data_loader.load_data_range(
                start_date, end_date, symbols
            )
            
            if historical_data.empty:
                raise ValueError("No historical data available for backtest period")
            
            # Stage 2: Generate signals using historical pipeline
            self.logger.info("Generating historical signals...")
            signals_df = await self._generate_historical_signals(
                historical_data, strategy_config
            )
            
            if signals_df.empty:
                self.logger.warning("No signals generated for backtest period")
            
            # Stage 3: Run trading simulation
            self.logger.info("Running trading simulation...")
            simulation_results = await self.simulator.simulate_trades(
                signals_df, historical_data, initial_capital
            )
            
            # Stage 4: Analyze performance
            self.logger.info("Analyzing performance...")
            performance_metrics = self.analyzer.calculate_metrics(
                simulation_results, initial_capital
            )
            
            # Stage 5: Generate detailed analysis
            detailed_analysis = await self._generate_detailed_analysis(
                simulation_results, performance_metrics, historical_data
            )
            
            # Prepare results
            end_time = datetime.now()
            duration = (end_time - run_start_time).total_seconds()
            
            metadata = {
                "start_date": start_date,
                "end_date": end_date,
                "duration_seconds": round(duration, 2),
                "initial_capital": initial_capital,
                "total_trades": len(simulation_results.get("trades", [])),
                "strategy_config": strategy_config or {},
                "data_points": len(historical_data)
            }
            
            # Save artifacts if requested
            saved_files = {}
            if save_artifacts:
                self.logger.info("Saving backtest artifacts...")
                saved_files = self._save_artifacts(
                    simulation_results, performance_metrics, detailed_analysis, metadata
                )
                metadata["saved_files"] = saved_files
            
            result = {
                "success": True,
                "simulation_results": simulation_results,
                "performance_metrics": performance_metrics,
                "detailed_analysis": detailed_analysis,
                "metadata": metadata,
                "saved_files": saved_files
            }
            
            self.logger.info(
                f"Backtest completed successfully in {duration:.1f}s. "
                f"Processed {metadata['total_trades']} trades"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Backtest failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return {
                "success": False,
                "error": error_msg,
                "simulation_results": {},
                "performance_metrics": {},
                "detailed_analysis": {},
                "metadata": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "error": str(e),
                    "duration_seconds": (datetime.now() - run_start_time).total_seconds()
                },
                "saved_files": {}
            }
    
    async def _generate_historical_signals(
        self, 
        historical_data: pd.DataFrame, 
        strategy_config: Optional[Dict[str, Any]]
    ) -> pd.DataFrame:
        """Generate trading signals for historical data."""
        
        # This would integrate with the existing pipeline components
        # For now, create simplified signals
        
        signals = []
        
        # Group by date to simulate daily pipeline runs
        dates = historical_data['date'].unique()
        
        for date in sorted(dates):
            try:
                daily_data = historical_data[historical_data['date'] == date]
                
                # Simulate screener (top movers)
                screener_results = self._simulate_screener(daily_data)
                
                if not screener_results.empty:
                    # Simulate analyzer (pattern classification)
                    analyzer_results = self._simulate_analyzer(screener_results)
                    
                    # Simulate strategy (signal generation)
                    daily_signals = self._simulate_strategy(analyzer_results, date)
                    
                    if not daily_signals.empty:
                        signals.append(daily_signals)
                        
            except Exception as e:
                self.logger.error(f"Error generating signals for {date}: {e}")
                continue
        
        if signals:
            return pd.concat(signals, ignore_index=True)
        else:
            return pd.DataFrame()
    
    def _simulate_screener(self, daily_data: pd.DataFrame) -> pd.DataFrame:
        """Simulate screener results for a day."""
        
        if daily_data.empty:
            return pd.DataFrame()
        
        # Calculate basic features
        daily_data = daily_data.copy()
        daily_data['range_pct'] = ((daily_data['high'] - daily_data['low']) / daily_data['close']) * 100
        daily_data['gap_pct'] = ((daily_data['open'] - daily_data['prev_close']) / daily_data['prev_close']) * 100
        daily_data['volume_ratio'] = daily_data['volume'] / daily_data['avg_volume_20d']
        
        # Simple screening criteria
        screener_criteria = (
            (daily_data['range_pct'] > 2.0) |  # Volatile stocks
            (abs(daily_data['gap_pct']) > 2.0) |  # Gapping stocks
            (daily_data['volume_ratio'] > 1.5)  # High volume
        )
        
        screened = daily_data[screener_criteria].copy()
        
        # Add score and rank
        screened['score'] = (
            screened['range_pct'] * 0.3 +
            abs(screened['gap_pct']) * 0.4 +
            screened['volume_ratio'] * 0.3
        )
        
        screened = screened.sort_values('score', ascending=False).head(50)
        screened['rank'] = range(1, len(screened) + 1)
        
        return screened
    
    def _simulate_analyzer(self, screener_data: pd.DataFrame) -> pd.DataFrame:
        """Simulate analyzer pattern classification."""
        
        if screener_data.empty:
            return pd.DataFrame()
        
        analyzer_data = screener_data.copy()
        
        # Simulate pattern classification
        conditions = [
            (analyzer_data['gap_pct'] > 3) & (analyzer_data['close'] < analyzer_data['high'] * 0.9),
            (analyzer_data['gap_pct'] > 2) & (analyzer_data['close'] > analyzer_data['high'] * 0.9),
            (analyzer_data['gap_pct'] < -2) & (analyzer_data['close'] > analyzer_data['low'] * 1.02),
            (analyzer_data['gap_pct'] < -1) & (analyzer_data['close'] < analyzer_data['low'] * 1.05),
        ]
        
        choices = [
            'MORNING_SPIKE_FADE',
            'MORNING_SURGE_UPTREND', 
            'MORNING_PLUNGE_RECOVERY',
            'MORNING_SELLOFF_DOWNTREND'
        ]
        
        analyzer_data['pattern_intraday'] = np.select(conditions, choices, default='CHOPPY_RANGE_BOUND')
        
        # Simulate confidence scores
        analyzer_data['pattern_confidence'] = np.random.uniform(0.5, 0.9, len(analyzer_data))
        
        return analyzer_data
    
    def _simulate_strategy(self, analyzer_data: pd.DataFrame, date: str) -> pd.DataFrame:
        """Simulate strategy signal generation."""
        
        if analyzer_data.empty:
            return pd.DataFrame()
        
        # Filter for high-confidence signals
        signals = analyzer_data[analyzer_data['pattern_confidence'] > 0.6].copy()
        
        if signals.empty:
            return pd.DataFrame()
        
        # Assign buckets based on patterns and price
        conditions = [
            signals['close'] <= 5.0,  # Bucket A: Penny stocks
            (signals['close'] > 10) & (signals['pattern_intraday'].isin(['MORNING_SURGE_UPTREND', 'MORNING_SELLOFF_DOWNTREND'])),
            signals['pattern_intraday'] == 'MORNING_PLUNGE_RECOVERY',  # Bucket C: Multi-day
            signals['gap_pct'].abs() > 5.0,  # Bucket D: Catalyst
        ]
        
        choices = ['BUCKET_A', 'BUCKET_B', 'BUCKET_C', 'BUCKET_D']
        signals['bucket'] = np.select(conditions, choices, default='BUCKET_B')
        
        # Generate signal types
        long_patterns = ['MORNING_SURGE_UPTREND', 'MORNING_PLUNGE_RECOVERY']
        signals['signal_type'] = signals['pattern_intraday'].apply(
            lambda x: 'LONG' if x in long_patterns else 'SHORT'
        )
        
        # Calculate position sizes (simplified)
        signals['position_size'] = 5000  # $5k per position
        signals['shares'] = (signals['position_size'] / signals['close']).astype(int)
        
        # Add trade parameters
        signals['entry_price'] = signals['close']
        signals['stop_loss_pct'] = 3.0
        signals['target_pct'] = 5.0
        
        # Calculate stop and target prices
        for idx, row in signals.iterrows():
            entry = row['entry_price']
            stop_pct = row['stop_loss_pct']
            target_pct = row['target_pct']
            
            if row['signal_type'] == 'LONG':
                signals.at[idx, 'stop_loss_price'] = entry * (1 - stop_pct / 100)
                signals.at[idx, 'target_price'] = entry * (1 + target_pct / 100)
            else:  # SHORT
                signals.at[idx, 'stop_loss_price'] = entry * (1 + stop_pct / 100)
                signals.at[idx, 'target_price'] = entry * (1 - target_pct / 100)
        
        signals['signal_date'] = date
        signals['signal_generated_at'] = pd.Timestamp.now()
        
        return signals.head(10)  # Limit to top 10 signals per day
    
    async def _generate_detailed_analysis(
        self,
        simulation_results: Dict[str, Any],
        performance_metrics: Dict[str, Any],
        historical_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Generate detailed backtest analysis."""
        
        trades_df = simulation_results.get("trades_df", pd.DataFrame())
        equity_curve = simulation_results.get("equity_curve", pd.DataFrame())
        
        analysis = {
            "trade_analysis": self._analyze_trades(trades_df),
            "pattern_analysis": self._analyze_patterns(trades_df),
            "bucket_analysis": self._analyze_buckets(trades_df),
            "risk_analysis": self._analyze_risk(equity_curve, trades_df),
            "market_analysis": self._analyze_market_conditions(historical_data, trades_df)
        }
        
        return analysis
    
    def _analyze_trades(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze trade performance."""
        
        if trades_df.empty:
            return {"message": "No trades to analyze"}
        
        return {
            "total_trades": len(trades_df),
            "winning_trades": len(trades_df[trades_df["pnl"] > 0]),
            "losing_trades": len(trades_df[trades_df["pnl"] < 0]),
            "win_rate": (trades_df["pnl"] > 0).mean() * 100,
            "avg_win": trades_df[trades_df["pnl"] > 0]["pnl"].mean(),
            "avg_loss": trades_df[trades_df["pnl"] < 0]["pnl"].mean(),
            "largest_win": trades_df["pnl"].max(),
            "largest_loss": trades_df["pnl"].min(),
            "avg_hold_time_hours": trades_df.get("hold_time_hours", pd.Series()).mean()
        }
    
    def _analyze_patterns(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze performance by pattern."""
        
        if trades_df.empty or "pattern" not in trades_df.columns:
            return {"message": "No pattern data to analyze"}
        
        pattern_stats = {}
        
        for pattern in trades_df["pattern"].unique():
            pattern_trades = trades_df[trades_df["pattern"] == pattern]
            
            pattern_stats[pattern] = {
                "trades": len(pattern_trades),
                "win_rate": (pattern_trades["pnl"] > 0).mean() * 100,
                "avg_pnl": pattern_trades["pnl"].mean(),
                "total_pnl": pattern_trades["pnl"].sum()
            }
        
        return pattern_stats
    
    def _analyze_buckets(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze performance by bucket."""
        
        if trades_df.empty or "bucket" not in trades_df.columns:
            return {"message": "No bucket data to analyze"}
        
        bucket_stats = {}
        
        for bucket in trades_df["bucket"].unique():
            bucket_trades = trades_df[trades_df["bucket"] == bucket]
            
            bucket_stats[bucket] = {
                "trades": len(bucket_trades),
                "win_rate": (bucket_trades["pnl"] > 0).mean() * 100,
                "avg_pnl": bucket_trades["pnl"].mean(),
                "total_pnl": bucket_trades["pnl"].sum()
            }
        
        return bucket_stats
    
    def _analyze_risk(self, equity_curve: pd.DataFrame, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze risk metrics."""
        
        risk_analysis = {}
        
        if not equity_curve.empty and "equity" in equity_curve.columns:
            returns = equity_curve["equity"].pct_change().dropna()
            
            risk_analysis.update({
                "volatility": returns.std() * np.sqrt(252) * 100,  # Annualized
                "max_drawdown": self._calculate_max_drawdown(equity_curve["equity"]),
                "sharpe_ratio": self._calculate_sharpe_ratio(returns),
                "var_95": np.percentile(returns, 5) * 100  # 95% VaR
            })
        
        if not trades_df.empty:
            risk_analysis.update({
                "consecutive_losses": self._calculate_max_consecutive_losses(trades_df),
                "risk_reward_ratio": self._calculate_risk_reward_ratio(trades_df)
            })
        
        return risk_analysis
    
    def _analyze_market_conditions(self, historical_data: pd.DataFrame, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze how strategy performed in different market conditions."""
        
        # Simplified market condition analysis
        return {
            "message": "Market condition analysis would be implemented here",
            "data_period": f"{historical_data['date'].min()} to {historical_data['date'].max()}" if not historical_data.empty else "N/A"
        }
    
    def _calculate_max_drawdown(self, equity_series: pd.Series) -> float:
        """Calculate maximum drawdown."""
        peak = equity_series.expanding(min_periods=1).max()
        drawdown = (equity_series - peak) / peak
        return drawdown.min() * 100
    
    def _calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio."""
        excess_returns = returns - risk_free_rate / 252  # Daily risk-free rate
        return (excess_returns.mean() / excess_returns.std()) * np.sqrt(252) if excess_returns.std() > 0 else 0
    
    def _calculate_max_consecutive_losses(self, trades_df: pd.DataFrame) -> int:
        """Calculate maximum consecutive losing trades."""
        if trades_df.empty:
            return 0
        
        losses = (trades_df["pnl"] < 0).astype(int)
        max_consecutive = 0
        current_consecutive = 0
        
        for loss in losses:
            if loss:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def _calculate_risk_reward_ratio(self, trades_df: pd.DataFrame) -> float:
        """Calculate average risk/reward ratio."""
        if trades_df.empty:
            return 0
        
        winning_trades = trades_df[trades_df["pnl"] > 0]
        losing_trades = trades_df[trades_df["pnl"] < 0]
        
        if winning_trades.empty or losing_trades.empty:
            return 0
        
        avg_win = winning_trades["pnl"].mean()
        avg_loss = abs(losing_trades["pnl"].mean())
        
        return avg_win / avg_loss if avg_loss > 0 else 0
    
    def _save_artifacts(
        self,
        simulation_results: Dict[str, Any],
        performance_metrics: Dict[str, Any],
        detailed_analysis: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, str]:
        """Save backtest artifacts."""
        
        # Create artifacts directory
        backtest_id = f"backtest_{metadata['start_date']}_{metadata['end_date']}_{datetime.now().strftime('%H%M%S')}"
        artifacts_dir = Path(settings.ARTIFACTS_PATH) / "backtests" / backtest_id
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = {}
        
        try:
            # Save trades
            trades_df = simulation_results.get("trades_df", pd.DataFrame())
            if not trades_df.empty:
                trades_path = artifacts_dir / "trades.parquet"
                trades_df.to_parquet(trades_path, index=False)
                saved_files["trades"] = str(trades_path)
            
            # Save equity curve
            equity_df = simulation_results.get("equity_curve", pd.DataFrame())
            if not equity_df.empty:
                equity_path = artifacts_dir / "equity_curve.parquet"
                equity_df.to_parquet(equity_path, index=False)
                saved_files["equity_curve"] = str(equity_path)
            
            # Save performance metrics
            import json
            metrics_path = artifacts_dir / "performance_metrics.json"
            with open(metrics_path, "w") as f:
                json.dump(performance_metrics, f, indent=2, default=str)
            saved_files["metrics"] = str(metrics_path)
            
            # Save detailed analysis
            analysis_path = artifacts_dir / "detailed_analysis.json"
            with open(analysis_path, "w") as f:
                json.dump(detailed_analysis, f, indent=2, default=str)
            saved_files["analysis"] = str(analysis_path)
            
            # Save metadata
            metadata_path = artifacts_dir / "metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2, default=str)
            saved_files["metadata"] = str(metadata_path)
            
            # Generate report
            report_path = artifacts_dir / "backtest_report.md"
            self._generate_report(simulation_results, performance_metrics, detailed_analysis, metadata, report_path)
            saved_files["report"] = str(report_path)
            
            self.logger.info(f"Saved backtest artifacts to {artifacts_dir}")
            
        except Exception as e:
            self.logger.error(f"Failed to save artifacts: {e}")
        
        return saved_files
    
    def _generate_report(
        self,
        simulation_results: Dict[str, Any],
        performance_metrics: Dict[str, Any],
        detailed_analysis: Dict[str, Any],
        metadata: Dict[str, Any],
        output_path: Path
    ):
        """Generate markdown backtest report."""
        
        with open(output_path, "w") as f:
            f.write(f"# Backtest Report\n\n")
            f.write(f"**Period**: {metadata['start_date']} to {metadata['end_date']}\n")
            f.write(f"**Initial Capital**: ${metadata['initial_capital']:,.2f}\n")
            f.write(f"**Total Trades**: {metadata['total_trades']}\n")
            f.write(f"**Duration**: {metadata['duration_seconds']:.1f}s\n\n")
            
            # Performance summary
            f.write("## Performance Summary\n\n")
            for key, value in performance_metrics.items():
                if isinstance(value, (int, float)):
                    if 'pct' in key or 'rate' in key:
                        f.write(f"- **{key.replace('_', ' ').title()}**: {value:.2f}%\n")
                    elif 'ratio' in key:
                        f.write(f"- **{key.replace('_', ' ').title()}**: {value:.2f}\n")
                    else:
                        f.write(f"- **{key.replace('_', ' ').title()}**: ${value:,.2f}\n")
            f.write("\n")
            
            # Trade analysis
            trade_analysis = detailed_analysis.get("trade_analysis", {})
            if trade_analysis and "message" not in trade_analysis:
                f.write("## Trade Analysis\n\n")
                f.write(f"- **Win Rate**: {trade_analysis.get('win_rate', 0):.1f}%\n")
                f.write(f"- **Average Win**: ${trade_analysis.get('avg_win', 0):.2f}\n")
                f.write(f"- **Average Loss**: ${trade_analysis.get('avg_loss', 0):.2f}\n")
                f.write(f"- **Largest Win**: ${trade_analysis.get('largest_win', 0):.2f}\n")
                f.write(f"- **Largest Loss**: ${trade_analysis.get('largest_loss', 0):.2f}\n\n")
            
            # Pattern analysis
            pattern_analysis = detailed_analysis.get("pattern_analysis", {})
            if pattern_analysis and "message" not in pattern_analysis:
                f.write("## Pattern Performance\n\n")
                f.write("| Pattern | Trades | Win Rate | Avg P&L | Total P&L |\n")
                f.write("|---------|--------|----------|---------|----------|\n")
                
                for pattern, stats in pattern_analysis.items():
                    f.write(f"| {pattern} | {stats['trades']} | {stats['win_rate']:.1f}% | ${stats['avg_pnl']:.2f} | ${stats['total_pnl']:.2f} |\n")
                f.write("\n")
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get pipeline status information."""
        return {
            "backtesting": {
                "data_loader": self.data_loader.__class__.__name__,
                "simulator": self.simulator.__class__.__name__,
                "analyzer": self.analyzer.__class__.__name__
            },
            "settings": {
                "artifacts_path": str(settings.ARTIFACTS_PATH),
                "debug": settings.DEBUG
            }
        }
