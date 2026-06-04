"""Pydantic models, JSON storage, rate limiting, and docker helper."""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import structlog
from pydantic import BaseModel, Field, field_validator

logger = structlog.get_logger("observability_mcp.models_storage")


class HealthCheckResult(BaseModel):
    service_name: str
    status: str = Field(description="Status: healthy, degraded, unhealthy")
    response_time_ms: float
    timestamp: datetime
    details: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None


class PerformanceMetrics(BaseModel):
    service_name: str
    timestamp: datetime
    cpu_percent: float
    memory_mb: float
    disk_usage_percent: float
    network_io: dict[str, float]
    response_times: list[float] = Field(default_factory=list)
    throughput: float | None = None
    error_rate: float = 0.0


class TraceInfo(BaseModel):
    trace_id: str
    service_name: str
    operation: str
    start_time: datetime
    duration_ms: float
    status: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class AlertConfig(BaseModel):
    metric_name: str
    threshold: float
    operator: str = Field(description="gt, lt, eq, ne")
    severity: str = Field(description="info, warning, error, critical")
    enabled: bool = True

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v):
        allowed = ["gt", "lt", "eq", "ne"]
        if v not in allowed:
            raise ValueError(f"Operator must be one of: {allowed}")
        return v


class ReportSummary(BaseModel):
    period_days: int
    generated_at: datetime
    service_count: int
    total_metrics: int
    average_cpu: float
    average_memory: float
    anomaly_count: int
    critical_alerts: int


class RateLimiter:
    def __init__(self, max_calls: int = 100, window_seconds: int = 60):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.calls: dict[str, list[float]] = {}

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        if key not in self.calls:
            self.calls[key] = []
        self.calls[key] = [t for t in self.calls[key] if now - t < self.window_seconds]
        if len(self.calls[key]) >= self.max_calls:
            return False
        self.calls[key].append(now)
        return True


class InputValidator:
    @staticmethod
    def validate_url(url: str) -> bool:
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ["http", "https"]:
                return False
            if parsed.hostname in ["localhost", "127.0.0.1", "0.0.0.0"] or (
                parsed.hostname and (parsed.hostname.startswith("192.168.") or parsed.hostname.startswith("10."))
            ):
                return False
            return True
        except Exception:
            return False

    @staticmethod
    def validate_service_name(name: str) -> bool:
        return bool(re.match(r"^[a-zA-Z0-9_-]+$", name) and len(name) <= 100)

    @staticmethod
    def validate_days(days: int) -> bool:
        return 1 <= days <= 365


class JsonFileStorage:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.lock = asyncio.Lock()
        if not os.path.exists(file_path):
            try:
                os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
                with open(file_path, "w") as f:
                    json.dump({}, f)
            except Exception as e:
                print(f"Warning: Could not initialize storage at {file_path}: {e}")

    async def get(self, key: str, default: Any = None) -> Any:
        async with self.lock:
            try:
                if not os.path.exists(self.file_path):
                    return default
                with open(self.file_path) as f:
                    data = json.load(f)
                return data.get(key, default)
            except Exception as e:
                logger.error("Failed to read storage", error=str(e), key=key)
                return default

    async def set(self, key: str, value: Any):
        async with self.lock:
            try:
                data = {}
                if os.path.exists(self.file_path):
                    with open(self.file_path) as f:
                        data = json.load(f)
                data[key] = value
                with open(self.file_path, "w") as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                logger.error("Failed to save storage", error=str(e), key=key)


rate_limiter = RateLimiter()
input_validator = InputValidator()
_server_state: dict[str, Any] = {}
storage_path = os.getenv("MCP_STORAGE_PATH", "storage.json")
storage = JsonFileStorage(storage_path)


async def check_docker_status() -> dict[str, Any]:
    try:
        process = await asyncio.create_subprocess_exec(
            "docker",
            "version",
            "--format",
            "{{.Server.Version}}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            return {
                "status": "running",
                "reachable": True,
                "version": stdout.decode().strip(),
                "timestamp": datetime.now().isoformat(),
            }
        error_msg = stderr.decode().strip() or "Daemon not reachable"
        return {
            "status": "stopped",
            "reachable": False,
            "error": error_msg,
            "timestamp": datetime.now().isoformat(),
        }
    except FileNotFoundError:
        return {
            "status": "missing",
            "reachable": False,
            "error": "Docker CLI not found in PATH",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "reachable": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


class AnomalyResult(BaseModel):
    metric_name: str
    detected_at: datetime
    severity: str
    description: str
    current_value: float
    threshold_value: float
    historical_average: float
