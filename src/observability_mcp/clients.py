"""Loki/Grafana HTTP clients and connectivity helpers."""

from __future__ import annotations

import os
import time
from typing import Any

import aiohttp
import structlog

logger = structlog.get_logger("observability_mcp.clients")


class LokiClient:
    """Client for sending logs to Loki."""

    def __init__(self, loki_url: str = "http://127.0.0.1:12002"):
        self.loki_url = loki_url.rstrip("/")
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def send_log(self, labels: dict[str, str], log_line: str, timestamp_ns: int | None = None):
        if not self.session:
            return
        if timestamp_ns is None:
            timestamp_ns = int(time.time() * 1e9)
        payload = {"streams": [{"stream": labels, "values": [[str(timestamp_ns), log_line]]}]}
        try:
            async with self.session.post(f"{self.loki_url}/loki/api/v1/push", json=payload) as response:
                if response.status != 204:
                    logger.warning("Failed to send log to Loki", status=response.status)
        except Exception as e:
            logger.error("Error sending log to Loki", error=str(e))

    async def query_logs(
        self, query: str, start: str | None = None, end: str | None = None, limit: int = 100
    ) -> dict[str, Any]:
        if not self.session:
            return {"error": "No session available"}
        params = {"query": query, "limit": str(limit)}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        try:
            async with self.session.get(
                f"{self.loki_url}/loki/api/v1/query_range", params=params
            ) as response:
                if response.status == 200:
                    return await response.json()
                return {"error": f"Query failed with status {response.status}"}
        except Exception as e:
            logger.error("Error querying Loki", error=str(e))
            return {"error": str(e)}


class GrafanaClient:
    """Client for interacting with Grafana API."""

    def __init__(self, url: str = "http://127.0.0.1:12000", auth_user: str = "admin", auth_pass: str = "admin123"):
        self.url = url.rstrip("/")
        self.auth = aiohttp.BasicAuth(auth_user, auth_pass)
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(auth=self.auth)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def list_dashboards(self) -> list[dict[str, Any]]:
        if not self.session:
            return []
        try:
            async with self.session.get(f"{self.url}/api/search?type=dash-db") as response:
                if response.status == 200:
                    return await response.json()
                return []
        except Exception as e:
            logger.error("Grafana: Failed to list dashboards", error=str(e))
            return []

    async def create_dashboard(self, dashboard_json: dict[str, Any]) -> dict[str, Any]:
        if not self.session:
            return {"error": "No session"}
        payload = {"dashboard": dashboard_json, "overwrite": True}
        try:
            async with self.session.post(f"{self.url}/api/dashboards/db", json=payload) as response:
                return await response.json()
        except Exception as e:
            logger.error("Grafana: Failed to create dashboard", error=str(e))
            return {"error": str(e)}

    async def delete_dashboard(self, uid: str) -> bool:
        if not self.session:
            return False
        try:
            async with self.session.delete(f"{self.url}/api/dashboards/uid/{uid}") as response:
                return response.status == 200
        except Exception as e:
            logger.error("Grafana: Failed to delete dashboard", error=str(e), uid=uid)
            return False

    async def list_datasources(self) -> list[dict[str, Any]]:
        if not self.session:
            return []
        try:
            async with self.session.get(f"{self.url}/api/datasources") as response:
                if response.status == 200:
                    return await response.json()
                return []
        except Exception as e:
            logger.error("Grafana: Failed to list datasources", error=str(e))
            return []

    async def add_datasource(self, ds_json: dict[str, Any]) -> dict[str, Any]:
        if not self.session:
            return {"error": "No session"}
        try:
            async with self.session.post(f"{self.url}/api/datasources", json=ds_json) as response:
                return await response.json()
        except Exception as e:
            logger.error("Grafana: Failed to add datasource", error=str(e))
            return {"error": str(e)}


loki_client = LokiClient(os.getenv("LOKI_URL", "http://127.0.0.1:12002"))
grafana_client = GrafanaClient(
    url=os.getenv("GRAFANA_URL", "http://127.0.0.1:12000"),
    auth_user=os.getenv("GRAFANA_USER", "admin"),
    auth_pass=os.getenv("GRAFANA_PASS", "admin123"),
)


async def check_service_connectivity(url: str, timeout: float = 2.0) -> bool:
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(url) as response:
                return response.status < 500
    except Exception:
        return False
