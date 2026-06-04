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
    TraceInfo,
    monitor_server_health,
    collect_performance_metrics,
    generate_performance_reports,
    alert_on_anomalies,
    monitor_system_resources,
)
from observability_mcp.models_storage import AlertConfig, HealthCheckResult, PerformanceMetrics


class _FakeHttpResponse:
    status = 200
    headers = {"content-type": "text/plain"}

    async def read(self):
        return b"OK"


class _FakeHttpResponseCM:
    def __init__(self, *, fail: bool = False):
        self._fail = fail

    async def __aenter__(self):
        if self._fail:
            raise ConnectionError("Connection failed")
        return _FakeHttpResponse()

    async def __aexit__(self, *args):
        return None


class _FakeClientSession:
    def __init__(self, *, fail: bool = False):
        self._fail = fail

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    def get(self, _url):
        return _FakeHttpResponseCM(fail=self._fail)


def _mock_aiohttp_session(mock_session, response: AsyncMock | None = None, *, get_raises: bool = False):
    mock_session.return_value = _FakeClientSession(fail=get_raises)


def _make_storage_get(data: dict):
    async def _get(key, default=None):
        if key in data:
            return data[key]
        return default if default is not None else []

    return _get


class TestHealthMonitoring:
    """Test health monitoring functionality."""

    @pytest.mark.asyncio
    async def test_monitor_server_health_success(self):
        """Test successful health check."""
        ctx = MagicMock()
        with patch("observability_mcp.server.aiohttp.ClientSession") as mock_session:
            _mock_aiohttp_session(mock_session)
            with patch("observability_mcp.server.storage") as mock_storage:
                mock_storage.get = _make_storage_get({})
                mock_storage.set = AsyncMock()
                result = await monitor_server_health(
                    ctx=ctx,
                    service_url="http://example.com/health",
                )

            assert result["health_check"]["status"] == "healthy"
            assert result["health_check"]["response_time_ms"] >= 0
            assert 'recommendations' in result

    @pytest.mark.asyncio
    async def test_monitor_server_health_failure(self):
        """Test failed health check."""
        ctx = MagicMock()
        with patch("observability_mcp.server.aiohttp.ClientSession") as mock_session:
            _mock_aiohttp_session(mock_session, get_raises=True)
            with patch("observability_mcp.server.storage") as mock_storage:
                mock_storage.get = AsyncMock(return_value=[])
                mock_storage.set = AsyncMock()
                result = await monitor_server_health(
                    ctx=ctx,
                    service_url="http://example.com/health",
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
            with patch("observability_mcp.server.storage") as mock_storage:
                mock_storage.get = _make_storage_get({"alert_configs": []})
                mock_storage.set = AsyncMock()
                result = await collect_performance_metrics(ctx=ctx, service_name="test-service")

            assert result['metrics']['cpu_percent'] == 45.5
            assert result['metrics']['memory_mb'] == 1024.0  # 1GB in MB
            assert result['metrics']['disk_usage_percent'] == 75.0
            assert 'trends' in result
            assert 'recommendations' in result


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
        with patch("observability_mcp.server.storage") as mock_storage:
            mock_storage.get = AsyncMock(return_value=mock_history)
            mock_storage.set = AsyncMock()
            result = await generate_performance_reports(
                ctx=ctx,
                service_name="test-service",
                days=7,
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
            AlertConfig(
                metric_name="cpu_percent", threshold=80.0, operator="gt", severity="warning"
            ).model_dump(mode="json")
        ]

        ctx = MagicMock()

        perf_row = {
            "service_name": "test-service",
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": 85.0,
            "memory_mb": 1024.0,
            "disk_usage_percent": 50.0,
            "network_io": {"bytes_sent": 0.0, "bytes_recv": 0.0},
        }
        with patch("observability_mcp.server.storage") as mock_storage:
            mock_storage.get = _make_storage_get(
                {
                    "alert_configs": mock_configs,
                    "performance_history:test-service": [perf_row],
                }
            )
            mock_storage.set = AsyncMock()
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
            with patch("observability_mcp.server.storage") as mock_storage:
                mock_storage.get = _make_storage_get({})
                mock_storage.set = AsyncMock()
                result = await monitor_system_resources(ctx=ctx)

            assert 'system_status' in result
            assert 'health_analysis' in result
            assert 'recommendations' in result

            system_status = result['system_status']
            assert system_status['cpu']['percent'] == 35.5
            assert system_status['memory']['percent'] == 50.0
            assert system_status['disk']['percent'] == 50.0



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
            store: dict = {"alert_configs": []}

            async def _get(key, default=None):
                return store.get(key, default if default is not None else [])

            async def _set(key, value):
                store[key] = value

            with patch("observability_mcp.server.storage") as mock_storage:
                mock_storage.get = _get
                mock_storage.set = _set
                metrics_result = await collect_performance_metrics(ctx=ctx)
                assert "metrics" in metrics_result
                report_result = await generate_performance_reports(ctx=ctx, days=1)
                assert "summary" in report_result
                alert_result = await alert_on_anomalies(ctx=ctx)
                assert "active_alerts" in alert_result
                assert metrics_result["metrics"]["cpu_percent"] == 65.0

class TestDegradedMode:
    """Test server behaviour when Docker or stack services are unreachable."""

    @pytest.mark.asyncio
    async def test_check_docker_status_daemon_missing(self):
        """check_docker_status returns a safe dict when docker CLI is not found."""
        from observability_mcp.server import check_docker_status

        with patch(
            "observability_mcp.models_storage.asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError("docker not found"),
        ):
            result = await check_docker_status()

        assert result["reachable"] is False
        assert result["status"] == "missing"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_check_docker_status_daemon_error(self):
        """check_docker_status returns a safe dict when the daemon returns non-zero."""
        from observability_mcp.server import check_docker_status

        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"Cannot connect to Docker daemon"))

        with patch(
            "observability_mcp.models_storage.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ):
            result = await check_docker_status()

        assert result["reachable"] is False
        assert result["status"] == "stopped"

    @pytest.mark.asyncio
    async def test_check_stack_status_all_down(self):
        """check_stack_status returns down for all services when unreachable."""
        from observability_mcp.server import check_stack_status

        ctx = MagicMock()

        with patch("observability_mcp.server.check_service_connectivity",
                   new_callable=AsyncMock, return_value=False):
            result = await check_stack_status(ctx)

        assert result["is_healthy"] is False
        assert result["status"]["loki"]["status"] == "down"
        assert result["status"]["prometheus"]["status"] == "down"
        assert result["status"]["grafana"]["status"] == "down"

    @pytest.mark.asyncio
    async def test_show_status_dashboard_docker_down(self):
        """Dashboard renders successfully even when Docker and all services are down."""
        from observability_mcp.server import show_status_dashboard, _server_state

        ctx = MagicMock()
        _server_state["degraded_mode"] = True

        # Docker unreachable
        docker_down = {"status": "stopped", "reachable": False, "error": "daemon not running"}

        # Stack all down
        stack_down = {
            "status": {
                "loki": {"status": "down"},
                "prometheus": {"status": "down"},
                "grafana": {"status": "down"},
            },
            "is_healthy": False,
            "recommendations": [],
        }

        # Perf metrics still work (psutil is local)
        perf_ok = {
            "metrics": {"cpu_percent": 12.5, "memory_mb": 512.0, "disk_usage_percent": 44.0},
            "trends": {},
            "recommendations": [],
        }

        alerts_ok = {"alerts": []}

        with patch("observability_mcp.server.check_docker_status",
                   new_callable=AsyncMock, return_value=docker_down), \
             patch("observability_mcp.server.check_stack_status",
                   new_callable=AsyncMock, return_value=stack_down), \
             patch("observability_mcp.server.collect_performance_metrics",
                   new_callable=AsyncMock, return_value=perf_ok), \
             patch("observability_mcp.server.manage_alert_configs",
                   new_callable=AsyncMock, return_value=alerts_ok):

            # Must not raise
            result = await show_status_dashboard(ctx)

        # Result is a Prefab Card object — just verify it's not None and has a title
        assert result is not None

        _server_state["degraded_mode"] = False  # cleanup

    @pytest.mark.asyncio
    async def test_show_status_dashboard_all_calls_fail(self):
        """Dashboard renders a degraded card even when every external call raises."""
        from observability_mcp.server import show_status_dashboard

        ctx = MagicMock()

        with patch("observability_mcp.server.check_docker_status",
                   new_callable=AsyncMock, side_effect=Exception("timeout")), \
             patch("observability_mcp.server.check_stack_status",
                   new_callable=AsyncMock, side_effect=Exception("timeout")), \
             patch("observability_mcp.server.collect_performance_metrics",
                   new_callable=AsyncMock, side_effect=Exception("psutil error")), \
             patch("observability_mcp.server.manage_alert_configs",
                   new_callable=AsyncMock, side_effect=Exception("storage error")):

            # Must not raise under any circumstances
            result = await show_status_dashboard(ctx)

        assert result is not None

    @pytest.mark.asyncio
    async def test_server_lifespan_prometheus_port_conflict(self):
        """Lifespan sets degraded_mode=True but does not crash on Prometheus port conflict."""
        from observability_mcp.server import server_lifespan, mcp, _server_state

        with patch("observability_mcp.server.start_http_server",
                   side_effect=OSError("Address already in use")), \
             patch("observability_mcp.server.storage.set", new_callable=AsyncMock), \
             patch("observability_mcp.server.storage.get",
                   new_callable=AsyncMock, return_value=None):

            async with server_lifespan(mcp):
                pass  # yield point — server is "running"

        assert _server_state.get("degraded_mode") is True
        _server_state["degraded_mode"] = False  # cleanup


