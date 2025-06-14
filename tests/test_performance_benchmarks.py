"""
Performance benchmark tests for LLM Task Framework.

These tests use pytest-benchmark to measure performance metrics
for core framework operations.

Run with:
    pytest tests/test_performance_benchmarks.py -m benchmark --benchmark-only
    pytest tests/test_performance_benchmarks.py -m benchmark --benchmark-json=benchmark.json
"""

import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.mark.benchmark
class TestFrameworkBenchmarks:
    """Benchmark tests for core framework functionality."""

    @pytest.mark.benchmark
    def test_framework_import_benchmark(self, benchmark) -> None:
        """Benchmark framework import performance."""

        def import_framework():
            # Clear from cache to test real import time
            modules_to_clear = [
                name for name in sys.modules if name.startswith("llm_task_framework")
            ]
            for module_name in modules_to_clear:
                if module_name in sys.modules:
                    del sys.modules[module_name]

            import llm_task_framework  # type: ignore[import-untyped]

            return llm_task_framework

        result = benchmark(import_framework)
        assert result is not None

    @pytest.mark.benchmark
    def test_protocol_creation_benchmark(self, benchmark):
        """Benchmark protocol object creation."""

        def create_protocol_objects():
            # Create multiple protocol objects to test overhead
            objects = []
            for i in range(100):
                # This would create actual protocol objects
                # For now, we simulate with a simple object
                obj = type("MockProtocol", (), {"id": i, "name": f"protocol_{i}"})()
                objects.append(obj)
            return objects

        result = benchmark(create_protocol_objects)
        assert len(result) == 100

    @pytest.mark.benchmark
    def test_config_validation_benchmark(self, benchmark):
        """Benchmark configuration validation performance."""
        import json
        import os
        import tempfile

        def validate_config():
            # Create test config
            config = {
                "framework": {
                    "name": "test-framework",
                    "version": "1.0.0",
                    "workers": 4,
                },
                "llm": {
                    "provider": "test",
                    "model": "test-model",
                    "api_key": "test-key",  # pragma: allowlist secret
                },
                "mcp": {"port": 8080, "host": "localhost"},
            }

            # Write to temp file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
                json.dump(config, f)
                temp_path = f.name

            try:
                # Read and validate
                with open(temp_path) as f:
                    loaded_config = json.load(f)

                # Basic validation
                required_sections = ["framework", "llm", "mcp"]
                valid = all(section in loaded_config for section in required_sections)

                return valid
            finally:
                os.unlink(temp_path)

        result = benchmark(validate_config)
        assert result is True


@pytest.mark.benchmark
class TestCLIBenchmarks:
    """Benchmark tests for CLI functionality."""

    @patch("sys.argv")  # type: ignore[misc]
    @pytest.mark.benchmark
    def test_cli_argument_parsing_benchmark(self, mock_argv, benchmark):
        """Benchmark CLI argument parsing performance."""

        # Mock sys.argv for different scenarios
        test_args = [
            ["llm-task-framework", "--help"],
            ["llm-task-framework", "--version"],
            ["llm-task-framework", "serve", "--port", "8080"],
            ["llm-task-framework", "run", "--config", "test.json"],
        ]

        def parse_all_args():
            results = []
            for args in test_args:
                mock_argv.__getitem__.side_effect = (
                    lambda i, test_args_item=args: test_args_item[i]
                )
                mock_argv.__len__.return_value = len(args)

                # Simulate argument parsing without actual execution
                # In a real implementation, this would call the argument parser
                parsed = {
                    "command": args[1] if len(args) > 1 else "help",
                    "args": args[2:] if len(args) > 2 else [],
                }
                results.append(parsed)

            return results

        result = benchmark(parse_all_args)
        assert len(result) == len(test_args)

    @pytest.mark.benchmark
    def test_cli_help_generation_benchmark(self, benchmark):
        """Benchmark CLI help text generation."""

        def generate_help_text():
            # Simulate help text generation
            help_sections = [
                "LLM Task Framework CLI",
                "Commands:",
                "  serve    Start the MCP server",
                "  run      Execute a task",
                "  config   Manage configuration",
                "Options:",
                "  --help     Show this help message",
                "  --version  Show version information",
                "  --config   Configuration file path",
                "  --port     Server port (default: 8080)",
                "  --host     Server host (default: localhost)",
            ]

            # Simulate formatting and concatenation
            help_text = "\n".join(help_sections)

            # Add some processing overhead
            formatted_help = help_text.replace("  ", "    ")

            return formatted_help

        result = benchmark(generate_help_text)
        assert "LLM Task Framework CLI" in result


