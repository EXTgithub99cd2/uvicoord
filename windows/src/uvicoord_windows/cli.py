"""Uvicoord Windows CLI - Extends core CLI with Windows-specific commands."""

import sys

import typer
from rich import print as rprint

# Import and extend the core CLI
from uvicoord.cli.main import app, service_app, check_service
from uvicoord_windows.platform import WindowsPlatform


# Override/extend service commands for Windows

@service_app.command("install")
def service_install(
    elevate: bool = typer.Option(False, "--elevate", "-e", help="Auto-elevate to admin"),
    for_user: str = typer.Option(None, "--for-user", hidden=True, help="Install for specific user"),
):
    """Install Uvicoord as a Windows startup task (Task Scheduler)."""
    if sys.platform != "win32":
        rprint("[red]This command is only available on Windows.[/red]")
        raise typer.Exit(1)
    
    platform = WindowsPlatform()
    success = platform.install(elevate=elevate, for_user=for_user)
    if not success:
        raise typer.Exit(1)


@service_app.command("uninstall")
def service_uninstall(
    elevate: bool = typer.Option(False, "--elevate", "-e", help="Auto-elevate to admin"),
):
    """Remove the Uvicoord startup task."""
    if sys.platform != "win32":
        rprint("[red]This command is only available on Windows.[/red]")
        raise typer.Exit(1)
    
    platform = WindowsPlatform()
    success = platform.uninstall(elevate=elevate)
    if not success:
        raise typer.Exit(1)


# Override stop to use Task Scheduler
@service_app.command("stop")
def service_stop():
    """Stop the coordinator service."""
    if sys.platform != "win32":
        rprint("[yellow]Service must be stopped manually.[/yellow]")
        return
    
    platform = WindowsPlatform()
    if platform.stop():
        rprint("[green]Service stopped.[/green]")
    else:
        rprint("[yellow]To stop the service, use Task Manager or Ctrl+C if running in foreground.[/yellow]")


# Override status to show Task Scheduler info
@service_app.command("status")
def service_status():
    """Check service status."""
    import httpx
    from uvicoord.cli.main import get_coordinator_url
    
    # Check task status on Windows
    if sys.platform == "win32":
        platform = WindowsPlatform()
        task_status = platform.get_task_status()
        
        if task_status.get("installed"):
            rprint("[green]Startup task: Installed[/green]")
            if "task_status" in task_status:
                rprint(f"  Task status: {task_status['task_status']}")
        else:
            rprint("[dim]Startup task: Not installed[/dim]")
    
    # Check if service is running
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
