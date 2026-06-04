"""FastMCP 3.3+ prompt templates for observability workflows."""

from __future__ import annotations

from fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    @mcp.prompt()
    def observability_getting_started() -> str:
        return """You are helping a user who is new to Grafana and the fleet monitoring stack.

Explain in plain language:
1. Unified PLG runs at Grafana :12000, Prometheus :12001, Loki :12002 (mcp-central-docs/monitoring).
2. observability-mcp is the control plane on MCP :12007 — not a second Grafana.
3. Start with the Fleet overview dashboard, then open the MCP-specific board they care about.
4. Green panels = healthy; red = check logs in Loki or /health on the MCP port.

Use manage_grafana_dashboards list + check_stack_status before suggesting fixes."""

    @mcp.prompt()
    def incident_triage() -> str:
        return """Incident triage on the Sandra MCP fleet:
1. check_stack_status — are 12000/12001/12002 up?
2. monitor_server_health on the failing MCP HTTP port
3. query_loki_logs with job label and level=error
4. correlate_logs_and_metrics when both signals exist
5. Summarize: symptom, likely cause, next command — no jargon without definitions."""
