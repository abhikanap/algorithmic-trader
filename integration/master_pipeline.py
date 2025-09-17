"""End-to-end pipeline integration script."""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List

from packages.core import get_logger
from packages.core.config import settings

# Import all pipeline components
from apps.screener.pipeline import ScreenerPipeline
from apps.analyzer.pipeline import AnalyzerPipeline  
from apps.strategy.pipeline import StrategyPipeline
from apps.execution.pipeline import ExecutionPipeline
from apps.backtesting.pipeline import BacktestPipeline


class MasterTradingPipeline:
    """Master pipeline that coordinates all trading phases."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Initialize all pipeline components
        self.screener = ScreenerPipeline()
        self.analyzer = AnalyzerPipeline()
        self.strategy = StrategyPipeline()
        self.execution = ExecutionPipeline()
        self.backtesting = BacktestPipeline()
        
        self.logger.info("Initialized master trading pipeline")
    
    async def run_live_pipeline(
        self,
        mode: str = "paper",
        max_positions: int = 20,
        capital_allocation: float = 100000.0,
        save_results: bool = True
    ) -> Dict[str, Any]:
        """
        Run the complete live trading pipeline.
        
        Args:
            mode: Trading mode ('paper' or 'live')
            max_positions: Maximum concurrent positions
            capital_allocation: Total capital to allocate
            save_results: Whether to save pipeline results
            
        Returns:
            Pipeline execution results
        """
        run_start = datetime.now()
        
        self.logger.info(f"🚀 Starting live pipeline (mode: {mode})")
        
        try:
            # Phase 1: Screener
            self.logger.info("📊 Phase 1: Running screener...")
            screener_results = await self.screener.run()
            
            if not screener_results["success"]:
                raise Exception(f"Screener failed: {screener_results.get('error')}")
            
            screened_symbols = screener_results["screened_data"]
            self.logger.info(f"✅ Screener found {len(screened_symbols)} candidates")
            
            if not screened_symbols:
                return self._empty_pipeline_result("No symbols passed screening")
            
            # Phase 2: Analyzer
            self.logger.info("🔍 Phase 2: Running pattern analysis...")
            analyzer_results = await self.analyzer.run(screened_symbols)
            
            if not analyzer_results["success"]:
                raise Exception(f"Analyzer failed: {analyzer_results.get('error')}")
            
            analyzed_data = analyzer_results["analyzed_data"]
            self.logger.info(f"✅ Analyzer processed {len(analyzed_data)} symbols")
            
            # Phase 3: Strategy
            self.logger.info("💡 Phase 3: Generating trading signals...")
            strategy_results = await self.strategy.run(
                analyzed_data, 
                capital_allocation=capital_allocation,
                max_positions=max_positions
            )
            
            if not strategy_results["success"]:
                raise Exception(f"Strategy failed: {strategy_results.get('error')}")
            
            trade_signals = strategy_results["signals"]
            self.logger.info(f"✅ Strategy generated {len(trade_signals)} signals")
            
            # Phase 4: Execution (if signals available)
            execution_results = {"success": True, "message": "No signals to execute"}
            
            if trade_signals:
                self.logger.info(f"⚡ Phase 4: Executing {len(trade_signals)} trades...")
                execution_results = await self.execution.run(
                    trade_signals,
                    mode=mode,
                    dry_run=(mode == "paper")
                )
                
                if execution_results["success"]:
                    executed_trades = execution_results.get("executed_trades", [])
                    self.logger.info(f"✅ Executed {len(executed_trades)} trades")
                else:
                    self.logger.error(f"❌ Execution failed: {execution_results.get('error')}")
            
            # Compile results
            duration = (datetime.now() - run_start).total_seconds()
            
            pipeline_results = {
                "success": True,
                "timestamp": run_start.isoformat(),
                "duration_seconds": duration,
                "mode": mode,
                "phases": {
                    "screener": screener_results,
                    "analyzer": analyzer_results,
                    "strategy": strategy_results,
                    "execution": execution_results
                },
                "summary": {
                    "symbols_screened": len(screened_symbols),
                    "symbols_analyzed": len(analyzed_data),
                    "signals_generated": len(trade_signals),
                    "trades_executed": len(execution_results.get("executed_trades", [])),
                    "mode": mode,
                    "capital_allocated": capital_allocation
                }
            }
            
            # Save results if requested
            if save_results:
                self._save_pipeline_results(pipeline_results)
            
            self.logger.info(f"🎉 Live pipeline completed successfully in {duration:.1f}s")
            
            return pipeline_results
            
        except Exception as e:
            error_msg = f"Live pipeline failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return {
                "success": False,
                "timestamp": run_start.isoformat(),
                "duration_seconds": (datetime.now() - run_start).total_seconds(),
                "error": error_msg,
                "mode": mode,
                "phases": {
                    "screener": screener_results if 'screener_results' in locals() else {},
                    "analyzer": analyzer_results if 'analyzer_results' in locals() else {},
                    "strategy": strategy_results if 'strategy_results' in locals() else {},
                    "execution": {"success": False, "error": "Not reached"}
                }
            }
    
    async def run_backtest_pipeline(
        self,
        start_date: str,
        end_date: str,
        initial_capital: float = 100000.0,
        strategy_config: Optional[Dict[str, Any]] = None,
        symbols: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Run historical backtest using the strategy.
        
        Args:
            start_date: Backtest start date (YYYY-MM-DD)
            end_date: Backtest end date (YYYY-MM-DD)
            initial_capital: Starting capital
            strategy_config: Strategy parameters
            symbols: Symbol universe (None = use default)
            
        Returns:
            Backtest results
        """
        self.logger.info(f"📈 Running backtest: {start_date} to {end_date}")
        
        return await self.backtesting.run(
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            strategy_config=strategy_config,
            symbols=symbols,
            save_artifacts=True
        )
    
    async def run_walk_forward_analysis(
        self,
        start_date: str,
        end_date: str,
        train_days: int = 252,
        test_days: int = 63,
        step_days: int = 21,
        capital_per_test: float = 100000.0
    ) -> Dict[str, Any]:
        """
        Run walk-forward analysis for robust strategy validation.
        
        Args:
            start_date: Analysis start date
            end_date: Analysis end date
            train_days: Training period length
            test_days: Testing period length
            step_days: Step size between windows
            capital_per_test: Capital for each test period
            
        Returns:
            Walk-forward analysis results
        """
        self.logger.info(f"🚶 Walk-forward analysis: {start_date} to {end_date}")
        
        # Generate date windows
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        windows = []
        current_start = start_dt
        
        while current_start + timedelta(days=train_days + test_days) <= end_dt:
            train_start = current_start
            train_end = current_start + timedelta(days=train_days)
            test_start = train_end
            test_end = test_start + timedelta(days=test_days)
            
            windows.append({
                'train_start': train_start.strftime('%Y-%m-%d'),
                'train_end': train_end.strftime('%Y-%m-%d'),
                'test_start': test_start.strftime('%Y-%m-%d'),
                'test_end': test_end.strftime('%Y-%m-%d')
            })
            
            current_start += timedelta(days=step_days)
        
        self.logger.info(f"Generated {len(windows)} walk-forward windows")
        
        # Run backtests for each window
        results = []
        
        for i, window in enumerate(windows, 1):
            self.logger.info(f"Window {i}/{len(windows)}: {window['test_start']} to {window['test_end']}")
            
            # Run backtest for this window
            backtest_result = await self.backtesting.run(
                start_date=window['test_start'],
                end_date=window['test_end'],
                initial_capital=capital_per_test,
                save_artifacts=False
            )
            
            if backtest_result['success']:
                metrics = backtest_result['performance_metrics']
                results.append({
                    'window': i,
                    'test_start': window['test_start'],
                    'test_end': window['test_end'],
                    'return_pct': metrics.get('total_return_pct', 0),
                    'trades': metrics.get('total_trades', 0),
                    'win_rate': metrics.get('win_rate', 0),
                    'sharpe': metrics.get('sharpe_ratio', 0),
                    'max_drawdown': metrics.get('max_drawdown', 0)
                })
                
                self.logger.info(f"✅ Window {i}: {metrics.get('total_return_pct', 0):.2f}% return")
            else:
                self.logger.error(f"❌ Window {i} failed: {backtest_result['error']}")
        
        # Aggregate results
        if results:
            import pandas as pd
            results_df = pd.DataFrame(results)
            
            summary = {
                'total_windows': len(results),
                'successful_windows': len(results),
                'avg_return': results_df['return_pct'].mean(),
                'avg_sharpe': results_df['sharpe'].mean(),
                'avg_max_drawdown': results_df['max_drawdown'].mean(),
                'win_rate_periods': (results_df['return_pct'] > 0).mean() * 100,
                'best_period': results_df['return_pct'].max(),
                'worst_period': results_df['return_pct'].min(),
                'consistency': results_df['return_pct'].std()
            }
            
            return {
                'success': True,
                'windows': results,
                'summary': summary,
                'metadata': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'train_days': train_days,
                    'test_days': test_days,
                    'step_days': step_days
                }
            }
        else:
            return {
                'success': False,
                'error': 'No successful windows in walk-forward analysis',
                'windows': [],
                'summary': {},
                'metadata': {}
            }
    
    def _empty_pipeline_result(self, reason: str) -> Dict[str, Any]:
        """Return empty pipeline result."""
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": 0,
            "message": reason,
            "phases": {
                "screener": {"success": True, "screened_data": []},
                "analyzer": {"success": True, "analyzed_data": []},
                "strategy": {"success": True, "signals": []},
                "execution": {"success": True, "executed_trades": []}
            },
            "summary": {
                "symbols_screened": 0,
                "symbols_analyzed": 0,
                "signals_generated": 0,
                "trades_executed": 0
            }
        }
    
    def _save_pipeline_results(self, results: Dict[str, Any]):
        """Save pipeline results to artifacts."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Create pipeline results directory
            results_dir = Path(settings.ARTIFACTS_PATH) / "pipeline_runs" / f"run_{timestamp}"
            results_dir.mkdir(parents=True, exist_ok=True)
            
            # Save complete results
            results_file = results_dir / "pipeline_results.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            # Save summary
            summary_file = results_dir / "summary.json"
            with open(summary_file, 'w') as f:
                json.dump(results.get("summary", {}), f, indent=2, default=str)
            
            self.logger.info(f"💾 Pipeline results saved to {results_dir}")
            
        except Exception as e:
            self.logger.error(f"Failed to save pipeline results: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        return {
            "master_pipeline": {
                "screener": self.screener.__class__.__name__,
                "analyzer": self.analyzer.__class__.__name__,
                "strategy": self.strategy.__class__.__name__,
                "execution": self.execution.__class__.__name__,
                "backtesting": self.backtesting.__class__.__name__
            },
            "screener_status": self.screener.get_pipeline_status(),
            "analyzer_status": self.analyzer.get_pipeline_status(),
            "strategy_status": self.strategy.get_pipeline_status(),
            "execution_status": self.execution.get_pipeline_status(),
            "backtesting_status": self.backtesting.get_pipeline_status()
        }
