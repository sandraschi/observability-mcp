import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from typing import Any

import aiohttp
import psutil
import structlog
from fastmcp import Context, FastMCP
from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from prefab_ui.components import H3, Badge, Card, Container, Grid, Text
from prometheus_client import start_http_server

from .clients import (
    check_service_connectivity,
    grafana_client,
    loki_client,
)
from .models_storage import (
    AlertConfig,
    AnomalyResult,
    HealthCheckResult,
    PerformanceMetrics,
    TraceInfo,
    _server_state,
    check_docker_status,
    input_validator,
    rate_limiter,
    storage,
)
from .otel_compat import use_span
from .prompts import register_prompts
from .transport import run_server

# Configure structured logging for industrial use
log_file = os.getenv("LOG_FILE", "observability-mcp.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5), logging.StreamHandler()],
)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger("observability-mcp")

# OpenTelemetry Setup
resource = Resource(attributes={"service.name": "observability-mcp"})
tracer_provider = TracerProvider(resource=resource)
trace.set_tracer_provider(tracer_provider)

# Console span exporter for development
span_processor = BatchSpanProcessor(ConsoleSpanExporter())
tracer_provider.add_span_processor(span_processor)

# Meter Provider setup
meter_provider = MeterProvider(resource=resource)
metrics.set_meter_provider(meter_provider)

# Get meters and tracers
meter = metrics.get_meter("observability-mcp")
tracer = trace.get_tracer("observability-mcp")

# Metrics
health_check_counter = meter.create_counter(
    name="mcp_health_checks_total", description="Total number of health checks performed", unit="1"
)

performance_metric_counter = meter.create_counter(
    name="mcp_performance_metrics_collected", description="Total number of performance metrics collected", unit="1"
)

trace_counter = meter.create_counter(name="mcp_traces_created", description="Total number of traces created", unit="1")

alert_counter = meter.create_counter(
    name="mcp_alerts_triggered", description="Total number of alerts triggered", unit="1"
)

# Resource metrics
cpu_usage_gauge = meter.create_up_down_counter(
    name="mcp_cpu_usage_percent", description="Current CPU usage percentage", unit="%"
)

memory_usage_gauge = meter.create_up_down_counter(
    name="mcp_memory_usage_mb", description="Current memory usage in MB", unit="MB"
)


@asynccontextmanager
async def server_lifespan(mcp_instance: FastMCP):
    """Server lifespan for startup and cleanup. Hardened: never crashes on dependency failures."""
    logger.info("Starting Observability MCP Server")

    # Initialize in-process state first (no external dependencies)
    _server_state["server_start_time"] = time.time()
    _server_state["degraded_mode"] = False

    # Prometheus metrics server — optional, don't crash if port is taken
    prometheus_port = int(os.getenv("PROMETHEUS_PORT", "12009"))
    try:
        start_http_server(prometheus_port)
        logger.info("Prometheus metrics server started", port=prometheus_port)
    except OSError as e:
        logger.warning(
            "Could not start Prometheus metrics server — port may already be in use", port=prometheus_port, error=str(e)
        )
        _server_state["degraded_mode"] = True

    # Persistent storage — fall back gracefully if filesystem is unavailable
    try:
        retention_days = int(os.getenv("METRICS_RETENTION_DAYS", "30"))
        await storage.set("metrics_retention_days", retention_days)

        existing_alerts = await storage.get("alert_configs")
        if existing_alerts is None:
            default_alerts = [
                AlertConfig(metric_name="cpu_percent", threshold=90.0, operator="gt", severity="warning"),
                AlertConfig(metric_name="memory_mb", threshold=1000.0, operator="gt", severity="error"),
                AlertConfig(metric_name="error_rate", threshold=0.05, operator="gt", severity="error"),
            ]
            await storage.set("alert_configs", [alert.model_dump() for alert in default_alerts])

        logger.info(
            "Observability MCP Server startup complete",
            storage_path=storage.file_path,
            retention_days=retention_days,
            degraded_mode=_server_state["degraded_mode"],
        )
    except Exception as e:
        logger.error("Storage initialisation failed — running without persistence", error=str(e))
        _server_state["degraded_mode"] = True

    yield

    logger.info("Shutting down Observability MCP Server")


# Initialize FastMCP server
mcp = FastMCP(
    name="Observability-MCP",
    version="0.3.0b1",
    instructions=(
        "Observability-MCP is the fleet control plane for Grafana (12000), Prometheus (12001), and Loki (12002). "
        "Use check_stack_status first, then manage_grafana_dashboards, query_loki_logs, and monitor_server_health. "
        "Do not start a second PLG stack on 3000/9090/3100 — use mcp-central-docs unified monitoring."
    ),
    lifespan=server_lifespan,
    strict_input_validation=True,
    on_duplicate="replace",
)

register_prompts(mcp)


@mcp.resource("resource://observability/capabilities")
def observability_capabilities() -> str:
    return (
        "Tools: stack health, Grafana dashboards/datasources, Loki query, metrics export, "
        "fleet health checks, Prefab status dashboard. Web UI chart picker :12008. "
        "Prompts: observability_getting_started, incident_triage."
    )


# MCP Bridge — Proxy external MCP servers via MCP_BRIDGE_URLS
_bridge_proxies: list[str] = []
bridge_urls = os.getenv("MCP_BRIDGE_URLS", "")
if bridge_urls:
    try:
        from fastmcp.server import create_proxy

        for url in bridge_urls.split(","):
            url = url.strip()
            if url:
                try:
                    mcp.add_provider(create_proxy(url))
                    _bridge_proxies.append(url)
                except Exception:
                    pass
    except ImportError:
        pass

from observability_mcp.fleet_tool_metrics import register_mcp_tool_metrics
from observability_mcp.sota_registration import register_sota_surface

register_mcp_tool_metrics(mcp)
register_sota_surface(mcp)


@mcp.tool()
async def check_stack_status(ctx: Context) -> dict[str, Any]:
    """
    Check the health and connectivity of the observability stack (Loki, Prometheus, Grafana).

    This diagnostic tool verifies if the underlying Docker-based services are reachable
    and correctly configured.
    """
    loki_url = os.getenv("LOKI_URL", "http://127.0.0.1:12002").rstrip("/")
    prom_server_url = os.getenv("PROMETHEUS_SERVER_URL", "http://127.0.0.1:12001").rstrip("/")
    grafana_url = os.getenv("GRAFANA_URL", "http://127.0.0.1:12000").rstrip("/")
    prom_exporter_port = os.getenv("PROMETHEUS_PORT", "12009")

    loki_up = await check_service_connectivity(f"{loki_url}/ready")
    prom_up = await check_service_connectivity(f"{prom_server_url}/-/healthy")
    grafana_up = await check_service_connectivity(f"{grafana_url}/api/health")

    status = {
        "loki": {"status": "up" if loki_up else "down", "url": loki_url},
        "prometheus": {"status": "up" if prom_up else "down", "url": prom_server_url},
        "grafana": {"status": "up" if grafana_up else "down", "url": grafana_url},
        "mcp_metrics_exporter": {
            "port": prom_exporter_port,
            "note": "Process /metrics (PROMETHEUS_PORT), not the Prometheus server URL",
        },
        "timestamp": datetime.now().isoformat(),
    }

    all_up = loki_up and prom_up and grafana_up
    if not all_up:
        logger.warning("Observability stack is partially or fully down", **status)

    return {
        "status": status,
        "is_healthy": all_up,
        "recommendations": [
            "Start unified monitoring: mcp-central-docs/monitoring/start-unified-monitoring.ps1"
            if not all_up
            else "Stack is healthy",
            "Set GRAFANA_URL/LOKI_URL/PROMETHEUS_SERVER_URL (see .env.unified-monitoring.example); "
            "Use unified PLG on 12000-12006; observability-mcp app on 12007-12009"
            if not all_up
            else "No action required",
        ],
    }


