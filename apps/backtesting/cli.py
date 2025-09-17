"""Command-line interface for the backtesting engine."""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

import click
import pandas as pd

from packages.core import get_logger
from packages.core.config import settings

from .pipeline import BacktestPipeline
from .data_loader import HistoricalDataLoader
from .simulator import TradingSimulator
from .metrics import PerformanceAnalyzer


logger = get_logger(__name__)


@click.group()
def cli():
    """Algorithmic Trading Backtesting Engine"""
    pass


@click.command()
@click.option('--start-date', '-s', required=True, help='Start date (YYYY-MM-DD)')
@click.option('--end-date', '-e', required=True, help='End date (YYYY-MM-DD)')
@click.option('--capital', '-c', default=100000.0, help='Initial capital (default: $100,000)')
@click.option('--symbols', help='Comma-separated list of symbols (default: use screener)')
@click.option('--commission', default=1.0, help='Commission per trade (default: $1.00)')
@click.option('--slippage', default=2.0, help='Slippage in basis points (default: 2.0)')
@click.option('--max-positions', default=20, help='Maximum concurrent positions (default: 20)')
@click.option('--save/--no-save', default=True, help='Save backtest artifacts (default: save)')
@click.option('--config', help='Strategy configuration JSON file')
@click.option('--output-dir', help='Custom output directory for results')
def run(
    start_date: str,
    end_date: str,
    capital: float,
    symbols: Optional[str],
    commission: float,
    slippage: float,
    max_positions: int,
    save: bool,
    config: Optional[str],
    output_dir: Optional[str]
):
    """Run a comprehensive backtest."""
    
    click.echo(f"🚀 Starting backtest: {start_date} to {end_date}")
    click.echo(f"💰 Initial capital: ${capital:,.2f}")
    
    # Parse symbols
    symbol_list = None
    if symbols:
        symbol_list = [s.strip().upper() for s in symbols.split(',')]
        click.echo(f"📊 Symbols: {len(symbol_list)} provided")
    else:
        click.echo("📊 Symbols: Using screener universe")
    
    # Load strategy config
    strategy_config = None
    if config:
        try:
            with open(config, 'r') as f:
                strategy_config = json.load(f)
            click.echo(f"⚙️  Loaded strategy config from {config}")
        except Exception as e:
            click.echo(f"❌ Failed to load config: {e}")
            return
    
    # Initialize components
    data_loader = HistoricalDataLoader()
    simulator = TradingSimulator(
        commission_per_trade=commission,
        slippage_bps=slippage,
        max_positions=max_positions
    )
    analyzer = PerformanceAnalyzer()
    
    pipeline = BacktestPipeline(data_loader, simulator, analyzer)
    
    # Run backtest
    async def run_backtest():
        return await pipeline.run(
            start_date=start_date,
            end_date=end_date,
            initial_capital=capital,
            strategy_config=strategy_config,
            symbols=symbol_list,
            save_artifacts=save
        )
    
    # Execute
    results = asyncio.run(run_backtest())
    
    if results["success"]:
        click.echo("\n✅ Backtest completed successfully!")
        
        # Display key metrics
        metrics = results["performance_metrics"]
        
        click.echo("\n📈 PERFORMANCE SUMMARY:")
        click.echo(f"  Total Return: ${metrics.get('total_return', 0):,.2f} ({metrics.get('total_return_pct', 0):.2f}%)")
        click.echo(f"  Total Trades: {metrics.get('total_trades', 0)}")
        click.echo(f"  Win Rate: {metrics.get('win_rate', 0):.1f}%")
        click.echo(f"  Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
        click.echo(f"  Max Drawdown: {metrics.get('max_drawdown', 0):.2f}%")
        
        if save and results["saved_files"]:
            click.echo(f"\n💾 Results saved to: {Path(results['saved_files']['report']).parent}")
        
    else:
        click.echo(f"\n❌ Backtest failed: {results['error']}")


@click.command()
@click.option('--start-date', '-s', required=True, help='Start date (YYYY-MM-DD)')
@click.option('--end-date', '-e', required=True, help='End date (YYYY-MM-DD)')
@click.option('--symbols', help='Comma-separated list of symbols')
@click.option('--clear-cache', is_flag=True, help='Clear existing cache')
def load_data(start_date: str, end_date: str, symbols: Optional[str], clear_cache: bool):
    """Pre-load historical data for backtesting."""
    
    click.echo(f"📥 Loading data: {start_date} to {end_date}")
    
    data_loader = HistoricalDataLoader()
    
    if clear_cache:
        data_loader.clear_cache()
        click.echo("🗑️  Cleared data cache")
    
    # Parse symbols
    symbol_list = None
    if symbols:
        symbol_list = [s.strip().upper() for s in symbols.split(',')]
        click.echo(f"📊 Loading {len(symbol_list)} symbols")
    
    async def load_data_async():
        return await data_loader.load_data_range(start_date, end_date, symbol_list)
    
    data = asyncio.run(load_data_async())
    
    if not data.empty:
        click.echo(f"✅ Loaded {len(data)} data points for {data['symbol'].nunique()} symbols")
        
        # Show data summary
        date_range = f"{data['date'].min()} to {data['date'].max()}"
        click.echo(f"📅 Date range: {date_range}")
        click.echo(f"📊 Symbols: {', '.join(sorted(data['symbol'].unique()[:10]))}" + 
                  (f" (and {data['symbol'].nunique() - 10} more)" if data['symbol'].nunique() > 10 else ""))
    else:
        click.echo("❌ No data loaded")


@click.command()
def cache_info():
    """Show cache information."""
    
    data_loader = HistoricalDataLoader()
    cache_info = data_loader.get_cache_info()
    
    click.echo("💽 CACHE INFORMATION:")
    click.echo(f"  Directory: {cache_info['cache_dir']}")
    click.echo(f"  Files: {cache_info['total_files']}")
    click.echo(f"  Size: {cache_info['total_size_mb']:.1f} MB")
    click.echo(f"  Symbols: {cache_info['symbols_cached']}")


@click.command()
@click.option('--symbol', help='Clear cache for specific symbol')
def clear_cache(symbol: Optional[str]):
    """Clear cached data."""
    
    data_loader = HistoricalDataLoader()
    
    if symbol:
        data_loader.clear_cache(symbol.upper())
        click.echo(f"🗑️  Cleared cache for {symbol.upper()}")
    else:
        data_loader.clear_cache()
        click.echo("🗑️  Cleared all cached data")


@click.command()
@click.argument('results_dir', type=click.Path(exists=True))
def analyze(results_dir: str):
    """Analyze saved backtest results."""
    
    results_path = Path(results_dir)
    
    click.echo(f"📊 Analyzing results from: {results_path}")
    
    # Load saved results
    try:
        # Load performance metrics
        metrics_file = results_path / "performance_metrics.json"
        if metrics_file.exists():
            with open(metrics_file, 'r') as f:
                metrics = json.load(f)
        else:
            click.echo("❌ No performance metrics found")
            return
        
        # Load trades
        trades_file = results_path / "trades.parquet"
        if trades_file.exists():
            trades_df = pd.read_parquet(trades_file)
        else:
            trades_df = pd.DataFrame()
        
        # Generate analysis
        analyzer = PerformanceAnalyzer()
        
        # Display comprehensive summary
        summary = analyzer.generate_performance_summary(metrics)
        click.echo(f"\n{summary}")
        
        # Pattern analysis
        if not trades_df.empty and 'pattern' in trades_df.columns:
            click.echo("\n🔍 PATTERN ANALYSIS:")
            pattern_stats = trades_df.groupby('pattern').agg({
                'pnl': ['count', 'mean', 'sum'],
            }).round(2)
            
            pattern_stats.columns = ['Trades', 'Avg P&L', 'Total P&L']
            click.echo(pattern_stats.to_string())
        
        # Bucket analysis
        if not trades_df.empty and 'bucket' in trades_df.columns:
            click.echo("\n🪣 BUCKET ANALYSIS:")
            bucket_stats = trades_df.groupby('bucket').agg({
                'pnl': ['count', 'mean', 'sum'],
            }).round(2)
            
            bucket_stats.columns = ['Trades', 'Avg P&L', 'Total P&L']
            click.echo(bucket_stats.to_string())
        
    except Exception as e:
        click.echo(f"❌ Analysis failed: {e}")


@click.command()
@click.option('--start-date', '-s', help='Start date for walk-forward (YYYY-MM-DD)')
@click.option('--end-date', '-e', help='End date for walk-forward (YYYY-MM-DD)')
@click.option('--train-days', default=252, help='Training period in days (default: 252)')
@click.option('--test-days', default=63, help='Testing period in days (default: 63)')
@click.option('--step-days', default=21, help='Step size in days (default: 21)')
@click.option('--capital', default=100000.0, help='Initial capital per test')
def walk_forward(
    start_date: Optional[str],
    end_date: Optional[str], 
    train_days: int,
    test_days: int,
    step_days: int,
    capital: float
):
    """Run walk-forward analysis."""
    
    # Default to last 2 years if no dates provided
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    if not start_date:
        start_dt = datetime.now() - timedelta(days=730)  # 2 years
        start_date = start_dt.strftime('%Y-%m-%d')
    
    click.echo(f"🚶 Walk-forward analysis: {start_date} to {end_date}")
    click.echo(f"📚 Train: {train_days} days, Test: {test_days} days, Step: {step_days} days")
    
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
    
    click.echo(f"🔄 Generated {len(windows)} walk-forward windows")
    
    # Run backtests for each window
    pipeline = BacktestPipeline()
    results = []
    
    async def run_walk_forward():
        for i, window in enumerate(windows, 1):
            click.echo(f"\n📊 Window {i}/{len(windows)}: {window['test_start']} to {window['test_end']}")
            
            result = await pipeline.run(
                start_date=window['test_start'],
                end_date=window['test_end'],
                initial_capital=capital,
                save_artifacts=False
            )
            
            if result['success']:
                metrics = result['performance_metrics']
                results.append({
                    'window': i,
                    'test_start': window['test_start'],
                    'test_end': window['test_end'],
                    'return_pct': metrics.get('total_return_pct', 0),
                    'trades': metrics.get('total_trades', 0),
                    'win_rate': metrics.get('win_rate', 0),
                    'sharpe': metrics.get('sharpe_ratio', 0),
                    'max_dd': metrics.get('max_drawdown', 0)
                })
                
                click.echo(f"  ✅ Return: {metrics.get('total_return_pct', 0):.2f}%, Trades: {metrics.get('total_trades', 0)}")
            else:
                click.echo(f"  ❌ Failed: {result['error']}")
    
    asyncio.run(run_walk_forward())
    
    if results:
        # Summary statistics
        results_df = pd.DataFrame(results)
        
        click.echo(f"\n📈 WALK-FORWARD SUMMARY:")
        click.echo(f"  Windows: {len(results)}")
        click.echo(f"  Avg Return: {results_df['return_pct'].mean():.2f}%")
        click.echo(f"  Win Rate (periods): {(results_df['return_pct'] > 0).mean() * 100:.1f}%")
        click.echo(f"  Best Period: {results_df['return_pct'].max():.2f}%")
        click.echo(f"  Worst Period: {results_df['return_pct'].min():.2f}%")
        click.echo(f"  Avg Sharpe: {results_df['sharpe'].mean():.2f}")
        
        # Show detailed results
        click.echo(f"\n📊 DETAILED RESULTS:")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        click.echo(results_df.round(2).to_string(index=False))


@click.command()
def status():
    """Show backtesting engine status."""
    
    pipeline = BacktestPipeline()
    status = pipeline.get_pipeline_status()
    
    click.echo("🔧 BACKTESTING ENGINE STATUS:")
    click.echo(f"  Data Loader: {status['backtesting']['data_loader']}")
    click.echo(f"  Simulator: {status['backtesting']['simulator']}")
    click.echo(f"  Analyzer: {status['backtesting']['analyzer']}")
    click.echo(f"  Artifacts Path: {status['settings']['artifacts_path']}")
    click.echo(f"  Debug Mode: {status['settings']['debug']}")
    
    # Cache info
    data_loader = HistoricalDataLoader()
    cache_info = data_loader.get_cache_info()
    
    click.echo(f"\n💽 CACHE STATUS:")
    click.echo(f"  Files: {cache_info['total_files']}")
    click.echo(f"  Size: {cache_info['total_size_mb']:.1f} MB")
    click.echo(f"  Symbols: {cache_info['symbols_cached']}")


# Register commands
cli.add_command(run)
cli.add_command(load_data)
cli.add_command(cache_info)
cli.add_command(clear_cache)
cli.add_command(analyze)
cli.add_command(walk_forward)
cli.add_command(status)


if __name__ == '__main__':
    cli()
