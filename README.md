# Uvicoord

**Uvicorn Coordinator** - Port registry and launcher for Python web applications.

Tired of port conflicts when running multiple uvicorn services? Uvicoord manages port allocation centrally and launches your apps with the correct ports automatically.

## Features

- **Centralized port management** - No more editing `.env` or `config.py` files
- **Multiple port strategies** - Dedicated, range, list, or stepped allocation
- **Automatic venv activation** - Handles `.venv` activation automatically
- **Instance tracking** - Track which apps are running on which ports
- **Immediate cleanup** - Ports released when processes exit
- **Windows service support** - Run coordinator on startup

## Installation (Uvicoord Service)

This section installs the **uvicoord coordinator service** itself - the central service that manages ports for all your Python apps.

```powershell
# Clone the repository
git clone https://github.com/EXTgithub99cd2/uvicoord.git
cd uvicoord

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install
pip install -e .
```

### Make `uvicoord` available globally

**Option A: Install as Windows Service (recommended)**

This automatically adds `uvicoord` to system PATH and starts on boot:

```powershell
# Run as Administrator
python -m uvicoord.service.windows_service install
python -m uvicoord.service.windows_service start

# Restart your terminal for PATH changes to take effect
```

**Option B: Manual PATH setup**

If you don't want to install as a Windows service:

```powershell
# Add to your user PATH (run once, persists across reboots)
$scriptsPath = "C:\Users\lm\.ghub\uvicorn-proxy\.venv\Scripts"
[Environment]::SetEnvironmentVariable("Path", "$env:Path;$scriptsPath", "User")

# Restart your terminal for PATH changes to take effect
```

## Quick Start

```powershell
# 1. Start the coordinator service (if not installed as Windows service)
uvicoord service start

# 2. Register an application
uvicoord add my-api --path "C:\Users\lm\.ghub\my-api" --dedicated 8001

# 3. Run the application
uvicoord run my-api
# => Activates venv, starts uvicorn on port 8001

# 4. Check status
uvicoord status
```

## Port Strategies

### Dedicated Port
Single fixed port, single instance only.

```powershell
uvicoord add my-api --path "C:\path\to\app" --dedicated 8001
```

### Port Range
Multiple instances, sequential ports from a range.

```powershell
uvicoord add workers --path "C:\path\to\workers" --range 8010-8019
```

### Port List
Explicit list of ports for instances.

```powershell
uvicoord add services --path "C:\path\to\services" --ports 8020,8025,8030
```

### Stepped Ports
Ports at regular intervals (e.g., 8040, 8045, 8050...).

```powershell
uvicoord add micro --path "C:\path\to\micro" --step-start 8040 --step-size 5 --step-count 8
```

### Any (Default)
Allocate from global default range (8100-8199).

```powershell
uvicoord add temp-app --path "C:\path\to\temp"
```

## CLI Commands

### Service Management

```powershell
uvicoord service start          # Start coordinator (foreground)
uvicoord service start -b       # Start in background
uvicoord service status         # Check if service is running
uvicoord service stop           # Stop service
```

### App Management

```powershell
uvicoord add <name> --path <dir> [options]   # Register app
uvicoord remove <name>                        # Unregister app
uvicoord list                                 # List all apps
uvicoord info <name>                          # Show app details
```

### Running Apps

```powershell
uvicoord run <name>                          # Run with allocated port
uvicoord run <name> --instance my-id         # Run with specific instance ID
uvicoord run <name> --no-reload              # Run without hot reload
```

### Status & Cleanup

```powershell
uvicoord status                              # Show running instances
uvicoord cleanup                             # Remove dead instances
```

## Configuration

Configuration is stored in `~/.uvicoord/config.json`:

```json
{
  "coordinator_port": 9000,
  "default_port_range": [8100, 8199],
  "apps": {
    "my-api": {
      "path": "C:/Users/lm/.ghub/my-api",
      "command": "uvicorn app.main:app --reload",
      "port_strategy": "dedicated",
      "port": 8001
    }
  }
}
```

You can also set `UVICOORD_CONFIG` environment variable to use a different config file.

## Windows Service (Auto-start)

To run the coordinator automatically on Windows startup. This also adds `uvicoord` to your system PATH automatically.

```powershell
# Install as Windows service (requires admin)
# - Installs the service with auto-start
# - Adds uvicoord to system PATH
python -m uvicoord.service.windows_service install

# Start the service
python -m uvicoord.service.windows_service start

# Stop the service
python -m uvicoord.service.windows_service stop

# Uninstall
python -m uvicoord.service.windows_service remove
```

## API Endpoints

The coordinator exposes a REST API on port 9000:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/apps` | GET | List registered apps |
| `/apps` | POST | Register new app |
| `/apps/{name}` | GET | Get app details |
| `/apps/{name}` | DELETE | Remove app |
| `/port/allocate` | POST | Allocate a port |
| `/port/release` | POST | Release a port |
| `/instances` | GET | List active instances |
| `/instances/{app_name}` | GET | List app instances |
| `/instances/cleanup` | POST | Clean dead instances |
| `/config` | GET | Get config |
| `/config/reload` | POST | Reload config |

## Example Workflow

```powershell
# Terminal 1: Start coordinator
uvicoord service start

# Terminal 2: Register and run your main API
uvicoord add main-api --path "C:\dev\main-api" --dedicated 8001
uvicoord run main-api
# => Running on http://127.0.0.1:8001

# Terminal 3: Run multiple worker instances
uvicoord add workers --path "C:\dev\workers" --range 8010-8019
uvicoord run workers
# => Running on http://127.0.0.1:8010

# Terminal 4: Another worker instance
uvicoord run workers
# => Running on http://127.0.0.1:8011

# Check what's running
uvicoord status
# ┌──────────┬─────────────┬──────┬───────┬─────────────────────┐
# │ App      │ Instance ID │ Port │ PID   │ Started             │
# ├──────────┼─────────────┼──────┼───────┼─────────────────────┤
# │ main-api │ a1b2c3d4    │ 8001 │ 12345 │ 2026-02-18T10:00:00 │
# │ workers  │ e5f6g7h8    │ 8010 │ 12346 │ 2026-02-18T10:01:00 │
# │ workers  │ i9j0k1l2    │ 8011 │ 12347 │ 2026-02-18T10:02:00 │
# └──────────┴─────────────┴──────┴───────┴─────────────────────┘
```

## GitHub Copilot Integration

Uvicoord includes an instruction file for GitHub Copilot / Claude AI assistants at `.github/copilot-instructions.md`. This teaches AI assistants to create new apps without hardcoded ports and to use uvicoord for port management.

### Automatic (this workspace)

VS Code Copilot automatically reads `.github/copilot-instructions.md` when working in this workspace.

### Use in other projects

Add to `.vscode/settings.json` in any project:

```json
{
  "github.copilot.chat.codeGeneration.instructions": [
    { "file": "C:/Users/lm/.ghub/uvicorn-proxy/.github/copilot-instructions.md" }
  ]
}
```

### Global availability

Copy to your VS Code user prompts folder:

```powershell
Copy-Item "C:\Users\lm\.ghub\uvicorn-proxy\.github\copilot-instructions.md" `
          "$env:APPDATA\Code\User\prompts\uvicoord.instructions.md"
```

Then the AI will know about uvicoord in all your projects.

## License

MIT
