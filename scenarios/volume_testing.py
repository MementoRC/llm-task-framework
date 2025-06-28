"""
Volume Testing Scenarios for LLM Task Framework.

Simulates large-scale data and batch processing.
"""

import json
import os
import subprocess  # nosec B404
import tempfile
import time

from locust import TaskSet, events, task


class VolumeTestingTaskSet(TaskSet):
    """
    Volume test: Large dataset and batch processing scenarios.
    """

    def on_start(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.large_batch_file = os.path.join(self.temp_dir, "large_batch.json")
        # Create a large batch of tasks
        batch = [{"input": "x" * 1000, "id": i} for i in range(1000)]
        with open(self.large_batch_file, "w") as f:
            json.dump(batch, f)

    @task(2)
    def volume_cli_batch(self) -> None:
        """Test CLI with large batch input."""
        start = time.time()
        try:
            # Simulate CLI batch processing (replace with real CLI if available)
            script = f"""
import json
with open('{self.large_batch_file}') as f:
    batch = json.load(f)
print('BATCH_SIZE', len(batch))
"""
            result = subprocess.run(  # nosec
                ["pixi", "run", "python", "-c", script],
                capture_output=True,
                text=True,
                timeout=15,
            )
            response_time = int((time.time() - start) * 1000)
            events.request.fire(
                request_type="CLI",
                name="volume_cli_batch",
                response_time=response_time,
                response_length=len(result.stdout),
                exception=None
                if result.returncode == 0 and "BATCH_SIZE" in result.stdout
                else Exception(result.stderr),
                context={},
            )
        except Exception as e:
            events.request.fire(
                request_type="CLI",
                name="volume_cli_batch",
                response_time=int((time.time() - start) * 1000),
                response_length=0,
                exception=e,
                context={},
            )

    @task(2)
    def volume_framework_batch_import(self) -> None:
        """Test framework import in batch."""
        start = time.time()
        try:
            script = """
for _ in range(1000):
    import llm_task_framework
print('VOLUME_IMPORT_OK')
"""
            result = subprocess.run(  # nosec
                ["pixi", "run", "python", "-c", script],
                capture_output=True,
                text=True,
                timeout=20,
            )
            response_time = int((time.time() - start) * 1000)
            events.request.fire(
                request_type="Framework",
                name="volume_framework_batch_import",
                response_time=response_time,
                response_length=len(result.stdout),
                exception=None
                if result.returncode == 0 and "VOLUME_IMPORT_OK" in result.stdout
                else Exception(result.stderr),
                context={},
            )
        except Exception as e:
            events.request.fire(
                request_type="Framework",
                name="volume_framework_batch_import",
                response_time=int((time.time() - start) * 1000),
                response_length=0,
                exception=e,
                context={},
            )

    @task(1)
    def volume_concurrent_batch(self) -> None:
        """Test concurrent batch operations."""
        start = time.time()
        try:
            script = """
import concurrent.futures
def batch_task(_):
    import llm_task_framework
    return True
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(batch_task, range(100)))
if all(results):
    print("VOLUME_CONCURRENT_OK")
else:
    print("VOLUME_CONCURRENT_FAIL")
"""
            result = subprocess.run(  # nosec
                ["pixi", "run", "python", "-c", script],
                capture_output=True,
                text=True,
                timeout=30,
            )
            response_time = int((time.time() - start) * 1000)
            events.request.fire(
                request_type="Concurrent",
                name="volume_concurrent_batch",
                response_time=response_time,
                response_length=len(result.stdout),
                exception=None
                if result.returncode == 0 and "VOLUME_CONCURRENT_OK" in result.stdout
                else Exception(result.stderr),
                context={},
            )
        except Exception as e:
            events.request.fire(
                request_type="Concurrent",
                name="volume_concurrent_batch",
                response_time=int((time.time() - start) * 1000),
                response_length=0,
                exception=e,
                context={},
            )