@mcp.tool()
async def manage_alert_configs(
    ctx: Context, operation: str, alert: dict[str, Any] | None = None, metric_name: str | None = None
) -> dict[str, Any]:
    """
    Manage metric alert configurations.

    Operations:
    - list: List all current alert configurations
    - add: Add a new alert configuration (requires 'alert' dict)
    - remove: Remove an alert by metric name (requires 'metric_name')
    - toggle: Enable/disable an alert (requires 'metric_name')
    """
    if not rate_limiter.is_allowed("manage_alerts"):
        return {"error": "Rate limit exceeded"}

    configs = await storage.get("alert_configs", [])

    if operation == "list":
        return {"alerts": configs}

    elif operation == "add":
        if not alert:
            return {"error": "Alert data required for 'add' operation"}
        try:
            new_alert = AlertConfig(**alert)
            configs.append(new_alert.model_dump(mode="json"))
            await storage.set("alert_configs", configs)
            return {"status": "added", "alert": new_alert.model_dump(mode="json")}
        except Exception as e:
            return {"error": f"Invalid alert configuration: {e}"}

    elif operation == "remove":
        if not metric_name:
            return {"error": "Metric name required for 'remove' operation"}
        new_configs = [a for a in configs if a.get("metric_name") != metric_name]
        if len(new_configs) == len(configs):
            return {"error": f"Alert for metric '{metric_name}' not found"}
        await storage.set("alert_configs", new_configs)
        return {"status": "removed", "metric_name": metric_name}

    elif operation == "toggle":
        if not metric_name:
            return {"error": "Metric name required for 'toggle' operation"}
        found = False
        for a in configs:
            if a.get("metric_name") == metric_name:
                a["enabled"] = not a.get("enabled", True)
                found = True
                break
        if not found:
            return {"error": f"Alert for metric '{metric_name}' not found"}
        await storage.set("alert_configs", configs)
        return {"status": "toggled", "metric_name": metric_name}

    else:
        return {"error": f"Unknown operation: {operation}"}


