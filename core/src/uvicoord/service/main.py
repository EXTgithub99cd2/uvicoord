"""FastAPI Coordinator Service."""

import os
import sys
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
    version="0.2.0",
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
    """Get all active instances."""
    return port_manager.get_active_instances()


@app.get("/instances/{app_name}", response_model=list[ActiveInstance])
async def get_app_instances(app_name: str) -> list[ActiveInstance]:
    """Get instances for a specific app."""
    return port_manager.get_instances_for_app(app_name)


@app.post("/instances/cleanup")
async def cleanup_instances() -> dict:
    """Clean up dead instances."""
    cleaned = port_manager.cleanup_dead_instances()
    return {"cleaned": cleaned}


# ============ App Configuration Endpoints ============

class AppAddRequest(BaseModel):
    """Request to add an app."""
    name: str
    path: str
    command: str = "uvicorn app.main:app --reload"
    port_strategy: str = "any"
    port: Optional[int] = None
    port_range: Optional[list[int]] = None
    ports: Optional[list[int]] = None
    port_step: Optional[dict] = None


class AppInfo(BaseModel):
    """App info response."""
    name: str
    path: str
    command: str
    port_strategy: str
    available_ports: list[int]


@app.get("/apps", response_model=dict[str, AppInfo])
async def list_apps() -> dict[str, AppInfo]:
    """List all registered apps."""
    apps = port_manager.list_apps()
    return {
        name: AppInfo(
            name=name,
            path=app.path,
            command=app.command,
            port_strategy=app.port_strategy.value,
            available_ports=app.get_available_ports(),
        )
        for name, app in apps.items()
    }


@app.get("/apps/{name}", response_model=AppInfo)
async def get_app(name: str) -> AppInfo:
    """Get app details."""
    app = port_manager.get_app(name)
    if not app:
        raise HTTPException(status_code=404, detail=f"App '{name}' not found")
    return AppInfo(
        name=name,
        path=app.path,
        command=app.command,
        port_strategy=app.port_strategy.value,
        available_ports=app.get_available_ports(),
    )


@app.post("/apps")
async def add_app(request: AppAddRequest) -> dict:
    """Register a new app."""
    # Build AppConfig
    port_step = None
    if request.port_step:
        port_step = SteppedPortConfig(**request.port_step)
    
    port_range = None
    if request.port_range and len(request.port_range) == 2:
        port_range = tuple(request.port_range)
    
    config = AppConfig(
        name=request.name,
        path=request.path,
        command=request.command,
        port_strategy=PortStrategy(request.port_strategy),
        port=request.port,
        port_range=port_range,
        ports=request.ports,
        port_step=port_step,
    )
    
    port_manager.add_app(config)
    return {"status": "ok", "name": request.name}


@app.delete("/apps/{name}")
async def remove_app(name: str) -> dict:
    """Remove an app."""
    if port_manager.remove_app(name):
        return {"status": "ok", "name": name}
    raise HTTPException(status_code=404, detail=f"App '{name}' not found")


@app.post("/config/reload")
async def reload_config() -> dict:
    """Reload configuration from disk."""
    port_manager.reload_config()
    return {"status": "ok"}


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
    # Detect if running without a console (pythonw.exe on Windows)
    has_console = sys.stdout is not None and hasattr(sys.stdout, 'write')
    try:
        # Test if we can actually write to stdout
        if has_console:
            sys.stdout.write("")
            sys.stdout.flush()
    except (OSError, AttributeError, ValueError):
        has_console = False
    
    config_path = os.environ.get("UVICOORD_CONFIG")
    if config_path:
        pm = PortManager(Path(config_path))
    else:
        pm = PortManager()
    
    port = pm.config.coordinator_port
    
    if has_console:
        print(f"Starting Uvicoord service on port {port}...")
        print(f"Config file: {pm.config_path}")
        log_config = None  # Use default uvicorn logging
    else:
        # Running windowless - disable console logging
        log_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {},
            "handlers": {},
            "loggers": {
                "uvicorn": {"handlers": [], "level": "WARNING"},
                "uvicorn.error": {"handlers": [], "level": "WARNING"},
                "uvicorn.access": {"handlers": [], "level": "WARNING"},
            },
        }
    
    uvicorn.run(app, host="127.0.0.1", port=port, log_config=log_config)


if __name__ == "__main__":
    run_service()
