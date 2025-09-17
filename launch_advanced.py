#!/usr/bin/env python3
"""
Advanced Trading Platform Launcher
Integrates all Phase 7 advanced features: monitoring, web dashboard, API endpoints, and analytics.
"""

import asyncio
import argparse
import signal
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import logging

# Import all advanced components
from monitoring.system import monitoring_system, console_alert_handler, file_alert_handler
from monitoring.dashboard import dashboard
from api.endpoints import trading_api
from analytics.performance import performance_analyzer, generate_mock_returns


class AdvancedPlatformLauncher:
    """Advanced trading platform launcher with all Phase 7 features."""
    
    def __init__(self):
        self.running = False
        self.tasks = []
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False
    
    async def start_monitoring_system(self, config):
        """Start the monitoring system."""
        self.logger.info("Starting monitoring system...")
        
        # Add alert handlers
        monitoring_system.add_alert_handler(console_alert_handler)
        monitoring_system.add_alert_handler(file_alert_handler)
        
        # Start monitoring loop
        monitoring_task = asyncio.create_task(
            monitoring_system.start_monitoring(interval=config.get('monitoring_interval', 30))
        )
        self.tasks.append(monitoring_task)
        
        self.logger.info("Monitoring system started")
        return monitoring_task
    
    async def start_web_dashboard(self, config):
        """Start the web dashboard."""
        self.logger.info("Starting web dashboard...")
        
        host = config.get('dashboard_host', '0.0.0.0')
        port = config.get('dashboard_port', 8080)
        
        # Start dashboard in executor to avoid blocking
        dashboard_task = asyncio.create_task(
            dashboard.start_server(host=host, port=port)
        )
        self.tasks.append(dashboard_task)
        
        self.logger.info(f"Web dashboard started on http://{host}:{port}")
        return dashboard_task
    
    async def start_api_server(self, config):
        """Start the API server."""
        self.logger.info("Starting API server...")
        
        host = config.get('api_host', '0.0.0.0')
        port = config.get('api_port', 8000)
        
        # Import uvicorn here to handle import errors gracefully
        try:
            import uvicorn
            
            api_config = uvicorn.Config(
                app=trading_api.app,
                host=host,
                port=port,
                log_level="info",
                access_log=True
            )
            server = uvicorn.Server(api_config)
            
            api_task = asyncio.create_task(server.serve())
            self.tasks.append(api_task)
            
            self.logger.info(f"API server started on http://{host}:{port}")
            return api_task
            
        except ImportError:
            self.logger.error("uvicorn not available, API server not started")
            return None
    
    async def start_performance_analytics(self, config):
        """Start performance analytics background tasks."""
        self.logger.info("Starting performance analytics...")
        
        # Generate sample analytics report
        if config.get('generate_sample_reports', False):
            await self._generate_sample_reports()
        
        # In production, this would connect to actual trading data
        self.logger.info("Performance analytics ready")
    
    async def _generate_sample_reports(self):
        """Generate sample performance reports for demonstration."""
        try:
            # Generate mock data
            mock_returns = generate_mock_returns(days=252, annual_return=0.12, volatility=0.18)
            benchmark_returns = generate_mock_returns(days=252, annual_return=0.08, volatility=0.15)
            
            # Analyze performance
            analysis = performance_analyzer.analyze_strategy_performance(
                mock_returns,
                benchmark_returns,
                "Sample_Strategy"
            )
            
            # Generate reports
            html_report = performance_analyzer.generate_performance_report(analysis, "html")
            json_report = performance_analyzer.generate_performance_report(analysis, "json")
            
            # Create charts
            chart_files = performance_analyzer.create_performance_charts(
                mock_returns,
                benchmark_returns,
                "Sample_Strategy"
            )
            
            self.logger.info(f"Sample reports generated:")
            self.logger.info(f"  HTML: {html_report}")
            self.logger.info(f"  JSON: {json_report}")
            self.logger.info(f"  Charts: {len(chart_files)} files")
            
        except Exception as e:
            self.logger.error(f"Failed to generate sample reports: {e}")
    
    async def run_full_platform(self, config):
        """Run the complete advanced trading platform."""
        self.logger.info("🚀 Starting Advanced Trading Platform...")
        self.logger.info("=" * 60)
        
        self.running = True
        
        try:
            # Start all components
            tasks = []
            
            # 1. Monitoring System
            if config.get('enable_monitoring', True):
                monitor_task = await self.start_monitoring_system(config)
                if monitor_task:
                    tasks.append(monitor_task)
            
            # 2. Web Dashboard
            if config.get('enable_dashboard', True):
                dashboard_task = await self.start_web_dashboard(config)
                if dashboard_task:
                    tasks.append(dashboard_task)
            
            # 3. API Server
            if config.get('enable_api', True):
                api_task = await self.start_api_server(config)
                if api_task:
                    tasks.append(api_task)
            
            # 4. Performance Analytics
            if config.get('enable_analytics', True):
                await self.start_performance_analytics(config)
            
            self.logger.info("=" * 60)
            self.logger.info("✅ All systems started successfully!")
            self.logger.info("")
            self.logger.info("📊 Access Points:")
            
            if config.get('enable_dashboard', True):
                dashboard_url = f"http://{config.get('dashboard_host', 'localhost')}:{config.get('dashboard_port', 8080)}"
                self.logger.info(f"  🌐 Web Dashboard: {dashboard_url}")
            
            if config.get('enable_api', True):
                api_url = f"http://{config.get('api_host', 'localhost')}:{config.get('api_port', 8000)}"
                self.logger.info(f"  🔌 API Endpoints: {api_url}")
                self.logger.info(f"  📚 API Documentation: {api_url}/docs")
            
            self.logger.info("")
            self.logger.info("🛑 Press Ctrl+C to stop all services")
            self.logger.info("=" * 60)
            
            # Wait for all tasks or shutdown signal
            if tasks:
                while self.running:
                    await asyncio.sleep(1)
                    
                    # Check if any task failed
                    for task in tasks:
                        if task.done() and task.exception():
                            self.logger.error(f"Task failed: {task.exception()}")
                            self.running = False
                            break
            else:
                self.logger.warning("No services were started successfully")
                
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        except Exception as e:
            self.logger.error(f"Platform error: {e}", exc_info=True)
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful shutdown of all services."""
        self.logger.info("🛑 Shutting down Advanced Trading Platform...")
        
        # Stop monitoring
        if monitoring_system.monitoring_active:
            monitoring_system.stop_monitoring()
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        self.logger.info("✅ Shutdown complete")


def create_default_config():
    """Create default configuration."""
    return {
        'enable_monitoring': True,
        'enable_dashboard': True,
        'enable_api': True,
        'enable_analytics': True,
        
        'monitoring_interval': 30,  # seconds
        
        'dashboard_host': '0.0.0.0',
        'dashboard_port': 8080,
        
        'api_host': '0.0.0.0',
        'api_port': 8000,
        
        'generate_sample_reports': True,
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Advanced Trading Platform Launcher',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Start full platform with defaults
  %(prog)s --no-dashboard           # Start without web dashboard
  %(prog)s --api-port 9000          # Use custom API port
  %(prog)s --monitoring-only        # Start monitoring system only
        """
    )
    
    # Service toggles
    parser.add_argument('--no-monitoring', action='store_true', help='Disable monitoring system')
    parser.add_argument('--no-dashboard', action='store_true', help='Disable web dashboard')
    parser.add_argument('--no-api', action='store_true', help='Disable API server')
    parser.add_argument('--no-analytics', action='store_true', help='Disable analytics')
    
    # Monitoring only mode
    parser.add_argument('--monitoring-only', action='store_true', help='Start monitoring system only')
    
    # Configuration options
    parser.add_argument('--monitoring-interval', type=int, default=30, help='Monitoring interval in seconds')
    parser.add_argument('--dashboard-host', default='0.0.0.0', help='Dashboard host')
    parser.add_argument('--dashboard-port', type=int, default=8080, help='Dashboard port')
    parser.add_argument('--api-host', default='0.0.0.0', help='API host')
    parser.add_argument('--api-port', type=int, default=8000, help='API port')
    
    # Development options
    parser.add_argument('--no-sample-reports', action='store_true', help='Skip generating sample reports')
    
    args = parser.parse_args()
    
    # Create configuration
    config = create_default_config()
    
    # Apply command line overrides
    if args.monitoring_only:
        config.update({
            'enable_monitoring': True,
            'enable_dashboard': False,
            'enable_api': False,
            'enable_analytics': False,
        })
    else:
        config.update({
            'enable_monitoring': not args.no_monitoring,
            'enable_dashboard': not args.no_dashboard,
            'enable_api': not args.no_api,
            'enable_analytics': not args.no_analytics,
        })
    
    config.update({
        'monitoring_interval': args.monitoring_interval,
        'dashboard_host': args.dashboard_host,
        'dashboard_port': args.dashboard_port,
        'api_host': args.api_host,
        'api_port': args.api_port,
        'generate_sample_reports': not args.no_sample_reports,
    })
    
    # Create and run launcher
    launcher = AdvancedPlatformLauncher()
    
    try:
        asyncio.run(launcher.run_full_platform(config))
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Failed to start platform: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
