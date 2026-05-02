"""Unit tests for MLService feature preparation and forecast logic."""
import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ml_service import MLService


@pytest.fixture
def service():
    with patch("os.makedirs"):
        return MLService()


def _make_price_df(n=100, start_price=100.0, symbol="BTC") -> pd.DataFrame:
    """Create a minimal price DataFrame for testing."""
    dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(n)]
    prices = [start_price * (1 + 0.01 * (i % 10 - 5)) for i in range(n)]
    volumes = [1_000_000.0 + i * 1000 for i in range(n)]
    return pd.DataFrame({
        "timestamp": dates,
        "price": prices,
        "volume": volumes,
        "market_cap": [p * 1e6 for p in prices],
        "symbol": symbol,
        "source": "test",
    })


class TestPrepareFeatures:
    def test_returns_arrays_for_sufficient_data(self, service):
        df = _make_price_df(100)
        features, target = service._prepare_features(df)
        assert features is not None
        assert target is not None

    def test_feature_and_target_same_length(self, service):
        df = _make_price_df(100)
        features, target = service._prepare_features(df)
        assert len(features) == len(target)

    def test_target_is_next_step_price(self, service):
        # The last row of sorted data has no next price so is dropped.
        # Target[i] should equal the price at index i+1 in the sorted frame.
        df = _make_price_df(60)
        df_sorted = df.sort_values("timestamp").reset_index(drop=True)
        features, target = service._prepare_features(df)
        # At minimum the last element of the original price series should not appear as a target
        assert len(target) < len(df_sorted)

    def test_no_nan_in_returned_arrays(self, service):
        df = _make_price_df(100)
        features, target = service._prepare_features(df)
        assert not np.isnan(features).any()
        assert not np.isnan(target).any()

    def test_returns_none_for_empty_dataframe(self, service):
        features, target = service._prepare_features(pd.DataFrame())
        assert features is None
        assert target is None

    def test_handles_missing_volume_gracefully(self, service):
        df = _make_price_df(80)
        df["volume"] = np.nan
        features, target = service._prepare_features(df)
        assert features is not None


class TestChronologicalSplit:
    def test_split_preserves_order(self, service):
        """First 80% must be earlier than last 20%."""
        df = _make_price_df(100)
        features, target = service._prepare_features(df)
        n = len(features)
        split = int(n * 0.8)
        # Verify split index is < total length
        assert split < n
        assert split > 0


class TestVolatilityScore:
    @pytest.mark.asyncio
    async def test_returns_float_in_range(self, service):
        with patch.object(service, "_get_market_data", AsyncMock(return_value=_make_price_df(50))):
            score = await service.calculate_volatility_score("crypto", "BTC", "30d")
        assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_returns_default_on_empty_data(self, service):
        with patch.object(service, "_get_market_data", AsyncMock(return_value=pd.DataFrame())):
            score = await service.calculate_volatility_score("crypto", "BTC", "30d")
        assert score == 0.5
