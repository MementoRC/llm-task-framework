"""Pytest configuration and shared fixtures for the LLM Task Framework."""

import asyncio
import contextlib
import os
import tempfile
import warnings
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest


@pytest.fixture(scope="function", autouse=True)
async def auto_cleanup_async_resources() -> AsyncGenerator[None, None]:
    """Automatically cleanup async resources after each test.

    Prevents resource leaks from unclosed sessions, tasks, and connections.
    Based on patterns from candles-feed project.
    """
    # Store initial async state
    initial_tasks = set(asyncio.all_tasks())

    yield

    # Cleanup hanging async tasks created during test
    current_tasks = set(asyncio.all_tasks())
    test_created_tasks = current_tasks - initial_tasks

    for task in test_created_tasks:
        if not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, asyncio.TimeoutError):
                await asyncio.wait_for(task, timeout=1.0)

    # Cleanup any pending aiohttp sessions if aiohttp is available
    try:
        import aiohttp  # type: ignore[import-untyped]

        # Close any unclosed client sessions
        connector = getattr(aiohttp, "_connector", None)
        if connector and hasattr(connector, "_conns"):
            for _conn_key, conns in list(connector._conns.items()):
                for conn in list(conns):
                    if not conn.closed:
                        conn.close()
    except ImportError:
        pass  # aiohttp not installed


@pytest.fixture(scope="function", autouse=True)
def prevent_environment_pollution() -> Generator[None, None, None]:
    """Prevent environment variable pollution between tests.

    Preserves original environment state and restores it after each test.
    Critical for tests that modify os.environ.
    """
    # Store original environment
    original_env = dict(os.environ)
    original_cwd = os.getcwd()

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)

    # Restore working directory
    with contextlib.suppress(FileNotFoundError):
        os.chdir(original_cwd)


@pytest.fixture(scope="function", autouse=True)
def prevent_warning_pollution() -> Generator[None, None, None]:
    """Prevent warning filter pollution between tests.

    Ensures that warning filters modified during tests don't affect other tests.
    """
    # Store original warning filters
    original_filters = warnings.filters[:]

    yield

    # Restore original warning filters (mypy workaround)
    warnings.filters[:] = original_filters  # type: ignore[index]


@pytest.fixture(scope="function", autouse=True)
def cleanup_temp_files() -> Generator[None, None, None]:
    """Automatically cleanup temporary files created during tests.

    Tracks and removes temporary files/directories to prevent disk space issues.
    """
    # Track temp files created during test
    temp_paths = set()
    original_mkstemp = tempfile.mkstemp
    original_mkdtemp = tempfile.mkdtemp

    def tracking_mkstemp(*args: Any, **kwargs: Any) -> tuple[int, str]:
        fd, path = original_mkstemp(*args, **kwargs)
        temp_paths.add(path)
        return fd, path

    def tracking_mkdtemp(*args: Any, **kwargs: Any) -> str:
        path: str = original_mkdtemp(*args, **kwargs)
        temp_paths.add(path)
        return path

    # Patch tempfile functions to track created files
    with (
        patch("tempfile.mkstemp", tracking_mkstemp),
        patch("tempfile.mkdtemp", tracking_mkdtemp),
    ):
        yield

    # Cleanup tracked temporary files
    for temp_path in temp_paths:
        try:
            path_obj = Path(temp_path)
            if path_obj.exists():
                if path_obj.is_file():
                    path_obj.unlink()
                elif path_obj.is_dir():
                    import shutil

                    shutil.rmtree(temp_path, ignore_errors=True)
        except (OSError, PermissionError):
            # Ignore cleanup errors - test isolation is more important
            pass


