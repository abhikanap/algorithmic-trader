"""Backtest CLI interface."""

import asyncio
import click
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from packages.core import get_logger
from packages.core.config import settings

from . import BacktestEngine


logger = get_logger(__name__)


@click.group(name="backtest")
@click.pass_context
def backtest_cli(ctx):
    """Backtesting commands for strategy validation and performance analysis."""
    ctx.ensure_object(dict)


@backtest_cli.command("run")
@click.option(
    "--start-date",
    type=str,
    required=True,
    help="Start date for backtest (YYYY-MM-DD)."
)
@click.option(
    "--end-date",
    type=str,
    help="End date for backtest (YYYY-MM-DD). Defaults to today."
)
@click.option(
    "--capital",
    type=float,
    default=100000.0,
    help="Initial capital for backtest."
)
@click.option(
    "--benchmark",
    type=str,
    default="SPY",
    help="Benchmark symbol for comparison."
)
@click.option(
    "--save-artifacts/--no-save-artifacts",
    default=True,
    help="Save backtest results to artifacts directory."
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose logging."
)
def run_backtest(start_date, end_date, capital, benchmark, save_artifacts, verbose):
    """Run strategy backtest over specified date range."""
    if verbose:
        import structlog
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(20)  # INFO level
        )
    
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    async def main():
        # Initialize backtest engine
        engine = BacktestEngine()
        
        # Run backtest
        result = await engine.run_backtest(
            start_date=start_date,
            end_date=end_date,
            initial_capital=capital,
            benchmark_symbol=benchmark,
            save_artifacts=save_artifacts
        )
        
        if result["success"]:
            metadata = result["metadata"]
            performance = result["performance"]
            trades = result["trades"]
            
            click.echo(f"✅ Backtest completed successfully!")
            click.echo(f"   Duration: {metadata['duration_seconds']:.1f}s")
            click.echo(f"   Period: {start_date} to {end_date}")
            click.echo(f"   Trading Days: {metadata['trading_days']}")
            
            # Show key performance metrics
            if performance:
                click.echo(f"\n📊 Performance Summary:")
                click.echo(f"   Total Return: {performance.get('total_return_pct', 0):.2f}%")
                click.echo(f"   Annualized Return: {performance.get('annualized_return_pct', 0):.2f}%")
                click.echo(f"   Sharpe Ratio: {performance.get('sharpe_ratio', 0):.3f}")
                click.echo(f"   Maximum Drawdown: {performance.get('max_drawdown_pct', 0):.2f}%")
                click.echo(f"   Win Rate: {performance.get('win_rate_pct', 0):.1f}%")
                
                # Benchmark comparison
                if performance.get('benchmark_return_pct'):
                    excess_return = performance.get('total_return_pct', 0) - performance.get('benchmark_return_pct', 0)
                    click.echo(f"\n📈 vs {benchmark}:")
                    click.echo(f"   Strategy: {performance.get('total_return_pct', 0):.2f}%")
                    click.echo(f"   Benchmark: {performance.get('benchmark_return_pct', 0):.2f}%")
                    click.echo(f"   Excess Return: {excess_return:.2f}%")
                    click.echo(f"   Beta: {performance.get('beta', 0):.3f}")
                    click.echo(f"   Alpha: {performance.get('alpha_pct', 0):.2f}%")
            
            # Show trade statistics
            if trades:
                click.echo(f"\n💼 Trade Statistics:")
                click.echo(f"   Total Trades: {trades.get('total_trades', 0)}")
                click.echo(f"   Winning Trades: {performance.get('winning_trades', 0)}")
                click.echo(f"   Total P&L: ${trades.get('total_pnl', 0):,.2f}")
                click.echo(f"   Average Trade: ${trades.get('avg_trade_pnl', 0):,.2f}")
                click.echo(f"   Best Trade: ${trades.get('best_trade', 0):,.2f}")
                click.echo(f"   Worst Trade: ${trades.get('worst_trade', 0):,.2f}")
            
            # Show saved files
            saved_files = result.get("saved_files", {})
            if saved_files:
                click.echo("\n💾 Saved Files:")
                for file_type, path in saved_files.items():
                    click.echo(f"   {file_type}: {path}")
        else:
            click.echo(f"❌ Backtest failed: {result['error']}")
            return 1
    
    # Run the async function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        click.echo("\n⚠️  Backtest interrupted by user")
        return 1
    except Exception as e:
        click.echo(f"❌ Unexpected error: {str(e)}")
        logger.error("Backtest failed", exc_info=True)
        return 1