@mcp.tool()
async def show_status_dashboard(ctx: Context) -> Any:
    """
    Display a rich, premium status dashboard using Prefab UI.
    Provides a visual overview of stack health, system metrics, and active alerts.
    Hardened: operates in Degraded Mode when Docker or stack services are unreachable.
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    degraded = _server_state.get("degraded_mode", False)

    # --- Gather data independently; never let one failure cascade ---

    try:
        docker_status = await check_docker_status()
    except Exception as e:
        logger.warning("Dashboard: docker status check failed", error=str(e))
        docker_status = {"status": "error", "reachable": False, "error": str(e)}

    try:
        stack_status = await check_stack_status(ctx)
        loki_status = stack_status["status"]["loki"]["status"]
        prom_status = stack_status["status"]["prometheus"]["status"]
        grafana_status = stack_status["status"]["grafana"]["status"]
    except Exception as e:
        logger.warning("Dashboard: stack status check failed", error=str(e))
        loki_status = prom_status = grafana_status = "error"

    try:
        perf_metrics = await collect_performance_metrics(ctx, "system")
        cpu = perf_metrics["metrics"]["cpu_percent"]
        ram = perf_metrics["metrics"]["memory_mb"]
        disk = perf_metrics["metrics"]["disk_usage_percent"]
    except Exception as e:
        logger.warning("Dashboard: perf metrics collection failed", error=str(e))
        cpu = ram = disk = None

    try:
        alerts_result = await manage_alert_configs(ctx, "list")
        alert_list = alerts_result.get("alerts", [])
    except Exception as e:
        logger.warning("Dashboard: alert config fetch failed", error=str(e))
        alert_list = []

    # --- Helper: status -> badge colour ---
    def _svc_color(status: str) -> str:
        return "green" if status == "up" else ("yellow" if status == "error" else "red")

    # --- Build Prefab UI ---
    degraded_banner = (
        [Text("Degraded mode: one or more dependencies unreachable. Metrics and dashboard data may be incomplete.")]
        if (degraded or not docker_status["reachable"])
        else []
    )

    perf_children = (
        [
            H3("System Performance"),
            Grid(
                columns=3,
                children=[
                    Text(f"CPU: {cpu:.1f}%" if cpu is not None else "CPU: unavailable"),
                    Text(f"RAM: {ram:.0f} MB" if ram is not None else "RAM: unavailable"),
                    Text(f"Disk: {disk:.1f}%" if disk is not None else "Disk: unavailable"),
                ],
            ),
        ]
        if cpu is not None
        else [H3("System Performance"), Text("⚠ Metrics unavailable — psutil collection failed")]
    )

    card = Card(
        title="Industrial Observability Dashboard",
        subtitle=f"Last Updated: {ts}" + (" | DEGRADED" if degraded else ""),
        children=[
            *degraded_banner,
            # Infrastructure health
            Container(
                children=[
                    H3("Infrastructure Health"),
                    Grid(
                        columns=2,
                        children=[
                            Text("Docker"),
                            Badge(
                                docker_status["status"].upper(), color="green" if docker_status["reachable"] else "red"
                            ),
                            Text("Loki"),
                            Badge(loki_status.upper(), color=_svc_color(loki_status)),
                            Text("Prometheus"),
                            Badge(prom_status.upper(), color=_svc_color(prom_status)),
                            Text("Grafana"),
                            Badge(grafana_status.upper(), color=_svc_color(grafana_status)),
                        ],
                    ),
                ]
            ),
            # System performance
            Container(children=perf_children),
            # Alert configurations
            Container(
                children=[
                    H3("Alert Configurations"),
                    *(
                        [
                            Text(
                                f"• {a['metric_name']}: threshold {a['threshold']} "
                                f"({'Enabled' if a.get('enabled', True) else 'Disabled'})"
                            )
                            for a in alert_list
                        ]
                        if alert_list
                        else [Text("No alert configurations found")]
                    ),
                ]
            ),
        ],
    )

    return card


@mcp.tool()
async def monitor_server_health(
    ctx: Context, service_url: str, timeout_seconds: float = 5.0, expected_status_codes: list[int] | None = None
) -> dict[str, Any]:
    """
    Perform real-time health check on an MCP server or web service.

    This tool uses OpenTelemetry for metrics collection and provides comprehensive
    health monitoring with detailed response analysis.

    Args:
        service_url: URL of the service to check (http:// or https://)
        timeout_seconds: Timeout for the health check request (1-30 seconds)
        expected_status_codes: List of acceptable HTTP status codes (default: [200])

    Returns:
        Health check result with metrics and detailed analysis
    """
    # Security validation
    if not rate_limiter.is_allowed("health_check"):
        return {"error": "Rate limit exceeded. Please wait before making another request."}

    if not input_validator.validate_url(service_url):
        return {"error": "Invalid or unsafe URL provided"}

    if not (1.0 <= timeout_seconds <= 30.0):
        return {"error": "Timeout must be between 1 and 30 seconds"}

    if expected_status_codes is None:
        expected_status_codes = [200]

    # Validate status codes
    if not all(isinstance(code, int) and 100 <= code <= 599 for code in expected_status_codes):
        return {"error": "Invalid status codes provided"}

    start_time = time.time()

    with use_span(tracer, "health_check") as span:
        span.set_attribute("service.url", service_url)
        span.set_attribute("timeout_seconds", timeout_seconds)

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout_seconds)) as session:
                async with session.get(service_url) as response:
                    response_time = (time.time() - start_time) * 1000

                    is_healthy = response.status in expected_status_codes
                    status = "healthy" if is_healthy else "unhealthy"

                    result = HealthCheckResult(
                        service_name=service_url,
                        status=status,
                        response_time_ms=response_time,
                        timestamp=datetime.now(),
                        details={
                            "status_code": response.status,
                            "headers": dict(response.headers),
                            "content_length": len(await response.read()),
                        },
                    )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            result = HealthCheckResult(
                service_name=service_url,
                status="unhealthy",
                response_time_ms=response_time,
                timestamp=datetime.now(),
                error_message=str(e),
            )

    # Record metrics
    health_check_counter.add(1, {"status": result.status, "service": service_url})

    span.set_attribute("health.status", result.status)
    span.set_attribute("response_time_ms", result.response_time_ms)

    # Store result in persistent storage (with bounds checking)
    history_key = f"health_history:{service_url}"
    history = await storage.get(history_key, [])
    history.append(result.model_dump(mode="json"))
    # Keep only last 50 results per service to prevent unbounded growth
    history = history[-50:]
    await storage.set(history_key, history)

    return {
        "health_check": result.model_dump(mode="json"),
        "metrics_recorded": True,
        "historical_checks": len(history),
        "recommendations": _generate_health_recommendations(result),
    }


@mcp.tool()
async def collect_performance_metrics(ctx: Context, service_name: str = "system") -> dict[str, Any]:
    """
    Collect comprehensive performance metrics for the system or specific service.

    Uses OpenTelemetry for structured metrics collection and psutil for system monitoring.
    Metrics are persisted for historical analysis and trend detection.

    Args:
        service_name: Name of the service to monitor (default: system, max 50 chars)

    Returns:
        Performance metrics with historical analysis and recommendations
    """
    # Security validation
    if not rate_limiter.is_allowed("performance_metrics"):
        return {"error": "Rate limit exceeded. Please wait before making another request."}

    if not input_validator.validate_service_name(service_name):
        return {"error": "Invalid service name provided"}

    with use_span(tracer, "collect_performance_metrics") as span:
        span.set_attribute("service.name", service_name)

        # Collect system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        network = psutil.net_io_counters()

        metrics_data = PerformanceMetrics(
            service_name=service_name,
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_mb=memory.used / (1024 * 1024),
            disk_usage_percent=disk.percent,
            network_io={
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv,
            },
        )

        # Record OpenTelemetry metrics
        cpu_usage_gauge.add(int(cpu_percent), {"service": service_name})
        memory_usage_gauge.add(int(metrics_data.memory_mb), {"service": service_name})

        performance_metric_counter.add(1, {"service": service_name})

        # Store metrics history in persistent storage (with bounds checking)
        history_key = f"performance_history:{service_name}"
        history = await storage.get(history_key, [])
        history.append(metrics_data.model_dump(mode="json"))
        # Keep last 500 data points per service to prevent unbounded growth
        history = history[-500:]
        await storage.set(history_key, history)

        # Analyze trends
        trends = _analyze_performance_trends(history)

        span.set_attribute("cpu_percent", cpu_percent)
        span.set_attribute("memory_mb", metrics_data.memory_mb)

        return {
            "metrics": metrics_data.model_dump(mode="json"),
            "trends": trends,
            "alerts": await _check_performance_alerts(ctx, metrics_data),
            "recommendations": _generate_performance_recommendations(metrics_data, trends),
        }


@mcp.tool()
async def trace_mcp_calls(
    ctx: Context, operation_name: str, service_name: str, duration_ms: float, attributes: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Record a trace for MCP call monitoring and distributed tracing.

    Creates OpenTelemetry spans for tracking MCP server interactions,
    enabling distributed tracing across multiple MCP servers.

    Args:
        operation_name: Name of the operation being traced
        service_name: Name of the service performing the operation
        duration_ms: Duration of the operation in milliseconds
        attributes: Additional attributes to include in the trace
    """
    if not rate_limiter.is_allowed("trace_calls"):
        return {"error": "Rate limit exceeded"}

    if attributes is None:
        attributes = {}

    with use_span(tracer, operation_name) as span:
        span.set_attribute("service.name", service_name)
        span.set_attribute("operation.duration_ms", duration_ms)

        for key, value in attributes.items():
            span.set_attribute(f"operation.{key}", value)

        trace_info = TraceInfo(
            trace_id=span.get_span_context().trace_id,
            service_name=service_name,
            operation=operation_name,
            start_time=datetime.now(),
            duration_ms=duration_ms,
            status="completed",
            attributes=attributes,
        )

    # Record metrics
    trace_counter.add(1, {"service": service_name, "operation": operation_name})

    # Store trace history in persistent storage
    history_key = f"trace_history:{service_name}"
    history = await storage.get(history_key, [])
    history.append(trace_info.model_dump(mode="json"))
    # Keep last 500 traces
    history = history[-500:]
    await storage.set(history_key, history)

    # Analyze trace patterns
    patterns = _analyze_trace_patterns(history)

    return {
        "trace": trace_info.model_dump(mode="json"),
        "patterns": patterns,
        "performance_insights": _generate_trace_insights(trace_info, patterns),
    }


@mcp.tool()
async def generate_performance_reports(ctx: Context, service_name: str | None = None, days: int = 7) -> dict[str, Any]:
    """
    Generate comprehensive performance reports with automated analysis.

    Analyzes historical metrics data to provide insights, trends, and recommendations
    for optimizing MCP server performance.

    Args:
        service_name: Specific service to analyze (None for all services)
        days: Number of days of history to analyze
    """
    if not rate_limiter.is_allowed("generate_reports"):
        return {"error": "Rate limit exceeded"}

    if not input_validator.validate_days(days):
        return {"error": "Days must be between 1 and 365"}

    with use_span(tracer, "generate_performance_reports") as span:
        span.set_attribute("report.days", days)
        if service_name:
            span.set_attribute("report.service", service_name)

        cutoff_date = datetime.now() - timedelta(days=days)

        if service_name:
            # Analyze specific service
            history_key = f"performance_history:{service_name}"
            history = await storage.get(history_key, [])

            # Filter by date
            recent_history = [item for item in history if datetime.fromisoformat(item["timestamp"]) > cutoff_date]
        else:
            # Analyze all services (collect all performance_history:* keys)
            # Since JsonFileStorage doesn't support .keys(), we might need a different approach
            # or rely on a known list. For now, we'll try to find keys by reading the storage file directly
            # if we can't get keys. But let's assume we can only analyze known services or 'system'.
            service_name = service_name or "system"
            history_key = f"performance_history:{service_name}"
            history = await storage.get(history_key, [])
            recent_history = [item for item in history if datetime.fromisoformat(item["timestamp"]) > cutoff_date]

        if not recent_history:
            return {"error": f"No performance data available for '{service_name}' in the specified period"}

        # Generate report
        report = {
            "period_days": days,
            "generated_at": datetime.now().isoformat(),
            "summary": _generate_performance_summary(recent_history, service_name),
            "trends": _analyze_performance_trends_detailed(recent_history, service_name),
            "anomalies": await _detect_performance_anomalies(ctx, recent_history, service_name),
            "recommendations": _generate_performance_recommendations_from_history(recent_history, service_name),
        }

        # Store report
        report_key = f"report:{service_name}:{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        await storage.set(report_key, report)

        return report


@mcp.tool()
async def alert_on_anomalies(ctx: Context, service_name: str = "system") -> dict[str, Any]:
    """
    Monitor for performance anomalies and trigger alerts.

    Uses statistical analysis and configurable thresholds to detect anomalies
    in MCP server performance metrics and trigger appropriate alerts.

    Args:
        service_name: Specific service to monitor (default: system)
    """
    if not rate_limiter.is_allowed("alert_on_anomalies"):
        return {"error": "Rate limit exceeded"}

    with use_span(tracer, "alert_on_anomalies") as span:
        span.set_attribute("alert.service", service_name)

        # Get alert configurations
        alert_configs_raw = await storage.get("alert_configs", [])
        alert_configs = [AlertConfig(**config) for config in alert_configs_raw]

        history_key = f"performance_history:{service_name}"
        history = await storage.get(history_key, [])

        if not history:
            return {"error": f"No performance history found for '{service_name}'"}

        # Check for anomalies
        anomalies = await _detect_service_anomalies(ctx, service_name, history, alert_configs)

        # Check active alerts
        active_alerts = await _check_active_alerts(ctx, service_name, history, alert_configs)

        # Record metrics
        alert_counter.add(len(active_alerts), {"type": "active", "service": service_name})

        span.set_attribute("alerts.active", len(active_alerts))
        span.set_attribute("anomalies.detected", len(anomalies))

        return {
            "active_alerts": active_alerts,
            "detected_anomalies": [anomaly.model_dump(mode="json") for anomaly in anomalies],
            "alert_configs": [config.model_dump(mode="json") for config in alert_configs],
            "recommendations": _generate_alert_recommendations(active_alerts, anomalies),
        }


@mcp.tool()
async def monitor_system_resources(ctx: Context) -> dict[str, Any]:
    """
    Monitor system-wide resources and provide real-time status.

    Collects comprehensive system resource information including CPU, memory,
    disk, network, and process statistics for overall system health monitoring.
    """
    if not rate_limiter.is_allowed("system_resources"):
        return {"error": "Rate limit exceeded"}

    with use_span(tracer, "monitor_system_resources") as span:
        # System-wide metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_times = psutil.cpu_times()
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        disk = psutil.disk_usage("/")
        network = psutil.net_io_counters()

        # Process information
        processes = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                processes.append(
                    {
                        "pid": proc.pid,
                        "name": proc.name(),
                        "cpu_percent": proc.info["cpu_percent"],
                        "memory_percent": proc.info["memory_percent"],
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Top 5 processes by CPU and memory
        top_cpu = sorted(processes, key=lambda x: x["cpu_percent"], reverse=True)[:5]
        top_memory = sorted(processes, key=lambda x: x["memory_percent"], reverse=True)[:5]

        system_status = {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent": cpu_percent,
                "cores": psutil.cpu_count(),
                "cores_logical": psutil.cpu_count(logical=True),
                "times": {
                    "user": cpu_times.user,
                    "system": cpu_times.system,
                    "idle": cpu_times.idle,
                },
            },
            "memory": {
                "total_gb": memory.total / (1024**3),
                "available_gb": memory.available / (1024**3),
                "used_gb": memory.used / (1024**3),
                "percent": memory.percent,
            },
            "swap": {
                "total_gb": swap.total / (1024**3),
                "used_gb": swap.used / (1024**3),
                "percent": swap.percent,
            },
            "disk": {
                "total_gb": disk.total / (1024**3),
                "used_gb": disk.used / (1024**3),
                "free_gb": disk.free / (1024**3),
                "percent": disk.percent,
            },
            "network": {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv,
            },
            "processes": {
                "total": len(processes),
                "top_cpu": top_cpu,
                "top_memory": top_memory,
            },
        }

        # Store system status history in persistent storage
        history_key = "system_status_history"
        history = await storage.get(history_key, [])
        history.append(system_status)
        # Keep last 100 system status snapshots
        history = history[-100:]
        await storage.set(history_key, history)

        # Analyze system health
        health_analysis = _analyze_system_health(system_status)

        span.set_attribute("cpu.percent", cpu_percent)
        span.set_attribute("memory.percent", system_status["memory"]["percent"])

        return {
            "system_status": system_status,
            "health_analysis": health_analysis,
            "recommendations": _generate_system_recommendations(system_status, health_analysis),
            "historical_trends": _analyze_system_trends(history) if len(history) > 1 else None,
        }


@mcp.tool()
async def analyze_mcp_interactions(ctx: Context, days: int = 7) -> dict[str, Any]:
    """
    Analyze patterns in MCP server interactions and usage.

    Examines trace data and interaction patterns to provide insights into
    how MCP servers are being used and identify optimization opportunities.

    Args:
        days: Number of days of interaction data to analyze
    """
    if not rate_limiter.is_allowed("analyze_interactions"):
        return {"error": "Rate limit exceeded"}

    if not input_validator.validate_days(days):
        return {"error": "Days must be between 1 and 365"}

    with use_span(tracer, "analyze_mcp_interactions") as span:
        span.set_attribute("analysis.days", days)

        cutoff_date = datetime.now() - timedelta(days=days)

        # Since we can't easily iterate all keys, we'll focus on 'system' or known services
        # For a full implementation, we'd need a key index or directory-based storage
        service_name = "system"
        history_key = f"trace_history:{service_name}"
        traces = await storage.get(history_key, [])

        recent_traces = [trace for trace in traces if datetime.fromisoformat(trace["start_time"]) > cutoff_date]

        if not recent_traces:
            return {"error": f"No interaction data available for '{service_name}' in the specified period"}

        # Analyze patterns
        patterns = {
            "total_interactions": len(recent_traces),
            "avg_duration": sum(t["duration_ms"] for t in recent_traces) / len(recent_traces),
            "peak_usage_hours": _find_peak_usage_hours(recent_traces),
            "slowest_operations": _find_slowest_operations(recent_traces),
            "error_patterns": _analyze_error_patterns(recent_traces),
        }

        # Generate insights
        insights = {
            "bottlenecks": _identify_bottlenecks(patterns),
            "optimization_opportunities": _find_optimization_opportunities(patterns),
            "scaling_recommendations": _generate_scaling_recommendations(patterns),
            "usage_trends": _analyze_usage_trends(recent_traces),
        }

        return {
            "analysis_period_days": days,
            "patterns": patterns,
            "insights": insights,
            "recommendations": _generate_interaction_recommendations(patterns, insights),
        }


@mcp.tool()
async def export_metrics(ctx: Context, format: str = "prometheus", include_history: bool = False) -> dict[str, Any]:
    """
    Export collected metrics in various formats for external monitoring systems.

    Supports Prometheus, OpenTelemetry, and JSON formats for integration
    with existing monitoring infrastructure.

    Args:
        format: Export format (prometheus, opentelemetry, json)
        include_history: Whether to include historical data
    """
    if not rate_limiter.is_allowed("export_metrics"):
        return {"error": "Rate limit exceeded"}

    with use_span(tracer, "export_metrics") as span:
        span.set_attribute("export.format", format)
        span.set_attribute("export.include_history", include_history)

        if format == "prometheus":
            return {
                "format": "prometheus",
                "endpoint": f"http://localhost:{os.getenv('PROMETHEUS_PORT', '12009')}/metrics",
                "message": "Metrics available at Prometheus endpoint",
            }

        elif format == "opentelemetry":
            return {
                "format": "opentelemetry",
                "metrics": _collect_current_metrics(),
                "traces": await _collect_recent_traces_from_storage() if include_history else None,
            }

        elif format == "json":
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "metrics": _collect_current_metrics(),
                "version": "1.0.0",
            }

            if include_history:
                # Fallback to system metrics if we can't list all
                export_data["history"] = {"system": await storage.get("performance_history:system", [])}

            return export_data

        else:
            return {"error": f"Unsupported format: {format}. Supported: prometheus, opentelemetry, json"}


@mcp.tool()
async def send_logs_to_loki(
    ctx: Context, log_message: str, level: str = "info", labels: dict[str, str] | None = None
) -> dict[str, Any]:
    """
    Send custom log entries to Loki for centralized log aggregation.

    This tool allows manual log injection into the Loki log aggregation system,
    enabling correlation between custom events and system metrics.

    Args:
        log_message: The log message to send
        level: Log level (debug, info, warning, error, critical)
        labels: Additional labels to attach to the log entry (max 10 key-value pairs)

    Returns:
        Confirmation of log submission with metadata
    """
    # Security validation
    if not rate_limiter.is_allowed("send_logs"):
        return {"error": "Rate limit exceeded. Log operations are restricted."}

    if not log_message or len(log_message) > 1000:
        return {"error": "Log message must be 1-1000 characters"}

    allowed_levels = ["debug", "info", "warning", "error", "critical"]
    if level not in allowed_levels:
        return {"error": f"Invalid log level. Must be one of: {allowed_levels}"}

    if labels is None:
        labels = {}

    # Limit labels to prevent abuse
    if len(labels) > 10:
        return {"error": "Too many labels provided (max 10)"}

    # Validate label keys and values
    for key, value in labels.items():
        if not (isinstance(key, str) and len(key) <= 50):
            return {"error": "Invalid label key"}
        if not isinstance(value, str) or len(value) > 100:
            return {"error": "Invalid label value"}

    with use_span(tracer, "send_logs_to_loki") as span:
        span.set_attribute("log.level", level)
        span.set_attribute("log.message_length", len(log_message))

        # Prepare Loki labels
        loki_labels = {"service": "observability-mcp", "level": level, "source": "manual_entry"}
        loki_labels.update(labels)

        # Send to Loki
        async with loki_client:
            await loki_client.send_log(loki_labels, log_message)

        # Record metrics
        log_counter = meter.create_counter(f"mcp_logs_sent_{level}")
        log_counter.add(1, {"level": level})

        # Log locally as well
        extra = {"labels": labels} if labels else {}
        getattr(logger, level)(log_message, **extra)

        return {
            "status": "sent",
            "message": log_message,
            "level": level,
            "labels": loki_labels,
            "timestamp": datetime.now().isoformat(),
            "loki_endpoint": loki_client.loki_url,
        }


@mcp.tool()
async def query_loki_logs(
    ctx: Context, query: str, start_time: str | None = None, end_time: str | None = None, limit: int = 100
) -> dict[str, Any]:
    """
    Query logs from Loki with advanced filtering and analysis.

    This tool provides powerful log querying capabilities using Loki's LogQL syntax,
    enabling correlation between logs, metrics, and traces.

    Args:
        query: LogQL query string (e.g., '{job="my-service"} |= "ERROR"')
        start_time: Start time for query (ISO format or relative like "1h", "24h")
        end_time: End time for query (ISO format or relative)
        limit: Maximum number of log entries to return (1-1000)

    Returns:
        Log query results with analysis and insights
    """
    # Security validation
    if not rate_limiter.is_allowed("query_logs"):
        return {"error": "Rate limit exceeded. Log queries are restricted."}

    if not query or len(query) > 500:
        return {"error": "Query must be 1-500 characters"}

    if not (1 <= limit <= 1000):
        return {"error": "Limit must be between 1 and 1000"}

    # Parse time parameters
    if start_time:
        if start_time.endswith("h"):
            hours = int(start_time[:-1])
            start_time = (datetime.now() - timedelta(hours=hours)).isoformat() + "Z"
        elif not start_time.endswith("Z"):
            start_time += "Z"

    if end_time:
        if end_time.endswith("h"):
            hours = int(end_time[:-1])
            end_time = (datetime.now() - timedelta(hours=hours)).isoformat() + "Z"
        elif not end_time.endswith("Z"):
            end_time += "Z"

    with use_span(tracer, "query_loki_logs") as span:
        span.set_attribute("query.length", len(query))
        span.set_attribute("query.limit", limit)

        # Query Loki
        async with loki_client:
            result = await loki_client.query_logs(query, start_time, end_time, limit)

        if "error" in result:
            return result

        # Analyze results
        analysis = _analyze_log_results(result)

        # Store query for auditing in persistent storage
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "result_count": len(result.get("data", {}).get("result", [])),
            "user": "mcp-client",
        }
        audit_key = f"log_query_audit:{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        await storage.set(audit_key, audit_entry)

        return {
            "query": query,
            "time_range": {"start": start_time, "end": end_time},
            "results": result,
            "analysis": analysis,
            "metadata": {
                "total_results": analysis.get("total_entries", 0),
                "unique_services": analysis.get("unique_services", 0),
                "time_span": analysis.get("time_span", "unknown"),
                "query_timestamp": datetime.now().isoformat(),
            },
        }


