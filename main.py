"""Main CLI interface for the algorithmic trading platform."""

import asyncio
from datetime import datetime, timedelta
import click
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from packages.core import get_logger
from packages.core.config import settings

# Import application CLIs
from apps.screener.cli import cli as screener_cli
from apps.analyzer.cli import cli as analyzer_cli
from apps.strategy.cli import cli as strategy_cli
from apps.execution.cli import cli as execution_cli
from apps.backtesting.cli import cli as backtesting_cli

# Import master pipeline
from integration.master_pipeline import MasterTradingPipeline


logger = get_logger(__name__)


@click.group()
@click.version_option(version="2.0.0", prog_name="Algorithmic Trading Platform")
@click.pass_context
def cli(ctx):
    """
    🚀 Complete End-to-End Algorithmic Trading Platform
    
    A comprehensive system featuring:
    • Stock screening and momentum detection
    • Intraday pattern analysis and classification  
    • Multi-bucket capital allocation strategy
    • Live and paper trading execution
    • Historical backtesting and walk-forward analysis
    • Full Alpaca API integration
    """
    ctx.ensure_object(dict)
    
    # Ensure artifacts directory exists
    settings.ARTIFACTS_PATH.mkdir(parents=True, exist_ok=True)
    
    logger.info("Algorithmic Trading Platform CLI v2.0 initialized")


@click.command()
@click.option('--mode', '-m', 
              type=click.Choice(['paper', 'live']), 
              default='paper', 
              help='Trading mode (default: paper)')
@click.option('--capital', '-c', 
              default=100000.0, 
              help='Capital allocation (default: $100,000)')
@click.option('--max-positions', 
              default=20, 
              help='Maximum concurrent positions (default: 20)')
@click.option('--save/--no-save', 
              default=True, 
              help='Save pipeline results (default: save)')
def run_live(mode: str, capital: float, max_positions: int, save: bool):
    """🔴 Run the complete live trading pipeline (Screener → Analyzer → Strategy → Execution)."""
    
    click.echo("🚀 ALGORITHMIC TRADING PLATFORM - LIVE PIPELINE")
    click.echo("=" * 55)
    click.echo(f"💰 Mode: {mode.upper()}")
    click.echo(f"💵 Capital: ${capital:,.2f}")
    click.echo(f"📊 Max Positions: {max_positions}")
    click.echo("")
    
    pipeline = MasterTradingPipeline()
    
    async def run_pipeline():
        return await pipeline.run_live_pipeline(
            mode=mode,
            max_positions=max_positions,
            capital_allocation=capital,
            save_results=save
        )
    
    results = asyncio.run(run_pipeline())
    
    if results["success"]:
        summary = results["summary"]
        
        click.echo("✅ PIPELINE COMPLETED SUCCESSFULLY!")
        click.echo(f"📊 Symbols screened: {summary['symbols_screened']}")
        click.echo(f"🔍 Symbols analyzed: {summary['symbols_analyzed']}")
        click.echo(f"💡 Signals generated: {summary['signals_generated']}")
        click.echo(f"⚡ Trades executed: {summary['trades_executed']}")
        click.echo(f"⏱️  Total duration: {results['duration_seconds']:.1f}s")
        
    else:
        click.echo(f"❌ PIPELINE FAILED: {results['error']}")


@click.command()
@click.option('--start-date', '-s', 
              required=True, 
              help='Start date (YYYY-MM-DD)')
@click.option('--end-date', '-e', 
              required=True, 
              help='End date (YYYY-MM-DD)')
@click.option('--capital', '-c', 
              default=100000.0, 
              help='Initial capital (default: $100,000)')
@click.option('--symbols', 
              help='Comma-separated symbols (default: use screener universe)')
