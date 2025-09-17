"""Command-line interface for the execution engine."""

import asyncio
import click
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from packages.core import get_logger
from packages.core.config import settings

from .pipeline import ExecutionPipeline
from .brokers import AlpacaBroker
from .orders import OrderManager
from .portfolio import PortfolioManager


logger = get_logger(__name__)


@click.group()  
def cli():
    """Execution Engine - Live and paper trading execution"""
    pass


@click.command()
@click.option('--signals-file', '-f', required=True, help='Signals file (JSON)')
@click.option('--mode', '-m', type=click.Choice(['paper', 'live']), default='paper', help='Trading mode')
@click.option('--dry-run/--execute', default=True, help='Dry run mode (no actual orders)')
@click.option('--save/--no-save', default=True, help='Save execution results')
def execute(signals_file: str, mode: str, dry_run: bool, save: bool):
    """Execute trading signals."""
    
    click.echo(f"⚡ Executing trades...")
    click.echo(f"🎯 Mode: {mode.upper()}")
    click.echo(f"🔄 Dry Run: {dry_run}")
    
    # Load signals
    try:
        with open(signals_file, 'r') as f:
            signals = json.load(f)
        
        if not signals:
            click.echo("❌ No signals found")
            return
            
        click.echo(f"📊 Loaded {len(signals)} signals")
        
    except Exception as e:
        click.echo(f"❌ Failed to load signals: {e}")
        return
    
    # Run execution pipeline
    pipeline = ExecutionPipeline()
    
    async def run_execution():
        return await pipeline.run(
            signals,
            mode=mode,
            dry_run=dry_run,
            save_artifacts=save
        )
    
    results = asyncio.run(run_execution())
    
    if results["success"]:
        executed_trades = results.get("executed_trades", [])
        failed_trades = results.get("failed_trades", [])
        
        click.echo(f"\n✅ Execution completed!")
        click.echo(f"⚡ Executed: {len(executed_trades)} trades")
        
        if failed_trades:
            click.echo(f"❌ Failed: {len(failed_trades)} trades")
        
        # Show executed trades summary
        if executed_trades:
            click.echo(f"\n📊 EXECUTED TRADES:")
            for trade in executed_trades[:5]:  # Show first 5
                symbol = trade.get('symbol', 'Unknown')
                side = trade.get('side', 'Unknown')
                qty = trade.get('qty', 0)
                price = trade.get('price', 0)
                click.echo(f"  {symbol}: {side} {qty} @ ${price:.2f}")
        
        if save and results.get("saved_files"):
            click.echo(f"\n💾 Results saved to: {results['saved_files']['trades']}")
    
    else:
        click.echo(f"❌ Execution failed: {results['error']}")


@click.command()
@click.option('--mode', '-m', type=click.Choice(['paper', 'live']), default='paper', help='Trading mode')
def positions(mode: str):
    """Show current positions."""
    
    click.echo(f"📊 Current positions ({mode.upper()} mode)")
    
    broker = AlpacaBroker(paper_trading=(mode == 'paper'))
    
    async def get_positions():
        return await broker.get_positions()
    
    try:
        positions = asyncio.run(get_positions())
        
        if positions:
            click.echo(f"\n📈 OPEN POSITIONS ({len(positions)}):")
            click.echo("=" * 50)
            
            total_value = 0
            for pos in positions:
                symbol = pos.get('symbol', 'Unknown')
                qty = float(pos.get('qty', 0))
                market_value = float(pos.get('market_value', 0))
                unrealized_pl = float(pos.get('unrealized_pl', 0))
                
                total_value += market_value
                
                click.echo(f"{symbol:8} | {qty:>8.0f} | ${market_value:>10.2f} | ${unrealized_pl:>8.2f}")
            
            click.echo("=" * 50) 
            click.echo(f"{'TOTAL':8} |          | ${total_value:>10.2f} |")
            
        else:
            click.echo("📭 No open positions")
            
    except Exception as e:
        click.echo(f"❌ Failed to get positions: {e}")


@click.command()
@click.option('--mode', '-m', type=click.Choice(['paper', 'live']), default='paper', help='Trading mode')
def portfolio(mode: str):
    """Show portfolio summary."""
    
    click.echo(f"💼 Portfolio summary ({mode.upper()} mode)")
    
    portfolio_mgr = PortfolioManager()
    
    async def get_portfolio():
        return await portfolio_mgr.get_portfolio_summary()
    
    try:
        summary = asyncio.run(get_portfolio())
        
        if summary["success"]:
            portfolio = summary["portfolio"]
            
            click.echo(f"\n💰 PORTFOLIO SUMMARY:")
            click.echo(f"  Cash: ${portfolio.get('cash', 0):,.2f}")
            click.echo(f"  Equity: ${portfolio.get('equity', 0):,.2f}")
            click.echo(f"  Day P&L: ${portfolio.get('day_pl', 0):,.2f}")
            click.echo(f"  Total P&L: ${portfolio.get('total_pl', 0):,.2f}")
            click.echo(f"  Buying Power: ${portfolio.get('buying_power', 0):,.2f}")
            
            positions = summary.get("positions", [])
            if positions:
                click.echo(f"\n📊 POSITIONS ({len(positions)}):")
                for pos in positions[:10]:  # Show first 10
                    symbol = pos.get('symbol', 'Unknown')
                    qty = pos.get('qty', 0)
                    value = pos.get('market_value', 0)
                    pl = pos.get('unrealized_pl', 0)
                    click.echo(f"  {symbol}: {qty} shares, ${value:.2f} value, ${pl:.2f} P&L")
        
        else:
            click.echo(f"❌ Failed to get portfolio: {summary['error']}")
            
    except Exception as e:
        click.echo(f"❌ Portfolio error: {e}")


