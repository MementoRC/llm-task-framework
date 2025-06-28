"""
Error Rate Testing Scenarios for LLM Task Framework.

Simulates error injection and recovery.
"""

import subprocess  # nosec B404
import time

from locust import TaskSet, events, task


class ErrorTestingTaskSet(TaskSet):
    """
    Error test: Inject errors and test recovery/metrics.
    """

    @task(2)
    def error_cli_invalid(self) -> None:
        """Run CLI with invalid args to induce error."""
        start = time.time()
        try:
            result = subprocess.run(  # nosec
                ["pixi", "run", "ltf", "--invalid-flag"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            response_time = int((time.time() - start) * 1000)
            events.request.fire(
                request_type="CLI",
                name="error_cli_invalid",
                response_time=response_time,
                response_length=len(result.stderr),
                exception=None
                if result.returncode != 0
                else Exception("Expected error not raised"),
                context={},
            )
        except Exception as e:
            events.request.fire(
                request_type="CLI",
                name="error_cli_invalid",
                response_time=int((time.time() - start) * 1000),
                response_length=0,
                exception=e,
                context={},
            )

    @task(2)
    def error_framework_import_fail(self) -> None:
        """Try to import a non-existent module to induce error."""
        start = time.time()
        try:
            result = subprocess.run(  # nosec
                ["pixi", "run", "python", "-c", "import not_a_real_module"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            response_time = int((time.time() - start) * 1000)
            events.request.fire(
                request_type="Framework",
                name="error_import_fail",
                response_time=response_time,
                response_length=len(result.stderr),
                exception=None
                if result.returncode != 0
                else Exception("Expected import error not raised"),
                context={},
            )
        except Exception as e:
            events.request.fire(
                request_type="Framework",
                name="error_import_fail",
                response_time=int((time.time() - start) * 1000),
                response_length=0,
                exception=e,
                context={},
            )

    @task(1)
    def error_recovery(self) -> None:
        """Test recovery after error by running a valid command."""
        start = time.time()
        try:
            result = subprocess.run(  # nosec
                ["pixi", "run", "ltf", "--help"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            response_time = int((time.time() - start) * 1000)
            events.request.fire(
                request_type="CLI",
                name="error_recovery_help",
                response_time=response_time,
                response_length=len(result.stdout),
                exception=None if result.returncode == 0 else Exception(result.stderr),
                context={},
            )
        except Exception as e:
            events.request.fire(
                request_type="CLI",
                name="error_recovery_help",
                response_time=int((time.time() - start) * 1000),
                response_length=0,
                exception=e,
                context={},
            )
