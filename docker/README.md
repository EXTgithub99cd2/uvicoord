# Uvicoord Docker

Run Uvicoord as a Docker/Podman container.

## Quick Start

### Using docker-compose

```bash
cd docker
docker-compose up -d
```

### Using docker directly

```bash
# Build
docker build -t uvicoord -f docker/Dockerfile .

# Run
docker run -d \
  --name uvicoord \
  -p 9000:9000 \
  -v uvicoord-data:/data \
  uvicoord
```

### Using podman

```bash
# Build
podman build -t uvicoord -f docker/Dockerfile .

# Run
podman run -d \
  --name uvicoord \
  -p 9000:9000 \
  -v uvicoord-data:/data \
  uvicoord
```

## Configuration

The container stores config in `/data/config.json`. Mount a volume to persist it.

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `UVICOORD_CONFIG` | `/data/config.json` | Config file path |

### Ports

| Port | Description |
|------|-------------|
| 9000 | Coordinator HTTP API |

## Usage with Docker

From your host machine, use `curl` or `httpx` to interact with the API:

```bash
# Check health
curl http://localhost:9000/health

# Register an app (note: path must be accessible from where you run apps)
curl -X POST http://localhost:9000/apps \
  -H "Content-Type: application/json" \
  -d '{"name": "myapi", "path": "/path/to/app", "port_strategy": "dedicated", "port": 8001}'

# List apps
curl http://localhost:9000/apps
```

## Note on container usage

When running Uvicoord in a container, the CLI commands (`uvicoord run`, etc.) would typically run on the host machine and communicate with the containerized coordinator via HTTP.

The container only runs the coordinator service - not the applications themselves. Applications run on the host (or in their own containers) and request ports from the coordinator.
