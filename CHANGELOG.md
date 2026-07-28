
## [Unreleased] — 2026-06-14

### Added
- Tauri 2.0 native wrapper with `bundle.resources` + `std::process::Command`
- PyInstaller frozen backend embedded in NSIS installer
- CUA-NSIS smoke test (`scripts/cua-smoke.py`, `scripts/cua-nsis-config.json`)
- `just cua-nsis-test` recipe
- Tauri CORS: `tauri://localhost` origins for WebView API access
- `GET /api/v1/diagnostics` endpoint for CUA verification
# Changelog

All notable changes to observability-mcp are documented here.

## [0.3.0b1] - 2026-06-04 (beta)

**Status:** pre-1.0 beta — FastMCP 3.3+ control plane for unified fleet monitoring (ports **12007–12009**).

### Added

- FastMCP 3.3 SOTA surface: composite ASGI, skills, agentic workflow, Prefab cards, OpenAPI `/docs`, MCPB pack + release workflow
- `web_sota` WEBAPP_SOTA pages (Settings, Chat, Logs, Tools, Skills, Help, Apps, API docs, Grafana chart picker)
- Fleet tool metrics on **12009**; unified PLG defaults **12000–12002**
- SOTA `justfile`: industrial `default`, `start`/`serve`/`web`, `test`/`install`; `just-ui` on **11030**

### Fixed

- Hatchling build (removed invalid classifier); just dashboard no longer binds **10789**
- Tests and OTEL span helper for CI stability

## [0.2.2] - 2026-06-04

### Added

- Module split: `clients.py`, `models_storage.py`, `otel_compat.py`, `openapi_spec.py`
- Prefab cards: `observability_stack_health_card`, `observability_grafana_dashboards_card`, `observability_capabilities_card`
- Resources: `resource://observability/sota/manifest`, `resource://observability/prefab/manifest`
- OpenAPI `/openapi.json` and Swagger `/docs`; web **API docs** route
- CI (Ruff, pytest, web build, MCPB pack), `uv.lock`, `build_mcpb.py`, tag workflow
- `llms-full.txt`; server backups moved to `archive/server_backups/`

### Changed

- `MCP_TRANSPORT=http` and `observability-mcp --http` use composite ASGI (REST + `/mcp`)
- FastMCP: `strict_input_validation=True`, `on_duplicate="replace"`, version on server
- Pydantic persistence uses `model_dump(mode="json")`

## [0.2.1] - 2026-06-03

### Added

- **Skills** provider (`skill://observability-expert/SKILL.md`)
- **`agentic_observability_workflow`** with sampling fallback chain
- Composite ASGI: `/api/health`, `/api/stats`, `/api/tools`, `/api/skills`, `/api/llm/discover`
- **web_sota** SOTA pages: Settings, Chat, session Logs, Tools, Skills, Help, Fleet apps, Logger dock
- Vite proxy to backend **12007** for `/api` and `/mcp`

### Fixed

- Removed invalid PyPI classifier `Framework :: FastMCP` and stale `pyproject.toml.bak` (hatchling build)

## [0.2.0] - 2026-06-03

### Added

- Webapp **Charts** hub (`/grafana`) — categorized Grafana dashboard picker for beginners
- Fleet tool metrics middleware (`mcp_tool_*` on `PROMETHEUS_PORT` **12009**)
- FastMCP **prompts** (`observability_getting_started`, `incident_triage`)
- `resource://observability/capabilities` discovery resource
- `docs/PRD.md`, `docs/FASTMCP_STATUS.md`, `llms.txt`
- `.env.unified-monitoring.example` for unified PLG on **12000–12006**

### Changed

- Default ports: MCP **12007**, web UI **12008**, metrics **12009** (12000 band)
- Grafana/Loki/Prometheus client defaults → unified stack **12000 / 12002 / 12001**
- `docker-compose.yml` — app-only container; no bundled PLG on 3000/9091/3100
- Dependency: `fastmcp>=3.3,<4`
- Ruff auto-fixes on active Python modules; backup `server_*.py` excluded from lint

### Fixed

- `check_stack_status` uses `PROMETHEUS_SERVER_URL` vs process exporter port
- `provision_standard_dashboards` datasource URLs read from env

## [0.1.0] - 2026-01-01

- Initial observability MCP with Grafana/Loki/Prometheus tools and Prefab status dashboard