@backtest_cli.command("analyze")
@click.option(
    "--backtest-id",
    type=str,
    required=True,
    help="Backtest ID to analyze (format: YYYY-MM-DD_to_YYYY-MM-DD)."
)
@click.option(
    "--metric",
    type=click.Choice(["performance", "trades", "buckets", "patterns", "all"]),
    default="all",
    help="Type of analysis to show."
)
def analyze_backtest(backtest_id, metric):
    """Analyze results from a completed backtest."""
    # Load backtest artifacts
    artifacts_dir = settings.artifacts_path / "backtest" / backtest_id
    
    if not artifacts_dir.exists():
        click.echo(f"❌ No backtest found with ID: {backtest_id}")
        return 1
    
    try:
        # Load performance metrics
        import json
        metrics_path = artifacts_dir / "performance.json"
        
        if not metrics_path.exists():
            click.echo(f"❌ No performance metrics found for backtest: {backtest_id}")
            return 1
        
        with open(metrics_path, "r") as f:
            data = json.load(f)
        
        performance = data.get("performance", {})
        trades = data.get("trades_analysis", {})
        metadata = data.get("metadata", {})
        
        if metric in ["performance", "all"]:
            click.echo(f"📊 Performance Analysis - {backtest_id}")
            click.echo(f"   Period: {metadata.get('start_date')} to {metadata.get('end_date')}")
            click.echo(f"   Total Return: {performance.get('total_return_pct', 0):.2f}%")
            click.echo(f"   Annualized Return: {performance.get('annualized_return_pct', 0):.2f}%")
            click.echo(f"   Volatility: {performance.get('volatility_pct', 0):.2f}%")
            click.echo(f"   Sharpe Ratio: {performance.get('sharpe_ratio', 0):.3f}")
            click.echo(f"   Max Drawdown: {performance.get('max_drawdown_pct', 0):.2f}%")
            click.echo(f"   Win Rate: {performance.get('win_rate_pct', 0):.1f}%")
            click.echo()
        
        if metric in ["trades", "all"]:
            click.echo(f"💼 Trade Analysis")
            click.echo(f"   Total Trades: {trades.get('total_trades', 0)}")
            click.echo(f"   Total P&L: ${trades.get('total_pnl', 0):,.2f}")
            click.echo(f"   Average Trade: ${trades.get('avg_trade_pnl', 0):,.2f}")
            click.echo(f"   Best Trade: ${trades.get('best_trade', 0):,.2f}")
            click.echo(f"   Worst Trade: ${trades.get('worst_trade', 0):,.2f}")
            click.echo()
        
        if metric in ["buckets", "all"]:
            bucket_analysis = trades.get("by_bucket", {})
            if bucket_analysis:
                click.echo(f"🗂️  Performance by Bucket")
                for bucket, stats in bucket_analysis.items():
                    if isinstance(stats, dict) and "sum" in stats:
                        count = stats.get("count", {})
                        pnl_sum = stats.get("sum", {})
                        pnl_mean = stats.get("mean", {})
                        
                        if "realized_pnl" in count:
                            click.echo(f"   Bucket {bucket}:")
                            click.echo(f"     Trades: {count['realized_pnl']}")
                            click.echo(f"     Total P&L: ${pnl_sum['realized_pnl']:,.2f}")
                            click.echo(f"     Avg P&L: ${pnl_mean['realized_pnl']:,.2f}")
                click.echo()
        
        if metric in ["patterns", "all"]:
            pattern_analysis = trades.get("by_intraday_pattern", {})
            if pattern_analysis:
                click.echo(f"📈 Performance by Intraday Pattern")
                for pattern, stats in pattern_analysis.items():
                    if isinstance(stats, dict) and "sum" in stats:
                        count = stats.get("count", {})
                        pnl_sum = stats.get("sum", {})
                        pnl_mean = stats.get("mean", {})
                        
                        if "realized_pnl" in count:
                            click.echo(f"   {pattern}:")
                            click.echo(f"     Trades: {count['realized_pnl']}")
                            click.echo(f"     Total P&L: ${pnl_sum['realized_pnl']:,.2f}")
                            click.echo(f"     Avg P&L: ${pnl_mean['realized_pnl']:,.2f}")
                click.echo()
        
    except Exception as e:
        click.echo(f"❌ Error analyzing backtest: {str(e)}")
        return 1