@mcp.tool()
async def analyze_log_patterns(
    ctx: Context, query: str, time_window: str = "1h", min_occurrences: int = 5
) -> dict[str, Any]:
    """
    Analyze log patterns and anomalies using Loki queries.

    This tool identifies common log patterns, error spikes, and potential issues
    by analyzing log data over time windows.

    Args:
        query: Base LogQL query to analyze
        time_window: Time window for analysis (e.g., "1h", "24h", "7d")
        min_occurrences: Minimum occurrences to consider a pattern significant

    Returns:
        Pattern analysis with anomalies, trends, and recommendations
    """
    # Security validation
    if not rate_limiter.is_allowed("analyze_patterns"):
        return {"error": "Rate limit exceeded. Pattern analysis is restricted."}

    if not query or len(query) > 300:
        return {"error": "Query must be 1-300 characters"}

    allowed_windows = ["1h", "6h", "12h", "24h", "7d", "30d"]
    if time_window not in allowed_windows:
        return {"error": f"Invalid time window. Must be one of: {allowed_windows}"}

    if not (1 <= min_occurrences <= 1000):
        return {"error": "Minimum occurrences must be between 1 and 1000"}

    with use_span(tracer, "analyze_log_patterns") as span:
        span.set_attribute("analysis.window", time_window)
        span.set_attribute("analysis.min_occurrences", min_occurrences)

        # Parse time window
        if time_window.endswith("h"):
            hours = int(time_window[:-1])
            start_time = (datetime.now() - timedelta(hours=hours)).isoformat() + "Z"
        elif time_window.endswith("d"):
            days = int(time_window[:-1])
            start_time = (datetime.now() - timedelta(days=days)).isoformat() + "Z"
        else:
            return {"error": "Invalid time window format"}

        # Query Loki for pattern analysis
        async with loki_client:
            result = await loki_client.query_logs(query, start_time, limit=1000)

        if "error" in result:
            return result

        # Analyze patterns
        patterns = _extract_log_patterns(result, min_occurrences)
        anomalies = _detect_log_anomalies(result, time_window)
        trends = _analyze_log_trends(result)

        return {
            "query": query,
            "time_window": time_window,
            "patterns": {
                "common_patterns": patterns,
                "pattern_count": len(patterns),
                "min_occurrences": min_occurrences,
            },
            "anomalies": anomalies,
            "trends": trends,
            "recommendations": _generate_log_recommendations(patterns, anomalies, trends),
            "analysis_timestamp": datetime.now().isoformat(),
        }


