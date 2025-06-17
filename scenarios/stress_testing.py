"""
Stress Testing Scenarios for LLM Task Framework.

Simulates extreme load and resource exhaustion.
"""

import json
import os
import subprocess
import tempfile
import time

from locust import TaskSet, events, task


class StressTestingTaskSet(TaskSet):
    """
    Stress test: CPU/memory intensive operations, rapid CLI and import calls.
    """

    def on_start(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.large_config_file = os.path.join(self.temp_dir, "large_config.json")
        # Create a large config file to stress config parsing
        config = {
            "framework": {
                "name": "stress-framework",
                "version": "1.0.0",
                "max_workers": 32,
                "extra": ["x" * 1000] * 1000,
            },
            "llm": {"provider": "mock", "model": "stress-model"},
            "data": ["data" * 1000] * 1000,
        }
        with open(self.large_config_file, "w") as f:
            json.dump(config, f)

    @task(3)
    def stress_cli_help(self) -> None:
        """Rapid CLI help calls under stress."""
        start = time.time()
        try:
            result = subprocess.run(  # nosec
                ["pixi", "run", "ltf", "--help"],
                capture_output=True,
                text=True,
                timeout=8,
            )
            response_time = int((time.time() - start) * 1000)
            events.request.fire(
                request_type="CLI",
                name="stress_help",
                response_time=response_time,
                response_length=len(result.stdout),
                exception=None if result.returncode == 0 else Exception(result.stderr),
                context={},
            )
        except Exception as e:
            events.request.fire(
                request_type="CLI",
                name="stress_help",
                response_time=int((time.time() - start) * 1000),
                response_length=0,
                exception=e,
                context={},
            )

    @task(2)
    def stress_framework_import(self) -> None:
        """Rapid framework import under stress."""
        start = time.time()
        try:
            result = subprocess.run(  # nosec
                ["pixi", "run", "python", "-c", "import llm_task_framework"],
                capture_output=True,
                text=True,
                timeout=8,
            )
            response_time = int((time.time() - start) * 1000)
            events.request.fire(
                request_type="Framework",
                name="stress_import",
                response_time=response_time,
                response_length=len(result.stdout),
                exception=None if result.returncode == 0 else Exception(result.stderr),
                context={},
            )
        except Exception as e:
            events.request.fire(
                request_type="Framework",
                name="stress_import",
                response_time=int((time.time() - start) * 1000),
                response_length=0,
                exception=e,
                context={},
            )

    @task(2)
    def stress_config_parsing(self) -> None:
        """Parse large config file to stress memory/CPU."""
        start = time.time()
        try:
            script = f"""
import json
with open('{self.large_config_file}') as f:
    config = json.load(f)
print('LARGE_CONFIG_OK')
"""
            result = subprocess.run(  # nosec
                ["pixi", "run", "python", "-c", script],
                capture_output=True,
                text=True,
                timeout=10,
            )
            response_time = int((time.time() - start) * 1000)
            events.request.fire(
                request_type="Config",
                name="stress_large_config",
                response_time=response_time,
                response_length=len(result.stdout),
                exception=None
                if result.returncode == 0 and "LARGE_CONFIG_OK" in result.stdout
                else Exception(result.stderr),
                context={},
            )
        except Exception as e:
            events.request.fire(
                request_type="Config",
                name="stress_large_config",
                response_time=int((time.time() - start) * 1000),
                response_length=0,
                exception=e,
                context={},
            )

    @task(1)
    def stress_concurrent_imports(self) -> None:
        """Concurrent imports to stress system."""
        start = time.time()
        try:
            script = """
import concurrent.futures
import subprocess
def import_test():
    result = subprocess.run(
        ["pixi", "run", "python", "-c", "import llm_task_framework"],
        capture_output=True,
        text=True,
        timeout=8
    )
    return result.returncode == 0
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
    results = list(executor.map(lambda _: import_test(), range(8)))
if all(results):
    print("STRESS_CONCURRENT_OK")
else:
    print("STRESS_CONCURRENT_FAIL")
"""
            result = subprocess.run(  # nosec
                ["pixi", "run", "python", "-c", script],
                capture_output=True,
                text=True,
                timeout=20,
            )
            response_time = int((time.time() - start) * 1000)
            events.request.fire(
                request_type="Concurrent",
                name="stress_concurrent_imports",
                response_time=response_time,
                response_length=len(result.stdout),
                exception=None
                if result.returncode == 0 and "STRESS_CONCURRENT_OK" in result.stdout
                else Exception(result.stderr),
                context={},
            )
        except Exception as e:
            events.request.fire(
                request_type="Concurrent",
                name="stress_concurrent_imports",
                response_time=int((time.time() - start) * 1000),
                response_length=0,
                exception=e,
                context={},
            )
