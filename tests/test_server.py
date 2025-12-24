"""
Tests for the Observability MCP Server.

Tests FastMCP 2.14.1 integration, OpenTelemetry functionality,
persistent storage, and all monitoring tools.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from observability_mcp.server import (
    mcp,
    HealthCheckResult,
    PerformanceMetrics,
    TraceInfo,
    AlertConfig,
    AnomalyResult,
    monitor_server_health,
    collect_performance_metrics,
    trace_mcp_calls,
    generate_performance_reports,
    alert_on_anomalies,
    monitor_system_resources,
    analyze_mcp_interactions,
    export_metrics,
)


class TestHealthMonitoring:
    """Test health monitoring functionality."""

    @pytest.mark.asyncio
    async def test_monitor_server_health_success(self):
        """Test successful health check."""
        with patch('observability_mcp.server.aiohttp.ClientSession') as mock_session:
            # Mock successful response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.read.return_value = b'OK'
            mock_response.headers = {'content-type': 'text/plain'}

            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            mock_session.return_value.__aenter__.return_value.get.return_value.__aexit__.return_value = None
            mock_session.return_value.__aexit__.return_value = None

            # Mock context
            ctx = MagicMock()
            ctx.storage.get.return_value = []
            ctx.storage.set = AsyncMock()

            result = await monitor_server_health(
                ctx=ctx,
                service_url="http://example.com/health"
            )

            assert result['health_check']['status'] == 'healthy'
            assert result['health_check']['response_time_ms'] > 0
            assert 'recommendations' in result

    @pytest.mark.asyncio
    async def test_monitor_server_health_failure(self):
        """Test failed health check."""
        with patch('observability_mcp.server.aiohttp.ClientSession') as mock_session:
            # Mock failed response
            mock_session.return_value.__aenter__.return_value.get.side_effect = Exception("Connection failed")

            ctx = MagicMock()
            ctx.storage.get.return_value = []
            ctx.storage.set = AsyncMock()

            result = await monitor_server_health(
                ctx=ctx,
                service_url="http://example.com/health"
            )

            assert result['health_check']['status'] == 'unhealthy'
            assert 'error_message' in result['health_check']


class TestPerformanceMonitoring:
    """Test performance monitoring functionality."""

    @pytest.mark.asyncio
    async def test_collect_performance_metrics(self):
        """Test performance metrics collection."""
        with patch('observability_mcp.server.psutil') as mock_psutil:
            # Mock psutil calls
            mock_psutil.cpu_percent.return_value = 45.5
            mock_psutil.virtual_memory.return_value = MagicMock()
            mock_psutil.virtual_memory.return_value.used = 1024 * 1024 * 1024  # 1GB
            mock_psutil.disk_usage.return_value = MagicMock()
            mock_psutil.disk_usage.return_value.percent = 75.0
            mock_psutil.net_io_counters.return_value = MagicMock(
                bytes_sent=1000,
                bytes_recv=2000,
                packets_sent=10,
                packets_recv=20
            )

            ctx = MagicMock()
            ctx.storage.get.return_value = []
            ctx.storage.set = AsyncMock()

            result = await collect_performance_metrics(ctx=ctx, service_name="test-service")

            assert result['metrics']['cpu_percent'] == 45.5
            assert result['metrics']['memory_mb'] == 1024.0  # 1GB in MB
            assert result['metrics']['disk_usage_percent'] == 75.0
            assert 'trends' in result
            assert 'recommendations' in result


class TestTracing:
    """Test tracing functionality."""

    @pytest.mark.asyncio
    async def test_trace_mcp_calls(self):
        """Test MCP call tracing."""
        ctx = MagicMock()
        ctx.storage.get.return_value = []
        ctx.storage.set = AsyncMock()

        result = await trace_mcp_calls(
            ctx=ctx,
            operation_name="test_operation",
            service_name="test-service",
            duration_ms=150.5,
            attributes={"param": "value"}
        )

        assert result['trace']['operation'] == 'test_operation'
        assert result['trace']['service_name'] == 'test-service'
        assert result['trace']['duration_ms'] == 150.5
        assert result['trace']['attributes']['param'] == 'value'
        assert 'patterns' in result
        assert 'performance_insights' in result


class TestReporting:
    """Test reporting functionality."""

    @pytest.mark.asyncio
    async def test_generate_performance_reports(self):
        """Test performance report generation."""
        # Mock historical data
        mock_history = [
            {
                "timestamp": (datetime.now() - timedelta(days=i)).isoformat(),
                "cpu_percent": 50.0 + i,
                "memory_mb": 1000.0 + i * 10
            }
            for i in range(7)  # 7 days of data
        ]

        ctx = MagicMock()
        ctx.storage.get.return_value = mock_history
        ctx.storage.set = AsyncMock()

        result = await generate_performance_reports(
            ctx=ctx,
            service_name="test-service",
            days=7
        )

        assert 'summary' in result
        assert 'trends' in result
        assert 'anomalies' in result
        assert 'recommendations' in result
        assert result['summary']['total_measurements'] == 7


class TestAlerting:
    """Test alerting functionality."""

    @pytest.mark.asyncio
    async def test_alert_on_anomalies(self):
        """Test anomaly detection and alerting."""
        # Mock alert configurations
        mock_configs = [
            AlertConfig(metric_name="cpu_percent", threshold=80.0, operator="gt", severity="warning").dict()
        ]

        ctx = MagicMock()
        ctx.storage.get.side_effect = lambda key: {
            "alert_configs": mock_configs,
            "performance_history:test-service": [
                {"timestamp": datetime.now().isoformat(), "cpu_percent": 85.0}  # Above threshold
            ]
        }[key]

        result = await alert_on_anomalies(ctx=ctx, service_name="test-service")

        assert 'active_alerts' in result
        assert 'detected_anomalies' in result
        assert 'alert_configs' in result
        assert 'recommendations' in result


class TestSystemMonitoring:
    """Test system monitoring functionality."""

    @pytest.mark.asyncio
    async def test_monitor_system_resources(self):
        """Test system resource monitoring."""
        with patch('observability_mcp.server.psutil') as mock_psutil:
            # Mock comprehensive system data
            mock_cpu_times = MagicMock()
            mock_cpu_times.user = 100.0
            mock_cpu_times.system = 50.0
            mock_cpu_times.idle = 200.0

            mock_memory = MagicMock()
            mock_memory.total = 8 * 1024**3  # 8GB
            mock_memory.available = 4 * 1024**3  # 4GB
            mock_memory.used = 4 * 1024**3  # 4GB
            mock_memory.percent = 50.0

            mock_swap = MagicMock()
            mock_swap.total = 2 * 1024**3  # 2GB
            mock_swap.used = 0.5 * 1024**3  # 0.5GB
            mock_swap.percent = 25.0

            mock_disk = MagicMock()
            mock_disk.total = 500 * 1024**3  # 500GB
            mock_disk.used = 250 * 1024**3  # 250GB
            mock_disk.free = 250 * 1024**3  # 250GB
            mock_disk.percent = 50.0

            mock_network = MagicMock()
            mock_network.bytes_sent = 1000000
            mock_network.bytes_recv = 2000000
            mock_network.packets_sent = 10000
            mock_network.packets_recv = 20000

            mock_psutil.cpu_times.return_value = mock_cpu_times
            mock_psutil.cpu_percent.return_value = 35.5
            mock_psutil.cpu_count.return_value = 8
            mock_psutil.cpu_count.return_value = 16
            mock_psutil.virtual_memory.return_value = mock_memory
            mock_psutil.swap_memory.return_value = mock_swap
            mock_psutil.disk_usage.return_value = mock_disk
            mock_psutil.net_io_counters.return_value = mock_network

            # Mock process iterator
            mock_process = MagicMock()
            mock_process.pid = 1234
            mock_process.name.return_value = "python"
            mock_process.cpu_percent.return_value = 5.0
            mock_process.memory_percent.return_value = 2.0

            mock_psutil.process_iter.return_value = [mock_process]

            ctx = MagicMock()
            ctx.storage.get.return_value = []
            ctx.storage.set = AsyncMock()

            result = await monitor_system_resources(ctx=ctx)

            assert 'system_status' in result
            assert 'health_analysis' in result
            assert 'recommendations' in result

            system_status = result['system_status']
            assert system_status['cpu']['percent'] == 35.5
            assert system_status['memory']['percent'] == 50.0
            assert system_status['disk']['percent'] == 50.0


class TestAnalytics:
    """Test analytics functionality."""

    @pytest.mark.asyncio
    async def test_analyze_mcp_interactions(self):
        """Test MCP interaction analysis."""
        # Mock trace data
        mock_traces = [
            {
                "timestamp": (datetime.now() - timedelta(hours=i)).isoformat(),
                "operation": "health_check",
                "service_name": "test-service",
                "duration_ms": 100.0 + i * 10,
                "status": "completed"
            }
            for i in range(24)  # 24 hours of data
        ]

        ctx = MagicMock()
        ctx.storage.keys.return_value = ["trace_history:test-service"]
        ctx.storage.get.side_effect = lambda key: {
            "trace_history:test-service": mock_traces
        }.get(key, [])

        result = await analyze_mcp_interactions(ctx=ctx, days=1)

        assert 'patterns' in result
        assert 'insights' in result
        assert 'recommendations' in result
        assert result['patterns']['total_interactions'] == 24


class TestExport:
    """Test export functionality."""

    @pytest.mark.asyncio
    async def test_export_metrics_prometheus(self):
        """Test Prometheus metrics export."""
        ctx = MagicMock()

        result = await export_metrics(ctx=ctx, format="prometheus")

        assert result['format'] == 'prometheus'
        assert 'endpoint' in result
        assert '9090' in result['endpoint']

    @pytest.mark.asyncio
    async def test_export_metrics_json(self):
        """Test JSON metrics export."""
        ctx = MagicMock()
        ctx.storage.keys.return_value = []
        ctx.storage.get.return_value = []

        result = await export_metrics(ctx=ctx, format="json", include_history=False)

        assert result['format'] == 'json'
        assert 'timestamp' in result
        assert 'metrics' in result
        assert 'version' in result


class TestDataModels:
    """Test data models and validation."""

    def test_health_check_result_creation(self):
        """Test HealthCheckResult model creation."""
        result = HealthCheckResult(
            service_name="test-service",
            status="healthy",
            response_time_ms=150.0,
            timestamp=datetime.now()
        )
        assert result.service_name == "test-service"
        assert result.status == "healthy"
        assert result.response_time_ms == 150.0

    def test_performance_metrics_creation(self):
        """Test PerformanceMetrics model creation."""
        metrics = PerformanceMetrics(
            service_name="test-service",
            timestamp=datetime.now(),
            cpu_percent=45.5,
            memory_mb=1024.0,
            disk_usage_percent=75.0,
            network_io={"bytes_sent": 1000, "bytes_recv": 2000}
        )
        assert metrics.service_name == "test-service"
        assert metrics.cpu_percent == 45.5
        assert metrics.memory_mb == 1024.0

    def test_trace_info_creation(self):
        """Test TraceInfo model creation."""
        trace = TraceInfo(
            trace_id="test-trace-id",
            service_name="test-service",
            operation="test-operation",
            start_time=datetime.now(),
            duration_ms=150.5,
            status="completed"
        )
        assert trace.trace_id == "test-trace-id"
        assert trace.operation == "test-operation"
        assert trace.duration_ms == 150.5

    def test_alert_config_creation(self):
        """Test AlertConfig model creation."""
        config = AlertConfig(
            metric_name="cpu_percent",
            threshold=90.0,
            operator="gt",
            severity="warning"
        )
        assert config.metric_name == "cpu_percent"
        assert config.threshold == 90.0
        assert config.operator == "gt"
        assert config.severity == "warning"


class TestIntegration:
    """Integration tests for the observability server."""

    @pytest.mark.asyncio
    async def test_full_monitoring_workflow(self):
        """Test complete monitoring workflow."""
        with patch('observability_mcp.server.psutil') as mock_psutil:
            # Setup mocks
            mock_psutil.cpu_percent.return_value = 65.0
            mock_memory = MagicMock()
            mock_memory.used = 2 * 1024**3  # 2GB
            mock_psutil.virtual_memory.return_value = mock_memory

            ctx = MagicMock()
            ctx.storage.get.return_value = []
            ctx.storage.set = AsyncMock()

            # Step 1: Collect metrics
            metrics_result = await collect_performance_metrics(ctx=ctx)
            assert 'metrics' in metrics_result

            # Step 2: Generate report
            report_result = await generate_performance_reports(ctx=ctx, days=1)
            assert 'summary' in report_result

            # Step 3: Check alerts
            alert_result = await alert_on_anomalies(ctx=ctx)
            assert 'active_alerts' in alert_result

            # Verify workflow completion
            assert metrics_result['metrics']['cpu_percent'] == 65.0