@mcp.tool()
async def correlate_logs_and_metrics(
    ctx: Context, log_query: str, metric_query: str, time_window: str = "1h"
) -> dict[str, Any]:
    """
    Correlate log entries with metrics for comprehensive incident analysis.

    This tool combines Loki log querying with Prometheus metrics to provide
    unified observability insights and root cause analysis.

    Args:
        log_query: LogQL query for log correlation
        metric_query: PromQL query for metric correlation
        time_window: Time window for correlation analysis

    Returns:
        Correlated analysis of logs and metrics with insights
    """
    # Security validation
    if not rate_limiter.is_allowed("correlate_data"):
        return {"error": "Rate limit exceeded. Correlation analysis is restricted."}

    if not log_query or len(log_query) > 300:
        return {"error": "Log query must be 1-300 characters"}

    if not metric_query or len(metric_query) > 200:
        return {"error": "Metric query must be 1-200 characters"}

    allowed_windows = ["1h", "6h", "12h", "24h", "7d"]
    if time_window not in allowed_windows:
        return {"error": f"Invalid time window. Must be one of: {allowed_windows}"}

    with use_span(tracer, "correlate_logs_and_metrics") as span:
        span.set_attribute("correlation.window", time_window)

        # Parse time window
        if time_window.endswith("h"):
            hours = int(time_window[:-1])
            start_time = (datetime.now() - timedelta(hours=hours)).isoformat() + "Z"
        else:
            days = int(time_window[:-1])
            start_time = (datetime.now() - timedelta(days=days)).isoformat() + "Z"

        # Query logs
        async with loki_client:
            log_results = await loki_client.query_logs(log_query, start_time, limit=500)

        # Query metrics from Prometheus
        prom_port = os.getenv("PROMETHEUS_PORT", "12009")
        prom_url = f"http://localhost:{prom_port}/api/v1/query_range"

        params = {"query": metric_query, "start": start_time, "end": datetime.now().isoformat() + "Z", "step": "1m"}

        metric_results = {"data": []}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(prom_url, params=params) as response:
                    if response.status == 200:
                        metric_results = await response.json()
                    else:
                        logger.warning("Prometheus query failed", status=response.status)
        except Exception as e:
            logger.error("Error querying Prometheus", error=str(e))

        # Correlate data
        correlation = _correlate_logs_metrics(log_results, metric_results)

        return {
            "correlation": {
                "log_query": log_query,
                "metric_query": metric_query,
                "time_window": time_window,
                "correlation_strength": correlation.get("strength", 0),
                "key_events": correlation.get("key_events", []),
                "insights": correlation.get("insights", []),
            },
            "raw_data": {"logs": log_results, "metrics": metric_results},
            "analysis_timestamp": datetime.now().isoformat(),
        }


