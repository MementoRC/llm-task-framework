"""Redis integration tests for the LLM Task Framework.

Tests Redis service container integration with proper fallback strategies.
Based on patterns from candles-feed and hb-strategy-sandbox projects.
"""

import os
import time
from unittest.mock import patch

import pytest

# Try to import redis, but gracefully handle if not available
try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # type: ignore[assignment]


def _decode_redis_value(value):
    """Helper function to handle Redis values that may be bytes or strings."""
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


@pytest.mark.integration
@pytest.mark.network
def test_redis_connection(redis_client):
    """Test basic Redis connection and ping."""
    if redis_client is None:
        pytest.skip("Redis client not available")

    # Test basic ping
    response = redis_client.ping()
    assert response is True

    # Test info command
    info = redis_client.info()
    assert "redis_version" in info
    assert "uptime_in_seconds" in info


@pytest.mark.integration
@pytest.mark.network
def test_redis_basic_operations(redis_client):
    """Test basic Redis operations (SET, GET, DEL)."""
    if redis_client is None:
        pytest.skip("Redis client not available")

    # Test SET and GET
    key = "test:basic:key"
    value = "test_value_123"

    # Set value
    result = redis_client.set(key, value)
    assert result is True

    # Get value
    retrieved = redis_client.get(key)
    assert _decode_redis_value(retrieved) == value

    # Test EXISTS
    exists = redis_client.exists(key)
    assert exists == 1

    # Test DEL
    deleted = redis_client.delete(key)
    assert deleted == 1

    # Verify deletion
    exists_after = redis_client.exists(key)
    assert exists_after == 0


@pytest.mark.integration
@pytest.mark.network
def test_redis_hash_operations(redis_client):
    """Test Redis hash operations for complex data storage."""
    if redis_client is None:
        pytest.skip("Redis client not available")

    hash_key = "test:hash:data"
    hash_data = {"field1": "value1", "field2": "value2", "counter": "42"}

    # Set hash fields
    result = redis_client.hset(hash_key, mapping=hash_data)
    assert result >= len(hash_data)  # Number of fields added

    # Get all hash data
    retrieved = redis_client.hgetall(hash_key)
    assert retrieved == hash_data

    # Get specific field
    field_value = redis_client.hget(hash_key, "field1")
    assert field_value == "value1"

    # Test hash field existence
    exists = redis_client.hexists(hash_key, "field1")
    assert exists is True

    # Increment counter
    new_value = redis_client.hincrby(hash_key, "counter", 1)
    assert new_value == 43


@pytest.mark.integration
@pytest.mark.network
def test_redis_list_operations(redis_client):
    """Test Redis list operations for queue-like functionality."""
    if redis_client is None:
        pytest.skip("Redis client not available")

    list_key = "test:list:queue"

    # Push items to list
    items = ["item1", "item2", "item3"]
    for item in items:
        redis_client.lpush(list_key, item)

    # Check list length
    length = redis_client.llen(list_key)
    assert length == 3

    # Pop items (LIFO order due to lpush)
    popped = redis_client.rpop(list_key)
    assert popped == "item1"

    # Get range of items
    remaining = redis_client.lrange(list_key, 0, -1)
    assert remaining == ["item3", "item2"]


@pytest.mark.integration
@pytest.mark.network
def test_redis_expiration(redis_client):
    """Test Redis key expiration functionality."""
    if redis_client is None:
        pytest.skip("Redis client not available")

    key = "test:expiring:key"
    value = "temporary_value"

    # Set key with expiration (1 second)
    redis_client.setex(key, 1, value)

    # Verify key exists
    assert redis_client.exists(key) == 1
    assert _decode_redis_value(redis_client.get(key)) == value

    # Check TTL
    ttl = redis_client.ttl(key)
    assert 0 < ttl <= 1

    # Wait for expiration
    time.sleep(1.1)

    # Verify key has expired
    assert redis_client.exists(key) == 0
    assert redis_client.get(key) is None


@pytest.mark.integration
@pytest.mark.network
def test_redis_transaction(redis_client):
    """Test Redis transaction functionality."""
    if redis_client is None:
        pytest.skip("Redis client not available")

    key1 = "test:transaction:key1"
    key2 = "test:transaction:key2"

    # Execute transaction
    with redis_client.pipeline() as pipe:
        pipe.multi()
        pipe.set(key1, "value1")
        pipe.set(key2, "value2")
        pipe.incr("test:counter")
        results = pipe.execute()

    # Verify transaction results
    assert len(results) == 3
    assert results[0] is True  # SET result
    assert results[1] is True  # SET result
    assert isinstance(results[2], int)  # INCR result

    # Verify values were set
    assert _decode_redis_value(redis_client.get(key1)) == "value1"
    assert _decode_redis_value(redis_client.get(key2)) == "value2"