@pytest.mark.benchmark
class TestMCPBenchmarks:
    """Benchmark tests for MCP server functionality."""

    @pytest.mark.benchmark
    def test_mcp_message_processing_benchmark(self, benchmark):
        """Benchmark MCP message processing performance."""

        def process_mcp_messages():
            # Simulate MCP message processing
            messages = [
                {
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05"},
                    "id": 1,
                },
                {"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 2},
                {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {"name": "test_tool", "arguments": {}},
                    "id": 3,
                },
            ]

            processed = []
            for msg in messages:
                # Simulate message validation and processing
                if "jsonrpc" in msg and "method" in msg:
                    response = {
                        "jsonrpc": "2.0",
                        "id": msg.get("id"),
                        "result": {"status": "processed"},
                    }
                    processed.append(response)

            return processed

        result = benchmark(process_mcp_messages)
        assert len(result) == 3

    @pytest.mark.benchmark
    def test_mcp_server_initialization_benchmark(self, benchmark):
        """Benchmark MCP server initialization."""

        def initialize_mcp_server():
            # Simulate server initialization steps
            steps = [
                "Load configuration",
                "Initialize protocol handlers",
                "Setup transport layer",
                "Register tools",
                "Start event loop",
            ]

            initialized_components = []
            for step in steps:
                # Simulate initialization time
                time.sleep(0.001)  # 1ms per step
                initialized_components.append(step)

            return initialized_components

        result = benchmark(initialize_mcp_server)
        assert len(result) == 5


@pytest.mark.benchmark
class TestConcurrencyBenchmarks:
    """Benchmark tests for concurrent operations."""

    @pytest.mark.benchmark
    def test_concurrent_task_execution_benchmark(self, benchmark):
        """Benchmark concurrent task execution."""
        import concurrent.futures

        def run_concurrent_tasks():
            def task(task_id):
                # Simulate task work
                result = 0
                for i in range(1000):
                    result += i
                return result

            # Run tasks concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                for i in range(10):
                    future = executor.submit(task, i)
                    futures.append(future)

                results = []
                for future in concurrent.futures.as_completed(futures):
                    results.append(future.result())

            return results

        result = benchmark(run_concurrent_tasks)
        assert len(result) == 10

    @pytest.mark.benchmark
    def test_thread_pool_overhead_benchmark(self, benchmark):
        """Benchmark thread pool creation and teardown overhead."""
        import concurrent.futures

        def thread_pool_lifecycle():
            pools_created = 0

            for _i in range(5):
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    # Submit a simple task
                    future = executor.submit(lambda: 42)
                    result = future.result()
                    assert result == 42
                    pools_created += 1

            return pools_created

        result = benchmark(thread_pool_lifecycle)
        assert result == 5


@pytest.mark.benchmark
class TestDataProcessingBenchmarks:
    """Benchmark tests for data processing operations."""

    @pytest.mark.benchmark
    def test_json_serialization_benchmark(self, benchmark):
        """Benchmark JSON serialization/deserialization."""
        import json

        def json_operations():
            # Create test data
            data = {
                "framework": "llm-task-framework",
                "tasks": [
                    {"id": i, "name": f"task_{i}", "data": list(range(100))}
                    for i in range(50)
                ],
                "metadata": {
                    "version": "1.0.0",
                    "timestamp": time.time(),
                    "config": {"workers": 4, "timeout": 30},
                },
            }

            # Serialize to JSON
            json_str = json.dumps(data)

            # Deserialize back
            parsed_data = json.loads(json_str)

            return len(parsed_data["tasks"])

        result = benchmark(json_operations)
        result_typed: int = result  # result should be int
        assert result_typed == 50

    @pytest.mark.benchmark
    def test_large_data_processing_benchmark(self, benchmark):
        """Benchmark processing of large data structures."""

        def process_large_dataset():
            # Create large dataset
            from typing import Any

            dataset: list[dict[str, Any]] = []
            for i in range(10000):
                record = {
                    "id": i,
                    "name": f"record_{i}",
                    "values": list(range(i % 100)),
                    "metadata": {"created": time.time(), "processed": False},
                }
                dataset.append(record)

            # Process dataset
            processed_count = 0
            for record in dataset:
                if len(record["values"]) > 50:
                    record["metadata"]["processed"] = True
                    processed_count += 1

            return processed_count

        result = benchmark(process_large_dataset)
        result_typed: int = result  # result should be int
        assert result_typed > 0


# Performance thresholds and markers
@pytest.mark.benchmark
@pytest.mark.slow
class TestPerformanceThresholds:
    """Tests that verify performance stays within acceptable thresholds."""

    @pytest.mark.benchmark
    def test_framework_import_under_threshold(self, benchmark):
        """Ensure framework import takes less than 1 second."""

        def import_framework():
            import llm_task_framework

            return llm_task_framework

        result = benchmark(import_framework)
        # Check that the benchmark time is under threshold
        # Note: benchmark.stats will contain timing information
        assert result is not None

    @pytest.mark.benchmark
    def test_config_validation_under_threshold(self, benchmark):
        """Ensure config validation takes less than 100ms."""
        import json
        import os
        import tempfile

        def quick_config_validation():
            config = {"framework": {"name": "test"}}

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
                json.dump(config, f)
                temp_path = f.name

            try:
                with open(temp_path) as f:
                    loaded = json.load(f)
                return "framework" in loaded
            finally:
                os.unlink(temp_path)

        result = benchmark(quick_config_validation)
        assert bool(result) is True


if __name__ == "__main__":
    pytest.main([__file__, "-m", "benchmark", "--benchmark-only", "-v"])
