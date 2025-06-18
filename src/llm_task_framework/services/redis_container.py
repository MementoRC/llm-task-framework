"""Redis service container implementation.

Provides connection management, health checking, and graceful degradation
for Redis services. Based on patterns from integration tests and production
deployments.
"""

import asyncio
import logging
import os
import time
from typing import Any

from ..core.protocols import (
    ServiceConnectionError,
    ServiceNotAvailableError,
)

logger = logging.getLogger(__name__)

# Try to import redis, gracefully handle if not available
try:
    import redis
    import redis.asyncio as async_redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # type: ignore[assignment]
    async_redis = None  # type: ignore[assignment]


class RedisServiceContainer:
    """
    Redis service container with connection management and health checking.
    
    Provides both synchronous and asynchronous Redis clients with automatic
    connection retry, health monitoring, and graceful degradation.
    """

    def __init__(
        self,
        redis_url: str | None = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        connection_timeout: float = 5.0,
        socket_timeout: float = 5.0,
        decode_responses: bool = True,
        test_database: int = 15,
    ):
        """
        Initialize Redis service container.

        Args:
            redis_url: Redis connection URL (defaults to REDIS_URL env var)
            max_retries: Maximum connection retry attempts
            retry_delay: Base delay between retries (exponential backoff)
            connection_timeout: Socket connection timeout in seconds
            socket_timeout: Socket operation timeout in seconds
            decode_responses: Whether to decode Redis responses to strings
            test_database: Database number to use for testing (default 15)
        """
        if not REDIS_AVAILABLE:
            logger.warning("Redis library not available, service container will be disabled")

        self._redis_url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379")
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._connection_timeout = connection_timeout
        self._socket_timeout = socket_timeout
        self._decode_responses = decode_responses
        self._test_database = test_database

        self._sync_client: Any | None = None
        self._async_client: Any | None = None
        self._is_connected = False
        self._last_health_check: float | None = None
        self._health_status: dict[str, Any] = {}

    @property
    def service_name(self) -> str:
        """Get the name of the service this container manages."""
        return "redis"

    @property
    def is_healthy(self) -> bool:
        """Check if the service is currently healthy and available."""
        if not REDIS_AVAILABLE:
            return False

        # Use cached health status if recent (within 30 seconds)
        if (
            self._last_health_check
            and time.time() - self._last_health_check < 30
            and self._health_status.get("status") == "healthy"
        ):
            return True

        # Perform quick ping test
        try:
            if self._sync_client:
                self._sync_client.ping()
                return True
        except Exception:
            pass

        return False

    async def connect(self) -> None:
        """
        Establish connection to Redis service.

        Raises:
            ServiceConnectionError: If connection fails after retries
        """
        if not REDIS_AVAILABLE:
            raise ServiceConnectionError("Redis library not available")

        last_exception = None

        for attempt in range(self._max_retries):
            try:
                # Create synchronous client
                if not self._sync_client:
                    self._sync_client = redis.Redis.from_url(
                        self._redis_url,
                        decode_responses=self._decode_responses,
                        socket_connect_timeout=self._connection_timeout,
                        socket_timeout=self._socket_timeout,
                    )

                # Create asynchronous client
                if not self._async_client:
                    self._async_client = async_redis.Redis.from_url(
                        self._redis_url,
                        decode_responses=self._decode_responses,
                        socket_connect_timeout=self._connection_timeout,
                        socket_timeout=self._socket_timeout,
                    )

                # Test both connections
                self._sync_client.ping()
                await self._async_client.ping()

                self._is_connected = True
                logger.info(f"Successfully connected to Redis at {self._redis_url}")
                return

            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Redis connection attempt {attempt + 1} failed: {e}"
                )

                if attempt < self._max_retries - 1:
                    delay = self._retry_delay * (2 ** attempt)  # Exponential backoff
                    await asyncio.sleep(delay)
                else:
                    # Cleanup on final failure
                    await self._cleanup_clients()

        raise ServiceConnectionError(
            f"Failed to connect to Redis after {self._max_retries} attempts: {last_exception}"
        )

    async def disconnect(self) -> None:
        """
        Close connection to Redis service.
        
        Idempotent - safe to call multiple times.
        """
        await self._cleanup_clients()
        self._is_connected = False
        logger.info("Disconnected from Redis service")

    async def _cleanup_clients(self) -> None:
        """Cleanup Redis clients safely."""
        if self._async_client:
            try:
                await self._async_client.close()
            except Exception as e:
                logger.warning(f"Error closing async Redis client: {e}")
            finally:
                self._async_client = None

        if self._sync_client:
            try:
                self._sync_client.close()
            except Exception as e:
                logger.warning(f"Error closing sync Redis client: {e}")
            finally:
                self._sync_client = None

    async def health_check(self) -> dict[str, Any]:
        """
        Perform detailed health check of Redis service.

        Returns:
            Dictionary containing health status and diagnostic information
        """
        health_info = {
            "service": "redis",
            "timestamp": time.time(),
            "status": "unhealthy",
            "available": REDIS_AVAILABLE,
            "connected": self._is_connected,
            "redis_url": self._redis_url,
        }

        if not REDIS_AVAILABLE:
            health_info["error"] = "Redis library not available"
            self._health_status = health_info
            self._last_health_check = time.time()
            return health_info

        if not self._sync_client:
            health_info["error"] = "Redis client not initialized"
            self._health_status = health_info
            self._last_health_check = time.time()
            return health_info

        try:
            # Test basic connectivity
            start_time = time.time()
            response = self._sync_client.ping()
            ping_time = time.time() - start_time

            if response:
                health_info["status"] = "healthy"
                health_info["ping_time_ms"] = round(ping_time * 1000, 2)

                # Get Redis server info
                try:
                    server_info = self._sync_client.info()
                    health_info["redis_version"] = server_info.get("redis_version")
                    health_info["uptime_seconds"] = server_info.get("uptime_in_seconds")
                    health_info["memory_used"] = server_info.get("used_memory_human")
                    health_info["connected_clients"] = server_info.get("connected_clients")
                except Exception as e:
                    logger.debug(f"Could not retrieve Redis server info: {e}")

        except Exception as e:
            health_info["error"] = str(e)
            health_info["status"] = "unhealthy"

        self._health_status = health_info
        self._last_health_check = time.time()
        return health_info

    def get_client(self, async_client: bool = False) -> Any:
        """
        Get the Redis client object.

        Args:
            async_client: If True, return async client; if False, return sync client

        Returns:
            Redis client object (sync or async)

        Raises:
            ServiceNotAvailableError: If service is not connected or unhealthy
        """
        if not REDIS_AVAILABLE:
            raise ServiceNotAvailableError("Redis library not available")

        client = self._async_client if async_client else self._sync_client

        if not client:
            raise ServiceNotAvailableError("Redis client not initialized - call connect() first")

        return client

    def get_sync_client(self) -> Any:
        """Get the synchronous Redis client."""
        return self.get_client(async_client=False)

    def get_async_client(self) -> Any:
        """Get the asynchronous Redis client."""
        return self.get_client(async_client=True)

    async def select_test_database(self) -> None:
        """
        Select the test database for integration testing.
        
        This is useful for isolation during testing.
        """
        if not self._sync_client:
            raise ServiceNotAvailableError("Redis client not available")

        try:
            self._sync_client.select(self._test_database)
            logger.debug(f"Selected Redis test database {self._test_database}")
        except Exception as e:
            raise ServiceConnectionError(f"Failed to select test database: {e}")

    async def flush_test_database(self) -> None:
        """
        Flush the test database.
        
        WARNING: This will delete all data in the test database.
        Only use for testing purposes.
        """
        if not self._sync_client:
            raise ServiceNotAvailableError("Redis client not available")

        try:
            current_db = self._sync_client.connection_pool.connection_kwargs.get("db", 0)
            if current_db != self._test_database:
                await self.select_test_database()

            self._sync_client.flushdb()
            logger.debug(f"Flushed Redis test database {self._test_database}")
        except Exception as e:
            raise ServiceConnectionError(f"Failed to flush test database: {e}")

    def __str__(self) -> str:
        """String representation of the Redis service container."""
        status = "healthy" if self.is_healthy else "unhealthy"
        return f"RedisServiceContainer(url={self._redis_url}, status={status})"

    def __repr__(self) -> str:
        """Detailed representation of the Redis service container."""
        return (
            f"RedisServiceContainer("
            f"url={self._redis_url!r}, "
            f"connected={self._is_connected}, "
            f"available={REDIS_AVAILABLE})"
        )
