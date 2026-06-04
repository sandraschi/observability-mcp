"""Minimal OpenAPI 3 spec for REST helpers (not MCP JSON-RPC)."""

OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "observability-mcp REST API",
        "version": "0.3.0b1",
        "description": "REST helpers for web_sota. MCP tools use POST /mcp (JSON-RPC).",
    },
    "paths": {
        "/api/health": {
            "get": {
                "summary": "Health probe",
                "responses": {"200": {"description": "OK"}},
            }
        },
        "/api/stats": {"get": {"summary": "Server stats and PLG URLs"}},
        "/api/llm/discover": {"get": {"summary": "Ollama / sampling discovery"}},
        "/api/tools": {"get": {"summary": "List MCP tools"}},
        "/api/prompts": {"get": {"summary": "List MCP prompts"}},
        "/api/skills": {"get": {"summary": "List bundled skills"}},
        "/api/skills/{name}": {"get": {"summary": "Skill markdown body"}},
    },
}

SWAGGER_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>observability-mcp API</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    SwaggerUIBundle({ url: '/openapi.json', dom_id: '#swagger-ui' });
  </script>
</body>
</html>"""
