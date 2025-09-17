"""Advanced monitoring and alerting system for the trading platform."""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

import pandas as pd
import structlog

from packages.core import get_logger
from packages.core.config import settings


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of alerts."""
    SYSTEM = "system"
    TRADING = "trading"
    PERFORMANCE = "performance"
    RISK = "risk"
    DATA = "data"


@dataclass
class Alert:
    """Alert data structure."""
    id: str
    timestamp: datetime
    level: AlertLevel
    type: AlertType
    title: str
    message: str
    component: str
    metadata: Dict[str, Any]
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class SystemMetrics:
    """System performance metrics."""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_positions: int
    daily_pnl: float
    total_trades: int
    error_rate: float
    latency_ms: float


class MonitoringSystem:
    """Advanced monitoring system for the trading platform."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.alerts: List[Alert] = []
        self.metrics_history: List[SystemMetrics] = []
        self.alert_handlers = []
        self.monitoring_active = False
        
        # Thresholds
        self.thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0,
            'error_rate': 5.0,
            'latency_ms': 1000.0,
            'daily_loss_limit': -5.0,  # 5% daily loss
            'position_concentration': 25.0,  # Max 25% in single position
        }
        
        self.logger.info("Monitoring system initialized")
    
    async def start_monitoring(self, interval: int = 60):
        """Start continuous monitoring."""
        self.monitoring_active = True
        self.logger.info(f"Starting monitoring with {interval}s interval")
        
        while self.monitoring_active:
            try:
                await self._collect_metrics()
                await self._check_alerts()
                await asyncio.sleep(interval)
                
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}", exc_info=True)
                await asyncio.sleep(interval)
    
    def stop_monitoring(self):
        """Stop monitoring."""
        self.monitoring_active = False
        self.logger.info("Monitoring stopped")
    
    async def _collect_metrics(self):
        """Collect system metrics."""
        try:
            import psutil
            
            # System metrics
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Trading metrics (mock data for now)
            active_positions = await self._get_active_positions_count()
            daily_pnl = await self._get_daily_pnl()
            total_trades = await self._get_total_trades_today()
            error_rate = await self._get_error_rate()
            latency_ms = await self._get_average_latency()
            
            metrics = SystemMetrics(
                timestamp=datetime.now(),
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=(disk.used / disk.total) * 100,
                active_positions=active_positions,
                daily_pnl=daily_pnl,
                total_trades=total_trades,
                error_rate=error_rate,
                latency_ms=latency_ms
            )
            
            self.metrics_history.append(metrics)
            
            # Keep only last 24 hours of metrics
            cutoff_time = datetime.now() - timedelta(hours=24)
            self.metrics_history = [
                m for m in self.metrics_history 
                if m.timestamp > cutoff_time
            ]
            
            self.logger.debug(f"Collected metrics: CPU={cpu_usage:.1f}%, Memory={memory.percent:.1f}%")
            
        except ImportError:
            self.logger.warning("psutil not available, using mock system metrics")
            await self._collect_mock_metrics()
        except Exception as e:
            self.logger.error(f"Failed to collect metrics: {e}")
    
    async def _collect_mock_metrics(self):
        """Collect mock metrics when psutil is not available."""
        import random
        
        metrics = SystemMetrics(
            timestamp=datetime.now(),
            cpu_usage=random.uniform(10, 30),
            memory_usage=random.uniform(40, 60),
            disk_usage=random.uniform(20, 40),
            active_positions=random.randint(5, 15),
            daily_pnl=random.uniform(-500, 1000),
            total_trades=random.randint(10, 50),
            error_rate=random.uniform(0, 2),
            latency_ms=random.uniform(50, 200)
        )
        
        self.metrics_history.append(metrics)
    
    async def _check_alerts(self):
        """Check for alert conditions."""
        if not self.metrics_history:
            return
        
        latest = self.metrics_history[-1]
        
        # System alerts
        await self._check_system_alerts(latest)
        
        # Trading alerts
        await self._check_trading_alerts(latest)
        
        # Performance alerts
        await self._check_performance_alerts(latest)
        
        # Risk alerts
        await self._check_risk_alerts(latest)
    
    async def _check_system_alerts(self, metrics: SystemMetrics):
        """Check system-related alerts."""
        
        # High CPU usage
        if metrics.cpu_usage > self.thresholds['cpu_usage']:
            await self._create_alert(
                AlertLevel.WARNING,
                AlertType.SYSTEM,
                "High CPU Usage",
                f"CPU usage at {metrics.cpu_usage:.1f}% (threshold: {self.thresholds['cpu_usage']}%)",
                "system",
                {"cpu_usage": metrics.cpu_usage}
            )
        
        # High memory usage
        if metrics.memory_usage > self.thresholds['memory_usage']:
            await self._create_alert(
                AlertLevel.WARNING,
                AlertType.SYSTEM,
                "High Memory Usage",
                f"Memory usage at {metrics.memory_usage:.1f}% (threshold: {self.thresholds['memory_usage']}%)",
                "system",
                {"memory_usage": metrics.memory_usage}
            )
        
        # High disk usage
        if metrics.disk_usage > self.thresholds['disk_usage']:
            await self._create_alert(
                AlertLevel.ERROR,
                AlertType.SYSTEM,
                "High Disk Usage",
                f"Disk usage at {metrics.disk_usage:.1f}% (threshold: {self.thresholds['disk_usage']}%)",
                "system",
                {"disk_usage": metrics.disk_usage}
            )
    
    async def _check_trading_alerts(self, metrics: SystemMetrics):
        """Check trading-related alerts."""
        
        # High error rate
        if metrics.error_rate > self.thresholds['error_rate']:
            await self._create_alert(
                AlertLevel.ERROR,
                AlertType.TRADING,
                "High Error Rate",
                f"Trading error rate at {metrics.error_rate:.1f}% (threshold: {self.thresholds['error_rate']}%)",
                "trading",
                {"error_rate": metrics.error_rate}
            )
        
        # Daily loss limit
        if metrics.daily_pnl < self.thresholds['daily_loss_limit'] * 1000:  # Convert to dollars
            await self._create_alert(
                AlertLevel.CRITICAL,
                AlertType.RISK,
                "Daily Loss Limit Approached",
                f"Daily P&L at ${metrics.daily_pnl:.2f} (limit: ${self.thresholds['daily_loss_limit'] * 1000:.2f})",
                "trading",
                {"daily_pnl": metrics.daily_pnl}
            )
    
    async def _check_performance_alerts(self, metrics: SystemMetrics):
        """Check performance-related alerts."""
        
        # High latency
        if metrics.latency_ms > self.thresholds['latency_ms']:
            await self._create_alert(
                AlertLevel.WARNING,
                AlertType.PERFORMANCE,
                "High Latency",
                f"Average latency at {metrics.latency_ms:.0f}ms (threshold: {self.thresholds['latency_ms']:.0f}ms)",
                "performance",
                {"latency_ms": metrics.latency_ms}
            )
    
    async def _check_risk_alerts(self, metrics: SystemMetrics):
        """Check risk-related alerts."""
        
        # Position concentration (would need actual position data)
        # This is a placeholder for risk monitoring
        pass
    
    async def _create_alert(
        self,
        level: AlertLevel,
        alert_type: AlertType,
        title: str,
        message: str,
        component: str,
        metadata: Dict[str, Any]
    ):
        """Create a new alert."""
        
        alert_id = f"{component}_{alert_type.value}_{int(time.time())}"
        
        # Check if similar alert already exists (avoid spam)
        similar_alerts = [
            a for a in self.alerts
            if a.title == title and a.component == component and not a.resolved
            and (datetime.now() - a.timestamp).seconds < 300  # Within last 5 minutes
        ]
        
        if similar_alerts:
            self.logger.debug(f"Skipping duplicate alert: {title}")
            return
        
        alert = Alert(
            id=alert_id,
            timestamp=datetime.now(),
            level=level,
            type=alert_type,
            title=title,
            message=message,
            component=component,
            metadata=metadata
        )
        
        self.alerts.append(alert)
        self.logger.warning(f"Alert created: [{level.value.upper()}] {title} - {message}")
        
        # Send to alert handlers
        await self._send_alert(alert)
    
    async def _send_alert(self, alert: Alert):
        """Send alert to configured handlers."""
        for handler in self.alert_handlers:
            try:
                await handler(alert)
            except Exception as e:
                self.logger.error(f"Alert handler failed: {e}")
    
    def add_alert_handler(self, handler):
        """Add an alert handler function."""
        self.alert_handlers.append(handler)
        self.logger.info("Alert handler added")
    
    def resolve_alert(self, alert_id: str):
        """Resolve an alert."""
        for alert in self.alerts:
            if alert.id == alert_id and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                self.logger.info(f"Alert resolved: {alert.title}")
                return True
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active (unresolved) alerts."""
        return [a for a in self.alerts if not a.resolved]
    
    def get_alerts_by_level(self, level: AlertLevel) -> List[Alert]:
        """Get alerts by severity level."""
        return [a for a in self.alerts if a.level == level and not a.resolved]
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        if not self.metrics_history:
            return {"status": "No metrics available"}
        
        latest = self.metrics_history[-1]
        active_alerts = self.get_active_alerts()
        
        # Determine overall system health
        critical_alerts = [a for a in active_alerts if a.level == AlertLevel.CRITICAL]
        error_alerts = [a for a in active_alerts if a.level == AlertLevel.ERROR]
        
        if critical_alerts:
            health_status = "CRITICAL"
        elif error_alerts:
            health_status = "DEGRADED"
        elif active_alerts:
            health_status = "WARNING"
        else:
            health_status = "HEALTHY"
        
        return {
            "health_status": health_status,
            "timestamp": latest.timestamp.isoformat(),
            "system_metrics": {
                "cpu_usage": latest.cpu_usage,
                "memory_usage": latest.memory_usage,
                "disk_usage": latest.disk_usage
            },
            "trading_metrics": {
                "active_positions": latest.active_positions,
                "daily_pnl": latest.daily_pnl,
                "total_trades": latest.total_trades,
                "error_rate": latest.error_rate,
                "latency_ms": latest.latency_ms
            },
            "alerts": {
                "total_active": len(active_alerts),
                "critical": len([a for a in active_alerts if a.level == AlertLevel.CRITICAL]),
                "error": len([a for a in active_alerts if a.level == AlertLevel.ERROR]),
                "warning": len([a for a in active_alerts if a.level == AlertLevel.WARNING]),
                "info": len([a for a in active_alerts if a.level == AlertLevel.INFO])
            },
            "uptime_hours": self._get_uptime_hours()
        }
    
    def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get metrics summary for the specified time period."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [m for m in self.metrics_history if m.timestamp > cutoff_time]
        
        if not recent_metrics:
            return {"error": "No metrics available for specified period"}
        
        # Calculate averages and extremes
        cpu_values = [m.cpu_usage for m in recent_metrics]
        memory_values = [m.memory_usage for m in recent_metrics]
        pnl_values = [m.daily_pnl for m in recent_metrics]
        
        return {
            "period_hours": hours,
            "data_points": len(recent_metrics),
            "cpu_usage": {
                "avg": sum(cpu_values) / len(cpu_values),
                "max": max(cpu_values),
                "min": min(cpu_values)
            },
            "memory_usage": {
                "avg": sum(memory_values) / len(memory_values),
                "max": max(memory_values),
                "min": min(memory_values)
            },
            "daily_pnl": {
                "current": recent_metrics[-1].daily_pnl,
                "max": max(pnl_values),
                "min": min(pnl_values)
            },
            "total_trades": recent_metrics[-1].total_trades,
            "avg_error_rate": sum(m.error_rate for m in recent_metrics) / len(recent_metrics)
        }
    
    def export_alerts(self, format: str = "json") -> str:
        """Export alerts in specified format."""
        if format == "json":
            alerts_data = [asdict(alert) for alert in self.alerts]
            # Convert datetime objects to strings
            for alert_data in alerts_data:
                alert_data['timestamp'] = alert_data['timestamp'].isoformat()
                if alert_data['resolved_at']:
                    alert_data['resolved_at'] = alert_data['resolved_at'].isoformat()
                alert_data['level'] = alert_data['level'].value
                alert_data['type'] = alert_data['type'].value
            
            return json.dumps(alerts_data, indent=2)
        
        elif format == "csv":
            if not self.alerts:
                return "No alerts to export"
            
            # Convert to DataFrame and export
            alerts_data = []
            for alert in self.alerts:
                alerts_data.append({
                    'id': alert.id,
                    'timestamp': alert.timestamp.isoformat(),
                    'level': alert.level.value,
                    'type': alert.type.value,
                    'title': alert.title,
                    'message': alert.message,
                    'component': alert.component,
                    'resolved': alert.resolved,
                    'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None
                })
            
            df = pd.DataFrame(alerts_data)
            return df.to_csv(index=False)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _get_uptime_hours(self) -> float:
        """Get system uptime in hours (mock implementation)."""
        if self.metrics_history:
            oldest = min(m.timestamp for m in self.metrics_history)
            return (datetime.now() - oldest).total_seconds() / 3600
        return 0.0
    
    # Mock implementations for trading metrics
    async def _get_active_positions_count(self) -> int:
        """Get count of active positions."""
        # This would integrate with the execution engine
        import random
        return random.randint(0, 20)
    
    async def _get_daily_pnl(self) -> float:
        """Get daily P&L."""
        # This would integrate with the portfolio manager
        import random
        return random.uniform(-1000, 2000)
    
    async def _get_total_trades_today(self) -> int:
        """Get total trades executed today."""
        # This would integrate with the execution engine
        import random
        return random.randint(0, 50)
    
    async def _get_error_rate(self) -> float:
        """Get current error rate percentage."""
        # This would analyze recent logs
        import random
        return random.uniform(0, 3)
    
    async def _get_average_latency(self) -> float:
        """Get average system latency in milliseconds."""
        # This would measure actual response times
        import random
        return random.uniform(50, 300)


# Example alert handlers
async def console_alert_handler(alert: Alert):
    """Simple console alert handler."""
    print(f"[{alert.level.value.upper()}] {alert.title}: {alert.message}")


async def file_alert_handler(alert: Alert):
    """File-based alert handler."""
    try:
        import os
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        with open(f"{log_dir}/alerts.log", "a") as f:
            f.write(f"{alert.timestamp.isoformat()} [{alert.level.value.upper()}] {alert.title}: {alert.message}\n")
    except Exception as e:
        print(f"Failed to write alert to file: {e}")


# Email alert handler (requires email configuration)
async def email_alert_handler(alert: Alert):
    """Email alert handler (placeholder)."""
    # This would send emails for critical alerts
    if alert.level == AlertLevel.CRITICAL:
        print(f"EMAIL ALERT: {alert.title} - {alert.message}")


# Slack alert handler (requires Slack webhook)
async def slack_alert_handler(alert: Alert):
    """Slack alert handler (placeholder)."""
    # This would send Slack notifications
    if alert.level in [AlertLevel.CRITICAL, AlertLevel.ERROR]:
        print(f"SLACK ALERT: {alert.title} - {alert.message}")


# Global monitoring instance
monitoring_system = MonitoringSystem()
