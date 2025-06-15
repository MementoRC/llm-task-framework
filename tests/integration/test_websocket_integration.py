"""WebSocket integration tests for the LLM Task Framework.

Tests WebSocket echo server container integration with proper fallback strategies.
Based on patterns from Redis integration and candles-feed/hb-strategy-sandbox projects.
"""

import asyncio
import os
import time
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import patch

import pytest

# Try to import websockets, but gracefully handle if not available
try:
    import websockets
    from websockets.client import WebSocketClientProtocol
    from websockets.exceptions import WebSocketException

    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    websockets = None
    WebSocketClientProtocol = Any
    ConnectionClosed = Exception
    WebSocketException = Exception


@pytest.fixture(scope="function")
async def websocket_client() -> AsyncGenerator[WebSocketClientProtocol | None, None]:
    """Provide a WebSocket client for testing.

    Skips tests if WebSocket library is not available or connection fails.
    """
    if not WEBSOCKETS_AVAILABLE:
        pytest.skip("websockets library not available")

    websocket_url = os.getenv("WEBSOCKET_URL", "ws://localhost:8080")
    test_with_services = os.getenv("TEST_WITH_SERVICES", "false").lower() == "true"

    if not test_with_services:
        pytest.skip(
            "Service container testing disabled (TEST_WITH_SERVICES is not 'true')"
        )

    client: WebSocketClientProtocol | None = None
    last_exception = None
    attempt = 0
    while attempt < 3:
        try:
            # Use a longer timeout for CI environments
            connect_coro = websockets.connect(websocket_url, open_timeout=10)
            client = await asyncio.wait_for(connect_coro, timeout=10.0)

            # Perform a quick ping-pong to ensure the connection is responsive
            pong_waiter = await client.ping()
            await asyncio.wait_for(pong_waiter, timeout=5.0)

            # If we got here, connection is good
            break
        except (OSError, asyncio.TimeoutError, WebSocketException) as e:
            last_exception = e
            if client:
                await client.close()
            client = None
            attempt += 1
            if attempt < 3:
                await asyncio.sleep(2 * attempt)  # Exponential backoff

    if not client:
        pytest.skip(f"WebSocket connection failed after 3 retries: {last_exception}")

    try:
        yield client
    finally:
        if client:
            try:
                await client.close()
            except Exception as e:
                print(f"Error closing WebSocket: {e}")


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
async def test_websocket_connection(websocket_client: WebSocketClientProtocol):
    """Test basic WebSocket connection and ping."""
    # Test ping/pong
    await websocket_client.ping()

    # Test basic connectivity
    assert websocket_client.closed is False


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
async def test_websocket_echo_basic(websocket_client: WebSocketClientProtocol):
    """Test basic WebSocket echo functionality."""
    # Test simple message echo
    test_message = "Hello WebSocket Echo Server!"

    await websocket_client.send(test_message)
    response = await asyncio.wait_for(websocket_client.recv(), timeout=5.0)

    assert response == test_message


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
async def test_websocket_echo_json(websocket_client: WebSocketClientProtocol):
    """Test WebSocket echo with JSON messages."""
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
async def test_websocket_echo_binary(websocket_client: WebSocketClientProtocol):
    """Test WebSocket echo with binary messages."""
    # Test binary message echo
    test_binary = b"Binary data: \x00\x01\x02\x03\xff"

    await websocket_client.send(test_binary)
    response = await asyncio.wait_for(websocket_client.recv(), timeout=5.0)

    assert response == test_binary


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
async def test_websocket_multiple_messages(websocket_client: WebSocketClientProtocol):
    """Test multiple consecutive WebSocket messages."""
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
async def test_websocket_large_message(websocket_client: WebSocketClientProtocol):
    """Test WebSocket echo with large messages."""
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
async def test_websocket_performance_basic(websocket_client: WebSocketClientProtocol):
    """Test basic WebSocket performance characteristics."""
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
