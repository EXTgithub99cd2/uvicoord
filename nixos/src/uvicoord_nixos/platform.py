"""NixOS/systemd platform implementation for Uvicoord."""

import os
import subprocess
import sys
from pathlib import Path


class NixOSPlatform:
    """NixOS/systemd-specific service management."""
    
    SERVICE_NAME = "uvicoord"
    
    def __init__(self):
        self.is_nixos = Path("/etc/NIXOS").exists()
        self.python_exe = sys.executable
    
    def is_service_installed(self) -> bool:
        """Check if the systemd user service is installed."""
        result = subprocess.run(
            ["systemctl", "--user", "is-enabled", self.SERVICE_NAME],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    
    def get_service_status(self) -> dict:
        """Get detailed service status."""
        result = subprocess.run(
            ["systemctl", "--user", "status", self.SERVICE_NAME],
            capture_output=True,
            text=True,
        )
        
        status = {
            "installed": self.is_service_installed(),
            "active": "active (running)" in result.stdout,
        }
        
        return status
    
    def install(self) -> bool:
        """
        Print installation instructions for NixOS.
        
        On NixOS, we don't modify the system directly - instead we output
        the configuration that the user should add to their config.nix or flake.
        """
        print("=" * 60)
        print("UVICOORD NIXOS INSTALLATION")
        print("=" * 60)
        print()
        
        if self.is_nixos:
            print("Detected NixOS system.")
            print()
            print("Option 1: Use the flake (recommended)")
            print("-" * 40)
            print("""
# In your flake.nix inputs:
uvicoord.url = "github:EXTgithub99cd2/uvicoord";

# In your nixosConfigurations:
modules = [
  uvicoord.nixosModules.default
  {
    services.uvicoord = {
      enable = true;
      # port = 9000;  # optional, default 9000
    };
  }
];
""")
            print()
            print("Option 2: Systemd user service (without flake)")
            print("-" * 40)
            
        self._print_systemd_unit()
        
        print()
        print("After creating the service file, run:")
        print("  systemctl --user daemon-reload")
        print("  systemctl --user enable --now uvicoord")
        print()
        
        return True
    
    def _print_systemd_unit(self) -> None:
        """Print systemd user service unit file."""
        config_dir = Path.home() / ".config" / "systemd" / "user"
        service_file = config_dir / "uvicoord.service"
        
        unit_content = f"""[Unit]
Description=Uvicoord - Uvicorn Coordinator Service
After=network.target

[Service]
Type=simple
ExecStart={self.python_exe} -m uvicoord.service.main
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
"""
        
        print(f"Create: {service_file}")
        print()
        print(unit_content)
    
    def uninstall(self) -> bool:
        """Print uninstallation instructions."""
        print("To remove the systemd service:")
        print()
        print("  systemctl --user disable --now uvicoord")
        print("  rm ~/.config/systemd/user/uvicoord.service")
        print("  systemctl --user daemon-reload")
        print()
        print("If using NixOS flake, remove the module from your configuration.")
        return True
    
    def start(self) -> bool:
        """Start the service via systemctl."""
        result = subprocess.run(
            ["systemctl", "--user", "start", self.SERVICE_NAME],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("Service started.")
            return True
        
        if "Unit uvicoord.service not found" in result.stderr:
            print("Service not installed. Run: uvicoord service install")
            return False
        
        print(f"Failed to start: {result.stderr}")
        return False
    
    def stop(self) -> bool:
        """Stop the service via systemctl."""
        result = subprocess.run(
            ["systemctl", "--user", "stop", self.SERVICE_NAME],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("Service stopped.")
            return True
        return False
    
    def restart(self) -> bool:
        """Restart the service."""
        result = subprocess.run(
            ["systemctl", "--user", "restart", self.SERVICE_NAME],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
