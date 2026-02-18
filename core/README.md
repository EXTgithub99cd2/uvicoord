# Uvicoord (Core)

**Uvicorn Coordinator** - Port registry and launcher for Python web applications.

This is the core package with cross-platform functionality. For platform-specific service management:

- **Windows**: `pip install uvicoord-windows` (Task Scheduler integration)
- **NixOS**: `pip install uvicoord-nixos` or use the Nix flake

## Installation

```bash
pip install uvicoord
```

## Usage

### Start the service

```bash
# Foreground (for testing)
uvicoord service start --foreground

# Background
uvicoord service start
```

### Register an app

```bash
# Dedicated port
uvicoord add myapi --path /path/to/app --dedicated 8001

# Port range (for multiple instances)
uvicoord add workers --path /path/to/workers --range 8010-8019
```

### Run an app

```bash
uvicoord run myapi
```

### Other commands

```bash
uvicoord list           # List registered apps
uvicoord status         # Show running instances
uvicoord info myapi     # Show app details
uvicoord cleanup        # Remove dead instances
```

## Platform-specific packages

The core package handles:
- Port allocation and management
- App registration
- Running applications
- Basic service start/status

For automatic service startup at boot, install the platform-specific package:

### Windows
```powershell
pip install uvicoord-windows
uvicoord service install --elevate
```

### NixOS
```nix
# flake.nix
{
  inputs.uvicoord.url = "github:EXTgithub99cd2/uvicoord";
  
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
uvicoord service install  # Prints systemd/NixOS configuration
```
