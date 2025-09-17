"""Command-line interface for the screener."""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import click
import pandas as pd

from packages.core import get_logger, settings
from .pipeline import ScreenerPipeline
from .providers import YahooProvider


logger = get_logger(__name__)


@click.group(name="screener")
@click.option("--debug", is_flag=True, help="Enable debug logging")
def screener_cli(debug: bool):
    """Stock Screener CLI."""
    if debug:
        logger.info("Debug mode enabled")


@screener_cli.command()
@click.option("--provider", default="yahoo", help="Data provider to use")
@click.option("--date", help="Date to run screener for (YYYY-MM-DD)")
@click.option("--symbols-file", help="File with symbols to screen (one per line)")
@click.option("--topk", type=int, default=50, help="Number of top symbols to return")
@click.option("--no-save", is_flag=True, help="Don't save artifacts")
@click.option("--output-format", default="table", type=click.Choice(["table", "json", "csv"]))
def run(
    provider: str,
    date: Optional[str],
    symbols_file: Optional[str],
    topk: int,
    no_save: bool,
    output_format: str
):
    """Run the screener pipeline."""
    async def _run():
        # Initialize pipeline
        if provider == "yahoo":
            data_provider = YahooProvider()
        else:
            raise click.ClickException(f"Unknown provider: {provider}")
        
        pipeline = ScreenerPipeline(provider=data_provider)
        
        # Load symbols if provided
        symbols = None
        if symbols_file:
            symbols_path = Path(symbols_file)
            if not symbols_path.exists():
                raise click.ClickException(f"Symbols file not found: {symbols_file}")
            
            with open(symbols_path, "r") as f:
                symbols = [line.strip() for line in f if line.strip()]
            
            click.echo(f"Loaded {len(symbols)} symbols from {symbols_file}")
        
        # Run pipeline
        click.echo("Starting screener pipeline...")
        result = await pipeline.run(
            date=date,
            symbols=symbols,
            save_artifacts=not no_save
        )
        
        if not result["success"]:
            click.echo(f"❌ Pipeline failed: {result['error']}", err=True)
            sys.exit(1)
        
        # Display results
        df = result["data"]
        metadata = result["metadata"]
        
        click.echo(f"✅ Pipeline completed successfully!")
        click.echo(f"⏱️  Duration: {metadata['duration_seconds']:.1f}s")
        click.echo(f"📊 Results: {len(df)} symbols")
        
        if not df.empty:
            # Limit to topk
            display_df = df.head(topk)
            
            if output_format == "table":
                _display_table(display_df)
            elif output_format == "json":
                _display_json(display_df)
            elif output_format == "csv":
                _display_csv(display_df)
        
        # Show saved files
        if result["saved_files"]:
            click.echo("\n💾 Saved artifacts:")
            for file_type, path in result["saved_files"].items():
                click.echo(f"  {file_type}: {path}")
    
    asyncio.run(_run())


@screener_cli.command()
@click.argument("symbols", nargs=-1, required=True)
@click.option("--output-format", default="table", type=click.Choice(["table", "json", "csv"]))
def quick(symbols: List[str], output_format: str):
    """Quick screen specific symbols."""
    async def _quick():
        pipeline = ScreenerPipeline()
        
        click.echo(f"Running quick screen for {len(symbols)} symbols...")
        df = await pipeline.run_quick_screen(list(symbols))
        
        if df.empty:
            click.echo("❌ No results returned")
            sys.exit(1)
        
        click.echo(f"✅ Results: {len(df)} symbols")
        
        if output_format == "table":
            _display_table(df)
        elif output_format == "json":
            _display_json(df)
        elif output_format == "csv":
            _display_csv(df)
    
    asyncio.run(_quick())


@screener_cli.command()
@click.option("--date", help="Date to export (YYYY-MM-DD)")
@click.option("--format", "export_format", default="jsonl", 
              type=click.Choice(["jsonl", "csv", "parquet"]))
@click.option("--output", help="Output file path")
def export(date: Optional[str], export_format: str, output: Optional[str]):
    """Export screener results."""
    from .artifacts import ArtifactManager
    
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    artifact_manager = ArtifactManager()
    
    try:
        results = artifact_manager.load_screener_results(date)
        df = results["dataframe"]
        
        if output is None:
            output = f"screener_{date}.{export_format}"
        
        if export_format == "jsonl":
            # Convert to JSONL format
            with open(output, "w") as f:
                for _, row in df.iterrows():
                    record = row.to_dict()
                    f.write(json.dumps(record, default=str) + "\n")
        elif export_format == "csv":
            df.to_csv(output, index=False)
        elif export_format == "parquet":
            df.to_parquet(output, index=False)
        
        click.echo(f"✅ Exported {len(df)} records to {output}")
        
    except FileNotFoundError:
        click.echo(f"❌ No results found for date: {date}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Export failed: {e}", err=True)
        sys.exit(1)


@screener_cli.command()
def list_dates():
    """List available screener result dates."""
    from .artifacts import ArtifactManager
    
    artifact_manager = ArtifactManager()
    dates = artifact_manager.list_available_dates()
    
    if not dates:
        click.echo("No screener results found")
        return
    
    click.echo("Available screener result dates:")
    for date in dates:
        click.echo(f"  {date}")


@screener_cli.command()
def status():
    """Show screener pipeline status."""
    pipeline = ScreenerPipeline()
    status_info = pipeline.get_pipeline_status()
    
    click.echo("📊 Screener Pipeline Status")
    click.echo("=" * 30)
    
    click.echo(f"Provider: {status_info['provider']['name']}")
    click.echo(f"Rate Limit: {status_info['provider']['rate_limit']} req/s")
    click.echo(f"Artifacts Path: {status_info['settings']['artifacts_path']}")
    click.echo(f"Debug Mode: {status_info['settings']['debug']}")
    
    click.echo("\nComponents:")
    for component, name in status_info['configuration'].items():
        click.echo(f"  {component}: {name}")


def _display_table(df: pd.DataFrame):
    """Display DataFrame as formatted table."""
    if df.empty:
        click.echo("No data to display")
        return
    
    # Select key columns for display
    display_cols = []
    for col in ["rank", "symbol", "score", "last", "atrp_14", "hv_20", "avg_dollar_volume_20d", "gap_pct"]:
        if col in df.columns:
            display_cols.append(col)
    
    if display_cols:
        display_df = df[display_cols].copy()
        
        # Format numeric columns
        for col in display_df.columns:
            if col in ["score", "atrp_14", "hv_20", "gap_pct"]:
                display_df[col] = display_df[col].round(2)
            elif col == "avg_dollar_volume_20d":
                display_df[col] = display_df[col].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "N/A")
        
        click.echo("\n📈 Top Screener Results:")
        click.echo(display_df.to_string(index=False))
    else:
        click.echo(df.head().to_string(index=False))


def _display_json(df: pd.DataFrame):
    """Display DataFrame as JSON."""
    records = df.to_dict("records")
    click.echo(json.dumps(records, indent=2, default=str))


def _display_csv(df: pd.DataFrame):
    """Display DataFrame as CSV."""
    click.echo(df.to_csv(index=False))


def main():
    """Main entry point."""
    screener_cli()


if __name__ == "__main__":
    main()
