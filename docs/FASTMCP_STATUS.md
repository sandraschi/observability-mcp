# FastMCP 3.3+ compliance status

**Package:** `observability-mcp` **0.3.0b1** · **FastMCP** 3.3+

## Summary

SOTA control plane without portmanteau (~18 core tools + 3 optional Prefab cards + agentic workflow). Web UI matches WEBAPP_SOTA core including API docs.

## Tool count guidance

**Do not add lots of extra tools.** The current surface is intentional:

| Range | Recommendation |
|-------|----------------|
| ~15–25 | Keep focused tools (this repo) |
| 25–40 | Consider grouping only if agents confuse names |
| 40+ | Portmanteau with `operation=` (not needed here) |

Add tools only when they map to a **new capability** (e.g. Tempo traces, Alertmanager), not for cosmetic splits.

## Feature matrix

| Capability | Status |
|------------|--------|
| FastMCP 3.3+ | ✅ |
| HTTP composite ASGI (`/api`, `/docs`, `/mcp`) | ✅ |
| stdio + `--http` via uvicorn composite app | ✅ |
| SkillsDirectoryProvider | ✅ |
| Agentic workflow + sampling fallback | ✅ |
| Tool metrics middleware | ✅ |
| Prefab (4 tools incl. status dashboard) | ✅ |
| strict_input_validation | ✅ |
| Module split (clients, models_storage) | ✅ |
| CI + uv.lock + MCPB pack | ✅ |
| Web SOTA (settings, logs, chat, tools, skills, help, apps, API docs, logger) | ✅ |
| Portmanteau | ⏭️ Skipped by design |
