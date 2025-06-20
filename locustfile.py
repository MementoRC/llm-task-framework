"""
Locust load testing configuration for LLM Task Framework.

This file provides comprehensive load testing for:
1. MCP server endpoints (simulated)
2. CLI functionality
3. Core framework functionality
4. Concurrent operations

This locustfile is designed to be run headlessly in a CI/CD environment.
Configuration (users, spawn rate, etc.) is controlled by the CI workflow,
which uses `scripts/load_test_config.py`.

Usage in CI (example):
    locust -f locustfile.py --headless \\
           --users 10 --spawn-rate 2 --run-time 60s \\
           --json report.json --html report.html

Environment Variables:
    MCP_SERVER_HOST: Host for MCP server testing (default: localhost)
    MCP_SERVER_PORT: Port for MCP server testing (default: 8080)
"""

import json
import os
import subprocess  # nosec B404
import tempfile
import time
from typing import Any

from locust import (
    TaskSet,
    User,
    between,
    events,
    task,
)
from locust.env import Environment


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
            # Using pixi to ensure correct environment
            result: subprocess.CompletedProcess[str] = subprocess.run(
                ["pixi", "run", "ltf", "--help"],
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
            result: subprocess.CompletedProcess[str] = subprocess.run(
                [
                    "pixi",
                    "run",
                    "python",
                    "-c",
                    "import llm_task_framework; print('OK')",
                ],
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

            result: subprocess.CompletedProcess[str] = subprocess.run(
                ["pixi", "run", "python", "-c", validation_script],  # nosec B603 B607
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

            result: subprocess.CompletedProcess[str] = subprocess.run(
                ["pixi", "run", "python", "-c", mcp_test_script],  # nosec B603 B607
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
        ["pixi", "run", "python", "-c", "import llm_task_framework; print('IMPORT_OK')"],
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

            result: subprocess.CompletedProcess[str] = subprocess.run(
                ["pixi", "run", "python", "-c", concurrent_script],  # nosec B603 B607
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


class LLMTaskFrameworkUser(User):
    """
    Load test user for LLM Task Framework.

    Simulates realistic usage patterns including CLI operations,
    framework initialization, and MCP server interactions.
    Since tasks are not HTTP-based, this inherits from locust.User.
    """

    # Task sets to execute (weighted distribution)
    tasks = [
        (FrameworkTaskSet, 5),  # 50% - Core framework operations
        (MCPServerTaskSet, 3),  # 30% - MCP server operations
        (ConcurrentOperationsTaskSet, 2),  # 20% - Concurrent operations
    ]

    # Wait time between tasks
    wait_time = between(1.0, 5.0)

    def on_start(self) -> None:
        """Called when a user starts."""
        print("Starting load test user...")

    def on_stop(self) -> None:
        """Called when a user stops."""
        print("Stopping load test user.")


# Event listeners for custom metrics and reporting
@events.init.add_listener
def on_locust_init(environment: Environment, **kwargs: Any) -> None:  # noqa: ARG001
    """Initialize custom metrics and reporting."""
    print("🚀 LLM Task Framework Load Testing Started")
    if environment.web_ui:
        print(
            f"Web UI running at http://{environment.web_ui.host}:{environment.web_ui.port}"
        )
    else:
        print("Running in headless mode.")


@events.test_stop.add_listener
def on_test_stop(environment: Environment, **kwargs: Any) -> None:  # noqa: ARG001
    """Generate performance summary report in console."""
    print("\n" + "=" * 60)
    print("🏁 Load Testing Complete - Performance Summary")
    print("=" * 60)

    if hasattr(environment.stats, "total"):
        stats = environment.stats.total
        print(f"📊 Total Requests: {stats.num_requests}")
        print(f"⏱️  Average Response Time: {stats.avg_response_time:.2f}ms")
        print(f"#️⃣  Median Response Time: {stats.median_response_time}ms")
        print(f"📈 Requests/s: {stats.total_rps:.2f}")
        print(f"❌ Failure Rate: {stats.fail_ratio:.2%}")

        # Performance thresholds check
        if stats.avg_response_time > 5000:
            print("⚠️  WARNING: High average response time detected (>5000ms)")
        if stats.fail_ratio > 0.05:
            print("⚠️  WARNING: High failure rate detected (>5%)")
        if stats.avg_response_time <= 1000 and stats.fail_ratio <= 0.01:
            print("✅ EXCELLENT: Performance within optimal thresholds.")

    print("=" * 60)
