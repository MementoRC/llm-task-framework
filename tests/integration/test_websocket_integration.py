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
    from websockets.exceptions import ConnectionClosed, WebSocketException
    from websockets.protocol import State

    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    websockets = None  # type: ignore[assignment]
    WebSocketClientProtocol = Any  # type: ignore[assignment]
    ConnectionClosed = Exception  # type: ignore[assignment]
    WebSocketException = Exception  # type: ignore[assignment]
    State = object()  # Dummy object for type checking and attribute access

# Use conservative parameters in CI to prevent timeouts
IS_CI = os.getenv("CI", "false").lower() == "true"


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
            # Use a shorter timeout to fail fast in CI
            connect_coro = websockets.connect(websocket_url, open_timeout=5)
            client = await asyncio.wait_for(connect_coro, timeout=5.0)

            # Perform a quick ping-pong to ensure the connection is responsive
            if client is not None:
                pong_waiter = await client.ping()
                await asyncio.wait_for(pong_waiter, timeout=3.0)

            # If we got here, connection is good
            break
        except (OSError, asyncio.TimeoutError, WebSocketException) as e:
            last_exception = e
            if client:
                await client.close()
            client = None
            attempt += 1
            if attempt < 3:
                await asyncio.sleep(1 * attempt)  # Exponential backoff

    if not client:
        pytest.skip(f"WebSocket connection failed after 3 retries: {last_exception}")

    try:
        yield client
    finally:
        if client and WEBSOCKETS_AVAILABLE:
            from contextlib import suppress

            # Only try to close if connection is still open
            if hasattr(client, "state") and client.state == State.OPEN:
                with suppress(ConnectionClosed, RuntimeError):
                    await client.close()
            elif not hasattr(client, "state"):
                # Fallback: try to close anyway, suppress errors
                with suppress(ConnectionClosed, RuntimeError, AttributeError):
                    await client.close()


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
async def test_websocket_connection(websocket_client: WebSocketClientProtocol):
    """Test basic WebSocket connection and ping."""
    # Test ping/pong
    await websocket_client.ping()

    # Test basic connectivity
    from websockets.protocol import State

    assert websocket_client.state == State.OPEN


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
async def test_websocket_echo_basic(websocket_client: WebSocketClientProtocol):
    """Test basic WebSocket echo functionality."""
    # Test simple message echo
    test_message = "Hello WebSocket Echo Server!"

    await websocket_client.send(test_message)
    response = await asyncio.wait_for(websocket_client.recv(), timeout=2.0)

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
    response = await asyncio.wait_for(websocket_client.recv(), timeout=2.0)

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
    response = await asyncio.wait_for(websocket_client.recv(), timeout=2.0)

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
        response = await asyncio.wait_for(websocket_client.recv(), timeout=2.0)
        responses.append(response)

    # Verify all messages were echoed correctly
    assert len(responses) == len(messages)
    for original, echoed in zip(messages, responses, strict=True):
        assert echoed == original


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
async def test_websocket_large_message(websocket_client: WebSocketClientProtocol):
    """Test WebSocket echo with large messages."""
    # Use a smaller message size in CI to avoid performance issues
    large_message_size = 64 * 1024 if IS_CI else 1024 * 1024
    timeout = 5.0 if IS_CI else 10.0
    large_message = "A" * large_message_size

    await websocket_client.send(large_message)
    response = await asyncio.wait_for(websocket_client.recv(), timeout=timeout)

    assert len(response) == large_message_size
    assert response == large_message


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
            async with websockets.connect(websocket_url, open_timeout=5) as websocket:
                message = f"Client {client_id} test message"
                await websocket.send(message)
                response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                return bool(response == message)
        except Exception:
            # Return False for connection failures - let the test handle it gracefully
            return False

    # Use fewer connections in CI to reduce load
    num_connections = 3 if IS_CI else 5
    tasks = [send_and_receive(i) for i in range(num_connections)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Verify all connections succeeded
    successful = [r for r in results if r is True]

    # If no connections succeeded, skip the test (service unavailable)
    if len(successful) == 0:
        pytest.skip("WebSocket service unavailable - all connections failed")

    assert len(successful) == num_connections, (
        f"Expected {num_connections} successful connections, got {len(successful)}"
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
        async with websockets.connect(websocket_url, open_timeout=5) as websocket1:
            await websocket1.send("Connection 1")
            response1 = await websocket1.recv()
            assert response1 == "Connection 1"

        # Connection 1 is now closed, test new connection
        async with websockets.connect(websocket_url, open_timeout=5) as websocket2:
            await websocket2.send("Connection 2")
            response2 = await websocket2.recv()
            assert response2 == "Connection 2"

    except (OSError, asyncio.TimeoutError, WebSocketException) as e:
        pytest.skip(f"WebSocket connection failed: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_websocket_fallback_when_unavailable():
    """Test graceful fallback when WebSocket service is unavailable."""
    if not WEBSOCKETS_AVAILABLE:
        pytest.skip("websockets library not available")

    # Mock WebSocket to raise connection error
    with patch("websockets.connect") as mock_connect:
        mock_connect.side_effect = OSError("Connection refused")

        websocket_url = "ws://localhost:9999"
        with pytest.raises(OSError):
            await asyncio.wait_for(websockets.connect(websocket_url), timeout=1.0)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_websocket_error_handling():
    """Test proper error handling for WebSocket operations."""
    if not WEBSOCKETS_AVAILABLE:
        pytest.skip("WebSocket library not available")

    # Test with invalid WebSocket URL
    with pytest.raises((OSError, asyncio.TimeoutError)):
        invalid_url = "ws://invalid-host:9999"
        await asyncio.wait_for(websockets.connect(invalid_url), timeout=1.0)


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
async def test_websocket_performance_basic(websocket_client: WebSocketClientProtocol):
    """Test basic WebSocket performance characteristics."""
    # Use fewer messages in CI to prevent timeouts
    num_messages = 10 if IS_CI else 100
    message = "Performance test message"

    start_time = time.time()

    # Send and receive messages
    for i in range(num_messages):
        await websocket_client.send(f"{message} {i}")
        response = await asyncio.wait_for(websocket_client.recv(), timeout=2.0)
        assert response == f"{message} {i}"

    elapsed_time = time.time() - start_time

    # Basic performance assertions (adjust thresholds for CI)
    messages_per_second = num_messages / elapsed_time
    min_msgs_per_sec = 5 if IS_CI else 10
    max_elapsed_time = 15.0 if IS_CI else 30.0

    assert messages_per_second > min_msgs_per_sec, (
        f"Performance too slow: {messages_per_second:.2f} msg/s (min: {min_msgs_per_sec})"
    )
    assert elapsed_time < max_elapsed_time, (
        f"Total time too slow: {elapsed_time:.2f}s (max: {max_elapsed_time}s)"
    )
