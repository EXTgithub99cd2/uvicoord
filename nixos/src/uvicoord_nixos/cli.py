"""Uvicoord NixOS CLI - Extends core CLI with NixOS/systemd commands."""

import sys

import typer
from rich import print as rprint

# Import and extend the core CLI
from uvicoord.cli.main import app, service_app, check_service
from uvicoord_nixos.platform import NixOSPlatform


@service_app.command("install")
def service_install():
    """Show NixOS/systemd installation instructions."""
    platform = NixOSPlatform()
    platform.install()


@service_app.command("uninstall")
def service_uninstall():
    """Show NixOS/systemd uninstallation instructions."""
    platform = NixOSPlatform()
    platform.uninstall()


@service_app.command("stop")
def service_stop():
    """Stop the coordinator service via systemctl."""
    platform = NixOSPlatform()
    if not platform.stop():
        rprint("[yellow]Service could not be stopped. Try: systemctl --user stop uvicoord[/yellow]")


@service_app.command("restart")
def service_restart():
    """Restart the coordinator service."""
    platform = NixOSPlatform()
    if platform.restart():
        rprint("[green]Service restarted.[/green]")
    else:
        rprint("[red]Failed to restart service.[/red]")


@service_app.command("status")
def service_status():
    """Check service status."""
    import httpx
    from uvicoord.cli.main import get_coordinator_url
    
    platform = NixOSPlatform()
    status = platform.get_service_status()
    
    if status.get("installed"):
        rprint("[green]Systemd service: Enabled[/green]")
        if status.get("active"):
            rprint("  Status: active (running)")
        else:
            rprint("  Status: inactive")
    else:
        rprint("[dim]Systemd service: Not installed[/dim]")
        rprint("  Run: [cyan]uvicoord service install[/cyan]")
    
    # Check if service is running via HTTP
    if check_service():
        rprint("[green]Service is running.[/green]")
        try:
            with httpx.Client() as client:
                response = client.get(f"{get_coordinator_url()}/health")
                data = response.json()
                rprint(f"  Apps registered: {data['apps_registered']}")
                rprint(f"  Active instances: {data['active_instances']}")
        except Exception:
            pass
    else:
        rprint("[red]Service is not running.[/red]")


if __name__ == "__main__":
    app()