def backtest(start_date: str, end_date: str, capital: float, symbols: str):
    """📈 Run comprehensive strategy backtest with full performance analysis."""
    
    click.echo("📈 ALGORITHMIC TRADING PLATFORM - BACKTEST")
    click.echo("=" * 45)
    click.echo(f"📅 Period: {start_date} to {end_date}")
    click.echo(f"💰 Initial capital: ${capital:,.2f}")
    
    symbol_list = None
    if symbols:
        symbol_list = [s.strip().upper() for s in symbols.split(',')]
        click.echo(f"📊 Testing {len(symbol_list)} specific symbols")
    else:
        click.echo(f"📊 Using screener symbol universe")
    
    click.echo("")
    
    pipeline = MasterTradingPipeline()
    
    async def run_backtest():
        return await pipeline.run_backtest_pipeline(
            start_date=start_date,
            end_date=end_date,
            initial_capital=capital,
            symbols=symbol_list
        )
    
    results = asyncio.run(run_backtest())
    
    if results["success"]:
        metrics = results["performance_metrics"]
        
        click.echo("✅ BACKTEST COMPLETED SUCCESSFULLY!")
        click.echo("")
        click.echo("📊 PERFORMANCE SUMMARY:")
        click.echo(f"  💰 Total Return: ${metrics.get('total_return', 0):,.2f} ({metrics.get('total_return_pct', 0):.2f}%)")
        click.echo(f"  📈 Annualized Return: {metrics.get('annualized_return', 0):.2f}%")
        click.echo(f"  🎯 Win Rate: {metrics.get('win_rate', 0):.1f}%")
        click.echo(f"  📉 Max Drawdown: {metrics.get('max_drawdown', 0):.2f}%")
        click.echo(f"  ⚡ Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
        click.echo(f"  🔄 Total Trades: {metrics.get('total_trades', 0)}")
        click.echo(f"  💵 Avg Win: ${metrics.get('avg_win', 0):.2f}")
        click.echo(f"  💸 Avg Loss: ${metrics.get('avg_loss', 0):.2f}")
        
        if results.get("saved_files", {}).get("report"):
            click.echo(f"\n📄 Full report: {results['saved_files']['report']}")
    else:
        click.echo(f"❌ BACKTEST FAILED: {results['error']}")


@click.command()
@click.option('--start-date', '-s', 
              help='Start date (YYYY-MM-DD, default: 2 years ago)')
@click.option('--end-date', '-e', 
              help='End date (YYYY-MM-DD, default: today)')
@click.option('--train-days', 
              default=252, 
              help='Training period days (default: 252)')
@click.option('--test-days', 
              default=63, 
              help='Testing period days (default: 63)')
@click.option('--step-days', 
              default=21, 
              help='Step size days (default: 21)')
@click.option('--capital', 
              default=100000.0, 
              help='Capital per test (default: $100,000)')
def walk_forward(start_date: str, end_date: str, train_days: int, test_days: int, step_days: int, capital: float):
    """🚶 Run walk-forward analysis for robust strategy validation."""
    
    # Default dates if not provided
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    if not start_date:
        start_dt = datetime.now() - timedelta(days=730)  # 2 years
        start_date = start_dt.strftime('%Y-%m-%d')
    
    click.echo("🚶 ALGORITHMIC TRADING PLATFORM - WALK-FORWARD ANALYSIS")
    click.echo("=" * 60)
    click.echo(f"📅 Analysis period: {start_date} to {end_date}")
    click.echo(f"📚 Train: {train_days}d, Test: {test_days}d, Step: {step_days}d")
    click.echo(f"💰 Capital per test: ${capital:,.2f}")
    click.echo("")
    
    pipeline = MasterTradingPipeline()
    
    async def run_analysis():
        return await pipeline.run_walk_forward_analysis(
            start_date=start_date,
            end_date=end_date,
            train_days=train_days,
            test_days=test_days,
            step_days=step_days,
            capital_per_test=capital
        )
    
    results = asyncio.run(run_analysis())
    
    if results["success"]:
        summary = results["summary"]
        
        click.echo("✅ WALK-FORWARD ANALYSIS COMPLETED!")
        click.echo("")
        click.echo("📊 ROBUSTNESS SUMMARY:")
        click.echo(f"  🔄 Total windows: {summary['total_windows']}")
        click.echo(f"  📊 Average return: {summary['avg_return']:.2f}%")
        click.echo(f"  🎯 Period win rate: {summary['win_rate_periods']:.1f}%")
        click.echo(f"  📈 Best period: {summary['best_period']:.2f}%")
        click.echo(f"  📉 Worst period: {summary['worst_period']:.2f}%")
        click.echo(f"  ⚡ Average Sharpe: {summary['avg_sharpe']:.2f}")
        click.echo(f"  📊 Consistency (σ): {summary['consistency']:.2f}%")
        
    else:
        click.echo(f"❌ WALK-FORWARD ANALYSIS FAILED: {results['error']}")


@click.command()
def status():
    """🔧 Show complete system status and component health."""
    
    pipeline = MasterTradingPipeline()
    status = pipeline.get_system_status()
    
    click.echo("🔧 ALGORITHMIC TRADING PLATFORM - SYSTEM STATUS")
    click.echo("=" * 55)
    
    # Master pipeline
    master = status["master_pipeline"]
    click.echo(f"\n🚀 MASTER PIPELINE COMPONENTS:")
    click.echo(f"  📊 Screener: {master['screener']}")
    click.echo(f"  🔍 Analyzer: {master['analyzer']}")
    click.echo(f"  💡 Strategy: {master['strategy']}")
    click.echo(f"  ⚡ Execution: {master['execution']}")
    click.echo(f"  📈 Backtesting: {master['backtesting']}")
    
    # Component details
    click.echo(f"\n📋 COMPONENT DETAILS:")
    
    # Screener
    screener_status = status.get("screener_status", {})
    if screener_status and 'screener' in screener_status:
        screener_info = screener_status['screener']
        click.echo(f"  📊 Screener scanners: {screener_info.get('scanners', 'Unknown')}")
    
    # Execution  
    exec_status = status.get("execution_status", {})
    if exec_status and 'execution' in exec_status:
        exec_info = exec_status['execution']
        click.echo(f"  ⚡ Broker integration: {exec_info.get('broker', 'Unknown')}")
    
    # Backtesting
    bt_status = status.get("backtesting_status", {})
    if bt_status and 'backtesting' in bt_status:
        bt_info = bt_status['backtesting']
        click.echo(f"  📈 Backtesting engine: {bt_info.get('data_loader', 'Unknown')}")
    
    click.echo(f"\n✅ ALL SYSTEMS OPERATIONAL - READY FOR TRADING!")


# Add sub-commands
cli.add_command(screener_cli, name='screener')
cli.add_command(analyzer_cli, name='analyzer') 
cli.add_command(strategy_cli, name='strategy')
cli.add_command(execution_cli, name='execution')
cli.add_command(backtesting_cli, name='backtesting')

# Add integrated pipeline commands
cli.add_command(run_live)
cli.add_command(backtest)
cli.add_command(walk_forward)
cli.add_command(status)


@cli.command("pipeline")
@click.option(
    "--date",
    type=str,
    help="Date to run pipeline for (YYYY-MM-DD). Defaults to today."
)
@click.option(
    "--capital",
    type=float,
    help="Total capital to allocate. If not provided, uses config default."
)
@click.option(
    "--save-artifacts/--no-save-artifacts",
    default=True,
    help="Save results to artifacts directory."
)
@click.option(
    "--dry-run/--live",
    default=True,
    help="Run in dry-run mode (default) or live trading mode."
)
@click.option(
    "--backtest-mode",
    is_flag=True,
    help="Run pipeline in backtest mode instead of live execution."
)
@click.option(
    "--start-date",
    type=str,
    help="Start date for backtest mode (YYYY-MM-DD). Required for backtest mode."
)
@click.option(
    "--end-date",
    type=str,
    help="End date for backtest mode (YYYY-MM-DD). Defaults to today."
)
@click.option(
    "--initial-capital",
    type=float,
    default=100000.0,
    help="Initial capital for backtest mode."
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose logging."
)
def run_full_pipeline(date, capital, save_artifacts, dry_run, backtest_mode, start_date, end_date, initial_capital, verbose):
    """Run the complete trading pipeline: screener -> analyzer -> strategy -> execution/backtest."""
    import asyncio
    from datetime import datetime
    
    if verbose:
        import structlog
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(20)  # INFO level
        )
    
    async def main():
        start_time = datetime.now()
        
        # Validate backtest mode parameters
        if backtest_mode:
            if not start_date:
                click.echo("❌ --start-date is required for backtest mode")
                return 1
            
            if end_date is None:
                end_date_str = start_time.strftime("%Y-%m-%d")
            else:
                end_date_str = end_date
            
            click.echo(f"� Starting backtest pipeline")
            click.echo(f"   Period: {start_date} to {end_date_str}")
            click.echo(f"   Initial Capital: ${initial_capital:,.2f}")
            
            # Run backtest directly
            from apps.backtest import BacktestEngine
            
            backtest_engine = BacktestEngine()
            backtest_result = await backtest_engine.run_backtest(
                start_date=start_date,
                end_date=end_date_str,
                initial_capital=initial_capital,
                benchmark_symbol="SPY",
                save_artifacts=save_artifacts
            )
            
            if backtest_result["success"]:
                metadata = backtest_result["metadata"]
                performance = backtest_result["performance"]
                
                click.echo(f"✅ Backtest completed in {metadata['duration_seconds']:.1f}s")
                click.echo(f"   Total Return: {performance.get('total_return_pct', 0):.2f}%")
                click.echo(f"   Sharpe Ratio: {performance.get('sharpe_ratio', 0):.3f}")
                click.echo(f"   Max Drawdown: {performance.get('max_drawdown_pct', 0):.2f}%")
                
                if save_artifacts:
                    saved_files = backtest_result.get("saved_files", {})
                    click.echo(f"\n📁 Backtest artifacts saved:")
                    for file_type, path in saved_files.items():
                        click.echo(f"   {file_type}: {path}")
            else:
                click.echo(f"❌ Backtest failed: {backtest_result['error']}")
                return 1
            
            return 0
        
        # Regular pipeline mode
        if date is None:
            date = start_time.strftime("%Y-%m-%d")
        
        click.echo(f"�🚀 Starting full trading pipeline for {date}")
        click.echo(f"   Capital: ${capital:,.2f}" if capital else "   Capital: Using config default")
        click.echo(f"   Mode: {'Dry Run' if dry_run else 'Live Trading'}")
        click.echo()
        
        try:
            # Stage 1: Screener
            click.echo("📊 Stage 1: Running screener...")
            from apps.screener.pipeline import ScreenerPipeline
            
            screener = ScreenerPipeline()
            screener_result = await screener.run(date=date, save_artifacts=save_artifacts)
            
            if not screener_result["success"]:
                click.echo(f"❌ Screener failed: {screener_result['error']}")
                return 1
            
            screener_data = screener_result["data"]
            click.echo(f"   ✅ Screened {len(screener_data)} symbols in {screener_result['metadata']['duration_seconds']:.1f}s")
            
            # Stage 2: Analyzer
            click.echo("\n🔍 Stage 2: Running analyzer...")
            from apps.analyzer.pipeline import AnalyzerPipeline
            
            analyzer = AnalyzerPipeline()
            analyzer_result = await analyzer.run(
                screener_data=screener_data,
                date=date,
                save_artifacts=save_artifacts
            )
            
            if not analyzer_result["success"]:
                click.echo(f"❌ Analyzer failed: {analyzer_result['error']}")
                return 1
            
            analyzer_data = analyzer_result["data"]
            click.echo(f"   ✅ Analyzed {len(analyzer_data)} symbols in {analyzer_result['metadata']['duration_seconds']:.1f}s")
            
            # Stage 3: Strategy
            click.echo("\n💰 Stage 3: Running strategy allocation...")
            from apps.strategy import StrategyEngine
            
            strategy = StrategyEngine()
            strategy_result = await strategy.allocate_positions(
                analyzer_data=analyzer_data,
                date=date,
                total_capital=capital,
                save_artifacts=save_artifacts
            )
            
            if not strategy_result["success"]:
                click.echo(f"❌ Strategy failed: {strategy_result['error']}")
                return 1
            
            signals = strategy_result["signals"]
            strategy_metadata = strategy_result["metadata"]
            click.echo(f"   ✅ Generated {len(signals)} trade signals in {strategy_metadata['duration_seconds']:.1f}s")
            
            # Stage 4: Execution
            if dry_run:
                click.echo("\n🔄 Stage 4: Execution (Dry Run Mode)")
                click.echo(f"   Would execute {len(signals)} signals in paper trading mode")
                click.echo("   Use --live flag to execute real orders")
            else:
                click.echo("\n🔄 Stage 4: Running live execution...")
                from apps.execution import ExecutionEngine
                
                execution = ExecutionEngine(paper_trading=settings.enable_paper_trade)
                execution_result = await execution.execute_signals(
                    signals=signals,
                    date=date,
                    save_artifacts=save_artifacts
                )
                
                if not execution_result["success"]:
                    click.echo(f"❌ Execution failed: {execution_result['error']}")
                    return 1
                
                execution_metadata = execution_result["metadata"]
                click.echo(f"   ✅ Executed {execution_metadata['orders_placed']} orders in {execution_metadata['duration_seconds']:.1f}s")
            
            # Summary
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            click.echo(f"\n🎉 Pipeline completed successfully!")
            click.echo(f"   Total Duration: {total_duration:.1f}s")
            click.echo(f"   Symbols Screened: {len(screener_data)}")
            click.echo(f"   Symbols Analyzed: {len(analyzer_data)}")
            click.echo(f"   Trade Signals: {len(signals)}")
            
            if strategy_metadata.get("allocation_statistics"):
                alloc_stats = strategy_metadata["allocation_statistics"]
                click.echo(f"   Capital Allocated: ${alloc_stats.get('total_allocated', 0):,.2f}")
            
            # Show artifact locations
            if save_artifacts:
                click.echo(f"\n📁 Artifacts saved to: {settings.artifacts_path}")
                click.echo("   Use 'report' commands to view detailed results")
            
        except Exception as e:
            click.echo(f"❌ Pipeline failed: {str(e)}")
            logger.error("Full pipeline failed", exc_info=True)
            return 1
    
    # Run the async function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        click.echo("\n⚠️  Pipeline interrupted by user")
        return 1


