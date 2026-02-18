"""Port allocation and instance management."""

import json
import socket
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import psutil

from uvicoord.models import (
    ActiveInstance,
    AppConfig,
    CoordinatorConfig,
    PortStrategy,
    SteppedPortConfig,
)


class PortManager:
    """Manages port allocation and active instances."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self._default_config_path()
        self.config = self._load_config()
        self.active_instances: dict[str, ActiveInstance] = {}  # key = "app_name:instance_id"
    
    @staticmethod
    def _default_config_path() -> Path:
        """Get default config path."""
        return Path.home() / ".uvicoord" / "config.json"
    
    def _load_config(self) -> CoordinatorConfig:
        """Load configuration from file."""
        if not self.config_path.exists():
            # Create default config
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            config = CoordinatorConfig()
            self._save_config(config)
            return config
        
        with open(self.config_path, "r") as f:
            data = json.load(f)
        
        # Convert apps dict to AppConfig objects
        apps = {}
        for name, app_data in data.get("apps", {}).items():
            app_data["name"] = name
            # Handle port_range as tuple
            if "port_range" in app_data and isinstance(app_data["port_range"], list):
                app_data["port_range"] = tuple(app_data["port_range"])
            # Handle port_step
            if "port_step" in app_data and isinstance(app_data["port_step"], dict):
                app_data["port_step"] = SteppedPortConfig(**app_data["port_step"])
            apps[name] = AppConfig(**app_data)
        
        # Handle default_port_range as tuple
        default_range = data.get("default_port_range", [8100, 8199])
        if isinstance(default_range, list):
            default_range = tuple(default_range)
        
        return CoordinatorConfig(
            coordinator_port=data.get("coordinator_port", 9000),
            default_port_range=default_range,
            apps=apps,
        )
    
    def _save_config(self, config: Optional[CoordinatorConfig] = None) -> None:
        """Save configuration to file."""
        config = config or self.config
        
        data = {
            "coordinator_port": config.coordinator_port,
            "default_port_range": list(config.default_port_range),
            "apps": {},
        }
        
        for name, app in config.apps.items():
            app_data = {
                "path": app.path,
                "command": app.command,
                "port_strategy": app.port_strategy.value,
            }
            if app.port is not None:
                app_data["port"] = app.port
            if app.port_range is not None:
                app_data["port_range"] = list(app.port_range)
            if app.ports is not None:
                app_data["ports"] = app.ports
            if app.port_step is not None:
                app_data["port_step"] = {
                    "start": app.port_step.start,
                    "step": app.port_step.step,
                    "count": app.port_step.count,
                }
            data["apps"][name] = app_data
        
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(data, f, indent=2)
    
    def reload_config(self) -> None:
        """Reload configuration from file."""
        self.config = self._load_config()
    
    def add_app(self, app: AppConfig) -> None:
        """Register a new application."""
        self.config.apps[app.name] = app
        self._save_config()
    
    def remove_app(self, name: str) -> bool:
        """Remove an application from registry."""
        if name in self.config.apps:
            del self.config.apps[name]
            self._save_config()
            return True
        return False
    
    def get_app(self, name: str) -> Optional[AppConfig]:
        """Get application config by name."""
        return self.config.apps.get(name)
    
    def list_apps(self) -> dict[str, AppConfig]:
        """List all registered applications."""
        return self.config.apps
    
    @staticmethod
    def is_port_available(port: int) -> bool:
        """Check if a port is available for binding."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return True
            except OSError:
                return False
    
    def _get_ports_for_app(self, app_name: str) -> list[int]:
        """Get list of ports available for an app."""
        app = self.config.apps.get(app_name)
        if not app:
            # Unknown app, use default range
            start, end = self.config.default_port_range
            return list(range(start, end + 1))
        
        ports = app.get_available_ports()
        if not ports:
            # ANY strategy, use default range
            start, end = self.config.default_port_range
            return list(range(start, end + 1))
        
        return ports
    
    def _get_used_ports(self) -> set[int]:
        """Get set of ports currently in use by active instances."""
        return {inst.port for inst in self.active_instances.values()}
    
    def allocate_port(
        self,
        app_name: str,
        instance_id: Optional[str] = None,
        pid: int = 0
    ) -> tuple[int, str]:
        """
        Allocate a port for an application instance.
        
        Returns:
            Tuple of (port, instance_id)
        
        Raises:
            ValueError: If no ports available
        """
        instance_id = instance_id or str(uuid.uuid4())[:8]
        instance_key = f"{app_name}:{instance_id}"
        
        # Check if this instance already has a port
        if instance_key in self.active_instances:
            existing = self.active_instances[instance_key]
            # Verify the process is still running
            if psutil.pid_exists(existing.pid):
                return existing.port, instance_id
            # Process died, clean up
            del self.active_instances[instance_key]
        
        # Get candidate ports
        candidate_ports = self._get_ports_for_app(app_name)
        used_ports = self._get_used_ports()
        
        # Find first available port
        for port in candidate_ports:
            if port not in used_ports and self.is_port_available(port):
                # Allocate this port
                self.active_instances[instance_key] = ActiveInstance(
                    app_name=app_name,
                    instance_id=instance_id,
                    port=port,
                    pid=pid,
                    started_at=datetime.now(timezone.utc).isoformat(),
                )
                return port, instance_id
        
        raise ValueError(f"No available ports for app '{app_name}'")
    
    def release_port(
        self,
        app_name: str,
        instance_id: Optional[str] = None,
        pid: Optional[int] = None
    ) -> bool:
        """
        Release a port allocation.
        
        Can identify by instance_id or pid.
        """
        if instance_id:
            instance_key = f"{app_name}:{instance_id}"
            if instance_key in self.active_instances:
                del self.active_instances[instance_key]
                return True
        
        if pid:
            # Find by PID
            to_remove = [
                key for key, inst in self.active_instances.items()
                if inst.pid == pid and inst.app_name == app_name
            ]
            for key in to_remove:
                del self.active_instances[key]
            return len(to_remove) > 0
        
        return False
    
    def cleanup_dead_instances(self) -> int:
        """Remove instances whose processes are no longer running."""
        dead_instances = [
            key for key, inst in self.active_instances.items()
            if not psutil.pid_exists(inst.pid)
        ]
        for key in dead_instances:
            del self.active_instances[key]
        return len(dead_instances)
    
    def get_active_instances(self) -> list[ActiveInstance]:
        """Get all active instances."""
        self.cleanup_dead_instances()
        return list(self.active_instances.values())
    
    def get_instances_for_app(self, app_name: str) -> list[ActiveInstance]:
        """Get active instances for a specific app."""
        self.cleanup_dead_instances()
        return [
            inst for inst in self.active_instances.values()
            if inst.app_name == app_name
        ]
