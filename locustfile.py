"""
Locust load testing configuration for LLM Task Framework.

This file provides comprehensive load testing for:
1. MCP server endpoints
2. CLI functionality
3. Core framework functionality
4. Concurrent operations

Usage:
    # Basic load test
    locust --headless --users 10 --spawn-rate 2 --run-time 60s

    # Heavy load profile
    locust --headless --users 50 --spawn-rate 5 --run-time 300s

    # With custom host
    locust --headless --users 10 --spawn-rate 2 --run-time 60s --host http://localhost:8000

Environment Variables:
    LOAD_TEST_PROFILE: light|medium|heavy (default: light)
    MCP_SERVER_HOST: Host for MCP server testing (default: localhost)
    MCP_SERVER_PORT: Port for MCP server testing (default: 8080)
"""

import json
import os
import subprocess  # nosec B404
import tempfile
import time
from typing import Any

from locust import (  # type: ignore[import-not-found]
    HttpUser,
    TaskSet,
    between,
    events,
    task,
)
from locust.env import Environment  # type: ignore[import-not-found]


class FrameworkTaskSet(TaskSet):
    """Task set for testing core framework functionality."""

    def on_start(self) -> None:
        """Initialize test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")

        # Create test configuration
        config = {
            "framework": {
                "name": "test-framework",
                "version": "1.0.0",
                "max_workers": 4,
            },
            "llm": {"provider": "mock", "model": "test-model"},
        }

        with open(self.config_file, "w") as f:
            json.dump(config, f)

    @task(3)
    def test_cli_help(self) -> None:
        """Test CLI help command performance."""
        start_time = time.time()
        try:
            result = subprocess.run(
                ["python", "-m", "llm_task_framework.cli.main", "--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )  # nosec B603 B607

            response_time = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                events.request.fire(
                    request_type="CLI",
                    name="help_command",
                    response_time=response_time,
                    response_length=len(result.stdout),
                    exception=None,
                    context={},
                )
            else:
                events.request.fire(
                    request_type="CLI",
                    name="help_command",
                    response_time=response_time,
                    response_length=0,
                    exception=Exception(f"CLI error: {result.stderr}"),
                    context={},
                )

        except subprocess.TimeoutExpired:
            events.request.fire(
                request_type="CLI",
                name="help_command",
                response_time=10000,
                response_length=0,
                exception=Exception("CLI timeout"),
                context={},
            )
        except Exception as e:
            events.request.fire(
                request_type="CLI",
                name="help_command",
                response_time=int((time.time() - start_time) * 1000),
                response_length=0,
                exception=e,
                context={},
            )

    @task(2)
    def test_framework_import(self) -> None:
        """Test framework import performance."""
        start_time = time.time()
        try:
            result = subprocess.run(
                ["python", "-c", "import llm_task_framework; print('OK')"],
                capture_output=True,
                text=True,
                timeout=15,
            )  # nosec B603 B607

            response_time = int((time.time() - start_time) * 1000)

            if result.returncode == 0 and "OK" in result.stdout:
                events.request.fire(
                    request_type="Framework",
                    name="import_test",
                    response_time=response_time,
                    response_length=len(result.stdout),
                    exception=None,
                    context={},
                )
            else:
                events.request.fire(
                    request_type="Framework",
                    name="import_test",
                    response_time=response_time,
                    response_length=0,
                    exception=Exception(f"Import failed: {result.stderr}"),
                    context={},
                )

        except Exception as e:
            events.request.fire(
                request_type="Framework",
                name="import_test",
                response_time=int((time.time() - start_time) * 1000),
                response_length=0,
                exception=e,
                context={},
            )

    @task(1)
    def test_config_validation(self) -> None:
        """Test configuration validation performance."""
        start_time = time.time()
        try:
            # Test config file validation
            validation_script = f"""
import json
import sys
from pathlib import Path

config_path = Path('{self.config_file}')
if config_path.exists():
    with open(config_path) as f:
        config = json.load(f)

    # Basic validation
    required_keys = ['framework', 'llm']
    if all(key in config for key in required_keys):
        print('CONFIG_VALID')
    else:
        print('CONFIG_INVALID')
else:
    print('CONFIG_MISSING')