@backtest_cli.command("list")
def list_backtests():
    """List available backtest results."""
    backtest_dir = settings.artifacts_path / "backtest"
    
    if not backtest_dir.exists():
        click.echo("📋 No backtests found")
        return
    
    backtests = list(backtest_dir.iterdir())
    
    if not backtests:
        click.echo("📋 No backtests found")
        return
    
    click.echo("📋 Available Backtests:")
    click.echo(f"{'Backtest ID':<25} {'Period':<20} {'Status'}")
    click.echo("-" * 60)
    
    for backtest_path in sorted(backtests):
        if backtest_path.is_dir():
            backtest_id = backtest_path.name
            
            # Try to extract period from ID
            if "_to_" in backtest_id:
                start_date, end_date = backtest_id.split("_to_")
                period = f"{start_date} to {end_date}"
            else:
                period = "Unknown"
            
            # Check if complete
            metrics_file = backtest_path / "performance.json"
            status = "Complete" if metrics_file.exists() else "Incomplete"
            
            click.echo(f"{backtest_id:<25} {period:<20} {status}")


@backtest_cli.command("report")
@click.option(
    "--backtest-id",
    type=str,
    required=True,
    help="Backtest ID to generate report for."
)
@click.option(
    "--output",
    type=click.Path(),
    help="Output file path. If not provided, prints to console."
)
def generate_report(backtest_id, output):
    """Generate detailed backtest report."""
    # Load backtest artifacts
    artifacts_dir = settings.artifacts_path / "backtest" / backtest_id
    
    if not artifacts_dir.exists():
        click.echo(f"❌ No backtest found with ID: {backtest_id}")
        return 1
    
    report_path = artifacts_dir / "REPORT.md"
    if not report_path.exists():
        click.echo(f"❌ No report found for backtest: {backtest_id}")
        return 1
    
    # Read and display/save report
    with open(report_path, "r") as f:
        report_content = f.read()
    
    if output:
        with open(output, "w") as f:
            f.write(report_content)
        click.echo(f"✅ Report saved to: {output}")
    else:
        click.echo(report_content)


@backtest_cli.command("compare")
@click.argument("backtest_ids", nargs=-1, required=True)
def compare_backtests(backtest_ids):
    """Compare multiple backtest results."""
    if len(backtest_ids) < 2:
        click.echo("❌ Need at least 2 backtest IDs to compare")
        return 1
    
    results = []
    
    for backtest_id in backtest_ids:
        artifacts_dir = settings.artifacts_path / "backtest" / backtest_id
        metrics_path = artifacts_dir / "performance.json"
        
        if not metrics_path.exists():
            click.echo(f"❌ No metrics found for backtest: {backtest_id}")
            continue
        
        try:
            import json
            with open(metrics_path, "r") as f:
                data = json.load(f)
            
            performance = data.get("performance", {})
            results.append({
                "id": backtest_id,
                "total_return": performance.get("total_return_pct", 0),
                "annualized_return": performance.get("annualized_return_pct", 0),
                "sharpe": performance.get("sharpe_ratio", 0),
                "max_drawdown": performance.get("max_drawdown_pct", 0),
                "win_rate": performance.get("win_rate_pct", 0),
                "trades": performance.get("total_trades", 0)
            })
            
        except Exception as e:
            click.echo(f"❌ Error loading {backtest_id}: {e}")
            continue
    
    if len(results) < 2:
        click.echo("❌ Not enough valid backtests to compare")
        return 1
    
    # Display comparison table
    click.echo("📊 Backtest Comparison")
    click.echo(f"{'Backtest ID':<25} {'Total Return':<12} {'Ann. Return':<12} {'Sharpe':<8} {'Max DD':<8} {'Win Rate':<9} {'Trades'}")
    click.echo("-" * 90)
    
    for result in results:
        click.echo(
            f"{result['id']:<25} "
            f"{result['total_return']:>11.2f}% "
            f"{result['annualized_return']:>11.2f}% "
            f"{result['sharpe']:>7.3f} "
            f"{result['max_drawdown']:>7.2f}% "
            f"{result['win_rate']:>8.1f}% "
            f"{result['trades']:>6d}"
        )
    
    # Show best performer
    best_return = max(results, key=lambda x: x['total_return'])
    best_sharpe = max(results, key=lambda x: x['sharpe'])
    
    click.echo(f"\n🏆 Best Total Return: {best_return['id']} ({best_return['total_return']:.2f}%)")
    click.echo(f"🏆 Best Sharpe Ratio: {best_sharpe['id']} ({best_sharpe['sharpe']:.3f})")


if __name__ == "__main__":
    backtest_cli()
