"""Tests for Redis service container implementation."""

import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm_task_framework.core.protocols import (
    ServiceConnectionError,
    ServiceNotAvailableError,
)
from llm_task_framework.services.redis_container import RedisServiceContainer


class TestRedisServiceContainerUnit:
    """Unit tests for Redis service container."""

    def test_init_default_values(self):
        """Test Redis container initialization with default values."""
        container = RedisServiceContainer()

        assert container.service_name == "redis"
        assert container._redis_url == "redis://localhost:6379"
        assert container._max_retries == 3
        assert container._retry_delay == 1.0
        assert container._connection_timeout == 5.0
        assert container._socket_timeout == 5.0
        assert container._decode_responses is True
        assert container._test_database == 15

    def test_init_with_custom_values(self):
        """Test Redis container initialization with custom values."""
        container = RedisServiceContainer(
            redis_url="redis://custom:6380",
            max_retries=5,
            retry_delay=2.0,
            connection_timeout=10.0,
            socket_timeout=15.0,
            decode_responses=False,
            test_database=5,
        )

        assert container._redis_url == "redis://custom:6380"
        assert container._max_retries == 5
        assert container._retry_delay == 2.0
        assert container._connection_timeout == 10.0
        assert container._socket_timeout == 15.0
        assert container._decode_responses is False
        assert container._test_database == 5

    def test_init_with_env_var(self):
        """Test Redis container initialization with environment variable."""
        with patch.dict(os.environ, {"REDIS_URL": "redis://env:6379"}):
            container = RedisServiceContainer()
            assert container._redis_url == "redis://env:6379"

    @patch("llm_task_framework.services.redis_container.REDIS_AVAILABLE", False)
    def test_redis_unavailable_is_not_healthy(self):
        """Test that container is not healthy when Redis library is unavailable."""
        container = RedisServiceContainer()
        assert not container.is_healthy

    @patch("llm_task_framework.services.redis_container.REDIS_AVAILABLE", False)
    async def test_redis_unavailable_connect_raises_error(self):
        """Test that connect raises error when Redis library is unavailable."""
        container = RedisServiceContainer()

        with pytest.raises(ServiceConnectionError, match="Redis library not available"):
            await container.connect()

    @patch("llm_task_framework.services.redis_container.REDIS_AVAILABLE", False)
    def test_redis_unavailable_get_client_raises_error(self):
        """Test that get_client raises error when Redis library is unavailable."""
        container = RedisServiceContainer()

        with pytest.raises(ServiceNotAvailableError, match="Redis library not available"):
            container.get_client()

    def test_get_client_not_connected_raises_error(self):
        """Test that get_client raises error when not connected."""
        with patch("llm_task_framework.services.redis_container.REDIS_AVAILABLE", True):
            container = RedisServiceContainer()

            with pytest.raises(ServiceNotAvailableError, match="Redis client not initialized"):
                container.get_client()

    def test_string_representations(self):
        """Test string representations of Redis container."""
        container = RedisServiceContainer()

        str_repr = str(container)
        assert "RedisServiceContainer" in str_repr
        assert "redis://localhost:6379" in str_repr
        assert "unhealthy" in str_repr

        repr_str = repr(container)
        assert "RedisServiceContainer" in repr_str
        assert "redis://localhost:6379" in repr_str
        assert "connected=False" in repr_str


