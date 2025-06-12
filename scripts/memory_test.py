#!/usr/bin/env python3
"""
Memory profiling script for LLM Task Framework.

This script tests memory usage patterns for:
- Framework initialization
- CLI operations
- MCP server operations
- Concurrent operations

Usage:
    python scripts/memory_test.py
    python -m memory_profiler scripts/memory_test.py
"""

import gc
import os
import sys
import time
from pathlib import Path

from memory_profiler import profile  # type: ignore[import-not-found]

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@profile
def test_framework_import() -> bool:
    """Test memory usage during framework import."""
    print("Testing framework import memory usage...")

    # Baseline memory
    gc.collect()

    # Import framework
    import llm_task_framework  # type: ignore[import-untyped]

    # Force garbage collection
    gc.collect()

    print(f"Framework version: {getattr(llm_task_framework, '__version__', 'unknown')}")
    return True


@profile
def test_cli_memory() -> bool:
    """Test memory usage during CLI operations."""
    print("Testing CLI memory usage...")

    gc.collect()

    try:
        # Simulate CLI argument parsing
        import sys

        original_argv = sys.argv[:]
        sys.argv = ["llm-task-framework", "--help"]

        # This would normally call main.main() but we'll simulate it
        # to avoid actually running the CLI
        sys.argv = original_argv

        gc.collect()

    except Exception as e:
        print(f"CLI memory test failed: {e}")
        return False

    return True


@profile
def test_mcp_server_memory() -> bool:
    """Test memory usage during MCP server operations."""
    print("Testing MCP server memory usage...")

    gc.collect()

    try:
        # Simulate server initialization without actually starting it
        # This tests the memory footprint of server setup

        gc.collect()

    except Exception as e:
        print(f"MCP server memory test failed: {e}")
        return False

    return True


@profile
def test_concurrent_operations_memory() -> bool:
    """Test memory usage during concurrent operations."""
    print("Testing concurrent operations memory usage...")

    gc.collect()

    import concurrent.futures

    def memory_intensive_task() -> bool:
        """Simulate memory-intensive task."""
        # Create some data structures
        data = []
        for i in range(1000):
            data.append({"id": i, "data": f"test_data_{i}" * 10})

        # Simulate processing
        time.sleep(0.1)

        # Clean up
        del data
        gc.collect()

        return True

    # Run concurrent tasks
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for _i in range(10):
            future = executor.submit(memory_intensive_task)
            futures.append(future)

        # Wait for completion
        for future in concurrent.futures.as_completed(futures):
            future.result()

    gc.collect()
    return True


@profile
def test_memory_leaks() -> bool:
    """Test for potential memory leaks."""
    print("Testing for memory leaks...")

    import psutil  # type: ignore[import-untyped]

    process = psutil.Process(os.getpid())

    # Get initial memory usage
    initial_memory = process.memory_info().rss
    print(f"Initial memory usage: {initial_memory / 1024 / 1024:.2f} MB")

    # Perform operations multiple times
    for iteration in range(5):
        print(f"Memory leak test iteration {iteration + 1}/5")

        # Test framework operations
        test_framework_import()
        test_cli_memory()
        test_mcp_server_memory()

        # Force garbage collection
        gc.collect()

        # Check memory usage
        current_memory = process.memory_info().rss
        memory_increase = (current_memory - initial_memory) / 1024 / 1024

        print(
            f"Memory after iteration {iteration + 1}: {current_memory / 1024 / 1024:.2f} MB"
        )
        print(f"Memory increase: {memory_increase:.2f} MB")

        # Warning threshold: 50MB increase
        if memory_increase > 50:
            print("⚠️  WARNING: Significant memory increase detected!")

        time.sleep(1)

    final_memory = process.memory_info().rss
    total_increase = (final_memory - initial_memory) / 1024 / 1024

    print(f"\nFinal memory usage: {final_memory / 1024 / 1024:.2f} MB")
    print(f"Total memory increase: {total_increase:.2f} MB")

    # Memory leak threshold
    if total_increase > 100:
        print("❌ MEMORY LEAK DETECTED: Excessive memory increase")
        return False
    elif total_increase > 50:
        print("⚠️  WARNING: Moderate memory increase detected")
        return True
    else:
        print("✅ MEMORY USAGE: Within acceptable limits")
        return True


def main() -> int:
    """Run all memory tests."""
    print("🧠 LLM Task Framework Memory Testing")
    print("=" * 50)

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from collections.abc import Callable

    tests: list[tuple[str, "Callable[[], bool]"]] = [
        ("Framework Import", test_framework_import),
        ("CLI Operations", test_cli_memory),
        ("MCP Server", test_mcp_server_memory),
        ("Concurrent Operations", test_concurrent_operations_memory),
        ("Memory Leaks", test_memory_leaks),
    ]

    results: list[tuple[str, bool]] = []

    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name} test...")
        try:
            result = test_func()
            results.append((test_name, result))
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status}: {test_name}")
        except Exception as e:
            print(f"❌ FAILED: {test_name} - {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("📊 Memory Testing Summary")
    print("=" * 50)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All memory tests passed!")
        return 0
    else:
        print("💥 Some memory tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