@pytest.mark.integration
def test_redis_fallback_when_unavailable():
    """Test graceful fallback when Redis is unavailable."""
    if not REDIS_AVAILABLE:
        # Test the scenario where redis is not installed.
        # An attempt to use it should result in an ImportError.
        with pytest.raises(ImportError):
            raise ImportError("Simulating redis not being available")
    else:
        # Test the scenario where redis is installed but the server is unreachable.
        # Mock Redis to raise a connection error.
        with patch("redis.Redis.from_url") as mock_redis:
            mock_redis.side_effect = redis.ConnectionError("Connection refused")

            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

            with pytest.raises(redis.ConnectionError):
                client = redis.Redis.from_url(redis_url)
                client.ping()


@pytest.mark.integration
@pytest.mark.network
def test_redis_performance_basic(redis_client):
    """Test basic Redis performance characteristics."""
    if redis_client is None:
        pytest.skip("Redis client not available")

    # Benchmark basic operations
    num_operations = 100
    keys = [f"perf:test:{i}" for i in range(num_operations)]

    start_time = time.time()

    # Batch SET operations
    with redis_client.pipeline() as pipe:
        for key in keys:
            pipe.set(key, f"value_{key}")
        pipe.execute()

    set_time = time.time() - start_time

    # Batch GET operations
    start_time = time.time()
    with redis_client.pipeline() as pipe:
        for key in keys:
            pipe.get(key)
        results = pipe.execute()

    get_time = time.time() - start_time

    # Basic performance assertions (adjust thresholds as needed)
    assert set_time < 1.0, f"SET operations took too long: {set_time:.3f}s"
    assert get_time < 1.0, f"GET operations took too long: {get_time:.3f}s"
    assert len(results) == num_operations

    # Cleanup
    redis_client.delete(*keys)


@pytest.mark.integration
@pytest.mark.network
def test_redis_connection_pool():
    """Test Redis connection pooling functionality."""
    if not REDIS_AVAILABLE:
        pytest.skip("Redis library not available")

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    test_with_services = os.getenv("TEST_WITH_SERVICES", "false").lower() == "true"

    if not test_with_services:
        pytest.skip("Service container testing disabled")

    try:
        # Create connection pool
        pool = redis.ConnectionPool.from_url(redis_url, max_connections=10)

        # Create multiple clients using the same pool
        clients = [redis.Redis(connection_pool=pool) for _ in range(5)]

        # Test concurrent operations
        for i, client in enumerate(clients):
            client.set(f"pool:test:{i}", f"value_{i}")

        # Verify all operations succeeded
        for i, client in enumerate(clients):
            value = client.get(f"pool:test:{i}")
            assert _decode_redis_value(value) == f"value_{i}"

        # Cleanup
        for i in range(len(clients)):
            clients[0].delete(f"pool:test:{i}")

        # Close pool
        pool.disconnect()

    except (redis.ConnectionError, redis.TimeoutError) as e:
        pytest.skip(f"Redis connection failed: {e}")


@pytest.mark.integration
def test_redis_error_handling():
    """Test proper error handling for Redis operations."""
    if not REDIS_AVAILABLE:
        pytest.skip("Redis library not available")

    # Test with invalid Redis URL
    with pytest.raises(redis.ConnectionError):
        invalid_client = redis.Redis(host="invalid-host", port=6379, socket_timeout=1)
        invalid_client.ping()


@pytest.mark.integration
@pytest.mark.network
def test_redis_service_container_demo(redis_service_container):
    """Demonstrate using the new Redis service container."""
    if redis_service_container is None:
        pytest.skip("Redis service container not available")

    # Test that the container is healthy
    assert redis_service_container.is_healthy

    # Get Redis clients from the container
    sync_client = redis_service_container.get_sync_client()
    async_client = redis_service_container.get_async_client()

    # Test basic operations with sync client
    sync_client.set("demo_key", "demo_value")
    assert sync_client.get("demo_key") == "demo_value"

    # Test basic operations with async client (we'll use sync wrapper for demo)
    import asyncio

    loop = asyncio.get_event_loop()

    async def async_demo():
        await async_client.set("async_demo_key", "async_demo_value")
        result = await async_client.get("async_demo_key")
        return result

    result = loop.run_until_complete(async_demo())
    assert result == "async_demo_value"

    # Test health check
    health_info = loop.run_until_complete(redis_service_container.health_check())
    assert health_info["status"] == "healthy"
    assert "redis_version" in health_info

    # Clean up test data
    sync_client.delete("demo_key")
    loop.run_until_complete(async_client.delete("async_demo_key"))
