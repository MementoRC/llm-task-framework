"""
Spike Testing Scenarios for LLM Task Framework.

Simulates sudden, sharp increases in load.
"""

import subprocess
import time

from locust import TaskSet, events, task


class SpikeTestingTaskSet(TaskSet):
    """
    Spike test: Simulate sudden load spikes on CLI and framework.
    """

    @task(3)
    def spike_cli_help(self) -> None:
        """Burst of CLI help calls."""
        start = time.time()
        try:
            for _ in range(10):  # Simulate a spike
                result = subprocess.run(  # nosec
                    ["pixi", "run", "ltf", "--help"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
            response_time = int((time.time() - start) * 1000)
            events.request.fire(
                request_type="CLI",
                name="spike_help_burst",
                response_time=response_time,
                response_length=len(result.stdout),
                exception=None if result.returncode == 0 else Exception(result.stderr),
                context={},
            )
        except Exception as e:
            events.request.fire(
                request_type="CLI",
                name="spike_help_burst",
                response_time=int((time.time() - start) * 1000),
                response_length=0,
                exception=e,
                context={},
            )

    @task(2)
    def spike_framework_import(self) -> None:
        """Burst of framework imports."""
        start = time.time()
        try:
            for _ in range(10):
                result = subprocess.run(  # nosec
                    ["pixi", "run", "python", "-c", "import llm_task_framework"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
            response_time = int((time.time() - start) * 1000)
            events.request.fire(
                request_type="Framework",
                name="spike_import_burst",
                response_time=response_time,
                response_length=len(result.stdout),
                exception=None if result.returncode == 0 else Exception(result.stderr),
                context={},
            )
        except Exception as e:
            events.request.fire(
                request_type="Framework",
                name="spike_import_burst",
                response_time=int((time.time() - start) * 1000),
                response_length=0,
                exception=e,
                context={},
            )

    @task(1)
    def spike_concurrent(self) -> None:
        """Spike of concurrent operations."""
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
        timeout=5
    )
    return result.returncode == 0
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(lambda _: import_test(), range(10)))
if all(results):
    print("SPIKE_CONCURRENT_OK")
else:
    print("SPIKE_CONCURRENT_FAIL")
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
                name="spike_concurrent",
                response_time=response_time,
                response_length=len(result.stdout),
                exception=None
                if result.returncode == 0 and "SPIKE_CONCURRENT_OK" in result.stdout
                else Exception(result.stderr),
                context={},
            )
        except Exception as e:
            events.request.fire(
                request_type="Concurrent",
                name="spike_concurrent",
                response_time=int((time.time() - start) * 1000),
                response_length=0,
                exception=e,
                context={},
            )
