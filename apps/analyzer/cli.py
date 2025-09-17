"""Analyzer CLI interface."""

import asyncio
import click
from datetime import datetime
from pathlib import Path

from packages.core import get_logger
from packages.core.config import settings

from .pipeline import AnalyzerPipeline


logger = get_logger(__name__)


@click.group(name="analyzer")
@click.pass_context
def analyzer_cli(ctx):
    """Analyzer commands for pattern classification."""
    ctx.ensure_object(dict)


@analyzer_cli.command("run")
@click.option(
    "--date",
    type=str,
    help="Date to run analyzer for (YYYY-MM-DD). Defaults to today."
)
@click.option(
    "--screener-data",
    type=click.Path(exists=True),
    help="Path to screener data file (parquet). If not provided, loads from artifacts."
)
@click.option(
    "--save-artifacts/--no-save-artifacts",
    default=True,
    help="Save analyzer results to artifacts directory."
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose logging."
)
def run_analyzer(date, screener_data, save_artifacts, verbose):
    """Run the analyzer pipeline."""
    if verbose:
        import structlog
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(20)  # INFO level
        )
    
    async def main():
        # Initialize pipeline
        pipeline = AnalyzerPipeline()
        
        # Load screener data if path provided
        screener_df = None
        if screener_data:
            import pandas as pd
            screener_df = pd.read_parquet(screener_data)
            logger.info(f"Loaded {len(screener_df)} symbols from {screener_data}")
        
        # Run pipeline
        result = await pipeline.run(
            screener_data=screener_df,
            date=date,
            save_artifacts=save_artifacts
        )
        
        if result["success"]:
            metadata = result["metadata"]
            click.echo(f"✅ Analyzer pipeline completed successfully!")
            click.echo(f"   Duration: {metadata['duration_seconds']:.1f}s")
            click.echo(f"   Symbols analyzed: {metadata['total_symbols']}")
            
            # Show pattern statistics
            pattern_stats = metadata.get("pattern_statistics", {})
            if pattern_stats:
                click.echo("\n📊 Pattern Distribution:")
                
                if "intraday_patterns" in pattern_stats:
                    click.echo("   Intraday:")
                    for pattern, count in pattern_stats["intraday_patterns"].items():
                        click.echo(f"     {pattern}: {count}")
                
                if "multiday_patterns" in pattern_stats:
                    click.echo("   Multi-day:")
                    for pattern, count in pattern_stats["multiday_patterns"].items():
                        click.echo(f"     {pattern}: {count}")
            
            # Show saved files
            saved_files = result.get("saved_files", {})
            if saved_files:
                click.echo("\n💾 Saved Files:")
                for file_type, path in saved_files.items():
                    click.echo(f"   {file_type}: {path}")
        else:
            click.echo(f"❌ Analyzer pipeline failed: {result['error']}")
            return 1
    
    # Run the async function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        click.echo("\n⚠️  Analyzer pipeline interrupted by user")
        return 1
    except Exception as e:
        click.echo(f"❌ Unexpected error: {str(e)}")
        logger.error("Analyzer pipeline failed", exc_info=True)
        return 1


@analyzer_cli.command("patterns")
@click.option(
    "--pattern-type",
    type=click.Choice(["intraday", "multiday", "all"]),
    default="all",
    help="Type of patterns to display."
)
def list_patterns(pattern_type):
    """List available pattern types."""
    from .classify_intraday import IntradayClassifier
    from .classify_multiday import MultidayClassifier
    
    if pattern_type in ["intraday", "all"]:
        click.echo("📈 Intraday Patterns:")
        patterns = IntradayClassifier.get_pattern_descriptions()
        for pattern, description in patterns.items():
            click.echo(f"   {pattern}: {description}")
        click.echo()
    
    if pattern_type in ["multiday", "all"]:
        click.echo("📊 Multi-day Patterns:")
        patterns = MultidayClassifier.get_pattern_descriptions()
        for pattern, description in patterns.items():
            click.echo(f"   {pattern}: {description}")


@analyzer_cli.command("report")
@click.option(
    "--date",
    type=str,
    help="Date to generate report for (YYYY-MM-DD). Defaults to today."
)
@click.option(
    "--output",
    type=click.Path(),
    help="Output file path. If not provided, prints to console."
)
def generate_report(date, output):
    """Generate analyzer report for a specific date."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    # Load analyzer artifacts
    artifacts_dir = settings.artifacts_path / "analyzer" / date
    
    if not artifacts_dir.exists():
        click.echo(f"❌ No analyzer artifacts found for {date}")
        return 1
    
    report_path = artifacts_dir / "REPORT.md"
    if not report_path.exists():
        click.echo(f"❌ No report found for {date}")
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


if __name__ == "__main__":
    analyzer_cli()
