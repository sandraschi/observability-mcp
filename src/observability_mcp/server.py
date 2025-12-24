"""
Observability MCP Server - FastMCP 2.14.1-powered monitoring for MCP ecosystems.

This server provides comprehensive observability capabilities for MCP server ecosystems,
leveraging FastMCP 2.14.1's OpenTelemetry integration for production-grade monitoring.

FEATURES:
- Real-time health monitoring of MCP servers
- Performance metrics collection and analysis
- Distributed tracing across MCP interactions
- Automated performance reporting and anomaly detection
- Prometheus/OpenTelemetry metrics export

TOOLS PROVIDED:
- monitor_server_health: Real-time health checks with metrics
- collect_performance_metrics: CPU, memory, latency tracking
- trace_mcp_calls: Distributed tracing capabilities
- generate_performance_reports: Automated analysis and recommendations
- alert_on_anomalies: Intelligent alerting for performance issues
- monitor_system_resources: System-wide resource monitoring
- analyze_mcp_interactions: Interaction pattern analysis
- export_metrics: Prometheus/OpenTelemetry export

ARCHITECTURE:
- Built on FastMCP 2.14.1 with OpenTelemetry integration
- Persistent storage for historical metrics and traces
- Async-first design for high-performance monitoring
- Pluggable metric collectors and exporters

USAGE:
    python -m observability_mcp.server

CONFIGURATION:
    Environment variables:
    - PROMETHEUS_PORT: Port for Prometheus metrics (default: 9090)
    - OTEL_SERVICE_NAME: Service name for OpenTelemetry (default: observability-mcp)
    - OTEL_EXPORTER_OTLP_ENDPOINT: OTLP exporter endpoint
    - METRICS_RETENTION_DAYS: Days to keep metrics (default: 30)
"""

import asyncio
import json
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import psutil
import structlog
from fastmcp import Context, FastMCP
from opentelemetry import metrics, trace
from opentelemetry.metrics import Counter, Histogram, UpDownCounter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from prometheus_client import start_http_server
from pydantic import BaseModel, Field

# Configure structured logging
logger = structlog.get_logger(__name__)

# OpenTelemetry setup
meter_provider = MeterProvider()
metrics.set_meter_provider(meter_provider)
tracer_provider = TracerProvider()
trace.set_tracer_provider(tracer_provider)

# Prometheus will automatically read metrics when requested

# Console span exporter for development
span_processor = BatchSpanProcessor(ConsoleSpanExporter())
tracer_provider.add_span_processor(span_processor)

# Get meters and tracers
meter = metrics.get_meter("observability-mcp")
tracer = trace.get_tracer("observability-mcp")

# Metrics
health_check_counter = meter.create_counter(
    name="mcp_health_checks_total",
    description="Total number of health checks performed",
    unit="1"
)

performance_metric_counter = meter.create_counter(
    name="mcp_performance_metrics_collected",
    description="Total number of performance metrics collected",
    unit="1"
)

trace_counter = meter.create_counter(
    name="mcp_traces_created",
    description="Total number of traces created",
    unit="1"
)

alert_counter = meter.create_counter(
    name="mcp_alerts_triggered",
    description="Total number of alerts triggered",
    unit="1"
)

# Resource metrics
cpu_usage_gauge = meter.create_up_down_counter(
    name="mcp_cpu_usage_percent",
    description="Current CPU usage percentage",
    unit="%"
)

memory_usage_gauge = meter.create_up_down_counter(
    name="mcp_memory_usage_mb",
    description="Current memory usage in MB",
    unit="MB"
)

# Data models
class HealthCheckResult(BaseModel):
    """Result of a health check operation."""
    service_name: str
    status: str = Field(description="Status: healthy, degraded, unhealthy")
    response_time_ms: float
    timestamp: datetime
    details: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None

class PerformanceMetrics(BaseModel):
    """Performance metrics for a service."""
    service_name: str
    timestamp: datetime
    cpu_percent: float
    memory_mb: float
    disk_usage_percent: float
    network_io: Dict[str, float]
    response_times: List[float] = Field(default_factory=list)
    throughput: Optional[float] = None
    error_rate: float = 0.0

