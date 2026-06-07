set windows-shell := ["pwsh.exe", "-NoLogo", "-Command"]

# ── Dashboard ─────────────────────────────────────────────────────────────────

# Display SOTA Industrial Dashboard (terminal help — fleet standard)
default:
    @pwsh.exe -NoProfile -ExecutionPolicy Bypass -File  -Path . -Title observability-mcp -Version 0.3.0b1 -Subtitle "Web http://127.0.0.1:12008 | MCP http://127.0.0.1:12007/mcp"

# Open click-to-run recipe dashboard in browser (port 11030 — not 10789)
just-ui:
    @pwsh.exe -NoProfile -ExecutionPolicy Bypass -File  -Path . -Port 11030

# ── Quality ───────────────────────────────────────────────────────────────────

# Lint Python and web_sota (Biome)
lint:
    Set-Location '{{justfile_directory()}}'
    uv run ruff check .
    Set-Location '{{justfile_directory()}}\web_sota'
    npx @biomejs/biome ci .

# Linting and formatting (SOTA mandatory)
check: lint

# Execute Ruff fix and Biome write
fix:
    Set-Location '{{justfile_directory()}}'
    uv run ruff check . --fix --unsafe-fixes
    uv run ruff format .
    Set-Location '{{justfile_directory()}}\web_sota'
    npx @biomejs/biome check --write .

# Automated verification (SOTA mandatory)
test:
    Set-Location '{{justfile_directory()}}'
    uv run --extra test pytest tests -q --cov=observability_mcp --cov-report=term-missing

# ── Development ───────────────────────────────────────────────────────────────

# Install/sync dependencies
install:
    Set-Location '{{justfile_directory()}}'
    uv sync --extra test --extra dev
    Set-Location '{{justfile_directory()}}\web_sota'
    npm install

# Start backend + Vite (12007 / 12008) — opens browser when ready
start:
    pwsh.exe -NoProfile -ExecutionPolicy Bypass -File web_sota/start.ps1

# MCP HTTP backend only (12007)
serve:
    Set-Location '{{justfile_directory()}}'
    $env:PYTHONPATH = '{{justfile_directory()}}\src'
    uv run uvicorn observability_mcp.server:app --host 127.0.0.1 --port 12007 --log-level info

# Vite frontend only (12008; proxies API to 12007)
web:
    Set-Location '{{justfile_directory()}}\web_sota'
    npm run dev -- --port 12008 --host

# Alias: full stack via start.ps1
dev: start

# Stdio MCP (IDE clients)
stdio:
    Set-Location '{{justfile_directory()}}'
    uv run observability-mcp

# ── Hardening ─────────────────────────────────────────────────────────────────

# Execute Bandit security audit
check-sec:
    Set-Location '{{justfile_directory()}}'
    uv run bandit -r src/

# Execute safety audit of dependencies
audit-deps:
    Set-Location '{{justfile_directory()}}'
    uv run safety check

# Perform the Docker Triple Kill and restart Docker Desktop
docker-reset:
    @Write-Host " [System] Initiating Docker Triple Kill Protocol..." -ForegroundColor Yellow
    -taskkill /F /IM "Docker Desktop.exe" /T
    -taskkill /F /IM "com.docker.backend.exe" /T
    -taskkill /F /IM "vpnkit.exe" /T
    @Write-Host " [System] Processes terminated. Restarting Docker Desktop..." -ForegroundColor Cyan
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Check Docker and unified monitoring stack
docker-status:
    @Write-Host " [System] Probing Docker infrastructure..." -ForegroundColor Cyan
    docker version
    Set-Location '{{justfile_directory()}}\
    docker compose -f docker-compose.unified-monitoring.yml ps

# ── Deployment ────────────────────────────────────────────────────────────────

# Build Python wheel and web_sota production bundle (SOTA mandatory)
build:
    Set-Location '{{justfile_directory()}}'
    uv build
    Set-Location '{{justfile_directory()}}\web_sota'
    npm run build

