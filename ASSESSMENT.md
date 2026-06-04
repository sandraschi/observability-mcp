# observability-mcp — Project Assessment

**Category:** MCP Server (observability control plane)  
**Assessment date:** 2026-06-03  
**Version:** 0.2.0

## Summary

| Metric | Value |
|--------|-------|
| **Status** | Active — 0.2.0 unified-port + Charts web UI |
| **FastMCP** | 3.3+ declared; partial SOTA — see `docs/FASTMCP_STATUS.md` |
| **Unified PLG** | Consumer only (12000–12006), not host |
| **MCPB packaging** | manifest.json present; not fully validated |
| **CI/CD** | Not configured |
| **Lint (Ruff)** | ~26 issues remain in `server.py` after 277 auto-fixes; backups excluded |

## Standards (0.2.0)

- ✅ FastMCP 3.3+ dependency, HTTP/stdio, lifespan, MCP bridge
- ✅ Tool metrics middleware (`mcp_tool_*`)
- ✅ Prompts + capabilities resource
- ✅ Prefab status dashboard tool
- ✅ Web Charts hub + docs/PRD + CHANGELOG
- ⚠️ Portmanteau, skills, agentic sampling, full Prefab list tools
- ❌ `uv.lock`, CI, MCPB pack pipeline

## Next steps

1. Portmanteau tool consolidation  
2. `skills/observability-expert/SKILL.md` + provider  
3. CI: ruff + pytest + web `npm run build`  
4. Archive/delete `server_*.py` backup modules  

## References

- [docs/PRD.md](./docs/PRD.md)
- [docs/FASTMCP_STATUS.md](./docs/FASTMCP_STATUS.md)
- [mcp-central-docs monitoring](https://github.com/sandraschi/mcp-central-docs/tree/main/monitoring)