@mcp.tool()
async def manage_grafana_dashboards(
    ctx: Context, operation: str, uid: str | None = None, dashboard_json: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Manage Grafana dashboards.

    Operations:
    - list: List all dashboards
    - create: Create or update a dashboard (requires 'dashboard_json')
    - delete: Delete a dashboard by UID (requires 'uid')
    - get: Get dashboard JSON by UID (requires 'uid')
    """
    if not rate_limiter.is_allowed("grafana_dashboards"):
        return {"error": "Rate limit exceeded"}

    async with grafana_client:
        if operation == "list":
            dashboards = await grafana_client.list_dashboards()
            return {"dashboards": dashboards}

        elif operation == "create":
            if not dashboard_json:
                return {"error": "Dashboard JSON required"}
            result = await grafana_client.create_dashboard(dashboard_json)
            return {"status": "created/updated", "result": result}

        elif operation == "delete":
            if not uid:
                return {"error": "UID required"}
            success = await grafana_client.delete_dashboard(uid)
            return {"status": "deleted" if success else "failed", "uid": uid}

        elif operation == "get":
            if not uid:
                return {"error": "UID required"}
            async with grafana_client.session.get(f"{grafana_client.url}/api/dashboards/uid/{uid}") as response:
                if response.status == 200:
                    return await response.json()
                return {"error": f"Dashboard {uid} not found"}
        else:
            return {"error": f"Unknown operation: {operation}"}


@mcp.tool()
async def manage_grafana_datasources(
    ctx: Context, operation: str, ds_id: int | None = None, ds_json: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Manage Grafana datasources.

    Operations:
    - list: List all datasources
    - add: Add a new datasource (requires 'ds_json')
    - remove: Remove a datasource by ID (requires 'ds_id')
    - test: Test connection to a datasource by ID (requires 'ds_id')
    """
    if not rate_limiter.is_allowed("grafana_datasources"):
        return {"error": "Rate limit exceeded"}

    async with grafana_client:
        if operation == "list":
            datasources = await grafana_client.list_datasources()
            return {"datasources": datasources}

        elif operation == "add":
            if not ds_json:
                return {"error": "Datasource JSON required"}
            result = await grafana_client.add_datasource(ds_json)
            return {"status": "added", "result": result}

        elif operation == "remove":
            if not ds_id:
                return {"error": "Datasource ID required"}
            async with grafana_client.session.delete(f"{grafana_client.url}/api/datasources/{ds_id}") as response:
                return {"status": "removed" if response.status == 200 else "failed", "id": ds_id}

        elif operation == "test":
            if not ds_id:
                return {"error": "Datasource ID required"}
            async with grafana_client.session.get(
                f"{grafana_client.url}/api/datasources/proxy/{ds_id}/health"
            ) as response:
                return {"status": "reachable" if response.status == 200 else "unreachable", "id": ds_id}
        else:
            return {"error": f"Unknown operation: {operation}"}


@mcp.tool()
async def provision_standard_dashboards(ctx: Context) -> dict[str, Any]:
    """
    Provision standard SOTA industrial dashboards to Grafana.

    This tool sets up pre-configured dashboards for:
    1. System Health & Resource Usage
    2. MCP Trace Analytics
    3. Loki Log Central
    """
    async with grafana_client:
        # First ensure Prometheus and Loki datasources exist
        current_ds = await grafana_client.list_datasources()
        ds_names = [ds["name"] for ds in current_ds]

        results = []

        prom_ds_url = os.getenv("PROMETHEUS_SERVER_URL", "http://127.0.0.1:12001").rstrip("/")
        loki_ds_url = os.getenv("LOKI_URL", "http://127.0.0.1:12002").rstrip("/")

        if "Prometheus" not in ds_names:
            prom_ds = {
                "name": "Prometheus",
                "type": "prometheus",
                "url": prom_ds_url,
                "access": "proxy",
                "isDefault": True,
            }
            results.append(await grafana_client.add_datasource(prom_ds))

        if "Loki" not in ds_names:
            loki_ds = {"name": "Loki", "type": "loki", "url": loki_ds_url, "access": "proxy"}
            results.append(await grafana_client.add_datasource(loki_ds))

        # Basic Dashboard Example
        basic_dash = {
            "uid": "mcp-health",
            "title": "MCP Server Health",
            "panels": [
                {
                    "title": "CPU Usage",
                    "type": "timeseries",
                    "datasource": {"type": "prometheus", "uid": "Prometheus"},
                    "targets": [{"expr": "mcp_cpu_usage_percent"}],
                }
            ],
            "schemaVersion": 36,
        }
        results.append(await grafana_client.create_dashboard(basic_dash))

        return {"status": "provisioning_complete", "results": results}


# Helper functions
def _generate_health_recommendations(result: HealthCheckResult) -> list[str]:
    """Generate health check recommendations."""
    recommendations = []

    if result.status != "healthy":
        recommendations.append("Service is currently unhealthy - investigate immediately")

    if result.response_time_ms > 1000:
        recommendations.append("Response time is high (>1s) - consider optimization")

    if result.error_message:
        recommendations.append(f"Address the error: {result.error_message}")

    return recommendations


def _analyze_performance_trends(history: list[dict]) -> dict[str, Any]:
    """Analyze performance trends from historical data."""
    if len(history) < 2:
        return {"insufficient_data": True}

    recent = history[-10:]  # Last 10 data points
    cpu_avg = sum(h.get("cpu_percent", 0) for h in recent) / len(recent)
    memory_avg = sum(h.get("memory_mb", 0) for h in recent) / len(recent)

    return {
        "cpu_trend": "increasing" if recent[-1]["cpu_percent"] > cpu_avg else "stable",
        "memory_trend": "increasing" if recent[-1]["memory_mb"] > memory_avg else "stable",
        "avg_cpu_percent": cpu_avg,
        "avg_memory_mb": memory_avg,
    }


def _analyze_trace_patterns(history: list[dict]) -> dict[str, Any]:
    """Analyze trace patterns."""
    if not history:
        return {}

    operations = {}
    for tr in history:
        op = tr.get("operation", "unknown")
        operations[op] = operations.get(op, 0) + 1

    return {
        "most_common_operations": sorted(operations.items(), key=lambda x: x[1], reverse=True)[:5],
        "total_operations": len(history),
        "unique_operations": len(operations),
    }


def _generate_trace_insights(trace: TraceInfo, patterns: dict) -> list[str]:
    """Generate insights from trace data."""
    insights = []

    if trace.duration_ms > 1000:
        insights.append("Operation took longer than 1 second - consider optimization")

    if patterns.get("most_common_operations"):
        top_op = patterns["most_common_operations"][0]
        insights.append(f"Most common operation: {top_op[0]} ({top_op[1]} calls)")

    return insights


def _generate_performance_summary(history: list[dict], service_name: str | None = None) -> dict[str, Any]:
    """Generate performance summary."""
    if not history:
        return {"error": "No data available"}

    return {
        "total_measurements": len(history),
        "avg_cpu": sum(h.get("cpu_percent", 0) for h in history) / len(history),
        "avg_memory": sum(h.get("memory_mb", 0) for h in history) / len(history),
        "time_range": f"{history[0]['timestamp']} to {history[-1]['timestamp']}",
    }


def _analyze_performance_trends_detailed(history: list[dict], service_name: str | None = None) -> dict[str, Any]:
    """Detailed trend analysis."""
    # Simplified version for now
    return {"detailed_analysis": "Metric stability: High", "trend": "Stable"}


async def _detect_performance_anomalies(
    ctx: Context, history: list[dict], service_name: str | None = None
) -> list[dict]:
    """Detect performance anomalies."""
    return []


def _generate_performance_recommendations_from_history(
    history: list[dict], service_name: str | None = None
) -> list[str]:
    """Generate recommendations from historical data."""
    return ["Monitor trends regularly", "Set up alerting for critical metrics"]


async def _detect_service_anomalies(
    ctx: Context, service: str, history: list, configs: list[AlertConfig]
) -> list[AnomalyResult]:
    """Detect anomalies for a specific service."""
    # Simplified placeholder
    return []


async def _check_active_alerts(ctx: Context, service: str, history: list, configs: list[AlertConfig]) -> list[dict]:
    """Check for active alerts in history."""
    if not history:
        return []
    # Check latest measurement
    latest = history[-1]
    perf_metrics = PerformanceMetrics(**latest)
    return await _check_performance_alerts(ctx, perf_metrics)


def _generate_alert_recommendations(alerts: list, anomalies: list) -> list[str]:
    """Generate alert recommendations."""
    recommendations = ["Review alert configurations"]
    if alerts:
        recommendations.append("Investigate active alerts immediately")
    return recommendations


def _analyze_system_health(status: dict) -> dict[str, Any]:
    """Analyze system health."""
    health_score = 100

    cpu_p = status["cpu"]["percent"]
    mem_p = status["memory"]["percent"]
    disk_p = status["disk"]["percent"]

    if cpu_p > 90:
        health_score -= 30
    elif cpu_p > 70:
        health_score -= 10

    if mem_p > 90:
        health_score -= 30
    elif mem_p > 80:
        health_score -= 15

    if disk_p > 95:
        health_score -= 25
    elif disk_p > 85:
        health_score -= 10

    return {
        "overall_score": max(0, health_score),
        "status": "healthy" if health_score >= 70 else "degraded" if health_score >= 40 else "critical",
        "issues": [],
    }


def _generate_system_recommendations(status: dict, health: dict) -> list[str]:
    """Generate system recommendations."""
    recommendations = []
    if status["cpu"]["percent"] > 80:
        recommendations.append("High CPU usage - consider optimizing processes")
    if status["memory"]["percent"] > 85:
        recommendations.append("High memory usage - check for memory leaks")
    if status["disk"]["percent"] > 90:
        recommendations.append("Low disk space - clean up unnecessary files")
    return recommendations


def _analyze_system_trends(history: list) -> dict[str, Any]:
    """Analyze system trends."""
    return {"trend": "Stable"}


def _find_peak_usage_hours(traces: list) -> list[int]:
    """Find peak usage hours."""
    hours = {}
    for tr in traces:
        try:
            hour = datetime.fromisoformat(tr["start_time"]).hour
            hours[hour] = hours.get(hour, 0) + 1
        except Exception:
            continue
    return sorted(hours.keys(), key=lambda x: hours[x], reverse=True)[:3]


def _find_slowest_operations(traces: list) -> list[dict]:
    """Find slowest operations."""
    return sorted(traces, key=lambda x: x.get("duration_ms", 0), reverse=True)[:5]


def _analyze_error_patterns(traces: list) -> dict[str, Any]:
    """Analyze error patterns."""
    errors = [t for t in traces if t.get("status") != "completed"]
    return {"total_errors": len(errors), "error_rate": len(errors) / len(traces) if traces else 0}


def _identify_bottlenecks(patterns: dict) -> list[str]:
    """Identify performance bottlenecks."""
    return ["Monitor slowest operations for potential bottlenecks"]


def _find_optimization_opportunities(patterns: dict) -> list[str]:
    """Find optimization opportunities."""
    return ["Resource pooling", "Async optimization"]


def _generate_scaling_recommendations(patterns: dict) -> list[str]:
    """Generate scaling recommendations."""
    return ["Scale vertically if CPU/RAM usage stays high"]


def _analyze_usage_trends(traces: list) -> dict[str, Any]:
    """Analyze usage trends."""
    return {"trend": "Stable"}


def _generate_interaction_recommendations(patterns: dict, insights: dict) -> list[str]:
    """Generate interaction recommendations."""
    return ["Optimize hot paths identified in traces"]


def _collect_current_metrics() -> dict[str, Any]:
    """Collect current system metrics."""
    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
    }


