# observability-mcp — Agent Guide

## Overview
FastMCP 3.1.0-powered observability server for monitoring MCP ecosystems with OpenTelemetry integration

## Entry Points
- `uv run observability-mcp` → `observability_mcp.cli:main`

## Standards
- FastMCP 3.2+ portmanteau tool pattern — tools use `operation` enum param
- Responses: structured dicts with `success`, `message`, domain-specific fields
- Dual transport: stdio (Claude Desktop) + HTTP (`MCP_TRANSPORT=http`)
- See [mcp-central-docs](https://github.com/sandraschi/mcp-central-docs) for fleet-wide coding standards

## Key Files
- `README.md` — full documentation
- `pyproject.toml` — build config and entry points
- `CLAUDE.md` — Claude Code context (if present)
