"""
Soak Testing Scenarios for LLM Task Framework.

Simulates long-duration, steady load to detect memory leaks and stability issues.
"""

import json
import os
import subprocess
import tempfile
import time

from locust import TaskSet, events, task


class SoakTestingTaskSet(TaskSet):
    """
    Soak test: Long-running, steady-state operations.
    """

    def on_start(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "soak_config.json")
        config = {
            "framework": {
                "name": "soak-framework",
                "version": "1.0.0",
                "max_workers": 8,
            },
            "llm": {"provider": "mock", "model": "soak-model"},
        }
        with open(self.config_file, "w") as f:
            json.dump(config, f)

    @task(2)
    def soak_cli_help(self) -> None:
        """Repeated CLI help calls over time."""
        start = time.time()
        try:
            result = subprocess.run(  # nosec
                ["pixi", "run", "ltf", "--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            response_time = int((time.time() - start) * 1000)
            events.request.fire(
                request_type="CLI",
                name="soak_help",
                response_time=response_time,
                response_length=len(result.stdout),
                exception=None if result.returncode == 0 else Exception(result.stderr),
                context={},
            )
        except Exception as e:
            events.request.fire(
                request_type="CLI",
                name="soak_help",
                response_time=int((time.time() - start) * 1000),
                response_length=0,
                exception=e,
                context={},
            )

    @task(2)
    def soak_framework_import(self) -> None:
        """Repeated framework imports over time."""
        start = time.time()
        try:
            result = subprocess.run(  # nosec
                ["pixi", "run", "python", "-c", "import llm_task_framework"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            response_time = int((time.time() - start) * 1000)
            events.request.fire(
                request_type="Framework",
                name="soak_import",
                response_time=response_time,
                response_length=len(result.stdout),
                exception=None if result.returncode == 0 else Exception(result.stderr),
                context={},
            )
        except Exception as e:
            events.request.fire(
                request_type="Framework",
                name="soak_import",
                response_time=int((time.time() - start) * 1000),
                response_length=0,
                exception=e,
                context={},
            )

    @task(1)
    def soak_config_validation(self) -> None:
        """Repeated config validation over time."""
        start = time.time()
        try:
            script = f"""
import json
with open('{self.config_file}') as f:
    config = json.load(f)
if 'framework' in config and 'llm' in config:
    print('SOAK_CONFIG_OK')
else:
    print('SOAK_CONFIG_FAIL')
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
                name="soak_config_validation",
                response_time=response_time,
                response_length=len(result.stdout),
                exception=None
                if result.returncode == 0 and "SOAK_CONFIG_OK" in result.stdout
                else Exception(result.stderr),
                context={},
            )
        except Exception as e:
            events.request.fire(
                request_type="Config",
                name="soak_config_validation",
                response_time=int((time.time() - start) * 1000),
                response_length=0,
                exception=e,
                context={},
            )