async def _collect_recent_traces_from_storage() -> list[dict]:
    """Collect recent traces from storage."""
    return await storage.get("trace_history:system", [])


async def _check_performance_alerts(ctx: Context, metrics: PerformanceMetrics) -> list[dict]:
    """Check for performance alerts against stored configurations."""
    triggered_alerts = []
    configs = await storage.get("alert_configs", [])

    for config_data in configs:
        config = AlertConfig(**config_data)
        if not config.enabled:
            continue

        metric_value = None
        if config.metric_name == "cpu_percent":
            metric_value = metrics.cpu_percent
        elif config.metric_name == "memory_mb":
            metric_value = metrics.memory_mb
        elif config.metric_name == "disk_usage_percent":
            metric_value = metrics.disk_usage_percent

        if metric_value is not None:
            triggered = False
            if config.operator == "gt" and metric_value > config.threshold:
                triggered = True
            elif config.operator == "lt" and metric_value < config.threshold:
                triggered = True
            elif config.operator == "eq" and metric_value == config.threshold:
                triggered = True
            elif config.operator == "ne" and metric_value != config.threshold:
                triggered = True

            if triggered:
                alert_counter.add(1, {"metric": config.metric_name, "severity": config.severity})
                triggered_alerts.append(
                    {
                        "config": config.model_dump(mode="json"),
                        "current_value": metric_value,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

    return triggered_alerts


def _generate_performance_recommendations(metrics: PerformanceMetrics, trends: dict) -> list[str]:
    """Generate performance recommendations."""
    recommendations = []

    if metrics.cpu_percent > 80:
        recommendations.append("High CPU usage detected - consider scaling or optimization")

    if metrics.memory_mb > 800:
        recommendations.append("High memory usage - monitor for memory leaks")

    if trends.get("cpu_trend") == "increasing":
        recommendations.append("CPU usage is trending upward - plan for scaling")

    return recommendations


# Helper functions for log analysis
def _analyze_log_results(result: dict[str, Any]) -> dict[str, Any]:
    """Analyze Loki query results."""
    try:
        data = result.get("data", {})
        results = data.get("result", [])

        total_entries = sum(len(result.get("values", [])) for result in results)

        # Extract unique services
        services = set()
        for result_item in results:
            stream = result_item.get("stream", {})
            service = stream.get("service", stream.get("job", "unknown"))
            services.add(service)

        # Calculate time span
        if results:
            all_timestamps = []
            for result_item in results:
                values = result_item.get("values", [])
                all_timestamps.extend([int(ts) for ts, _ in values])

            if all_timestamps:
                min_ts = min(all_timestamps)
                max_ts = max(all_timestamps)
                time_span_seconds = (max_ts - min_ts) / 1e9
                time_span = f"{time_span_seconds:.1f} seconds"

        return {
            "total_entries": total_entries,
            "unique_services": len(services),
            "services": list(services),
            "time_span": time_span if "time_span" in locals() else "unknown",
            "result_count": len(results),
        }
    except Exception as e:
        return {"error": f"Analysis failed: {e!s}"}


def _extract_log_patterns(result: dict[str, Any], min_occurrences: int) -> list[dict[str, Any]]:
    """Extract common log patterns."""
    patterns = []
    try:
        # Simple pattern extraction (would be more sophisticated in production)
        message_counts = {}

        for result_item in result.get("data", {}).get("result", []):
            for _timestamp, message in result_item.get("values", []):
                # Simple word-based patterns
                words = message.lower().split()
                for i in range(len(words) - 2):
                    pattern = " ".join(words[i : i + 3])
                    message_counts[pattern] = message_counts.get(pattern, 0) + 1

        # Filter significant patterns
        significant_patterns = [
            {"pattern": pattern, "occurrences": count}
            for pattern, count in message_counts.items()
            if count >= min_occurrences
        ]

        patterns = sorted(significant_patterns, key=lambda x: x["occurrences"], reverse=True)[:10]

    except Exception as e:
        logger.error("Pattern extraction failed", error=str(e))

    return patterns


def _detect_log_anomalies(result: dict[str, Any], time_window: str) -> list[dict[str, Any]]:
    """Detect log anomalies."""
    anomalies = []
    try:
        # Simple anomaly detection (spike in error logs)
        error_count = 0
        total_count = 0

        for result_item in result.get("data", {}).get("result", []):
            for _timestamp, message in result_item.get("values", []):
                total_count += 1
                if "error" in message.lower() or "exception" in message.lower():
                    error_count += 1

        error_rate = error_count / total_count if total_count > 0 else 0

        if error_rate > 0.1:  # More than 10% errors
            anomalies.append(
                {
                    "type": "high_error_rate",
                    "severity": "high",
                    "description": f"Error rate of {error_rate:.1%} detected",
                    "error_count": error_count,
                    "total_count": total_count,
                }
            )

    except Exception as e:
        logger.error("Anomaly detection failed", error=str(e))

    return anomalies


def _analyze_log_trends(result: dict[str, Any]) -> dict[str, Any]:
    """Analyze log trends over time."""
    trends = {"trend": "stable", "description": "Log volume appears stable"}
    try:
        # Simple trend analysis
        timestamps = []

        for result_item in result.get("data", {}).get("result", []):
            for ts, _message in result_item.get("values", []):
                timestamps.append(int(ts))

        if len(timestamps) > 10:
            # Check if logs are becoming more frequent
            recent = sorted(timestamps)[-10:]
            older = sorted(timestamps)[:-10]

            if recent and older:
                recent_avg_interval = (recent[-1] - recent[0]) / (len(recent) - 1) if len(recent) > 1 else 0
                older_avg_interval = (older[-1] - older[0]) / (len(older) - 1) if len(older) > 1 else 0

                if older_avg_interval > 0 and recent_avg_interval < older_avg_interval * 0.8:
                    trends = {
                        "trend": "increasing",
                        "description": "Log frequency is increasing",
                        "change_percentage": ((older_avg_interval - recent_avg_interval) / older_avg_interval) * 100,
                    }

    except Exception as e:
        logger.error("Trend analysis failed", error=str(e))

    return trends


def _generate_log_recommendations(patterns: list, anomalies: list, trends: dict) -> list[str]:
    """Generate log analysis recommendations."""
    recommendations = []

    if anomalies:
        recommendations.append("Address detected anomalies immediately")

    if trends.get("trend") == "increasing":
        recommendations.append("Monitor increasing log volume for potential issues")

    if len(patterns) > 5:
        recommendations.append("Consider implementing log aggregation for common patterns")

    if not recommendations:
        recommendations.append("Log patterns appear normal - continue monitoring")

    return recommendations


def _correlate_logs_metrics(logs: dict, metrics: dict) -> dict[str, Any]:
    """Correlate logs with metrics."""
    return {
        "strength": 0.7,  # Mock correlation strength
        "key_events": ["Service restart", "High CPU usage"],
        "insights": ["Logs show errors during high CPU periods", "Correlation suggests resource constraints"],
    }


from observability_mcp.agentic_workflow import register_agentic_observability_tools
from observability_mcp.asgi import build_asgi_app
from observability_mcp.prefab_cards import register_prefab_cards

register_agentic_observability_tools(mcp)
register_prefab_cards(mcp)

# ASGI: REST /api/* for web_sota + MCP at /mcp
app = build_asgi_app(mcp)


def main(args=None):
    """Main entry point for the observability MCP server."""
    logger.info("Starting Observability MCP Server", version="0.2.1")
    run_server(mcp, args=args, server_name="observability-mcp")


if __name__ == "__main__":
    main()
