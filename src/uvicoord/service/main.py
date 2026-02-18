"""FastAPI Coordinator Service."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from uvicoord.models import (
    ActiveInstance,
    AppConfig,
    PortRequest,
    PortResponse,
    PortStrategy,
    ReleaseRequest,
    SteppedPortConfig,
)
from uvicoord.service.port_manager import PortManager


# Global port manager instance
port_manager: Optional[PortManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize port manager on startup."""
    global port_manager
    config_path = os.environ.get("UVICOORD_CONFIG")
    port_manager = PortManager(Path(config_path) if config_path else None)
    yield
    # Cleanup on shutdown (instances tracked in memory only)


app = FastAPI(
    title="Uvicoord",
    description="Uvicorn Coordinator - Port registry and launcher for Python web applications",
    version="0.1.0",
    lifespan=lifespan,
)


# ============ Port Allocation Endpoints ============

@app.post("/port/allocate", response_model=PortResponse)
async def allocate_port(request: PortRequest) -> PortResponse:
    """Allocate a port for an application instance."""
    try:
        port, instance_id = port_manager.allocate_port(
            app_name=request.app_name,
            instance_id=request.instance_id,
            pid=request.pid,
        )
        return PortResponse(
            port=port,
            app_name=request.app_name,
            instance_id=instance_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/port/release")
async def release_port(request: ReleaseRequest) -> dict:
    """Release a port allocation."""
    released = port_manager.release_port(
        app_name=request.app_name,
        instance_id=request.instance_id,
        pid=request.pid,
    )
    return {"released": released}


# ============ Instance Management Endpoints ============

@app.get("/instances", response_model=list[ActiveInstance])
async def list_instances() -> list[ActiveInstance]:
    """List all active instances."""
    return port_manager.get_active_instances()


@app.get("/instances/{app_name}", response_model=list[ActiveInstance])
async def list_app_instances(app_name: str) -> list[ActiveInstance]:
    """List active instances for a specific app."""
    return port_manager.get_instances_for_app(app_name)


@app.post("/instances/cleanup")
async def cleanup_instances() -> dict:
    """Remove dead instances (processes no longer running)."""
    count = port_manager.cleanup_dead_instances()
    return {"cleaned": count}


# ============ App Registry Endpoints ============

class AddAppRequest(BaseModel):
    """Request to add a new app."""
    name: str
    path: str
    command: str = "uvicorn app.main:app --reload"
    port_strategy: PortStrategy = PortStrategy.ANY
    port: Optional[int] = None
    port_range: Optional[list[int]] = None
    ports: Optional[list[int]] = None
    port_step: Optional[dict] = None


@app.get("/apps")
async def list_apps() -> dict:
    """List all registered applications."""
    apps = port_manager.list_apps()
    result = {}
    for name, app in apps.items():
        result[name] = {
            "path": app.path,
            "command": app.command,
            "port_strategy": app.port_strategy.value,
            "available_ports": app.get_available_ports()[:10],  # First 10 for display
        }
    return result


@app.get("/apps/{name}")
async def get_app(name: str) -> dict:
    """Get details of a specific application."""
    app = port_manager.get_app(name)
    if not app:
        raise HTTPException(status_code=404, detail=f"App '{name}' not found")
    return {
        "name": app.name,
        "path": app.path,
        "command": app.command,
        "port_strategy": app.port_strategy.value,
        "available_ports": app.get_available_ports(),
    }


@app.post("/apps")
async def add_app(request: AddAppRequest) -> dict:
    """Register a new application."""
    # Build AppConfig
    port_range = tuple(request.port_range) if request.port_range else None
    port_step = SteppedPortConfig(**request.port_step) if request.port_step else None
    
    app = AppConfig(
        name=request.name,
        path=request.path,
        command=request.command,
        port_strategy=request.port_strategy,
        port=request.port,
        port_range=port_range,
        ports=request.ports,
        port_step=port_step,
    )
    port_manager.add_app(app)
    return {"status": "added", "name": request.name}


@app.delete("/apps/{name}")
async def remove_app(name: str) -> dict:
    """Remove an application from registry."""
    if port_manager.remove_app(name):
        return {"status": "removed", "name": name}
    raise HTTPException(status_code=404, detail=f"App '{name}' not found")


# ============ Config Endpoints ============

@app.get("/config")
async def get_config() -> dict:
    """Get current configuration."""
    return {
        "coordinator_port": port_manager.config.coordinator_port,
        "default_port_range": list(port_manager.config.default_port_range),
        "config_path": str(port_manager.config_path),
    }


@app.post("/config/reload")
async def reload_config() -> dict:
    """Reload configuration from file."""
    port_manager.reload_config()
    return {"status": "reloaded"}


# ============ Health Check ============

@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "apps_registered": len(port_manager.config.apps),
        "active_instances": len(port_manager.active_instances),
    }


def run_service():
    """Run the coordinator service."""
    config_path = os.environ.get("UVICOORD_CONFIG")
    if config_path:
        pm = PortManager(Path(config_path))
    else:
        pm = PortManager()
    
    port = pm.config.coordinator_port
    print(f"Starting Uvicoord service on port {port}...")
    print(f"Config file: {pm.config_path}")
    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    run_service()
