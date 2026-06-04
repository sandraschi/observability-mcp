"""Agentic observability workflow (SEP-1577 sampling with tool fallback)."""

from __future__ import annotations

import os
from typing import Any

from fastmcp import Context

import structlog

logger = structlog.get_logger("observability_mcp.agentic")


async def _fallback_workflow(goal: str, ctx: Context) -> dict[str, Any]:
    """Deterministic triage when sampling is unavailable."""
    from observability_mcp.server import check_stack_status, monitor_server_health, query_loki_logs

    steps: list[dict[str, Any]] = []

    stack = await check_stack_status(ctx)
    steps.append({"step": "check_stack_status", "result": stack})

    if not stack.get("is_healthy"):
        return {
            "success": True,
            "mode": "fallback",
            "goal": goal,
            "summary": "Unified PLG stack is down or misconfigured. Start mcp-central-docs/monitoring.",
            "steps": steps,
        }

    logs = await query_loki_logs(
        ctx,
        query='{level=~"error|ERROR"}',
        limit=20,
    )
    steps.append({"step": "query_loki_logs", "result": logs})

    health = await monitor_server_health(
        ctx,
        service_url="http://127.0.0.1:12007/health",
        timeout_seconds=5.0,
    )
    steps.append({"step": "monitor_server_health", "result": health})

    return {
        "success": True,
        "mode": "fallback",
        "goal": goal,
        "summary": "Ran stack check, recent error logs, and local MCP health.",
        "steps": steps,
    }


def register_agentic_observability_tools(mcp) -> None:
    @mcp.tool()
    async def agentic_observability_workflow(
        ctx: Context,
        goal: str,
        use_sampling: bool = True,
    ) -> dict[str, Any]:
        """
        Multi-step observability triage (stack → logs → health).

        Uses host LLM sampling when available; otherwise runs a fixed tool chain.
        """
        goal = (goal or "").strip() or "Check fleet observability health"
        sampling_url = os.getenv("OBSERVABILITY_SAMPLING_BASE_URL", os.getenv("LLM_BASE_URL", ""))

        if use_sampling and sampling_url and hasattr(ctx, "sample"):
            try:
                prompt = (
                    f"Observability goal: {goal}\n"
                    "Use tools: check_stack_status, query_loki_logs, monitor_server_health, "
                    "manage_grafana_dashboards. Return a short operator summary."
                )
                sample_result = await ctx.sample(prompt)
                text = getattr(sample_result, "text", None) or str(sample_result)
                return {
                    "success": True,
                    "mode": "sampling",
                    "goal": goal,
                    "summary": text,
                }
            except Exception as exc:
                logger.warning("Sampling failed, using fallback", error=str(exc))

        return await _fallback_workflow(goal, ctx)
