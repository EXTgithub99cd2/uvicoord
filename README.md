# Uvicoord

**Uvicorn Coordinator** - Port registry and launcher for Python web applications.

Tired of port conflicts when running multiple uvicorn services? Uvicoord manages port allocation centrally and launches your apps with the correct ports automatically.

## Packages

This is a monorepo with platform-specific packages:

| Package | Description | Install |
|---------|-------------|---------|
| [core](core/) | Core library and cross-platform CLI | `pip install uvicoord` |
| [windows](windows/) | Windows Task Scheduler integration | `pip install uvicoord-windows` |
| [nixos](nixos/) | NixOS/systemd integration | `pip install uvicoord-nixos` or use flake |
| [docker](docker/) | Docker/Podman deployment | `docker-compose up` |

## Quick Start

### Windows

```powershell
pip install uvicoord-windows

# Install as startup service (auto-requests admin)
uvicoord service install --elevate

# Start the service
uvicoord service start

# Register and run an app
uvicoord add myapi --path C:\projects\myapi --dedicated 8001
uvicoord run myapi
```

### NixOS

```nix
# flake.nix
{
  inputs.uvicoord.url = "github:EXTgithub99cd2/uvicoord?dir=nixos/nix";
  
  outputs = { self, nixpkgs, uvicoord }: {
    nixosConfigurations.myhost = nixpkgs.lib.nixosSystem {
      modules = [
        uvicoord.nixosModules.default
        { services.uvicoord.enable = true; }
      ];
    };
  };
}
```

Or with pip:
```bash
pip install uvicoord-nixos
uvicoord service install  # Shows systemd unit configuration
```

### Docker

```bash
cd docker
docker-compose up -d
```

## Features

- **Centralized port management** - No more editing `.env` or `config.py` files
- **Multiple port strategies** - Dedicated, range, list, or stepped allocation
- **Automatic venv activation** - Handles `.venv` activation automatically
- **Instance tracking** - Track which apps are running on which ports
- **Immediate cleanup** - Ports released when processes exit
- **Platform-specific service management** - Native integration per OS

## Commands

All platforms share the same CLI interface:

```bash
# Service management
uvicoord service start        # Start the coordinator
uvicoord service stop         # Stop the coordinator
uvicoord service status       # Check status
uvicoord service install      # Install as system service (platform-specific)

# App management
uvicoord add <name> --path <dir> [port options]
uvicoord remove <name>
uvicoord list
uvicoord info <name>

# Running apps
uvicoord run <name>
uvicoord run <name> -i <instance-id>  # Multiple instances

# Utilities
uvicoord status              # Show running instances
uvicoord cleanup             # Remove dead instances
```

## Port Strategies

| Strategy | Flag | Example | Use Case |
|----------|------|---------|----------|
| Dedicated | `--dedicated 8001` | Single fixed port | Main API |
| Range | `--range 8010-8019` | Sequential ports | Workers |
| List | `--ports 8010,8015,8020` | Specific ports | Microservices |
| Stepped | `--step-start 8040 --step-size 5` | Spaced ports | Dev/staging |
| Any | (default) | 8100-8199 | Temporary apps |

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   Your App 1    │────▶│                 │
│   (port 8001)   │     │   Uvicoord      │
├─────────────────┤     │   Coordinator   │
│   Your App 2    │────▶│   (port 9000)   │
│   (port 8002)   │     │                 │
├─────────────────┤     │  - Port registry│
│   Your App 3    │────▶│  - Config store │
│   (port 8003)   │     │  - Health check │
└─────────────────┘     └─────────────────┘
```

## Development

```bash
# Clone
git clone https://github.com/EXTgithub99cd2/uvicoord.git
cd uvicoord

# Install core in development mode
cd core
pip install -e .

# Install platform package (Windows example)
cd ../windows
pip install -e .
```

## License

MIT
