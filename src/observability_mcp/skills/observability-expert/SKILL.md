# Observability-MCP expert skill

Use this server as the **control plane** for the unified fleet PLG stack (Grafana 12000, Prometheus 12001, Loki 12002).

## Workflow

1. Call `check_stack_status` before deep dives.
2. For Grafana boards, use the web Charts hub or `manage_grafana_dashboards` operation `list`.
3. For logs: `query_loki_logs` with `{job="..."}` labels from fleet scrape config.
4. For a single MCP process: `monitor_server_health` on its HTTP port.
5. Multi-step triage: `agentic_observability_workflow`.

## Do not

- Start observability-mcp bundled docker-compose on 3000/9091/3100.
- Confuse `PROMETHEUS_PORT` (12009 exporter) with Prometheus server (12001).
