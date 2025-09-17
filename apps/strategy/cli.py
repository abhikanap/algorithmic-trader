"""Command-line interface for the strategy engine."""

import asyncio
import click
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from packages.core import get_logger
from packages.core.config import settings

from .pipeline import StrategyPipeline
from .allocators import BucketAllocator
from .signals import SignalGenerator


logger = get_logger(__name__)


@click.group()
def cli():
    """Strategy Engine - Capital allocation and signal generation"""
    pass


@click.command()
@click.option('--data-file', '-f', required=True, help='Analyzer data file (JSON)')
@click.option('--capital', '-c', default=100000.0, help='Total capital to allocate (default: $100,000)')
@click.option('--max-positions', default=20, help='Maximum concurrent positions (default: 20)')
@click.option('--save/--no-save', default=True, help='Save results (default: save)')
def run(data_file: str, capital: float, max_positions: int, save: bool):
    """Run strategy pipeline to generate trading signals."""
    
    click.echo(f"💡 Running strategy engine...")
    click.echo(f"💰 Capital: ${capital:,.2f}")
    click.echo(f"📊 Max positions: {max_positions}")
    
    # Load analyzer data
    try:
        with open(data_file, 'r') as f:
            analyzer_data = json.load(f)
        
        if not analyzer_data:
            click.echo("❌ No analyzer data found")
            return
            
        click.echo(f"📈 Loaded {len(analyzer_data)} analyzed symbols")
        
    except Exception as e:
        click.echo(f"❌ Failed to load data: {e}")
        return
    
    # Run strategy pipeline
    pipeline = StrategyPipeline()
    
    async def run_strategy():
        return await pipeline.run(
            analyzer_data,
            capital_allocation=capital,
            max_positions=max_positions,
            save_artifacts=save
        )
    
    results = asyncio.run(run_strategy())
    
    if results["success"]:
        signals = results["signals"]
        allocations = results["allocations"]
        
        click.echo(f"\n✅ Strategy completed successfully!")
        click.echo(f"💡 Generated {len(signals)} signals")
        
        # Show allocation summary
        if allocations:
            click.echo(f"\n📊 ALLOCATION SUMMARY:")
            total_allocated = sum(alloc.get('allocated_capital', 0) for alloc in allocations.values())
            click.echo(f"  Total allocated: ${total_allocated:,.2f}")
            
            for bucket, alloc in allocations.items():
                click.echo(f"  {bucket}: ${alloc.get('allocated_capital', 0):,.2f} ({alloc.get('symbol_count', 0)} symbols)")
        
        # Show top signals
        if signals:
            click.echo(f"\n🎯 TOP SIGNALS:")
            for i, signal in enumerate(signals[:5], 1):
                click.echo(f"  {i}. {signal.get('symbol')} - {signal.get('signal_type')} - ${signal.get('position_size', 0):,.0f}")
        
        if save and results.get("saved_files"):
            click.echo(f"\n💾 Results saved to: {results['saved_files']['signals']}")
    
    else:
        click.echo(f"❌ Strategy failed: {results['error']}")


@click.command()
@click.option('--symbols', required=True, help='Comma-separated list of symbols')
@click.option('--capital', '-c', default=100000.0, help='Total capital (default: $100,000)')
def allocate(symbols: str, capital: float):
    """Test capital allocation for specific symbols."""
    
    symbol_list = [s.strip().upper() for s in symbols.split(',')]
    
    click.echo(f"📊 Testing allocation for {len(symbol_list)} symbols")
    click.echo(f"💰 Total capital: ${capital:,.2f}")
    
    # Create mock analyzer data
    mock_data = []
    for symbol in symbol_list:
        mock_data.append({
            'symbol': symbol,
            'price': 50.0,  # Mock price
            'pattern_intraday': 'MORNING_SURGE_UPTREND',
            'pattern_confidence': 0.8,
            'volatility': 2.5
        })
    
    # Test allocation
    allocator = BucketAllocator(total_capital=capital)
    
    async def test_allocation():
        return await allocator.allocate_capital(mock_data)
    
    results = asyncio.run(test_allocation())
    
    if results["success"]:
        allocations = results["allocations"]
        
        click.echo(f"\n✅ Allocation completed!")
        
        for bucket, alloc in allocations.items():
            symbols_in_bucket = alloc.get('symbols', [])
            if symbols_in_bucket:
                click.echo(f"\n{bucket}:")
                click.echo(f"  Capital: ${alloc.get('allocated_capital', 0):,.2f}")
                click.echo(f"  Symbols: {', '.join(s['symbol'] for s in symbols_in_bucket)}")
    
    else:
        click.echo(f"❌ Allocation failed: {results['error']}")


