"""WebSocket integration tests for the LLM Task Framework.

Tests WebSocket echo server container integration with proper fallback strategies.
Based on patterns from Redis integration and candles-feed/hb-strategy-sandbox projects.
"""

import asyncio
import contextlib
import os
import time
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import patch

import pytest

# Try to import websockets, but gracefully handle if not available
try:
    import websockets
    from websockets.exceptions import ConnectionClosed, WebSocketException

    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    websockets = None  # type: ignore[assignment]
    ConnectionClosed = Exception  # type: ignore[misc,assignment]
    WebSocketException = Exception  # type: ignore[misc,assignment]


@pytest.fixture(scope="function")
async def websocket_client() -> AsyncGenerator[Any, None]:
    """Provide a WebSocket client for testing.

    Returns None if WebSocket library is not available or connection fails.
    This allows tests to gracefully skip when WebSocket service is unavailable.
    """
    if not WEBSOCKETS_AVAILABLE:
        yield None
        return

    websocket_url = os.getenv("WEBSOCKET_URL", "ws://localhost:8080")
    test_with_services = os.getenv("TEST_WITH_SERVICES", "false").lower() == "true"

    if not test_with_services:
        yield None
        return

    client = None
    try:
        # Test connection with timeout
        client = await asyncio.wait_for(websockets.connect(websocket_url), timeout=5.0)
        yield client
    except (OSError, asyncio.TimeoutError, WebSocketException) as e:
        pytest.skip(f"WebSocket connection failed: {e}")
    finally:
        if client:
            with contextlib.suppress(Exception):
                await client.close()


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
async def test_websocket_connection(websocket_client):
    """Test basic WebSocket connection and ping."""
    if not WEBSOCKETS_AVAILABLE:
        pytest.skip("WebSocket library not available")

    if websocket_client is None:
        pytest.skip("WebSocket client not available")

    # Test ping/pong
    await websocket_client.ping()

    # Test basic connectivity
    assert websocket_client.open
    assert websocket_client.closed is False


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
async def test_websocket_echo_basic(websocket_client):
    """Test basic WebSocket echo functionality."""
    if not WEBSOCKETS_AVAILABLE:
        pytest.skip("WebSocket library not available")

    if websocket_client is None:
        pytest.skip("WebSocket client not available")

    # Test simple message echo
    test_message = "Hello WebSocket Echo Server!"

    await websocket_client.send(test_message)
    response = await asyncio.wait_for(websocket_client.recv(), timeout=5.0)

    assert response == test_message


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
async def test_websocket_echo_json(websocket_client):
    """Test WebSocket echo with JSON messages."""
    if not WEBSOCKETS_AVAILABLE:
        pytest.skip("WebSocket library not available")

    if websocket_client is None:
        pytest.skip("WebSocket client not available")

    import json

    # Test JSON message echo
    test_data = {
        "type": "test",
        "message": "Hello from JSON!",
        "timestamp": time.time(),
        "data": {"nested": "value", "number": 42},
    }

    json_message = json.dumps(test_data)
    await websocket_client.send(json_message)
    response = await asyncio.wait_for(websocket_client.recv(), timeout=5.0)

    # Verify the echo response
    assert response == json_message

    # Verify we can parse it back
    parsed_response = json.loads(response)
    assert parsed_response == test_data


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
async def test_websocket_echo_binary(websocket_client):
    """Test WebSocket echo with binary messages."""
    if not WEBSOCKETS_AVAILABLE:
        pytest.skip("WebSocket library not available")

    if websocket_client is None:
        pytest.skip("WebSocket client not available")

    # Test binary message echo
    test_binary = b"Binary data: \x00\x01\x02\x03\xff"

    await websocket_client.send(test_binary)
    response = await asyncio.wait_for(websocket_client.recv(), timeout=5.0)

    assert response == test_binary


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
async def test_websocket_multiple_messages(websocket_client):
    """Test multiple consecutive WebSocket messages."""
    if not WEBSOCKETS_AVAILABLE:
        pytest.skip("WebSocket library not available")

    if websocket_client is None:
        pytest.skip("WebSocket client not available")

    # Test multiple messages in sequence
    messages = [
        "Message 1",
        "Message 2",
        "Message 3",
        '{"type": "json", "id": 4}',
        b"Binary message 5",
    ]

    responses = []
    for message in messages:
        await websocket_client.send(message)
        response = await asyncio.wait_for(websocket_client.recv(), timeout=5.0)
        responses.append(response)

    # Verify all messages were echoed correctly
    assert len(responses) == len(messages)
    for original, echoed in zip(messages, responses, strict=False):
        assert echoed == original


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
async def test_websocket_large_message(websocket_client):
    """Test WebSocket echo with large messages."""
    if not WEBSOCKETS_AVAILABLE:
        pytest.skip("WebSocket library not available")

    if websocket_client is None:
        pytest.skip("WebSocket client not available")

    # Test large message (1MB)
    large_message = "A" * (1024 * 1024)

    await websocket_client.send(large_message)
    response = await asyncio.wait_for(websocket_client.recv(), timeout=10.0)

    assert response == large_message
    assert len(response) == 1024 * 1024


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
async def test_websocket_concurrent_connections():
    """Test multiple concurrent WebSocket connections."""
    if not WEBSOCKETS_AVAILABLE:
        pytest.skip("WebSocket library not available")

    websocket_url = os.getenv("WEBSOCKET_URL", "ws://localhost:8080")
    test_with_services = os.getenv("TEST_WITH_SERVICES", "false").lower() == "true"

    if not test_with_services:
        pytest.skip("Service container testing disabled")

    async def send_and_receive(client_id: int) -> bool:
        """Helper to test a single connection."""
        try:
            async with websockets.connect(websocket_url) as websocket:
                message = f"Client {client_id} test message"
                await websocket.send(message)
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                return response == message
        except Exception as e:
            pytest.skip(f"WebSocket connection failed for client {client_id}: {e}")
            return False

    # Test 5 concurrent connections
    tasks = [send_and_receive(i) for i in range(5)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Verify all connections succeeded
    successful = [r for r in results if r is True]
    assert len(successful) == 5, (
        f"Expected 5 successful connections, got {len(successful)}"
    )


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
async def test_websocket_connection_resilience():
    """Test WebSocket connection handling and reconnection scenarios."""
    if not WEBSOCKETS_AVAILABLE:
        pytest.skip("WebSocket library not available")

    websocket_url = os.getenv("WEBSOCKET_URL", "ws://localhost:8080")
    test_with_services = os.getenv("TEST_WITH_SERVICES", "false").lower() == "true"

    if not test_with_services:
        pytest.skip("Service container testing disabled")

    try:
        # Test connection, close, and reconnection
        async with websockets.connect(websocket_url) as websocket1:
            await websocket1.send("Connection 1")
            response1 = await websocket1.recv()
            assert response1 == "Connection 1"

        # Connection 1 is now closed, test new connection
        async with websockets.connect(websocket_url) as websocket2:
            await websocket2.send("Connection 2")
            response2 = await websocket2.recv()
            assert response2 == "Connection 2"

    except (OSError, asyncio.TimeoutError, WebSocketException) as e:
        pytest.skip(f"WebSocket connection failed: {e}")


@pytest.mark.integration
async def test_websocket_fallback_when_unavailable():
    """Test graceful fallback when WebSocket service is unavailable."""

    # Mock WebSocket to raise connection error
    with patch("websockets.connect") as mock_connect:
        mock_connect.side_effect = OSError("Connection refused")

        # This should be handled gracefully by the fixture
        websocket_url = os.getenv("WEBSOCKET_URL", "ws://localhost:8080")
        test_with_services = os.getenv("TEST_WITH_SERVICES", "false").lower() == "true"

        if not test_with_services:
            pytest.skip("Service container testing disabled")

        # Test that the test skips gracefully rather than failing
        try:
            async with websockets.connect(websocket_url) as websocket:
                await websocket.send("test")
        except OSError:
            # Expected behavior - connection should fail and test should handle it
            pass


@pytest.mark.integration
def test_websocket_error_handling():
    """Test proper error handling for WebSocket operations."""
    if not WEBSOCKETS_AVAILABLE:
        pytest.skip("WebSocket library not available")

    # Test with invalid WebSocket URL
    async def test_invalid_connection():
        with pytest.raises(OSError):
            invalid_url = "ws://invalid-host:9999"
            await asyncio.wait_for(websockets.connect(invalid_url), timeout=1.0)

    # Run the async test
    asyncio.run(test_invalid_connection())


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
async def test_websocket_performance_basic(websocket_client):
    """Test basic WebSocket performance characteristics."""
    if not WEBSOCKETS_AVAILABLE:
        pytest.skip("WebSocket library not available")

    if websocket_client is None:
        pytest.skip("WebSocket client not available")

    # Test message throughput
    num_messages = 100
    message = "Performance test message"

    start_time = time.time()

    # Send and receive messages
    for i in range(num_messages):
        await websocket_client.send(f"{message} {i}")
        response = await asyncio.wait_for(websocket_client.recv(), timeout=5.0)
        assert response == f"{message} {i}"

    elapsed_time = time.time() - start_time

    # Basic performance assertions (adjust thresholds as needed)
    messages_per_second = num_messages / elapsed_time
    assert messages_per_second > 10, (
        f"Performance too slow: {messages_per_second:.2f} msg/s"
    )
    assert elapsed_time < 30.0, f"Total time too slow: {elapsed_time:.2f}s"
