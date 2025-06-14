import json
import tempfile
from typing import Any

from llm_task_framework.reporting.benchmark_analyzer import BenchmarkAnalyzer
from llm_task_framework.reporting.benchmark_reporter import BenchmarkReporter


def create_temp_json_file(data: dict[str, Any]) -> str:
    """
    Creates a temporary JSON file with the given data and returns its path.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        return f.name


def test_benchmark_analyzer_no_regressions():
    """
    Tests the BenchmarkAnalyzer with no regressions.
    """
    baseline_data: list[dict[str, Any]] = [
        {"name": "test_benchmark_1", "stats": {"mean": 1.0}},
        {"name": "test_benchmark_2", "stats": {"mean": 2.0}},
    ]
    current_data: list[dict[str, Any]] = [
        {"name": "test_benchmark_1", "stats": {"mean": 1.05}},
        {"name": "test_benchmark_2", "stats": {"mean": 1.95}},
    ]

    analyzer = BenchmarkAnalyzer(regression_threshold=0.1)
    analysis_results = analyzer.analyze_results(baseline_data, current_data)

    assert len(analysis_results["regressions"]) == 0


def test_benchmark_analyzer_with_regressions():
    """
    Tests the BenchmarkAnalyzer with regressions.
    """
    baseline_data: list[dict[str, Any]] = [
        {"name": "test_benchmark_1", "stats": {"mean": 1.0}},
        {"name": "test_benchmark_2", "stats": {"mean": 2.0}},
    ]
    current_data: list[dict[str, Any]] = [
        {"name": "test_benchmark_1", "stats": {"mean": 1.2}},
        {"name": "test_benchmark_2", "stats": {"mean": 2.5}},
    ]

    analyzer = BenchmarkAnalyzer(regression_threshold=0.1)
    analysis_results = analyzer.analyze_results(baseline_data, current_data)

    assert len(analysis_results["regressions"]) == 2
    assert analysis_results["regressions"][0]["name"] == "test_benchmark_1"
    assert analysis_results["regressions"][1]["name"] == "test_benchmark_2"


def test_benchmark_reporter_generates_report():
    """
    Tests that the BenchmarkReporter generates a report.
    """
    analysis_results: dict[str, Any] = {
        "analysis": {
            "test_benchmark_1": {
                "baseline": 1.0,
                "current": 1.2,
                "percentage_change": 0.2,
            },
            "test_benchmark_2": {
                "baseline": 2.0,
                "current": 2.5,
                "percentage_change": 0.25,
            },
        },
        "regressions": [
            {
                "name": "test_benchmark_1",
                "percentage_change": 0.2,
                "baseline_mean": 1.0,
                "current_mean": 1.2,
            },
            {
                "name": "test_benchmark_2",
                "percentage_change": 0.25,
                "baseline_mean": 2.0,
                "current_mean": 2.5,
            },
        ],
    }

    reporter = BenchmarkReporter()
    report = reporter.generate_report(analysis_results)

    assert "Performance Benchmark Report" in report
    assert "Regressions Detected" in report
    assert "test_benchmark_1" in report
    assert "test_benchmark_2" in report


def test_benchmark_analyzer_loads_data():
    """
    Tests that the BenchmarkAnalyzer loads data from a JSON file.
    """
    data: dict[str, Any] = {
        "benchmarks": [
            {"name": "test_benchmark_1", "stats": {"mean": 1.0}},
            {"name": "test_benchmark_2", "stats": {"mean": 2.0}},
        ]
    }

    temp_file = create_temp_json_file(data)

    analyzer = BenchmarkAnalyzer()
    loaded_data = analyzer.load_benchmark_data(temp_file)

    assert len(loaded_data) == 2
    assert loaded_data[0]["name"] == "test_benchmark_1"
    assert loaded_data[1]["name"] == "test_benchmark_2"

    # Clean up the temporary file
    import os

    os.unlink(temp_file)