@click.command()
@click.option('--bucket', type=click.Choice(['BUCKET_A', 'BUCKET_B', 'BUCKET_C', 'BUCKET_D', 'BUCKET_E']),
              help='Show allocation rules for specific bucket')
def rules(bucket: Optional[str]):
    """Show strategy allocation rules."""
    
    click.echo("📋 STRATEGY ALLOCATION RULES")
    click.echo("=" * 40)
    
    bucket_rules = {
        'BUCKET_A': {
            'name': 'Penny Stocks',
            'criteria': 'Price ≤ $5.00',
            'allocation': '10%',
            'position_size': '$2,000',
            'patterns': 'All patterns'
        },
        'BUCKET_B': {
            'name': 'Large Cap Stocks',
            'criteria': 'Price > $10, Market Cap > $10B',
            'allocation': '40%',
            'position_size': '$8,000',
            'patterns': 'Surge/Uptrend, Selloff/Downtrend'
        },
        'BUCKET_C': {
            'name': 'Multi-day Plays',
            'criteria': 'Recovery patterns, Strong base',
            'allocation': '25%',
            'position_size': '$6,000',
            'patterns': 'Plunge/Recovery primarily'
        },
        'BUCKET_D': {
            'name': 'Catalyst Driven',
            'criteria': 'Gap > 5%, High volume',
            'allocation': '20%',
            'position_size': '$5,000',
            'patterns': 'Gap patterns, news driven'
        },
        'BUCKET_E': {
            'name': 'Defensive/Other',
            'criteria': 'Lower volatility, stable patterns',
            'allocation': '5%',
            'position_size': '$3,000',
            'patterns': 'Range-bound, low risk'
        }
    }
    
    if bucket:
        rules = bucket_rules.get(bucket, {})
        click.echo(f"\n{bucket} - {rules.get('name', 'Unknown')}")
        click.echo(f"  Criteria: {rules.get('criteria', 'N/A')}")
        click.echo(f"  Allocation: {rules.get('allocation', 'N/A')}")
        click.echo(f"  Position Size: {rules.get('position_size', 'N/A')}")
        click.echo(f"  Patterns: {rules.get('patterns', 'N/A')}")
    else:
        for bucket_id, rules in bucket_rules.items():
            click.echo(f"\n{bucket_id} - {rules['name']}")
            click.echo(f"  Allocation: {rules['allocation']} | Position: {rules['position_size']}")
            click.echo(f"  Criteria: {rules['criteria']}")


@click.command()
def status():
    """Show strategy engine status."""
    
    pipeline = StrategyPipeline()
    status = pipeline.get_pipeline_status()
    
    click.echo("💡 STRATEGY ENGINE STATUS")
    click.echo("=" * 30)
    
    strategy_info = status.get('strategy', {})
    click.echo(f"Allocator: {strategy_info.get('allocator', 'Unknown')}")
    click.echo(f"Signal Generator: {strategy_info.get('signal_generator', 'Unknown')}")
    
    settings_info = status.get('settings', {})
    click.echo(f"Artifacts Path: {settings_info.get('artifacts_path', 'Unknown')}")
    click.echo(f"Debug Mode: {settings_info.get('debug', 'Unknown')}")


# Register commands
cli.add_command(run)
cli.add_command(allocate)
cli.add_command(rules)
cli.add_command(status)


if __name__ == '__main__':
    cli()