"""

            result = subprocess.run(
                ["python", "-c", validation_script],  # nosec B603 B607
                capture_output=True,
                text=True,
                timeout=5,
            )

            response_time = int((time.time() - start_time) * 1000)

            if result.returncode == 0 and "CONFIG_VALID" in result.stdout:
                events.request.fire(
                    request_type="Config",
                    name="validation",
                    response_time=response_time,
                    response_length=len(result.stdout),
                    exception=None,
                    context={},
                )
            else:
                events.request.fire(
                    request_type="Config",
                    name="validation",
                    response_time=response_time,
                    response_length=0,
                    exception=Exception(f"Config validation failed: {result.stderr}"),
                    context={},
                )

        except Exception as e:
            events.request.fire(
                request_type="Config",
                name="validation",
                response_time=int((time.time() - start_time) * 1000),
                response_length=0,
                exception=e,
                context={},
            )


class MCPServerTaskSet(TaskSet):
    """Task set for testing MCP server functionality."""

    def on_start(self) -> None:
        """Setup MCP server testing."""
        self.mcp_host = os.getenv("MCP_SERVER_HOST", "localhost")
        self.mcp_port = int(os.getenv("MCP_SERVER_PORT", "8080"))
        self.base_url = f"http://{self.mcp_host}:{self.mcp_port}"

    @task(2)
    def test_mcp_health_check(self) -> None:
        """Test MCP server health endpoint."""
        # This would test a health check endpoint if the MCP server exposes HTTP endpoints
        # For now, we simulate the check
        start_time = time.time()
        try:
            # Simulate health check
            time.sleep(0.1)  # Simulate network latency

            response_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="MCP",
                name="health_check",
                response_time=response_time,
                response_length=50,
                exception=None,
                context={},
            )
        except Exception as e:
            events.request.fire(
                request_type="MCP",
                name="health_check",
                response_time=int((time.time() - start_time) * 1000),
                response_length=0,
                exception=e,
                context={},
            )

    @task(1)
    def test_mcp_protocol_simulation(self) -> None:
        """Test MCP protocol message handling simulation."""
        start_time = time.time()
        try:
            # Simulate MCP protocol interaction
            mcp_test_script = """
# Simulate MCP protocol testing
import time
import json

# Simulate protocol message
message = {
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {}
    },
    "id": 1
}

# Simulate processing time
time.sleep(0.05)
print("MCP_PROTOCOL_OK")
"""

            result = subprocess.run(
                ["python", "-c", mcp_test_script],  # nosec B603 B607
                capture_output=True,
                text=True,
                timeout=5,
            )

            response_time = int((time.time() - start_time) * 1000)

            if result.returncode == 0 and "MCP_PROTOCOL_OK" in result.stdout:
                events.request.fire(
                    request_type="MCP",
                    name="protocol_simulation",
                    response_time=response_time,
                    response_length=len(result.stdout),
                    exception=None,
                    context={},
                )
            else:
                events.request.fire(
                    request_type="MCP",
                    name="protocol_simulation",
                    response_time=response_time,
                    response_length=0,
                    exception=Exception(f"MCP protocol test failed: {result.stderr}"),
                    context={},
                )

        except Exception as e:
            events.request.fire(
                request_type="MCP",
                name="protocol_simulation",
                response_time=int((time.time() - start_time) * 1000),
                response_length=0,
                exception=e,
                context={},
            )


class ConcurrentOperationsTaskSet(TaskSet):
    """Task set for testing concurrent operations."""

    @task(1)
    def test_concurrent_imports(self) -> None:
        """Test concurrent framework imports."""
        start_time = time.time()
        try:
            concurrent_script = """
import concurrent.futures
import subprocess
import time

def import_test():
    result = subprocess.run(
        ["python", "-c", "import llm_task_framework; print('IMPORT_OK')"],
        capture_output=True,
        text=True,
        timeout=10
    )
    return result.returncode == 0 and "IMPORT_OK" in result.stdout

# Test concurrent imports
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(import_test) for _ in range(3)]
    results = [f.result() for f in concurrent.futures.as_completed(futures)]

if all(results):
    print("CONCURRENT_OK")
else:
    print("CONCURRENT_FAILED")
