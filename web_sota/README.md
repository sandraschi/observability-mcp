# observability-mcp web UI

React + Vite dashboard for the observability control plane.

## Ports

| Service | Port |
|---------|------|
| Frontend (this app) | **12008** |
| MCP backend | **12007** (`observability_mcp.server:app`) |
| Unified Grafana | **12000** (external) |

## Start

```powershell
Set-Location D:\Dev\repos\observability-mcp\web_sota
pwsh -NoProfile -File .\start.ps1
```

Copy `.env.example` to `.env.local` for `VITE_*` overrides.

## Routes

| Path | Purpose |
|------|---------|
| `/` | System metrics |
| `/grafana` | **Charts** — categorized Grafana dashboard picker |
| `/grafana/manage` | Admin: datasources, provision, delete |
| `/health` | Fleet health checks |
| `/logs` | Log explorer |
| `/alerts` | Alerts |

## Lint

```powershell
npm run biome
npm run build
```
