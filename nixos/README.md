# Uvicoord NixOS

NixOS/systemd integration for [Uvicoord](../core/README.md).

## Installation Options

### Option 1: Nix Flake (recommended for NixOS)

Add to your `flake.nix`:

```nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    uvicoord.url = "github:EXTgithub99cd2/uvicoord?dir=nixos/nix";
  };

  outputs = { self, nixpkgs, uvicoord }: {
    nixosConfigurations.myhost = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        uvicoord.nixosModules.default
        {
          services.uvicoord = {
            enable = true;
            port = 9000;  # optional
          };
        }
      ];
    };
  };
}
```

Then rebuild:
```bash
sudo nixos-rebuild switch
```

### Option 2: Pip with systemd user service

```bash
pip install uvicoord-nixos

# Show installation instructions
uvicoord service install
```

This prints the systemd unit file to create manually.

### Option 3: Home Manager

```nix
# In your home.nix
systemd.user.services.uvicoord = {
  Unit = {
    Description = "Uvicoord - Uvicorn Coordinator Service";
    After = [ "network.target" ];
  };
  Service = {
    Type = "simple";
    ExecStart = "${pkgs.uvicoord}/bin/uvicoord-service";
    Restart = "on-failure";
  };
  Install = {
    WantedBy = [ "default.target" ];
  };
};
```

## Usage

### With NixOS module
```bash
# Service is managed by systemd
sudo systemctl status uvicoord
sudo systemctl restart uvicoord

# CLI commands
uvicoord list
uvicoord add myapp --path /path/to/app --dedicated 8001
uvicoord run myapp
```

### With user service
```bash
systemctl --user status uvicoord
systemctl --user restart uvicoord
```

## Configuration

The NixOS module supports these options:

| Option | Default | Description |
|--------|---------|-------------|
| `enable` | `false` | Enable the service |
| `port` | `9000` | Coordinator port |
| `configDir` | `/var/lib/uvicoord` | Config directory |
| `user` | `"uvicoord"` | Service user |
| `group` | `"uvicoord"` | Service group |