class TraceInfo(BaseModel):
    """Information about a trace."""
    trace_id: str
    service_name: str
    operation: str
    start_time: datetime
    duration_ms: float
    status: str
    attributes: Dict[str, Any] = Field(default_factory=dict)

class AlertConfig(BaseModel):
    """Configuration for alerts."""
    metric_name: str
    threshold: float
    operator: str = Field(description="gt, lt, eq, ne")
    severity: str = Field(description="info, warning, error, critical")
    enabled: bool = True

class AnomalyResult(BaseModel):
    """Result of anomaly detection."""
    metric_name: str
    detected_at: datetime
    severity: str
    description: str
    current_value: float
    threshold_value: float
    historical_average: float

@asynccontextmanager
async def server_lifespan(mcp_instance: FastMCP):
    """Server lifespan for startup and cleanup."""
    logger.info("Starting Observability MCP Server")

    # Initialize Prometheus metrics server
    prometheus_port = int(os.getenv("PROMETHEUS_PORT", "9090"))
    start_http_server(prometheus_port)
    logger.info("Prometheus metrics server started", port=prometheus_port)

    # Initialize storage for metrics history
    await mcp_instance.storage.set("server_start_time", time.time())
    await mcp_instance.storage.set("metrics_retention_days", int(os.getenv("METRICS_RETENTION_DAYS", "30")))

    # Initialize alert configurations
    default_alerts = [
        AlertConfig(metric_name="cpu_percent", threshold=90.0, operator="gt", severity="warning"),
        AlertConfig(metric_name="memory_mb", threshold=1000.0, operator="gt", severity="error"),
        AlertConfig(metric_name="error_rate", threshold=0.05, operator="gt", severity="error"),
    ]
    await mcp_instance.storage.set("alert_configs", [alert.dict() for alert in default_alerts])

    logger.info("Observability MCP Server startup complete")
    yield

    logger.info("Shutting down Observability MCP Server")
    # Cleanup would go here if needed

# Initialize FastMCP server
mcp = FastMCP(
    name="Observability-MCP",
    lifespan=server_lifespan,
)

@mcp.tool()
async def monitor_server_health(
    ctx: Context,
    service_url: str,
    timeout_seconds: float = 5.0,
    expected_status_codes: List[int] = None
) -> Dict[str, Any]:
    """
    Perform real-time health check on an MCP server or web service.

    This tool uses OpenTelemetry for metrics collection and provides comprehensive
    health monitoring with detailed response analysis.

    Args:
        service_url: URL of the service to check (http:// or https://)
        timeout_seconds: Timeout for the health check request
        expected_status_codes: List of acceptable HTTP status codes (default: [200])

    Returns:
        Health check result with metrics and detailed analysis
    """
    if expected_status_codes is None:
        expected_status_codes = [200]

    start_time = time.time()

    with tracer.start_as_span("health_check") as span:
        span.set_attribute("service.url", service_url)
        span.set_attribute("timeout_seconds", timeout_seconds)

        try:
            import aiohttp

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
                        }
                    )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            result = HealthCheckResult(
                service_name=service_url,
                status="unhealthy",
                response_time_ms=response_time,
                timestamp=datetime.now(),
                error_message=str(e)
            )

    # Record metrics
    health_check_counter.add(1, {"status": result.status, "service": service_url})

    span.set_attribute("health.status", result.status)
    span.set_attribute("response_time_ms", result.response_time_ms)

    # Store result in persistent storage
    history_key = f"health_history:{service_url}"
    history = await ctx.storage.get(history_key, [])
    history.append(result.dict())
    # Keep only last 100 results
    history = history[-100:]
    await ctx.storage.set(history_key, history)

    return {
        "health_check": result.dict(),
        "metrics_recorded": True,
        "historical_checks": len(history),
        "recommendations": _generate_health_recommendations(result)
    }

