"""Web dashboard for monitoring and alerting system."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

from monitoring.system import monitoring_system, AlertLevel, AlertType


class WebDashboard:
    """Web dashboard for the monitoring system."""
    
    def __init__(self):
        self.app = FastAPI(title="Trading Platform Dashboard", version="1.0.0")
        self.templates = Jinja2Templates(directory="monitoring/templates")
        self.websocket_clients: List[WebSocket] = []
        
        self._setup_routes()
        self._setup_websockets()
    
    def _setup_routes(self):
        """Setup web routes."""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard(request: Request):
            """Main dashboard page."""
            return self.templates.TemplateResponse("dashboard.html", {"request": request})
        
        @self.app.get("/api/status")
        async def get_status():
            """Get system status."""
            return monitoring_system.get_system_status()
        
        @self.app.get("/api/alerts")
        async def get_alerts(level: str = None, type: str = None, active_only: bool = True):
            """Get alerts with optional filtering."""
            alerts = monitoring_system.alerts
            
            if active_only:
                alerts = [a for a in alerts if not a.resolved]
            
            if level:
                try:
                    alert_level = AlertLevel(level.lower())
                    alerts = [a for a in alerts if a.level == alert_level]
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid alert level: {level}")
            
            if type:
                try:
                    alert_type = AlertType(type.lower())
                    alerts = [a for a in alerts if a.type == alert_type]
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid alert type: {type}")
            
            # Convert to dict for JSON serialization
            alerts_data = []
            for alert in alerts:
                alert_data = {
                    'id': alert.id,
                    'timestamp': alert.timestamp.isoformat(),
                    'level': alert.level.value,
                    'type': alert.type.value,
                    'title': alert.title,
                    'message': alert.message,
                    'component': alert.component,
                    'resolved': alert.resolved,
                    'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
                    'metadata': alert.metadata
                }
                alerts_data.append(alert_data)
            
            return {"alerts": alerts_data}
        
        @self.app.post("/api/alerts/{alert_id}/resolve")
        async def resolve_alert(alert_id: str):
            """Resolve an alert."""
            success = monitoring_system.resolve_alert(alert_id)
            if success:
                # Notify WebSocket clients
                await self._broadcast_alert_update(alert_id, "resolved")
                return {"status": "success", "message": f"Alert {alert_id} resolved"}
            else:
                raise HTTPException(status_code=404, detail="Alert not found or already resolved")
        
        @self.app.get("/api/metrics")
        async def get_metrics(hours: int = 24):
            """Get metrics summary."""
            return monitoring_system.get_metrics_summary(hours)
        
        @self.app.get("/api/metrics/history")
        async def get_metrics_history(hours: int = 24):
            """Get metrics history for charts."""
            cutoff_time = datetime.now() - timedelta(hours=hours)
            metrics = [
                m for m in monitoring_system.metrics_history 
                if m.timestamp > cutoff_time
            ]
            
            # Convert to chart-friendly format
            chart_data = {
                'timestamps': [m.timestamp.isoformat() for m in metrics],
                'cpu_usage': [m.cpu_usage for m in metrics],
                'memory_usage': [m.memory_usage for m in metrics],
                'disk_usage': [m.disk_usage for m in metrics],
                'daily_pnl': [m.daily_pnl for m in metrics],
                'active_positions': [m.active_positions for m in metrics],
                'error_rate': [m.error_rate for m in metrics],
                'latency_ms': [m.latency_ms for m in metrics]
            }
            
            return chart_data
        
        @self.app.get("/api/alerts/export")
        async def export_alerts(format: str = "json"):
            """Export alerts."""
            try:
                data = monitoring_system.export_alerts(format)
                
                if format == "json":
                    return JSONResponse(content=json.loads(data))
                elif format == "csv":
                    from fastapi.responses import PlainTextResponse
                    return PlainTextResponse(data, media_type="text/csv")
                else:
                    raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
                    
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    
    def _setup_websockets(self):
        """Setup WebSocket connections for real-time updates."""
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.websocket_clients.append(websocket)
            
            try:
                while True:
                    # Keep connection alive and send periodic updates
                    await asyncio.sleep(5)
                    
                    # Send current status
                    status = monitoring_system.get_system_status()
                    await websocket.send_json({
                        "type": "status_update",
                        "data": status
                    })
                    
            except WebSocketDisconnect:
                self.websocket_clients.remove(websocket)
            except Exception as e:
                print(f"WebSocket error: {e}")
                if websocket in self.websocket_clients:
                    self.websocket_clients.remove(websocket)
    
    async def _broadcast_alert_update(self, alert_id: str, action: str):
        """Broadcast alert updates to all connected clients."""
        message = {
            "type": "alert_update",
            "data": {
                "alert_id": alert_id,
                "action": action,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # Remove disconnected clients
        disconnected = []
        for client in self.websocket_clients:
            try:
                await client.send_json(message)
            except:
                disconnected.append(client)
        
        for client in disconnected:
            self.websocket_clients.remove(client)
    
    async def start_server(self, host: str = "0.0.0.0", port: int = 8080):
        """Start the web server."""
        config = uvicorn.Config(
            app=self.app,
            host=host,
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    def run(self, host: str = "0.0.0.0", port: int = 8080):
        """Run the web server (blocking)."""
        uvicorn.run(self.app, host=host, port=port)


# Global dashboard instance
dashboard = WebDashboard()


# Setup alert handler to broadcast new alerts
async def websocket_alert_handler(alert):
    """Alert handler that broadcasts to WebSocket clients."""
    message = {
        "type": "new_alert",
        "data": {
            "id": alert.id,
            "timestamp": alert.timestamp.isoformat(),
            "level": alert.level.value,
            "type": alert.type.value,
            "title": alert.title,
            "message": alert.message,
            "component": alert.component
        }
    }
    
    # Remove disconnected clients
    disconnected = []
    for client in dashboard.websocket_clients:
        try:
            await client.send_json(message)
        except:
            disconnected.append(client)
    
    for client in disconnected:
        dashboard.websocket_clients.remove(client)


# Add the WebSocket alert handler
monitoring_system.add_alert_handler(websocket_alert_handler)


if __name__ == "__main__":
    # Run dashboard
    dashboard.run()
