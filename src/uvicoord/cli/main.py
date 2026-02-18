"""Uvicoord CLI - Command line interface for managing uvicorn applications."""

import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Optional

import httpx
import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="uvicoord",
    help="Uvicorn Coordinator - Port registry and launcher for Python web applications",
)
console = Console()

# Default coordinator URL
DEFAULT_COORDINATOR_URL = "http://127.0.0.1:9000"


def get_coordinator_url() -> str:
    """Get coordinator service URL from environment or default."""
    return os.environ.get("UVICOORD_URL", DEFAULT_COORDINATOR_URL)


def check_service() -> bool:
    """Check if coordinator service is running."""
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get(f"{get_coordinator_url()}/health")
            return response.status_code == 200
    except httpx.RequestError:
        return False


def require_service():
    """Ensure service is running, raise error if not."""
    if not check_service():
        rprint("[red]Error: Uvicoord service is not running.[/red]")
        rprint("Start it with: [cyan]uvicoord service start[/cyan]")
        raise typer.Exit(1)


# ============ Service Commands ============

service_app = typer.Typer(help="Manage the coordinator service")
app.add_typer(service_app, name="service")


@service_app.command("start")
def service_start(
    background: bool = typer.Option(False, "--background", "-b", help="Run in background"),
):
    """Start the coordinator service."""
    if check_service():
        rprint("[yellow]Service is already running.[/yellow]")
        return
    
    if background:
        # Start as background process
        if sys.platform == "win32":
            # Windows: use pythonw or start in background
            subprocess.Popen(
                [sys.executable, "-m", "uvicoord.service.main"],
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            rprint("[green]Service started in background.[/green]")
        else:
            # Unix: fork
            subprocess.Popen(
                [sys.executable, "-m", "uvicoord.service.main"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            rprint("[green]Service started in background.[/green]")
    else:
        # Run in foreground
        rprint("[cyan]Starting Uvicoord service (Ctrl+C to stop)...[/cyan]")
        from uvicoord.service.main import run_service
        run_service()


@service_app.command("stop")
def service_stop():
    """Stop the coordinator service."""
    if sys.platform == "win32":
        # Try to stop via Task Scheduler first
        result = subprocess.run(
            ["schtasks", "/End", "/TN", "Uvicoord"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            rprint("[green]Service stopped.[/green]")
            return
    
    rprint("[yellow]To stop the service, use Task Manager or Ctrl+C if running in foreground.[/yellow]")


@service_app.command("install")
def service_install(
    elevate: bool = typer.Option(False, "--elevate", "-e", help="Auto-elevate to admin (opens new window)"),
    for_user: str = typer.Option(None, "--for-user", hidden=True, help="Install for specific user (internal use)"),
):
    """Install the coordinator as a startup service (uses Task Scheduler on Windows)."""
    if sys.platform != "win32":
        rprint("[red]Service installation is only supported on Windows.[/red]")
        rprint("On Linux/macOS, use systemd or launchd instead.")
        raise typer.Exit(1)
    
    python_exe = sys.executable
    pythonw_exe = python_exe.replace("python.exe", "pythonw.exe")
    
    # Get the target user (current user, or the one passed via --for-user)
    target_user = for_user or os.environ.get("USERNAME", "")
    target_user_domain = os.environ.get("USERDOMAIN", "")
    
    # Check for Windows Store Python
    if "WindowsApps" in python_exe:
        rprint("[yellow]Note: Windows Store Python detected. Using Task Scheduler.[/yellow]")
    
    # If elevate requested, restart as admin but pass the CURRENT user
    if elevate:
        current_user = os.environ.get("USERNAME", "")
        rprint(f"[cyan]Requesting administrator privileges (for user: {current_user})...[/cyan]")
        subprocess.run([
            "powershell", "-Command",
            f"Start-Process powershell -Verb RunAs -ArgumentList '-NoExit -ExecutionPolicy Bypass -Command \"& ''{python_exe}'' -m uvicoord.cli.main service install --for-user {current_user}; Write-Host; Read-Host ''Press Enter to close''\"'"
        ])
        return
    
    # Use pythonw if available (no console window)
    exe_to_use = pythonw_exe if Path(pythonw_exe).exists() else python_exe
    
    # Full user identifier for scheduled task
    full_user = f"{target_user_domain}\\{target_user}" if target_user_domain and target_user else target_user
    
    # Create scheduled task via schtasks command
    task_xml = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Uvicorn Coordinator - Port registry for Python web applications</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <UserId>{full_user}</UserId>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{full_user}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Actions>
    <Exec>
      <Command>{exe_to_use}</Command>
      <Arguments>-m uvicoord.service.main</Arguments>
    </Exec>
  </Actions>
</Task>'''
    
    # Write XML to temp file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-16') as f:
        f.write(task_xml)
        xml_path = f.name
    
    try:
        # Register the task for the target user
        rprint(f"[dim]Installing for user: {full_user}[/dim]")
        result = subprocess.run(
            ["schtasks", "/Create", "/TN", "Uvicoord", "/XML", xml_path, "/F"],
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            if "Access is denied" in result.stderr or "access is denied" in result.stderr.lower():
                rprint("[red]Error: Administrator privileges required.[/red]")
                rprint("\nOptions:")
                rprint("  1. Run with --elevate flag: [cyan]uvicoord service install --elevate[/cyan]")
                rprint("  2. Run terminal as Administrator")
            else:
                rprint(f"[red]Error installing service: {result.stderr}[/red]")
            raise typer.Exit(1)
        
        rprint("[green]Uvicoord installed as startup task.[/green]")
        
        # Add to PATH
        scripts_dir = Path(sys.executable).parent
        
        # If installing for another user (via elevation), modify their registry directly
        if for_user and for_user != os.environ.get("USERNAME", ""):
            # Get the user's SID and modify their PATH via registry
            try:
                # Get SID for the target user
                sid_result = subprocess.run(
                    ["powershell", "-Command", f"(New-Object System.Security.Principal.NTAccount('{for_user}')).Translate([System.Security.Principal.SecurityIdentifier]).Value"],
                    capture_output=True,
                    text=True,
                )
                user_sid = sid_result.stdout.strip()
                
                if user_sid:
                    # Read current PATH from user's registry
                    path_result = subprocess.run(
                        ["reg", "query", f"HKU\\{user_sid}\\Environment", "/v", "Path"],
                        capture_output=True,
                        text=True,
                    )
                    
                    current_user_path = ""
                    if path_result.returncode == 0:
                        # Parse the PATH value from reg query output
                        for line in path_result.stdout.split('\n'):
                            if 'Path' in line and 'REG_' in line:
                                parts = line.split('REG_EXPAND_SZ')
                                if len(parts) > 1:
                                    current_user_path = parts[1].strip()
                                    break
                                parts = line.split('REG_SZ')
                                if len(parts) > 1:
                                    current_user_path = parts[1].strip()
                                    break
                    
                    if str(scripts_dir) not in current_user_path:
                        new_path = f"{current_user_path};{scripts_dir}" if current_user_path else str(scripts_dir)
                        # Set the new PATH
                        set_result = subprocess.run(
                            ["reg", "add", f"HKU\\{user_sid}\\Environment", "/v", "Path", "/t", "REG_EXPAND_SZ", "/d", new_path, "/f"],
                            capture_output=True,
                            text=True,
                        )
                        if set_result.returncode == 0:
                            rprint(f"[green]Added to {for_user}'s PATH: {scripts_dir}[/green]")
                            rprint("[yellow]Restart your terminal for PATH changes to take effect.[/yellow]")
                        else:
                            rprint(f"[yellow]Could not add to PATH: {set_result.stderr}[/yellow]")
                    else:
                        rprint(f"[dim]Already in {for_user}'s PATH[/dim]")
                else:
                    rprint(f"[yellow]Could not find SID for user {for_user}[/yellow]")
            except Exception as e:
                rprint(f"[yellow]Could not add to PATH: {e}[/yellow]")
        else:
            # Add to current user's PATH
            current_path = os.environ.get("PATH", "")
            if str(scripts_dir) not in current_path:
                import winreg
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE)
                    try:
                        user_path, _ = winreg.QueryValueEx(key, "Path")
                    except FileNotFoundError:
                        user_path = ""
                    
                    if str(scripts_dir) not in user_path:
                        new_path = f"{user_path};{scripts_dir}" if user_path else str(scripts_dir)
                        winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
                        rprint(f"[green]Added to user PATH: {scripts_dir}[/green]")
                        rprint("[yellow]Restart your terminal for PATH changes to take effect.[/yellow]")
                    winreg.CloseKey(key)
                except Exception as e:
                    rprint(f"[yellow]Could not add to PATH: {e}[/yellow]")
        
        # Ask if user wants to start now
        rprint("\nStart the service now? Run: [cyan]uvicoord service start[/cyan]")
        
    finally:
        Path(xml_path).unlink(missing_ok=True)


@service_app.command("uninstall")
def service_uninstall():
    """Uninstall the coordinator startup service."""
    if sys.platform != "win32":
        rprint("[red]Service uninstallation is only supported on Windows.[/red]")
        raise typer.Exit(1)
    
    # Stop if running
    subprocess.run(["schtasks", "/End", "/TN", "Uvicoord"], capture_output=True)
    
    # Delete the task
    result = subprocess.run(
        ["schtasks", "/Delete", "/TN", "Uvicoord", "/F"],
        capture_output=True,
        text=True,
    )
    
    if result.returncode == 0:
        rprint("[green]Uvicoord startup task removed.[/green]")
    else:
        rprint(f"[yellow]Could not remove task (may not exist): {result.stderr}[/yellow]")


@service_app.command("status")
def service_status():
    """Check service status."""
    # Check if startup task is installed (Windows)
    if sys.platform == "win32":
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", "Uvicoord"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            rprint("[green]Startup task: Installed[/green]")
        else:
            rprint("[dim]Startup task: Not installed[/dim]")
    
    # Check if service is running
    if check_service():
        rprint("[green]Service is running.[/green]")
        with httpx.Client() as client:
            response = client.get(f"{get_coordinator_url()}/health")
            data = response.json()
            rprint(f"  Apps registered: {data['apps_registered']}")
            rprint(f"  Active instances: {data['active_instances']}")
    else:
        rprint("[red]Service is not running.[/red]")


# ============ App Management Commands ============

@app.command("add")
def add_app(
    name: str = typer.Argument(..., help="Application name"),
    path: str = typer.Option(..., "--path", "-p", help="Path to application directory"),
    command: str = typer.Option(
        "uvicorn app.main:app --reload",
        "--command", "-c",
        help="Uvicorn command to run"
    ),
    dedicated: Optional[int] = typer.Option(None, "--dedicated", "-d", help="Dedicated port"),
    port_range: Optional[str] = typer.Option(None, "--range", "-r", help="Port range (e.g., 8010-8019)"),
    ports: Optional[str] = typer.Option(None, "--ports", "-l", help="Port list (e.g., 8010,8015,8020)"),
    step_start: Optional[int] = typer.Option(None, "--step-start", help="Stepped: start port"),
    step_size: int = typer.Option(1, "--step-size", help="Stepped: increment size"),
    step_count: int = typer.Option(10, "--step-count", help="Stepped: number of ports"),
):
    """Register a new application."""
    require_service()
    
    # Build request
    request_data = {
        "name": name,
        "path": path,
        "command": command,
    }
    
    if dedicated:
        request_data["port_strategy"] = "dedicated"
        request_data["port"] = dedicated
    elif port_range:
        start, end = map(int, port_range.split("-"))
        request_data["port_strategy"] = "range"
        request_data["port_range"] = [start, end]
    elif ports:
        port_list = [int(p.strip()) for p in ports.split(",")]
        request_data["port_strategy"] = "list"
        request_data["ports"] = port_list
    elif step_start:
        request_data["port_strategy"] = "stepped"
        request_data["port_step"] = {
            "start": step_start,
            "step": step_size,
            "count": step_count,
        }
    else:
        request_data["port_strategy"] = "any"
    
    with httpx.Client() as client:
        response = client.post(f"{get_coordinator_url()}/apps", json=request_data)
        if response.status_code == 200:
            rprint(f"[green]Added app '{name}'[/green]")
        else:
            rprint(f"[red]Error: {response.text}[/red]")


@app.command("remove")
def remove_app(name: str = typer.Argument(..., help="Application name")):
    """Remove an application from registry."""
    require_service()
    
    with httpx.Client() as client:
        response = client.delete(f"{get_coordinator_url()}/apps/{name}")
        if response.status_code == 200:
            rprint(f"[green]Removed app '{name}'[/green]")
        else:
            rprint(f"[red]Error: {response.text}[/red]")


@app.command("list")
def list_apps():
    """List all registered applications."""
    require_service()
    
    with httpx.Client() as client:
        response = client.get(f"{get_coordinator_url()}/apps")
        apps = response.json()
    
    if not apps:
        rprint("[yellow]No applications registered.[/yellow]")
        return
    
    table = Table(title="Registered Applications")
    table.add_column("Name", style="cyan")
    table.add_column("Path")
    table.add_column("Strategy", style="green")
    table.add_column("Ports")
    
    for name, app in apps.items():
        ports_str = ", ".join(map(str, app["available_ports"]))
        if len(ports_str) > 30:
            ports_str = ports_str[:27] + "..."
        table.add_row(
            name,
            app["path"],
            app["port_strategy"],
            ports_str or "[dim](default range)[/dim]",
        )
    
    console.print(table)


@app.command("status")
def status():
    """Show status of running instances."""
    require_service()
    
    with httpx.Client() as client:
        response = client.get(f"{get_coordinator_url()}/instances")
        instances = response.json()
    
    if not instances:
        rprint("[yellow]No active instances.[/yellow]")
        return
    
    table = Table(title="Active Instances")
    table.add_column("App", style="cyan")
    table.add_column("Instance ID")
    table.add_column("Port", style="green")
    table.add_column("PID")
    table.add_column("Started")
    
    for inst in instances:
        table.add_row(
            inst["app_name"],
            inst["instance_id"],
            str(inst["port"]),
            str(inst["pid"]),
            inst["started_at"][:19],  # Trim microseconds
        )
    
    console.print(table)


# ============ Run Command ============

@app.command("run")
def run_app(
    name: str = typer.Argument(..., help="Application name"),
    instance_id: Optional[str] = typer.Option(None, "--instance", "-i", help="Instance ID for multiple instances"),
    no_reload: bool = typer.Option(False, "--no-reload", help="Disable auto-reload"),
):
    """Run an application with automatic port allocation."""
    require_service()
    
    # Get app info
    with httpx.Client() as client:
        response = client.get(f"{get_coordinator_url()}/apps/{name}")
        if response.status_code == 404:
            rprint(f"[red]Error: App '{name}' not found. Register it first with 'uvicoord add'.[/red]")
            raise typer.Exit(1)
        app_info = response.json()
    
    app_path = Path(app_info["path"])
    command = app_info["command"]
    
    # Validate path exists
    if not app_path.exists():
        rprint(f"[red]Error: App path does not exist: {app_path}[/red]")
        raise typer.Exit(1)
    
    # Allocate port
    pid = os.getpid()  # We'll update this after subprocess starts
    
    with httpx.Client() as client:
        response = client.post(
            f"{get_coordinator_url()}/port/allocate",
            json={"app_name": name, "instance_id": instance_id, "pid": pid}
        )
        if response.status_code != 200:
            rprint(f"[red]Error allocating port: {response.text}[/red]")
            raise typer.Exit(1)
        
        port_info = response.json()
        port = port_info["port"]
        instance_id = port_info["instance_id"]
    
    rprint(f"[green]Starting {name} on port {port} (instance: {instance_id})[/green]")
    
    # Build the full command
    # Replace --port if present, or add it
    if "--port" in command:
        # Replace existing port
        import re
        command = re.sub(r"--port\s+\d+", f"--port {port}", command)
    else:
        command = f"{command} --port {port}"
    
    # Handle --reload flag
    if no_reload and "--reload" in command:
        command = command.replace("--reload", "")
    
    # Build activation + run command
    venv_path = app_path / ".venv" / "Scripts" / "Activate.ps1"
    if venv_path.exists():
        full_command = f'& "{venv_path}"; {command}'
    else:
        full_command = command
    
    rprint(f"[dim]Running: {full_command}[/dim]")
    rprint(f"[dim]Directory: {app_path}[/dim]")
    
    # Run the process
    process = None
    try:
        process = subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", full_command],
            cwd=app_path,
            # Pass through stdin/stdout/stderr
        )
        
        # Update PID in coordinator
        with httpx.Client() as client:
            # Re-allocate with correct PID
            client.post(
                f"{get_coordinator_url()}/port/allocate",
                json={"app_name": name, "instance_id": instance_id, "pid": process.pid}
            )
        
        # Wait for process to complete
        process.wait()
        
    except KeyboardInterrupt:
        rprint("\n[yellow]Interrupted. Shutting down...[/yellow]")
        if process:
            process.terminate()
            process.wait(timeout=5)
    finally:
        # Release port
        with httpx.Client() as client:
            client.post(
                f"{get_coordinator_url()}/port/release",
                json={"app_name": name, "instance_id": instance_id}
            )
        rprint(f"[green]Released port {port}[/green]")


# ============ Utility Commands ============

@app.command("cleanup")
def cleanup():
    """Clean up dead instances."""
    require_service()
    
    with httpx.Client() as client:
        response = client.post(f"{get_coordinator_url()}/instances/cleanup")
        data = response.json()
        rprint(f"[green]Cleaned up {data['cleaned']} dead instance(s).[/green]")


@app.command("info")
def info(name: str = typer.Argument(..., help="Application name")):
    """Show detailed info about an application."""
    require_service()
    
    with httpx.Client() as client:
        response = client.get(f"{get_coordinator_url()}/apps/{name}")
        if response.status_code == 404:
            rprint(f"[red]App '{name}' not found.[/red]")
            raise typer.Exit(1)
        app_info = response.json()
    
    rprint(f"[cyan]Application: {app_info['name']}[/cyan]")
    rprint(f"  Path: {app_info['path']}")
    rprint(f"  Command: {app_info['command']}")
    rprint(f"  Strategy: {app_info['port_strategy']}")
    rprint(f"  Available ports: {app_info['available_ports']}")
    
    # Get running instances
    with httpx.Client() as client:
        response = client.get(f"{get_coordinator_url()}/instances/{name}")
        instances = response.json()
    
    if instances:
        rprint(f"\n[green]Running instances:[/green]")
        for inst in instances:
            rprint(f"  - {inst['instance_id']}: port {inst['port']} (PID {inst['pid']})")
    else:
        rprint(f"\n[dim]No running instances.[/dim]")


@app.command("readme")
def show_readme():
    """Display the README documentation."""
    # Find README relative to package location
    package_dir = Path(__file__).resolve().parent.parent.parent.parent
    readme_path = package_dir / "README.md"
    
    if not readme_path.exists():
        # Try alternative locations
        for candidate in [
            Path.home() / ".uvicoord" / "README.md",
            Path.cwd() / "README.md",
        ]:
            if candidate.exists():
                readme_path = candidate
                break
    
    if not readme_path.exists():
        rprint("[red]README.md not found.[/red]")
        raise typer.Exit(1)
    
    from rich.markdown import Markdown
    
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    console.print(Markdown(content))


if __name__ == "__main__":
    app()