class TestRedisServiceContainerWithMocks:
    """Tests for Redis service container with mocked Redis."""

    @pytest.fixture
    def mock_redis_module(self):
        """Mock Redis module and classes."""
        with patch("llm_task_framework.services.redis_container.REDIS_AVAILABLE", True):
            with patch("llm_task_framework.services.redis_container.redis") as mock_redis:
                with patch("llm_task_framework.services.redis_container.async_redis") as mock_async_redis:
                    # Setup mock sync client
                    mock_sync_client = MagicMock()
                    mock_sync_client.ping.return_value = True
                    mock_sync_client.info.return_value = {
                        "redis_version": "7.0.0",
                        "uptime_in_seconds": 3600,
                        "used_memory_human": "1M",
                        "connected_clients": 2,
                    }
                    mock_redis.Redis.from_url.return_value = mock_sync_client

                    # Setup mock async client
                    mock_async_client = AsyncMock()
                    mock_async_client.ping.return_value = True
                    mock_async_redis.Redis.from_url.return_value = mock_async_client

                    yield {
                        "redis": mock_redis,
                        "async_redis": mock_async_redis,
                        "sync_client": mock_sync_client,
                        "async_client": mock_async_client,
                    }

    async def test_successful_connect(self, mock_redis_module):
        """Test successful connection to Redis."""
        container = RedisServiceContainer()

        await container.connect()

        assert container._is_connected is True
        mock_redis_module["sync_client"].ping.assert_called_once()
        mock_redis_module["async_client"].ping.assert_called_once()

    async def test_connect_retry_on_failure(self, mock_redis_module):
        """Test connection retry logic on failure."""
        container = RedisServiceContainer(max_retries=3, retry_delay=0.01)

        # Both sync and async ping fail on first attempt, succeed on second
        call_count = [0]  # Use list to allow modification in nested function

        def sync_ping_side_effect():
            call_count[0] += 1
            if call_count[0] == 1:  # First call fails
                raise ConnectionError("Failed")
            return True  # Subsequent calls succeed

        async def async_ping_side_effect():
            if call_count[0] == 1:  # First call (sync already incremented)
                raise ConnectionError("Failed")
            return True  # Subsequent calls succeed

        mock_redis_module["sync_client"].ping.side_effect = sync_ping_side_effect
        mock_redis_module["async_client"].ping.side_effect = async_ping_side_effect

        await container.connect()

        assert container._is_connected is True
        # Should have been called twice - once failed, once succeeded
        assert call_count[0] == 2

    async def test_connect_max_retries_exceeded(self, mock_redis_module):
        """Test connection failure after max retries."""
        container = RedisServiceContainer(max_retries=2, retry_delay=0.1)

        # All attempts fail
        mock_redis_module["sync_client"].ping.side_effect = ConnectionError("Failed")

        with pytest.raises(ServiceConnectionError, match="Failed to connect to Redis after 2 attempts"):
            await container.connect()

        assert container._is_connected is False

    async def test_disconnect_cleans_up_clients(self, mock_redis_module):
        """Test that disconnect properly cleans up clients."""
        container = RedisServiceContainer()
        await container.connect()

        await container.disconnect()

        assert container._is_connected is False
        assert container._sync_client is None
        assert container._async_client is None
        mock_redis_module["async_client"].close.assert_called_once()

    async def test_health_check_healthy(self, mock_redis_module):
        """Test health check with healthy Redis."""
        container = RedisServiceContainer()
        await container.connect()

        health_info = await container.health_check()

        assert health_info["status"] == "healthy"
        assert health_info["service"] == "redis"
        assert "ping_time_ms" in health_info
        assert health_info["redis_version"] == "7.0.0"
        assert health_info["uptime_seconds"] == 3600

    async def test_health_check_unhealthy(self, mock_redis_module):
        """Test health check with unhealthy Redis."""
        container = RedisServiceContainer()
        await container.connect()

        # Make ping fail
        mock_redis_module["sync_client"].ping.side_effect = ConnectionError("Connection failed")

        health_info = await container.health_check()

        assert health_info["status"] == "unhealthy"
        assert "error" in health_info
        assert "Connection failed" in health_info["error"]

    def test_is_healthy_with_recent_check(self, mock_redis_module):
        """Test is_healthy uses cached health status when recent."""
        container = RedisServiceContainer()

        # Set up cached health status
        container._last_health_check = time.time()
        container._health_status = {"status": "healthy"}

        assert container.is_healthy is True

    def test_is_healthy_with_old_check(self, mock_redis_module):
        """Test is_healthy performs new check when cached status is old."""
        container = RedisServiceContainer()

        # Set up old cached health status
        container._last_health_check = time.time() - 60  # 60 seconds ago
        container._health_status = {"status": "healthy"}
        container._sync_client = mock_redis_module["sync_client"]

        assert container.is_healthy is True
        mock_redis_module["sync_client"].ping.assert_called_once()

    async def test_get_sync_client(self, mock_redis_module):
        """Test getting synchronous client."""
        container = RedisServiceContainer()
        await container.connect()

        sync_client = container.get_sync_client()

        assert sync_client == mock_redis_module["sync_client"]

    async def test_get_async_client(self, mock_redis_module):
        """Test getting asynchronous client."""
        container = RedisServiceContainer()
        await container.connect()

        async_client = container.get_async_client()

        assert async_client == mock_redis_module["async_client"]

    async def test_select_test_database(self, mock_redis_module):
        """Test selecting test database."""
        container = RedisServiceContainer()
        await container.connect()

        await container.select_test_database()

        mock_redis_module["sync_client"].select.assert_called_once_with(15)

    async def test_flush_test_database(self, mock_redis_module):
        """Test flushing test database."""
        container = RedisServiceContainer()
        await container.connect()

        # Mock connection pool to return test database
        mock_redis_module["sync_client"].connection_pool.connection_kwargs = {"db": 15}

        await container.flush_test_database()

        mock_redis_module["sync_client"].flushdb.assert_called_once()

    async def test_flush_test_database_with_select(self, mock_redis_module):
        """Test flushing test database when not currently selected."""
        container = RedisServiceContainer()
        await container.connect()

        # Mock connection pool to return different database
        mock_redis_module["sync_client"].connection_pool.connection_kwargs = {"db": 0}

        await container.flush_test_database()

        mock_redis_module["sync_client"].select.assert_called_once_with(15)
        mock_redis_module["sync_client"].flushdb.assert_called_once()


