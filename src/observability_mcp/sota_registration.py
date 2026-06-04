"""FastMCP 3.3 SOTA: skills provider and feature manifest."""

from __future__ import annotations

from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

import structlog

logger = structlog.get_logger("observability_mcp.sota")


def _fastmcp_version() -> str:
    try:
        return pkg_version("fastmcp")
    except Exception:
        return "unknown"


def get_sota_feature_manifest() -> dict[str, Any]:
    return {
        "package": "observability-mcp",
        "fastmcp": _fastmcp_version(),
        "sota_target": "3.3",
        "features": {
            "sampling": True,
            "agentic_workflow": "agentic_observability_workflow",
            "skills_provider": True,
            "skills_uris": ["skill://observability-expert/SKILL.md"],
            "rest_api": ["/api/health", "/api/stats", "/api/tools", "/api/skills"],
            "portmanteau": False,
        },
    }


def register_sota_resources(mcp: FastMCP) -> None:
    import json

    @mcp.resource("resource://observability/sota/manifest")
    def observability_sota_manifest() -> str:
        return json.dumps(get_sota_feature_manifest(), indent=2)

    @mcp.resource("resource://observability/prefab/manifest")
    def observability_prefab_manifest() -> str:
        tools = [
            "show_status_dashboard",
            "observability_stack_health_card",
            "observability_grafana_dashboards_card",
            "observability_capabilities_card",
        ]
        return json.dumps({"prefab_tools": tools, "disable": "OBSERVABILITY_PREFAB_TOOLS=0"}, indent=2)


def register_sota_surface(mcp: FastMCP) -> None:
    register_sota_resources(mcp)
    skills_dir = Path(__file__).resolve().parent / "skills"
    try:
        from fastmcp.server.providers.skills import SkillsDirectoryProvider
    except ImportError:
        logger.warning("SkillsDirectoryProvider not available")
        return

    if not skills_dir.is_dir():
        logger.warning("Skills directory missing: %s", skills_dir)
        return

    try:
        mcp.add_provider(SkillsDirectoryProvider(roots=[skills_dir]))
        logger.info("Skills provider registered at %s", skills_dir)
    except Exception as exc:
        logger.warning("Skills provider failed: %s", exc)