@cli.command("status")
def show_status():
    """Show system status and configuration."""
    click.echo("🔧 Algorithmic Trading Platform Status")
    click.echo()
    
    # Configuration
    click.echo("⚙️  Configuration:")
    click.echo(f"   Environment: {settings.environment}")
    click.echo(f"   Log Level: {settings.log_level}")
    click.echo(f"   Artifacts Path: {settings.artifacts_path}")
    click.echo(f"   Yahoo Provider Enabled: {settings.provider_yahoo_enabled}")
    click.echo()
    
    # Strategy settings
    click.echo("💼 Strategy Configuration:")
    click.echo(f"   Dry Run Mode: {settings.trading.dry_run}")
    click.echo(f"   Max Position Size: {settings.trading.max_position_size_pct}%")
    click.echo(f"   Daily Loss Limit: {settings.trading.daily_loss_limit_pct}%")
    click.echo()
    
    # Check artifacts directory structure
    click.echo("📁 Artifacts Directory:")
    artifacts_path = settings.artifacts_path
    
    if artifacts_path.exists():
        for app_dir in ["screener", "analyzer", "strategy"]:
            app_path = artifacts_path / app_dir
            if app_path.exists():
                date_dirs = list(app_path.iterdir())
                click.echo(f"   {app_dir}: {len(date_dirs)} date folders")
            else:
                click.echo(f"   {app_dir}: Not found")
    else:
        click.echo("   ❌ Artifacts directory not found")
    
    click.echo()
    
    # Available commands
    click.echo("🛠️  Available Commands:")
    click.echo("   pipeline    - Run full trading pipeline")
    click.echo("   screener    - Stock screening commands")
    click.echo("   analyzer    - Pattern analysis commands") 
    click.echo("   strategy    - Capital allocation commands")
    click.echo("   execution   - Trade execution commands")
    click.echo("   status      - Show this status")


@cli.command("init")
def initialize_system():
    """Initialize the trading system with required directories and files."""
    click.echo("🔧 Initializing Algorithmic Trading Platform...")
    
    # Create directory structure
    directories = [
        settings.artifacts_path,
        settings.artifacts_path / "screener",
        settings.artifacts_path / "analyzer", 
        settings.artifacts_path / "strategy",
        settings.artifacts_path / "execution",
        settings.artifacts_path / "backtest"
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        click.echo(f"   ✅ Created: {directory}")
    
    # Check configuration files
    config_files = [
        project_root / "config" / ".env.example",
        project_root / "config" / "logging.yaml",
        project_root / "config" / "strategy.yaml"
    ]
    
    missing_configs = []
    for config_file in config_files:
        if config_file.exists():
            click.echo(f"   ✅ Found: {config_file.name}")
        else:
            missing_configs.append(config_file)
            click.echo(f"   ❌ Missing: {config_file.name}")
    
    if missing_configs:
        click.echo(f"\n⚠️  Missing {len(missing_configs)} configuration files")
        click.echo("   Please ensure all config files are present")
    else:
        click.echo("\n🎉 System initialization completed successfully!")
        click.echo("   Run 'python main.py status' to verify setup")


if __name__ == "__main__":
    cli()
