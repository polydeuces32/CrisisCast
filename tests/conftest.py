"""Session-level patches so tests run without live Redis or PostgreSQL."""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(scope="session", autouse=True)
def mock_redis_client():
    mock = MagicMock()
    mock.get.return_value = None
    mock.setex.return_value = True
    mock.ping.return_value = True
    mock.keys.return_value = []
    mock.delete.return_value = 0
    mock.flushdb.return_value = True
    mock.info.return_value = {
        "used_memory_human": "1.00M",
        "connected_clients": 1,
        "total_commands_processed": 0,
        "keyspace_hits": 0,
        "keyspace_misses": 0,
    }
    with patch("app.core.database.redis_client", mock):
        yield mock