@click.command()
@click.option('--mode', '-m', type=click.Choice(['paper', 'live']), default='paper', help='Trading mode')
def orders(mode: str):
    """Show recent orders."""
    
    click.echo(f"📋 Recent orders ({mode.upper()} mode)")
    
    broker = AlpacaBroker(paper_trading=(mode == 'paper'))
    
    async def get_orders():
        return await broker.get_orders(limit=20)
    
    try:
        orders = asyncio.run(get_orders())
        
        if orders:
            click.echo(f"\n📋 RECENT ORDERS ({len(orders)}):")
            click.echo("=" * 70)
            click.echo(f"{'Symbol':8} | {'Side':4} | {'Qty':>6} | {'Status':10} | {'Type':8} | {'Time':>12}")
            click.echo("=" * 70)
            
            for order in orders:
                symbol = order.get('symbol', 'Unknown')[:8]
                side = order.get('side', 'Unknown')[:4]
                qty = int(float(order.get('qty', 0)))
                status = order.get('status', 'Unknown')[:10]
                order_type = order.get('type', 'Unknown')[:8]
                created_at = order.get('created_at', '')[:12]
                
                click.echo(f"{symbol:8} | {side:4} | {qty:>6} | {status:10} | {order_type:8} | {created_at:>12}")
                
        else:
            click.echo("📭 No recent orders")
            
    except Exception as e:
        click.echo(f"❌ Failed to get orders: {e}")


@click.command()
@click.option('--symbol', required=True, help='Symbol to close')
@click.option('--mode', '-m', type=click.Choice(['paper', 'live']), default='paper', help='Trading mode')
@click.option('--dry-run/--execute', default=True, help='Dry run mode')
def close(symbol: str, mode: str, dry_run: bool):
    """Close a position."""
    
    symbol = symbol.upper()
    click.echo(f"🔒 Closing position: {symbol}")
    click.echo(f"🎯 Mode: {mode.upper()}")
    click.echo(f"🔄 Dry Run: {dry_run}")
    
    if dry_run:
        click.echo(f"✅ Would close position in {symbol} (dry run)")
        return
    
    broker = AlpacaBroker(paper_trading=(mode == 'paper'))
    
    async def close_position():
        return await broker.close_position(symbol)
    
    try:
        result = asyncio.run(close_position())
        
        if result.get("success"):
            click.echo(f"✅ Successfully closed position in {symbol}")
        else:
            click.echo(f"❌ Failed to close {symbol}: {result.get('error')}")
            
    except Exception as e:
        click.echo(f"❌ Close error: {e}")


@click.command()
@click.option('--mode', '-m', type=click.Choice(['paper', 'live']), default='paper', help='Trading mode')
def risks(mode: str):
    """Show portfolio risk metrics."""
    
    click.echo(f"⚠️  Portfolio risks ({mode.upper()} mode)")
    
    portfolio_mgr = PortfolioManager()
    
    async def get_risks():
        return await portfolio_mgr.check_risk_violations()
    
    try:
        risk_check = asyncio.run(get_risks())
        
        if risk_check["success"]:
            violations = risk_check.get("violations", [])
            
            if violations:
                click.echo(f"\n⚠️  RISK VIOLATIONS ({len(violations)}):")
                for violation in violations:
                    click.echo(f"  {violation.get('type')}: {violation.get('message')}")
            else:
                click.echo(f"\n✅ No risk violations detected")
            
            # Show risk metrics
            metrics = risk_check.get("metrics", {})
            if metrics:
                click.echo(f"\n📊 RISK METRICS:")
                click.echo(f"  Portfolio Beta: {metrics.get('beta', 0):.2f}")
                click.echo(f"  Max Position %: {metrics.get('max_position_pct', 0):.1f}%")
                click.echo(f"  Day P&L %: {metrics.get('day_pl_pct', 0):.2f}%")
        
        else:
            click.echo(f"❌ Risk check failed: {risk_check['error']}")
            
    except Exception as e:
        click.echo(f"❌ Risk check error: {e}")


@click.command()
def status():
    """Show execution engine status."""
    
    pipeline = ExecutionPipeline()
    status = pipeline.get_pipeline_status()
    
    click.echo("⚡ EXECUTION ENGINE STATUS")
    click.echo("=" * 30)
    
    execution_info = status.get('execution', {})
    click.echo(f"Broker: {execution_info.get('broker', 'Unknown')}")
    click.echo(f"Order Manager: {execution_info.get('order_manager', 'Unknown')}")
    click.echo(f"Portfolio Manager: {execution_info.get('portfolio_manager', 'Unknown')}")
    
    settings_info = status.get('settings', {})
    click.echo(f"Artifacts Path: {settings_info.get('artifacts_path', 'Unknown')}")
    click.echo(f"Debug Mode: {settings_info.get('debug', 'Unknown')}")


# Register commands
cli.add_command(execute)
cli.add_command(positions)
cli.add_command(portfolio)
cli.add_command(orders)
cli.add_command(close)
cli.add_command(risks)
cli.add_command(status)


if __name__ == '__main__':
    cli()
