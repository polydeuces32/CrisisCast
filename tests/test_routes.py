"""Integration-level smoke tests for key API routes."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

# Patch heavy service initialisation before importing the app
with (
    patch("app.core.database.create_engine"),
    patch("app.core.database.redis.from_url"),
    patch("app.core.database.Base.metadata.create_all"),
):
    from app.main import app
    from app.core.config import settings

client = TestClient(app, raise_server_exceptions=False)
VALID_KEY = settings.api_key


class TestHealthAndRoot:
    def test_root_returns_200(self):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "CrisisCast API"

    def test_health_returns_200(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_health_timestamp_is_dynamic(self):
        r1 = client.get("/health").json()["timestamp"]
        r2 = client.get("/health").json()["timestamp"]
        # Both should be valid ISO strings (not the hardcoded 2024-01-01)
        assert r1 != "2024-01-01T00:00:00Z"
        assert r2 != "2024-01-01T00:00:00Z"


class TestAuth:
    def test_protected_route_rejects_missing_key(self):
        resp = client.get("/api/v1/markets/")
        assert resp.status_code == 401

    def test_protected_route_rejects_wrong_key(self):
        resp = client.get("/api/v1/markets/", headers={"X-API-Key": "wrong-key"})
        assert resp.status_code == 401

    def test_protected_route_accepts_valid_key(self):
        resp = client.get("/api/v1/markets/", headers={"X-API-Key": VALID_KEY})
        # May return 500 if DB is unavailable in test env, but auth passed
        assert resp.status_code != 401


class TestAlertValidation:
    def test_create_alert_rejects_invalid_market(self):
        payload = {
            "user_id": "u1",
            "market": "invalid_market",
            "symbol": "BTC",
            "alert_type": "price_above",
            "threshold_value": 50000.0,
            "notification_method": "email",
            "notification_endpoint": "test@example.com",
        }
        resp = client.post(
            "/api/v1/alerts/",
            json=payload,
            headers={"X-API-Key": VALID_KEY},
        )
        assert resp.status_code == 422

    def test_create_alert_rejects_invalid_alert_type(self):
        payload = {
            "user_id": "u1",
            "market": "crypto",
            "symbol": "BTC",
            "alert_type": "not_a_real_type",
            "threshold_value": 50000.0,
            "notification_method": "email",
            "notification_endpoint": "test@example.com",
        }
        resp = client.post(
            "/api/v1/alerts/",
            json=payload,
            headers={"X-API-Key": VALID_KEY},
        )
        assert resp.status_code == 422

    def test_create_alert_rejects_invalid_notification_method(self):
        payload = {
            "user_id": "u1",
            "market": "crypto",
            "symbol": "BTC",
            "alert_type": "price_above",
            "threshold_value": 50000.0,
            "notification_method": "carrier_pigeon",
            "notification_endpoint": "test@example.com",
        }
        resp = client.post(
            "/api/v1/alerts/",
            json=payload,
            headers={"X-API-Key": VALID_KEY},
        )
        assert resp.status_code == 422