@pytest.mark.integration
@pytest.mark.network
class TestRedisServiceContainerIntegration:
    """Integration tests for Redis service container with real Redis."""

    @pytest.fixture
    def redis_container(self):
        """Create Redis container for integration tests."""
        return RedisServiceContainer(test_database=14)  # Use different DB than conftest.py

    async def test_full_lifecycle_with_real_redis(self, redis_container):
        """Test full lifecycle with real Redis if available."""
        test_with_services = os.environ.get("TEST_WITH_SERVICES", "false").lower() == "true"
        if not test_with_services:
            pytest.skip("Service container testing disabled (TEST_WITH_SERVICES is not 'true')")

        try:
            # Test connection
            await redis_container.connect()
            assert redis_container.is_healthy

            # Test health check
            health_info = await redis_container.health_check()
            assert health_info["status"] == "healthy"
            assert "redis_version" in health_info

            # Test client access
            sync_client = redis_container.get_sync_client()
            async_client = redis_container.get_async_client()

            # Test basic operations
            sync_client.set("test_key", "test_value")
            assert sync_client.get("test_key") == "test_value"

            await async_client.set("async_test_key", "async_test_value")
            result = await async_client.get("async_test_key")
            assert result == "async_test_value"

            # Test database operations
            await redis_container.select_test_database()
            await redis_container.flush_test_database()

        finally:
            # Always cleanup
            await redis_container.disconnect()
            assert not redis_container._is_connected

    async def test_connection_failure_handling(self, redis_container):
        """Test connection failure handling with invalid URL."""
        # Use invalid Redis URL
        redis_container._redis_url = "redis://nonexistent:6379"
        redis_container._max_retries = 1
        redis_container._retry_delay = 0.1

        with pytest.raises(ServiceConnectionError):
            await redis_container.connect()

        assert not redis_container.is_healthy

        health_info = await redis_container.health_check()
        assert health_info["status"] == "unhealthy"
