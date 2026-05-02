"""Unit tests for AlertService logic."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.services.alert_service import AlertService


@pytest.fixture
def service():
    return AlertService()


class TestDetermineSeverity:
    def test_price_alert_critical(self, service):
        # 25% deviation -> critical
        assert service._determine_severity("price_above", 125.0, 100.0) == "critical"

    def test_price_alert_high(self, service):
        assert service._determine_severity("price_below", 88.0, 100.0) == "high"

    def test_price_alert_medium(self, service):
        assert service._determine_severity("price_above", 106.0, 100.0) == "medium"

    def test_price_alert_low(self, service):
        assert service._determine_severity("price_above", 102.0, 100.0) == "low"

    def test_volatility_critical(self, service):
        assert service._determine_severity("volatility_high", 0.9, 0.5) == "critical"

    def test_volatility_high(self, service):
        assert service._determine_severity("volatility_high", 0.65, 0.5) == "high"

    def test_volatility_medium(self, service):
        assert service._determine_severity("volatility_high", 0.45, 0.5) == "medium"

    def test_volume_spike_critical(self, service):
        assert service._determine_severity("volume_spike", 250.0, 50.0) == "critical"

    def test_volume_spike_high(self, service):
        assert service._determine_severity("volume_spike", 150.0, 50.0) == "high"

    def test_unknown_type_defaults_medium(self, service):
        assert service._determine_severity("unknown_type", 1.0, 1.0) == "medium"


class TestCheckAlert:
    @pytest.mark.asyncio
    async def test_price_above_triggers_when_exceeded(self, service):
        alert = MagicMock()
        alert.alert_type = "price_above"
        alert.threshold_value = 100.0
        alert.market = "crypto"
        alert.symbol = "BTC"

        service._get_current_value = AsyncMock(return_value=110.0)
        service._was_recently_triggered = AsyncMock(return_value=False)
        service._trigger_alert = AsyncMock()

        await service.check_alert(alert)
        service._trigger_alert.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_price_above_suppressed_in_cooldown(self, service):
        alert = MagicMock()
        alert.alert_type = "price_above"
        alert.threshold_value = 100.0
        alert.market = "crypto"
        alert.symbol = "BTC"

        service._get_current_value = AsyncMock(return_value=110.0)
        service._was_recently_triggered = AsyncMock(return_value=True)
        service._trigger_alert = AsyncMock()

        await service.check_alert(alert)
        service._trigger_alert.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_price_above_does_not_trigger_when_below(self, service):
        alert = MagicMock()
        alert.alert_type = "price_above"
        alert.threshold_value = 100.0
        alert.market = "crypto"
        alert.symbol = "BTC"

        service._get_current_value = AsyncMock(return_value=90.0)
        service._trigger_alert = AsyncMock()

        await service.check_alert(alert)
        service._trigger_alert.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_current_value_skips_alert(self, service):
        alert = MagicMock()
        alert.alert_type = "price_above"
        alert.market = "crypto"
        alert.symbol = "BTC"

        service._get_current_value = AsyncMock(return_value=None)
        service._trigger_alert = AsyncMock()

        await service.check_alert(alert)
        service._trigger_alert.assert_not_awaited()
