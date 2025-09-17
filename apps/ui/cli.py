"""UI CLI interface for launching the Streamlit dashboard."""

import click
import subprocess
import sys
from pathlib import Path

from packages.core import get_logger

logger = get_logger(__name__)


@click.group(name="ui")
@click.pass_context
def ui_cli(ctx):
    """User interface commands for the trading platform."""
    ctx.ensure_object(dict)


@ui_cli.command("dashboard")
@click.option(
    "--port",
    type=int,
    default=8501,
    help="Port to run the dashboard on."
)
@click.option(
    "--host",
    type=str,
    default="localhost",
    help="Host to bind the dashboard to."
)
@click.option(
    "--browser/--no-browser",
    default=True,
    help="Open browser automatically."
)
def launch_dashboard(port, host, browser):
    """Launch the Streamlit trading dashboard."""
    try:
        # Get the path to the dashboard module
        dashboard_path = Path(__file__).parent / "dashboard.py"
        
        if not dashboard_path.exists():
            click.echo(f"❌ Dashboard file not found: {dashboard_path}")
            return 1
        
        # Build Streamlit command
        cmd = [
            sys.executable, "-m", "streamlit", "run",
            str(dashboard_path),
            "--server.port", str(port),
            "--server.address", host,
            "--theme.base", "light",
            "--theme.primaryColor", "#1f77b4",
            "--theme.backgroundColor", "#ffffff",
            "--theme.secondaryBackgroundColor", "#f0f2f6"
        ]
        
        if not browser:
            cmd.extend(["--server.headless", "true"])
        
        click.echo(f"🚀 Starting trading dashboard...")
        click.echo(f"   URL: http://{host}:{port}")
        click.echo(f"   Dashboard: {dashboard_path}")
        
        # Run Streamlit
        process = subprocess.run(cmd, check=True)
        
        if process.returncode == 0:
            click.echo("✅ Dashboard stopped gracefully")
        else:
            click.echo(f"❌ Dashboard exited with code: {process.returncode}")
            return process.returncode
            
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Failed to start dashboard: {e}")
        return 1
    except KeyboardInterrupt:
        click.echo("\n⚠️  Dashboard interrupted by user")
        return 0
    except Exception as e:
        click.echo(f"❌ Unexpected error: {str(e)}")
        logger.error("Dashboard launch failed", exc_info=True)
        return 1


@ui_cli.command("install")
def install_dependencies():
    """Install Streamlit and other UI dependencies."""
    try:
        click.echo("📦 Installing UI dependencies...")
        
        # Install Streamlit and related packages
        packages = [
            "streamlit>=1.28.0",
            "plotly>=5.17.0",
            "altair>=5.1.0",
            "bokeh>=3.3.0"
        ]
        
        for package in packages:
            click.echo(f"   Installing {package}...")
            subprocess.run([
                sys.executable, "-m", "pip", "install", package
            ], check=True, capture_output=True)
        
        click.echo("✅ All UI dependencies installed successfully!")
        
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Failed to install dependencies: {e}")
        return 1
    except Exception as e:
        click.echo(f"❌ Unexpected error: {str(e)}")
        return 1


@ui_cli.command("check")
def check_dependencies():
    """Check if UI dependencies are installed."""
    try:
        import streamlit
        import plotly
        import altair
        import bokeh
        
        click.echo("✅ All UI dependencies are installed:")
        click.echo(f"   Streamlit: {streamlit.__version__}")
        click.echo(f"   Plotly: {plotly.__version__}")
        click.echo(f"   Altair: {altair.__version__}")
        click.echo(f"   Bokeh: {bokeh.__version__}")
        
    except ImportError as e:
        missing_package = str(e).split("'")[1] if "'" in str(e) else "unknown"
        click.echo(f"❌ Missing dependency: {missing_package}")
        click.echo("   Run 'python main.py ui install' to install dependencies")
        return 1


if __name__ == "__main__":
    ui_cli()
