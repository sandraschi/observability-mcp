set windows-shell := ["pwsh.exe", "-NoLogo", "-Command"]

# ── Dashboard ─────────────────────────────────────────────────────────────────

# Open the interactive recipe dashboard in the browser
default:
    @pwsh.exe -NoProfile -ExecutionPolicy Bypass -File ../mcp-central-docs/scripts/just-dashboard.ps1 -Path .

# ── Quality ───────────────────────────────────────────────────────────────────

# Execute Ruff SOTA v13.1 linting
lint:
    Set-Location '{{justfile_directory()}}'
    uv run ruff check .
    Set-Location '{{justfile_directory()}}\web_sota'
    npx @biomejs/biome ci .

# Execute Ruff SOTA v13.1 fix and formatting
fix:
    Set-Location '{{justfile_directory()}}'
    uv run ruff check . --fix --unsafe-fixes
    uv run ruff format .
    Set-Location '{{justfile_directory()}}\web_sota'
    npx @biomejs/biome check --write .

# ── Hardening ─────────────────────────────────────────────────────────────────

# Execute Bandit security audit
check-sec:
    Set-Location '{{justfile_directory()}}'
    uv run bandit -r src/

# Execute safety audit of dependencies
audit-deps:
    Set-Location '{{justfile_directory()}}'
    uv run safety check

# Perform the "Triple Kill" and restart Docker Desktop (Standard Recovery Protocol)
docker-reset:
    @Write-Host " [System] Initiating Docker Triple Kill Protocol..." -ForegroundColor Yellow
    -taskkill /F /IM "Docker Desktop.exe" /T
    -taskkill /F /IM "com.docker.backend.exe" /T
    -taskkill /F /IM "vpnkit.exe" /T
    @Write-Host " [System] Processes terminated. Restarting Docker Desktop..." -ForegroundColor Cyan
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Check Docker and monitoring stack status
docker-status:
    @Write-Host " [System] Probing Docker infrastructure..." -ForegroundColor Cyan
    docker version
    docker-compose ps

# ── Development ───────────────────────────────────────────────────────────────

# Run the MCP server in development mode
server:
    uv run observability-mcp

# Run the Web SOTA dashboard
web:
    Set-Location '{{justfile_directory()}}\web_sota'
    npm run dev

# Run both server and web dashboard (requires multiple terminals or backgrounding)
dev:
    Write-Host "Tip: Use separate terminals for 'just server' and 'just web'" -ForegroundColor Yellow
    just server

# ── Deployment ────────────────────────────────────────────────────────────────

# Build the project for production
build:
    uv build
    Set-Location '{{justfile_directory()}}\web_sota'
    npm run build
