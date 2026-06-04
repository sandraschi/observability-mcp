"""Optional Prefab UI card tools (OBSERVABILITY_PREFAB_TOOLS=0 to disable)."""

from __future__ import annotations

import os
from typing import Any

from fastmcp import Context
from fastmcp.tools import ToolResult
from prefab_ui.app import PrefabApp
from prefab_ui.components import Card, CardContent, CardHeader, CardTitle, Text

from observability_mcp.clients import grafana_client
from observability_mcp.sota_registration import get_sota_feature_manifest


def register_prefab_cards(mcp) -> None:
    if os.getenv("OBSERVABILITY_PREFAB_TOOLS", "1") == "0":
        return

    @mcp.tool()
    async def observability_stack_health_card(ctx: Context) -> Any:
        """Prefab card: unified PLG stack health (Grafana, Prometheus, Loki)."""
        from observability_mcp.server import check_stack_status

        await ctx.info("Building stack health card")
        data = await check_stack_status(ctx)
        status = data.get("status", {})
        lines = [
            f"Loki: {status.get('loki', {}).get('status', '?')}",
            f"Prometheus: {status.get('prometheus', {}).get('status', '?')}",
            f"Grafana: {status.get('grafana', {}).get('status', '?')}",
        ]
        summary = "healthy" if data.get("is_healthy") else "degraded"
        with Card(css_class="max-w-xl") as view:
            with CardHeader():
                CardTitle("Fleet PLG stack")
                Text(f"Overall: {summary}")
            with CardContent():
                for line in lines:
                    Text(line)
        return ToolResult(
            content=f"Stack {summary}: " + "; ".join(lines),
            structured_content=PrefabApp(view=view, title="Stack health"),
        )

    @mcp.tool()
    async def observability_grafana_dashboards_card(ctx: Context) -> Any:
        """Prefab card: Grafana dashboard list (read-only)."""
        await ctx.info("Listing Grafana dashboards")
        async with grafana_client:
            boards = await grafana_client.list_dashboards()
        names = [b.get("title") or b.get("uid") or "?" for b in boards[:12]]
        summary = f"{len(boards)} dashboards"
        with Card(css_class="max-w-xl") as view:
            with CardHeader():
                CardTitle("Grafana dashboards")
            with CardContent():
                Text(summary)
                for n in names:
                    Text(f"• {n}")
                if len(boards) > 12:
                    Text(f"… and {len(boards) - 12} more")
        return ToolResult(
            content=summary + ": " + ", ".join(names[:5]),
            structured_content=PrefabApp(view=view, title="Grafana dashboards"),
        )

    @mcp.tool()
    async def observability_capabilities_card(ctx: Context) -> Any:
        """Prefab card: SOTA manifest and tool surface summary."""
        manifest = get_sota_feature_manifest()
        feats = manifest.get("features", {})
        summary = (
            f"{manifest.get('package')} FastMCP {manifest.get('fastmcp')} — "
            f"~18 tools, portmanteau={feats.get('portmanteau')}"
        )
        await ctx.info(summary)
        with Card(css_class="max-w-xl") as view:
            with CardHeader():
                CardTitle("Observability-MCP capabilities")
            with CardContent():
                Text(summary)
                Text(f"Agentic: {feats.get('agentic_workflow')}")
                Text(f"Skills: {', '.join(feats.get('skills_uris', []))}")
        return ToolResult(
            content=summary,
            structured_content=PrefabApp(view=view, title="Capabilities"),
        )