@pytest.fixture(scope="function")
def isolated_event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Provide an isolated event loop for async tests.

    Creates a fresh event loop for each test to prevent event loop pollution.
    Useful for tests that need complete async isolation.
    """
    # Create new event loop for complete isolation
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    yield loop

    # Cleanup event loop
    try:
        # Cancel all pending tasks
        pending_tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
        if pending_tasks:
            for task in pending_tasks:
                task.cancel()
            # Wait for cancelled tasks to complete
            loop.run_until_complete(
                asyncio.gather(*pending_tasks, return_exceptions=True)
            )
    finally:
        loop.close()


@pytest.fixture(scope="function")
def temp_project_dir() -> Generator[Path, None, None]:
    """Provide a temporary project directory for tests.

    Creates a clean temporary directory with proper cleanup.
    Useful for tests that need to create project files.
    """
    with tempfile.TemporaryDirectory(prefix="llm_task_framework_test_") as temp_dir:
        yield Path(temp_dir)


@pytest.fixture(scope="function")
def redis_connection() -> Generator[Any, None, None]:
    """Provide Redis connection for integration tests.

    Safely handles Redis connection with fallback strategies.
    Returns None if Redis is not available.
    """
    try:
        import redis
    except ImportError:
        # Redis not available, yield None to allow graceful skipping
        yield None
        return

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    test_with_services = os.environ.get("TEST_WITH_SERVICES", "false").lower() == "true"

    if not test_with_services:
        # Service container testing disabled
        yield None
        return

    client = None
    try:
        # Create Redis client with timeout
        client = redis.Redis.from_url(
            redis_url, decode_responses=True, socket_timeout=5
        )

        # Test connection
        client.ping()

        # Use test-specific database
        client.select(15)
        client.flushdb()  # Clear test database

        yield client

    except (redis.ConnectionError, redis.TimeoutError, ConnectionRefusedError):
        # Redis not available, yield None for graceful skipping
        yield None

    finally:
        # Cleanup
        if client:
            try:
                client.flushdb()  # Clear test data
                client.close()
            except Exception:
                pass  # Ignore cleanup errors


@pytest.fixture(scope="function")
def mock_api_keys() -> Generator[dict[str, str], None, None]:
    """Provide mock API keys for testing without real credentials.

    Sets up fake API keys in environment for tests that need them.
    """
    mock_keys = {
        "ANTHROPIC_API_KEY": "test-anthropic-key-12345",  # pragma: allowlist secret
        "OPENAI_API_KEY": "test-openai-key-12345",  # pragma: allowlist secret
        "GOOGLE_API_KEY": "test-google-key-12345",  # pragma: allowlist secret
    }

    # Store original values
    original_values = {}
    for key in mock_keys:
        original_values[key] = os.environ.get(key)
        os.environ[key] = mock_keys[key]

    yield mock_keys

    # Restore original values
    for key, original_value in original_values.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture(scope="session", autouse=True)
def configure_test_logging() -> None:
    """Configure logging for test runs.

    Sets up appropriate logging levels and formats for testing.
    """
    import logging

    # Configure root logger for tests
    logging.basicConfig(
        level=logging.WARNING,  # Reduce noise in test output
        format="%(name)s - %(levelname)s - %(message)s",
    )

    # Set specific loggers to appropriate levels
    logging.getLogger("llm_task_framework").setLevel(logging.INFO)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


# Enhanced test markers for better categorization
pytest_plugins: list[str] = []


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers and settings."""
    # Register custom markers
    config.addinivalue_line("markers", "unit: Unit tests with no external dependencies")
    config.addinivalue_line(
        "markers", "integration: Integration tests with external services"
    )
    config.addinivalue_line("markers", "e2e: End-to-end tests with full system")
    config.addinivalue_line("markers", "load: Load and performance tests")
    config.addinivalue_line("markers", "security: Security-focused tests")
    config.addinivalue_line("markers", "slow: Slow-running tests (>30s)")
    config.addinivalue_line("markers", "network: Tests requiring network access")
    config.addinivalue_line("markers", "mcp: MCP server integration tests")
    config.addinivalue_line("markers", "llm: Tests requiring LLM API access")
    config.addinivalue_line("markers", "benchmark: Performance benchmark tests")
    config.addinivalue_line("markers", "isolation: Tests requiring complete isolation")


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Modify test collection to add automatic markers."""
    for item in items:
        # Auto-mark slow tests
        if "slow" in item.nodeid.lower() or getattr(
            getattr(item, "function", None), "_slow_test", False
        ):
            item.add_marker(pytest.mark.slow)

        # Auto-mark network tests
        if "network" in item.nodeid.lower() or "http" in item.nodeid.lower():
            item.add_marker(pytest.mark.network)

        # Auto-mark integration tests based on path
        if "integration" in str(item.fspath) or item.get_closest_marker("integration"):
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="function")
def no_requests() -> Generator[None, None, None]:
    """Prevent real HTTP requests during unit tests.

    Raises an error if code tries to make real HTTP requests.
    Useful for ensuring unit tests don't have external dependencies.
    """

    def mock_request(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError(
            "Real HTTP requests are not allowed in unit tests. "
            "Use mocks or mark the test with @pytest.mark.network"
        )

    with (
        patch("requests.request", mock_request),
        patch("urllib.request.urlopen", mock_request),
        patch("http.client.HTTPConnection.request", mock_request),
        patch("http.client.HTTPSConnection.request", mock_request),
    ):
        yield