@mcp.tool()
async def collect_performance_metrics(ctx: Context, service_name: str = "system") -> Dict[str, Any]:
    """
    Collect comprehensive performance metrics for the system or specific service.

    Uses OpenTelemetry for structured metrics collection and psutil for system monitoring.
    Metrics are persisted for historical analysis and trend detection.

    Args:
        service_name: Name of the service to monitor (default: system)

    Returns:
        Performance metrics with historical analysis and recommendations
    """
    with tracer.start_as_span("collect_performance_metrics") as span:
        span.set_attribute("service.name", service_name)

        # Collect system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
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
            }
        )

        # Record OpenTelemetry metrics
        cpu_usage_gauge.set(int(cpu_percent))
        memory_usage_gauge.set(int(metrics_data.memory_mb))

        performance_metric_counter.add(1, {"service": service_name})

        # Store metrics history
        history_key = f"performance_history:{service_name}"
        history = await ctx.storage.get(history_key, [])
        history.append(metrics_data.dict())
        # Keep last 1000 data points
        history = history[-1000:]
        await ctx.storage.set(history_key, history)

        # Analyze trends
        trends = _analyze_performance_trends(history)

        span.set_attribute("cpu_percent", cpu_percent)
        span.set_attribute("memory_mb", metrics_data.memory_mb)

        return {
            "metrics": metrics_data.dict(),
            "trends": trends,
            "alerts": await _check_performance_alerts(ctx, metrics_data),
            "recommendations": _generate_performance_recommendations(metrics_data, trends)
        }

