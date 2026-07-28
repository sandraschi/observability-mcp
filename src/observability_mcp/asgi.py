"""Composite ASGI: REST helpers for web_sota + MCP HTTP at /mcp."""

from __future__ import annotations

import os
from pathlib import Path

import aiohttp
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Mount, Route

from observability_mcp import __version__ as package_version
from observability_mcp.openapi_spec import OPENAPI_SPEC, SWAGGER_HTML


def build_asgi_app(mcp) -> Starlette:
    mcp_http = mcp.http_app(path="/")

    async def health(_: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "service": "observability-mcp"})

    async def stats(_: Request) -> JSONResponse:
        tool_count = 0
        try:
            tools = await mcp.list_tools()
            tool_count = len(tools) if tools else 0
        except Exception:
            pass
        return JSONResponse(
            {
                "version": package_version,
                "tool_count": tool_count,
                "grafana_url": os.getenv("GRAFANA_URL", "http://127.0.0.1:12000"),
                "prometheus_url": os.getenv("PROMETHEUS_SERVER_URL", "http://127.0.0.1:12001"),
                "loki_url": os.getenv("LOKI_URL", "http://127.0.0.1:12002"),
                "mcp_port": int(os.getenv("MCP_PORT", "12007")),
            }
        )

    async def llm_discover(_: Request) -> JSONResponse:
        probes = []
        ollama_ok = False
        for url in ("http://127.0.0.1:11434/api/tags", "http://localhost:11434/api/tags"):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=2)) as resp:
                        probes.append({"kind": "ollama", "url": url, "status": resp.status})
                        if resp.status == 200:
                            ollama_ok = True
            except Exception as exc:
                probes.append({"kind": "ollama", "url": url, "error": str(exc)})
        return JSONResponse(
            {
                "ollama_detected": ollama_ok,
                "configured_sampling_url": os.getenv("OBSERVABILITY_SAMPLING_BASE_URL") or os.getenv("LLM_BASE_URL"),
                "configured_model": os.getenv("OBSERVABILITY_LLM_MODEL", "llama3.2"),
                "probes": probes,
                "recommendation": None
                if ollama_ok
                else "Install Ollama on :11434 for free local chat and sampling fallback.",
            }
        )

    async def api_tools(_: Request) -> JSONResponse:
        items = []
        try:
            for t in await mcp.list_tools():
                items.append(
                    {
                        "name": getattr(t, "name", ""),
                        "description": getattr(t, "description", "") or "",
                    }
                )
        except Exception as exc:
            return JSONResponse({"error": str(exc), "tools": []}, status_code=500)
        return JSONResponse({"tools": items})

    async def api_prompts(_: Request) -> JSONResponse:
        items = []
        try:
            for p in await mcp.list_prompts():
                items.append(
                    {
                        "name": getattr(p, "name", ""),
                        "description": getattr(p, "description", "") or "",
                    }
                )
        except Exception:
            pass
        return JSONResponse({"prompts": items})

    async def api_skills(_: Request) -> JSONResponse:
        root = Path(__file__).resolve().parent / "skills"
        skills = []
        if root.is_dir():
            for skill_dir in sorted(root.iterdir()):
                skill_file = skill_dir / "SKILL.md"
                if skill_file.is_file():
                    skills.append({"name": skill_dir.name, "uri": f"skill://{skill_dir.name}/SKILL.md"})
        return JSONResponse({"skills": skills})

    async def api_skill_detail(request: Request) -> JSONResponse:
        name = request.path_params["name"]
        path = Path(__file__).resolve().parent / "skills" / name / "SKILL.md"
        if not path.is_file():
            return JSONResponse({"error": "not found"}, status_code=404)
        return JSONResponse({"name": name, "markdown": path.read_text(encoding="utf-8")})

    async def openapi_json(_: Request) -> JSONResponse:
        spec = {**OPENAPI_SPEC, "info": {**OPENAPI_SPEC["info"], "version": package_version}}
        return JSONResponse(spec)

    async def docs_page(_: Request) -> HTMLResponse:
        return HTMLResponse(SWAGGER_HTML)

    return Starlette(
        routes=[
            Route("/health", health),
            Route("/openapi.json", openapi_json),
            Route("/docs", docs_page),
            Route("/api/health", health),
            Route("/api/stats", stats),
            Route("/api/llm/discover", llm_discover),
            Route("/api/tools", api_tools),
            Route("/api/prompts", api_prompts),
            Route("/api/skills", api_skills),
            Route("/api/skills/{name}", api_skill_detail),
            Mount("/mcp", app=mcp_http),
        ]
    )
