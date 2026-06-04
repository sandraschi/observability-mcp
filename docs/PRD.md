# observability-mcp — Product Requirements Document

**Version:** 0.2.0  
**Last updated:** 2026-06-03  
**Status:** Active development

## Executive summary

observability-mcp is the **fleet observability control plane**: an MCP server plus web UI that helps humans and agents work with the **unified** Grafana/Loki/Prometheus stack (`mcp-central-docs/monitoring`, host ports **12000–12006**). It is not a second monitoring datastore.

## Product vision

Make production monitoring approachable for people who do not live in Grafana — while giving agents structured tools for health checks, logs, dashboards, and correlation.

## Users

| Persona | Need |
|---------|------|
| Fleet owner | One place to open the right dashboard and verify PLG is up |
| Agent / IDE | `check_stack_status`, Loki queries, Grafana API without memorizing ports |
| Operator | Datasource provisioning, dashboard admin (advanced UI) |

## Architecture

```text
┌─────────────────────┐     ┌──────────────────────────────────┐
│ observability-mcp   │     │ Unified PLG (mcp-central-docs)   │
│  :12007 MCP         │────▶│ Grafana :12000                   │
│  :12008 Web Charts  │     │ Prometheus :12001                │
│  :12009 /metrics    │     │ Loki :12002                      │
└─────────────────────┘     └──────────────────────────────────┘
```

## Functional requirements

### FR-1: Stack connectivity (P0)

- `check_stack_status` against env-configured URLs
- Clear distinction: Prometheus **server** (12001) vs MCP **exporter** (12009)

### FR-2: Grafana (P0)

- List/create/delete dashboards and datasources via API
- Web **Charts** page: categorized cards with plain-language copy and deep links
- Admin page for operators (`/grafana/manage`)

### FR-3: Loki (P1)

- Push and query logs; pattern and correlation helpers

### FR-4: Fleet health (P1)

- HTTP health checks for MCP services
- Prometheus export of `mcp_tool_*` for tool-call observability

### FR-5: Agent UX (P1)

- MCP prompts for onboarding and incident triage
- Prefab status dashboard tool for rich host UI

## Non-functional requirements

| Area | Target |
|------|--------|
| FastMCP | 3.3+ (`fastmcp>=3.3,<4`) |
| Python | 3.12+ |
| Webapp | React + Vite on **12008** |
| Lint | Ruff on active `src/observability_mcp`; Biome on `web_sota` |

## FastMCP 3.3 “mod cons” compliance

See [FASTMCP_STATUS.md](./FASTMCP_STATUS.md) for an honest matrix. **Summary:** partially compliant — core HTTP/stdio, middleware metrics, prompts, one resource, Prefab; **gaps:** skills provider, sampling/agentic workflow, portmanteau tools, full Prefab coverage on list tools.

## Out of scope (0.2.0)

- Hosting a second Grafana/Prometheus/Loki stack in this repo
- Replacing unified monitoring provisioning in `mcp-central-docs`

## Success metrics

- User can open fleet overview from web UI without typing URLs
- `check_stack_status` reports correct state when unified stack is running
- Prometheus scrapes `mcp_tool_calls_total` from :12009 after tool use

## References

- [MONITORING_CURRENT_SETUP.md](https://github.com/sandraschi/mcp-central-docs/blob/main/monitoring/MONITORING_CURRENT_SETUP.md)
- [SOTA_REQUIREMENTS.md](https://github.com/sandraschi/mcp-central-docs/blob/main/standards/SOTA_REQUIREMENTS.md)
- [WEBAPP_PORTS.md](https://github.com/sandraschi/mcp-central-docs/blob/main/operations/WEBAPP_PORTS.md) — ports 12007–12009