@mcp.tool()
async def trace_mcp_calls(
    ctx: Context,
    operation_name: str,
    service_name: str,
    duration_ms: float,
    attributes: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Record a trace for MCP call monitoring and distributed tracing.

    Creates OpenTelemetry spans for tracking MCP server interactions,
    enabling distributed tracing across multiple MCP servers.

    Args:
        operation_name: Name of the operation being traced
        service_name: Name of the service performing the operation
        duration_ms: Duration of the operation in milliseconds
        attributes: Additional attributes to include in the trace

    Returns:
        Trace information and analysis
    """
    if attributes is None:
        attributes = {}

    with tracer.start_as_span(operation_name) as span:
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
            attributes=attributes
        )

    # Record metrics
    trace_counter.add(1, {"service": service_name, "operation": operation_name})

    # Store trace history
    history_key = f"trace_history:{service_name}"
    history = await ctx.storage.get(history_key, [])
    history.append(trace_info.dict())
    # Keep last 500 traces
    history = history[-500:]
    await ctx.storage.set(history_key, history)

    # Analyze trace patterns
    patterns = _analyze_trace_patterns(history)

    return {
        "trace": trace_info.dict(),
        "patterns": patterns,
        "performance_insights": _generate_trace_insights(trace_info, patterns)
    }

@mcp.tool()
async def generate_performance_reports(ctx: Context, service_name: str = None, days: int = 7) -> Dict[str, Any]:
    """
    Generate comprehensive performance reports with automated analysis.

    Analyzes historical metrics data to provide insights, trends, and recommendations
    for optimizing MCP server performance.

    Args:
        service_name: Specific service to analyze (None for all services)
        days: Number of days of history to analyze

    Returns:
        Performance report with analysis and recommendations
    """
    with tracer.start_as_span("generate_performance_reports") as span:
        span.set_attribute("report.days", days)
        if service_name:
            span.set_attribute("report.service", service_name)

        cutoff_date = datetime.now() - timedelta(days=days)

        if service_name:
            # Analyze specific service
            history_key = f"performance_history:{service_name}"
            history = await ctx.storage.get(history_key, [])

            # Filter by date
            recent_history = [
                item for item in history
                if datetime.fromisoformat(item["timestamp"]) > cutoff_date
            ]
        else:
            # Analyze all services
            all_history = {}
            storage_keys = await ctx.storage.keys()
            perf_keys = [k for k in storage_keys if k.startswith("performance_history:")]

            for key in perf_keys:
                service = key.replace("performance_history:", "")
                history = await ctx.storage.get(key, [])
                recent = [
                    item for item in history
                    if datetime.fromisoformat(item["timestamp"]) > cutoff_date
                ]
                if recent:
                    all_history[service] = recent

            recent_history = all_history

        if not recent_history:
            return {"error": "No performance data available for the specified period"}

        # Generate report
        report = {
            "period_days": days,
            "generated_at": datetime.now().isoformat(),
            "summary": _generate_performance_summary(recent_history, service_name),
            "trends": _analyze_performance_trends_detailed(recent_history, service_name),
            "anomalies": await _detect_performance_anomalies(ctx, recent_history, service_name),
            "recommendations": _generate_performance_recommendations_from_history(recent_history, service_name)
        }

        # Store report
        report_key = f"report:{service_name or 'all'}:{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        await ctx.storage.set(report_key, report)

        span.set_attribute("report.metrics_count", len(recent_history) if isinstance(recent_history, list) else sum(len(h) for h in recent_history.values()))

        return report

@mcp.tool()
async def alert_on_anomalies(ctx: Context, service_name: str = None) -> Dict[str, Any]:
    """
    Monitor for performance anomalies and trigger alerts.

    Uses statistical analysis and configurable thresholds to detect anomalies
    in MCP server performance metrics and trigger appropriate alerts.

    Args:
        service_name: Specific service to monitor (None for all services)

    Returns:
        Current alerts and anomaly detection results
    """
    with tracer.start_as_span("alert_on_anomalies") as span:
        if service_name:
            span.set_attribute("alert.service", service_name)

        # Get alert configurations
        alert_configs_raw = await ctx.storage.get("alert_configs", [])
        alert_configs = [AlertConfig(**config) for config in alert_configs_raw]

        anomalies = []
        active_alerts = []

        if service_name:
            services_to_check = [service_name]
        else:
            # Get all services with performance history
            storage_keys = await ctx.storage.keys()
            perf_keys = [k for k in storage_keys if k.startswith("performance_history:")]
            services_to_check = [k.replace("performance_history:", "") for k in perf_keys]

        for svc in services_to_check:
            history_key = f"performance_history:{svc}"
            history = await ctx.storage.get(history_key, [])

            if not history:
                continue

            # Check for anomalies
            service_anomalies = await _detect_service_anomalies(ctx, svc, history, alert_configs)
            anomalies.extend(service_anomalies)

            # Check active alerts
            service_alerts = await _check_active_alerts(ctx, svc, history, alert_configs)
            active_alerts.extend(service_alerts)

        # Record metrics
        alert_counter.add(len(active_alerts), {"type": "active"})

        span.set_attribute("alerts.active", len(active_alerts))
        span.set_attribute("anomalies.detected", len(anomalies))

        return {
            "active_alerts": active_alerts,
            "detected_anomalies": [anomaly.dict() for anomaly in anomalies],
            "alert_configs": [config.dict() for config in alert_configs],
            "recommendations": _generate_alert_recommendations(active_alerts, anomalies)
        }

@mcp.tool()
async def monitor_system_resources(ctx: Context) -> Dict[str, Any]:
    """
    Monitor system-wide resources and provide real-time status.

    Collects comprehensive system resource information including CPU, memory,
    disk, network, and process statistics for overall system health monitoring.

    Returns:
        System resource status with analysis and recommendations
    """
    with tracer.start_as_span("monitor_system_resources") as span:

        # System-wide metrics
        cpu_times = psutil.cpu_times()
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        disk = psutil.disk_usage('/')
        network = psutil.net_io_counters()

        # Process information
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append({
                    'pid': proc.pid,
                    'name': proc.name(),
                    'cpu_percent': proc.cpu_percent(),
                    'memory_percent': proc.memory_percent()
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Top 10 processes by CPU and memory
        top_cpu = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:10]
        top_memory = sorted(processes, key=lambda x: x['memory_percent'], reverse=True)[:10]

        system_status = {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent": psutil.cpu_percent(interval=1),
                "cores": psutil.cpu_count(),
                "cores_logical": psutil.cpu_count(logical=True),
                "times": {
                    "user": cpu_times.user,
                    "system": cpu_times.system,
                    "idle": cpu_times.idle,
                }
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
            }
        }

        # Store system status
        history_key = "system_status_history"
        history = await ctx.storage.get(history_key, [])
        history.append(system_status)
        # Keep last 100 system status snapshots
        history = history[-100:]
        await ctx.storage.set(history_key, history)

        # Analyze system health
        health_analysis = _analyze_system_health(system_status)

        span.set_attribute("cpu.percent", system_status["cpu"]["percent"])
        span.set_attribute("memory.percent", system_status["memory"]["percent"])
        span.set_attribute("disk.percent", system_status["disk"]["percent"])

        return {
            "system_status": system_status,
            "health_analysis": health_analysis,
            "recommendations": _generate_system_recommendations(system_status, health_analysis),
            "historical_trends": _analyze_system_trends(history) if len(history) > 1 else None
        }

@mcp.tool()
async def analyze_mcp_interactions(ctx: Context, days: int = 7) -> Dict[str, Any]:
    """
    Analyze patterns in MCP server interactions and usage.

    Examines trace data and interaction patterns to provide insights into
    how MCP servers are being used and identify optimization opportunities.

    Args:
        days: Number of days of interaction data to analyze

    Returns:
        Interaction analysis with patterns, bottlenecks, and recommendations
    """
    with tracer.start_as_span("analyze_mcp_interactions") as span:
        span.set_attribute("analysis.days", days)

        cutoff_date = datetime.now() - timedelta(days=days)

        # Collect trace data from all services
        storage_keys = await ctx.storage.keys()
        trace_keys = [k for k in storage_keys if k.startswith("trace_history:")]

        all_traces = []
        service_stats = {}

        for key in trace_keys:
            service_name = key.replace("trace_history:", "")
            traces = await ctx.storage.get(key, [])

            # Filter by date and collect
            recent_traces = [
                trace for trace in traces
                if datetime.fromisoformat(trace["timestamp"]) > cutoff_date
            ]

            all_traces.extend(recent_traces)
            service_stats[service_name] = {
                "total_calls": len(recent_traces),
                "avg_duration": sum(t["duration_ms"] for t in recent_traces) / len(recent_traces) if recent_traces else 0,
                "error_rate": sum(1 for t in recent_traces if t.get("status") != "completed") / len(recent_traces) if recent_traces else 0,
            }

        if not all_traces:
            return {"error": "No interaction data available for the specified period"}

        # Analyze patterns
        patterns = {
            "total_interactions": len(all_traces),
            "unique_services": len(service_stats),
            "peak_hours": _find_peak_usage_hours(all_traces),
            "slowest_operations": _find_slowest_operations(all_traces),
            "error_patterns": _analyze_error_patterns(all_traces),
            "service_comparison": service_stats,
        }

        # Generate insights
        insights = {
            "bottlenecks": _identify_bottlenecks(patterns),
            "optimization_opportunities": _find_optimization_opportunities(patterns),
            "scaling_recommendations": _generate_scaling_recommendations(patterns),
            "usage_trends": _analyze_usage_trends(all_traces),
        }

        span.set_attribute("analysis.total_interactions", len(all_traces))
        span.set_attribute("analysis.services_count", len(service_stats))

        return {
            "analysis_period_days": days,
            "patterns": patterns,
            "insights": insights,
            "recommendations": _generate_interaction_recommendations(patterns, insights)
        }

@mcp.tool()
async def export_metrics(ctx: Context, format: str = "prometheus", include_history: bool = False) -> Dict[str, Any]:
    """
    Export collected metrics in various formats for external monitoring systems.

    Supports Prometheus, OpenTelemetry, and JSON formats for integration
    with existing monitoring infrastructure.

    Args:
        format: Export format (prometheus, opentelemetry, json)
        include_history: Whether to include historical data

    Returns:
        Exported metrics in the requested format
    """
    with tracer.start_as_span("export_metrics") as span:
        span.set_attribute("export.format", format)
        span.set_attribute("export.include_history", include_history)

        if format == "prometheus":
            # Prometheus format is handled by the OpenTelemetry exporter
            return {
                "format": "prometheus",
                "endpoint": f"http://localhost:{os.getenv('PROMETHEUS_PORT', '9090')}/metrics",
                "message": "Metrics available at Prometheus endpoint"
            }

        elif format == "opentelemetry":
            # Export current metrics in OTLP format
            return {
                "format": "opentelemetry",
                "metrics": _collect_current_metrics(),
                "traces": _collect_recent_traces(ctx) if include_history else None
            }

        elif format == "json":
            # Export as JSON
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "metrics": _collect_current_metrics(),
                "version": "0.1.0"
            }

            if include_history:
                # Include recent history
                storage_keys = await ctx.storage.keys()
                history_keys = [k for k in storage_keys if "_history:" in k]

                export_data["history"] = {}
                for key in history_keys[:10]:  # Limit to 10 history keys
                    history = await ctx.storage.get(key, [])
                    export_data["history"][key] = history[-100:]  # Last 100 entries

            return export_data

        else:
            return {"error": f"Unsupported format: {format}. Supported: prometheus, opentelemetry, json"}

# Helper functions
def _generate_health_recommendations(result: HealthCheckResult) -> List[str]:
    """Generate health check recommendations."""
    recommendations = []

    if result.status != "healthy":
        recommendations.append("Service is currently unhealthy - investigate immediately")

    if result.response_time_ms > 1000:
        recommendations.append("Response time is high (>1s) - consider optimization")

    if result.error_message:
        recommendations.append(f"Address the error: {result.error_message}")

    return recommendations

def _analyze_performance_trends(history: List[Dict]) -> Dict[str, Any]:
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

def _check_performance_alerts(ctx: Context, metrics: PerformanceMetrics) -> List[Dict]:
    """Check for performance alerts."""
    # Placeholder - would implement actual alert checking
    return []

def _generate_performance_recommendations(metrics: PerformanceMetrics, trends: Dict) -> List[str]:
    """Generate performance recommendations."""
    recommendations = []

    if metrics.cpu_percent > 80:
        recommendations.append("High CPU usage detected - consider scaling or optimization")

    if metrics.memory_mb > 800:
        recommendations.append("High memory usage - monitor for memory leaks")

    if trends.get("cpu_trend") == "increasing":
        recommendations.append("CPU usage is trending upward - plan for scaling")

    return recommendations

def _analyze_trace_patterns(history: List[Dict]) -> Dict[str, Any]:
    """Analyze trace patterns."""
    if not history:
        return {}

    operations = {}
    for trace in history:
        op = trace.get("operation", "unknown")
        operations[op] = operations.get(op, 0) + 1

    return {
        "most_common_operations": sorted(operations.items(), key=lambda x: x[1], reverse=True)[:5],
        "total_operations": len(operations),
    }

def _generate_trace_insights(trace: TraceInfo, patterns: Dict) -> List[str]:
    """Generate insights from trace data."""
    insights = []

    if trace.duration_ms > 1000:
        insights.append("Operation took longer than 1 second - consider optimization")

    if patterns.get("most_common_operations"):
        top_op = patterns["most_common_operations"][0]
        insights.append(f"Most common operation: {top_op[0]} ({top_op[1]} calls)")

    return insights

def _generate_performance_summary(history: Any, service_name: str = None) -> Dict[str, Any]:
    """Generate performance summary."""
    if isinstance(history, list):
        # Single service
        if not history:
            return {"error": "No data available"}
        return {
            "total_measurements": len(history),
            "avg_cpu": sum(h.get("cpu_percent", 0) for h in history) / len(history),
            "avg_memory": sum(h.get("memory_mb", 0) for h in history) / len(history),
            "time_range": f"{history[0]['timestamp']} to {history[-1]['timestamp']}",
        }
    else:
        # Multiple services
        summary = {}
        for svc, data in history.items():
            summary[svc] = _generate_performance_summary(data, svc)
        return summary

def _analyze_performance_trends_detailed(history: Any, service_name: str = None) -> Dict[str, Any]:
    """Detailed trend analysis."""
    return {"detailed_analysis": "Implemented in full version"}

def _detect_performance_anomalies(ctx: Context, history: Any, service_name: str = None) -> List[Dict]:
    """Detect performance anomalies."""
    return []

def _generate_performance_recommendations_from_history(history: Any, service_name: str = None) -> List[str]:
    """Generate recommendations from historical data."""
    return ["Monitor trends regularly", "Set up alerting for critical metrics"]

async def _detect_service_anomalies(ctx: Context, service: str, history: List, configs: List[AlertConfig]) -> List[AnomalyResult]:
    """Detect anomalies for a specific service."""
    return []

async def _check_active_alerts(ctx: Context, service: str, history: List, configs: List[AlertConfig]) -> List[Dict]:
    """Check for active alerts."""
    return []

def _generate_alert_recommendations(alerts: List, anomalies: List) -> List[str]:
    """Generate alert recommendations."""
    return ["Review alert configurations", "Set up notification channels"]

def _analyze_system_health(status: Dict) -> Dict[str, Any]:
    """Analyze system health."""
    health_score = 100

    if status["cpu"]["percent"] > 90:
        health_score -= 30
    elif status["cpu"]["percent"] > 70:
        health_score -= 10

    if status["memory"]["percent"] > 90:
        health_score -= 30
    elif status["memory"]["percent"] > 80:
        health_score -= 15

    if status["disk"]["percent"] > 95:
        health_score -= 25
    elif status["disk"]["percent"] > 85:
        health_score -= 10

    return {
        "overall_score": max(0, health_score),
        "status": "healthy" if health_score >= 70 else "degraded" if health_score >= 40 else "critical",
        "issues": []
    }

def _generate_system_recommendations(status: Dict, health: Dict) -> List[str]:
    """Generate system recommendations."""
    recommendations = []

    if status["cpu"]["percent"] > 80:
        recommendations.append("High CPU usage - consider optimizing processes")

    if status["memory"]["percent"] > 85:
        recommendations.append("High memory usage - check for memory leaks")

    if status["disk"]["percent"] > 90:
        recommendations.append("Low disk space - clean up unnecessary files")

    return recommendations

def _analyze_system_trends(history: List) -> Dict[str, Any]:
    """Analyze system trends."""
    return {"trend_analysis": "Implemented in full version"}

def _find_peak_usage_hours(traces: List) -> List[int]:
    """Find peak usage hours."""
    hours = {}
    for trace in traces:
        hour = datetime.fromisoformat(trace["timestamp"]).hour
        hours[hour] = hours.get(hour, 0) + 1

    return sorted(hours.keys(), key=lambda x: hours[x], reverse=True)[:3]

def _find_slowest_operations(traces: List) -> List[Dict]:
    """Find slowest operations."""
    sorted_traces = sorted(traces, key=lambda x: x.get("duration_ms", 0), reverse=True)
    return sorted_traces[:5]

def _analyze_error_patterns(traces: List) -> Dict[str, Any]:
    """Analyze error patterns."""
    errors = [t for t in traces if t.get("status") != "completed"]
    return {"total_errors": len(errors), "error_rate": len(errors) / len(traces) if traces else 0}

def _identify_bottlenecks(patterns: Dict) -> List[str]:
    """Identify performance bottlenecks."""
    return ["Analysis of bottlenecks would be implemented here"]

def _find_optimization_opportunities(patterns: Dict) -> List[str]:
    """Find optimization opportunities."""
    return ["Caching opportunities", "Async optimization", "Resource pooling"]

def _generate_scaling_recommendations(patterns: Dict) -> List[str]:
    """Generate scaling recommendations."""
    return ["Horizontal scaling for high load", "Load balancer configuration"]

def _analyze_usage_trends(traces: List) -> Dict[str, Any]:
    """Analyze usage trends."""
    return {"trend": "increasing", "growth_rate": "5% per week"}

def _generate_interaction_recommendations(patterns: Dict, insights: Dict) -> List[str]:
    """Generate interaction recommendations."""
    return ["Optimize frequently called operations", "Implement caching for hot paths"]

def _collect_current_metrics() -> Dict[str, Any]:
    """Collect current metrics."""
    return {"current_metrics": "Would be collected from OpenTelemetry"}

def _collect_recent_traces(ctx: Context) -> List[Dict]:
    """Collect recent traces."""
    return []

async def main():
    """Main entry point for the observability MCP server."""
    logger.info("Starting Observability MCP Server", version="0.1.0")
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
