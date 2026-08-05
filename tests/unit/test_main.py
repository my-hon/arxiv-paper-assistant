"""应用入口src/main.py的单元测试。"""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.main import app, startup_event


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "系统运行正常"}


def test_root_reports_metadata(client):
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "AI论文搜集解读复现系统"
    assert body["version"] == "1.0.0"
    assert body["health"] == "/health"
    assert body["docs"] in {"/docs", "Documentation disabled"}


def test_api_router_is_mounted_under_v1(client):
    response = client.get("/api/v1/crawler/sources")

    assert response.status_code == 200
    assert response.json()["sources"][0]["id"] == "arxiv"


def test_cors_headers_are_returned(client):
    response = client.get("/health", headers={"Origin": "http://example.com"})

    assert response.headers["access-control-allow-origin"] == "http://example.com"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_static_mounts_exist():
    mounted = {route.path for route in app.routes if hasattr(route, "app")}

    assert "/static" in mounted
    assert "/storage" in mounted


@pytest.mark.asyncio
async def test_startup_event_initializes_system(monkeypatch):
    initialize = AsyncMock()
    monkeypatch.setattr("src.main.initialize_system", initialize)

    await startup_event()

    initialize.assert_awaited_once()
