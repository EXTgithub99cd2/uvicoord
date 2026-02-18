# Uvicoord Integration Instructions

**For GitHub Copilot / Claude AI assistants**

This instruction file explains how to integrate Python web applications with **uvicoord** - a port coordinator service that manages port allocation for uvicorn-based applications.

## What is Uvicoord?

Uvicoord is a local service running on port 9000 that:
- Allocates ports to Python web applications automatically
- Eliminates port conflicts between multiple services
- Handles venv activation and app launching
- Tracks running instances

## Key Principle

**Applications should NOT hardcode ports.** Instead, they register with uvicoord and receive an assigned port.

---

## For NEW Applications

When creating a new Python web application (FastAPI, Starlette, etc.):

### 1. Do NOT include port configuration

**❌ Don't do this:**
```python
# main.py
if __name__ == "__main__":
    uvicorn.run(app, port=8000)  # Hardcoded port!
```

**✅ Do this instead:**
```python
# main.py
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1")  # Port will be injected by uvicoord
```

### 2. Do NOT create .env files with PORT settings

**❌ Don't create:**
```env
PORT=8000
```

### 3. Register the app with uvicoord

After creating the project, instruct the user to register it:

```powershell
# For a dedicated port (single instance)
uvicoord add <app-name> --path "C:\path\to\app" --dedicated 8001

# For multiple instances with a port range
uvicoord add <app-name> --path "C:\path\to\app" --range 8010-8019

# For specific ports per instance
uvicoord add <app-name> --path "C:\path\to\app" --ports 8010,8015,8020

# For stepped ports (8040, 8045, 8050...)
uvicoord add <app-name> --path "C:\path\to\app" --step-start 8040 --step-size 5 --step-count 8
```

### 4. Run via uvicoord

```powershell
uvicoord run <app-name>
```

---

## For EXISTING Applications

When modifying an existing application to use uvicoord:

### 1. Remove hardcoded port configurations

Look for and remove/modify:

- `uvicorn.run(app, port=XXXX)` → `uvicorn.run(app)`
- `.env` files with `PORT=XXXX` → Remove the PORT variable
- `config.py` with port settings → Remove or make port optional
- `docker-compose.yml` port mappings → Keep for Docker, but local dev uses uvicoord

### 2. Update the main entry point

**Before:**
```python
import os
from dotenv import load_dotenv

load_dotenv()
PORT = int(os.getenv("PORT", 8000))

if __name__ == "__main__":
    uvicorn.run("app.main:app", port=PORT, reload=True)
```

**After:**
```python
if __name__ == "__main__":
    # Port is injected by uvicoord via --port flag
    uvicorn.run("app.main:app", reload=True)
```

### 3. Register with uvicoord

```powershell
uvicoord add <app-name> --path "C:\path\to\existing\app" --dedicated 8005
```

---

## Project Structure Assumptions

Uvicoord assumes:
- Virtual environment at `.venv/` in project root
- Activation script at `.venv/Scripts/Activate.ps1` (Windows)
- Default command: `uvicorn app.main:app --reload`

If your app has a different structure, specify the command:

```powershell
uvicoord add my-app --path "C:\path\to\app" -c "uvicorn src.main:app --reload" --dedicated 8001
```

---

## Common Scenarios

### Scenario: User asks to create a new FastAPI app

1. Create the FastAPI app structure normally
2. Do NOT add port configuration
3. At the end, provide registration command:
   ```powershell
   uvicoord add <suggested-name> --path "<project-path>" --dedicated <suggest-port>
   uvicoord run <suggested-name>
   ```

### Scenario: User has port conflict errors

1. Suggest using uvicoord to manage ports
2. Help them register the app
3. Remove hardcoded port from their code

### Scenario: User needs multiple instances of same app

Suggest range or list strategy:
```powershell
uvicoord add workers --path "C:\path\to\workers" --range 8010-8019

# Then run multiple instances
uvicoord run workers  # Gets 8010
uvicoord run workers  # Gets 8011
uvicoord run workers --instance special  # Gets 8012, remembers "special"
```

---

## Useful Commands Reference

```powershell
# Service
uvicoord service start       # Start coordinator
uvicoord service status      # Check if running

# App management
uvicoord add <name> --path <dir> [port options]
uvicoord remove <name>
uvicoord list                # Show all registered apps
uvicoord info <name>         # Show app details

# Running
uvicoord run <name>          # Run with allocated port
uvicoord run <name> -i <id>  # Run with instance ID
uvicoord status              # Show running instances
uvicoord cleanup             # Remove dead instances

# Help
uvicoord readme              # Show full documentation
```

---

## Port Strategy Quick Reference

| Need | Strategy | Example |
|------|----------|---------|
| Single instance, fixed port | `--dedicated 8001` | Main API |
| Multiple instances, sequential | `--range 8010-8019` | Workers |
| Multiple instances, specific ports | `--ports 8010,8015,8020` | Microservices |
| Multiple instances, spaced | `--step-start 8040 --step-size 5` | Dev/staging |
| Any available port | (no option) | Temporary/test apps |

---

## Important Notes

1. **Uvicoord service must be running** - Start with `uvicoord service start` or install as Windows service
2. **Ports are released immediately** when process exits (Ctrl+C or crash)
3. **Config is stored** at `~/.uvicoord/config.json`
4. **Coordinator runs on port 9000** by default