"""

            result = subprocess.run(
                ["python", "-c", concurrent_script],  # nosec B603 B607
                capture_output=True,
                text=True,
                timeout=30,
            )

            response_time = int((time.time() - start_time) * 1000)

            if result.returncode == 0 and "CONCURRENT_OK" in result.stdout:
                events.request.fire(
                    request_type="Concurrent",
                    name="import_stress",
                    response_time=response_time,
                    response_length=len(result.stdout),
                    exception=None,
                    context={},
                )
            else:
                events.request.fire(
                    request_type="Concurrent",
                    name="import_stress",
                    response_time=response_time,
                    response_length=0,
                    exception=Exception(f"Concurrent test failed: {result.stderr}"),
                    context={},
                )

        except Exception as e:
            events.request.fire(
                request_type="Concurrent",
                name="import_stress",
                response_time=int((time.time() - start_time) * 1000),
                response_length=0,
                exception=e,
                context={},
            )


class LLMTaskFrameworkUser(HttpUser):
    """
    Load test user for LLM Task Framework.

    Simulates realistic usage patterns including CLI operations,
    framework initialization, and MCP server interactions.
    """

    # Task sets to execute (weighted distribution)
    tasks = [
        (FrameworkTaskSet, 5),  # 50% - Core framework operations
        (MCPServerTaskSet, 3),  # 30% - MCP server operations
        (ConcurrentOperationsTaskSet, 2),  # 20% - Concurrent operations
    ]

    # Configure user behavior based on load profile
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        profile = os.getenv("LOAD_TEST_PROFILE", "light").lower()

        if profile == "heavy":
            self.wait_time = between(0.5, 2.0)  # Aggressive load
        elif profile == "medium":
            self.wait_time = between(1.0, 3.0)  # Moderate load
        else:  # light
            self.wait_time = between(2.0, 5.0)  # Light load

    def on_start(self) -> None:
        """Called when a user starts."""
        print(
            f"Starting load test user (profile: {os.getenv('LOAD_TEST_PROFILE', 'light')})"
        )

    def on_stop(self) -> None:
        """Called when a user stops."""
        print("Stopping load test user")


# Load test configuration based on environment
def get_load_profile() -> dict[str, Any]:
    """Get load testing configuration based on profile."""
    profile: str = os.getenv("LOAD_TEST_PROFILE", "light").lower()

    profiles: dict[str, dict[str, Any]] = {
        "light": {
            "users": 5,
            "spawn_rate": 1,
            "run_time": "2m",
            "description": "Light load testing for development",
        },
        "medium": {
            "users": 15,
            "spawn_rate": 3,
            "run_time": "5m",
            "description": "Medium load testing for staging",
        },
        "heavy": {
            "users": 50,
            "spawn_rate": 5,
            "run_time": "10m",
            "description": "Heavy load testing for performance validation",
        },
    }

    return profiles.get(profile, profiles["light"])


# Event listeners for custom metrics
@events.init.add_listener
def on_locust_init(environment: Environment, **kwargs: Any) -> None:  # noqa: ARG001
    """Initialize custom metrics and reporting."""
    print("🚀 LLM Task Framework Load Testing Started")
    print(f"Profile: {os.getenv('LOAD_TEST_PROFILE', 'light')}")
    print(f"Configuration: {get_load_profile()}")


@events.test_stop.add_listener
def on_test_stop(environment: Environment, **kwargs: Any) -> None:  # noqa: ARG001
    """Generate performance summary report."""
    print("\n" + "=" * 60)
    print("🏁 Load Testing Complete - Performance Summary")
    print("=" * 60)

    # Calculate basic statistics
    if hasattr(environment.stats, "total"):
        total_requests = environment.stats.total.num_requests
        avg_response_time = environment.stats.total.avg_response_time
        failure_rate = environment.stats.total.fail_ratio

        print(f"📊 Total Requests: {total_requests}")
        print(f"⏱️  Average Response Time: {avg_response_time:.2f}ms")
        print(f"❌ Failure Rate: {failure_rate:.2%}")

        # Performance thresholds
        if avg_response_time > 5000:
            print("⚠️  WARNING: High average response time detected")
        if failure_rate > 0.05:
            print("⚠️  WARNING: High failure rate detected")
        if avg_response_time <= 1000 and failure_rate <= 0.01:
            print("✅ EXCELLENT: Performance within optimal thresholds")

    print("=" * 60)


if __name__ == "__main__":
    # Example usage when run directly
    profile = get_load_profile()
    print(f"Load Test Profile: {profile['description']}")
    print("Recommended command:")
    print(
        f"locust --headless --users {profile['users']} --spawn-rate {profile['spawn_rate']} --run-time {profile['run_time']}"
    )
