# observability-mcp — Agent Guide

FastMCP 3.3+ control plane for fleet Grafana, Prometheus, and Loki (not a second PLG stack).

## Entry points

- `just start` — backend **12007** + Vite **12008**
- `uv run observability-mcp` → `observability_mcp.cli:main` (stdio or HTTP via `MCP_TRANSPORT=http`)

## Ports

| Service | Port |
|---|---|
| Backend (MCP HTTP) | 12007 |
| Frontend (Vite) | 12008 |
| Process `/metrics` | 12009 |
| Unified Grafana / Prometheus / Loki | 12000 / 12001 / 12002 |

## Standards

- Structured tool responses (`success`, `message`, domain fields)
- Dual transport: stdio (IDE) + composite ASGI HTTP (`/mcp`, `/api/*`, `/docs`)
- Fleet standards: [mcp-central-docs](https://github.com/sandraschi/mcp-central-docs)
- Install: mcp-central-docs/standards/AGENT_INSTALL_REFERENCE.md

## Key files

- `README.md`, `INSTALL.md`, `CHANGELOG.md`, `llms.txt`
- `docs/PRD.md`, `docs/FASTMCP_STATUS.md`
- `mcp-central-docs/monitoring/MONITORING_CURRENT_SETUP.md`

## Quick ref

```powershell
just install
just test
just serve
```
