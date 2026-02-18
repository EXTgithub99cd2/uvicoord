# Uvicoord Windows

Windows integration for [Uvicoord](../core/README.md) - Task Scheduler service management.

## Installation

```powershell
pip install uvicoord-windows
```

This installs:
- `uvicoord` core package
- `pywin32` for Windows API access
- Windows-specific CLI extensions

## Usage

### Install as startup service

```powershell
# Auto-elevate to admin (opens new window)
uvicoord service install --elevate

# Or run terminal as Administrator first
uvicoord service install
```

This creates a Task Scheduler task that:
- Runs at user logon
- Uses `pythonw.exe` (no console window)
- Auto-restarts on failure

### Service management

```powershell
uvicoord service status     # Check if installed and running
uvicoord service start      # Start via Task Scheduler
uvicoord service stop       # Stop the service
uvicoord service uninstall  # Remove the startup task
```

### All other commands

All other commands (`add`, `remove`, `run`, `list`, etc.) work the same as the core package.

## How it works

1. **Task Scheduler** creates a task that runs `pythonw.exe -m uvicoord.service.main` at logon
2. The service runs windowless (no console) in the background
3. Ports are managed via HTTP API on `127.0.0.1:9000`

## Troubleshooting

### Service not starting at boot

Check Task Scheduler:
```powershell
schtasks /Query /TN "Uvicoord" /V
```

Look at "Last Result" - code `0` means success.

### PATH not updated

After install, restart your terminal for PATH changes to take effect.
