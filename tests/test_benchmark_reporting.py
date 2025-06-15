import json
import os
import tempfile
from typing import Any

import pytest

from llm_task_framework.reporting.benchmark_analyzer import (
    BenchmarkAnalyzer,
    RegressionDetector,
)
from llm_task_framework.reporting.benchmark_reporter import BenchmarkReporter


def create_temp_json_file(data: dict[str, Any]) -> str:
    """
    Creates a temporary JSON file with the given data and returns its path.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        return f.name


@pytest.fixture
def temp_files():
    """Fixture to manage temporary file cleanup."""
    files: list[str] = []
    yield files
    for file_path in files:
        if os.path.exists(file_path):
            os.unlink(file_path)


class TestRegressionDetector:
    def test_no_regression(self):
        rules = [{"metric": "mean", "threshold_type": "percentage", "threshold": 0.1}]
        detector = RegressionDetector(rules)
        baseline = {"mean": 1.0, "stddev": 0.1}
        current = {"mean": 1.05, "stddev": 0.11}
        regressions = detector.detect(baseline, current)
        assert len(regressions) == 0

    def test_percentage_regression(self):
        rules = [
            {
                "metric": "mean",
                "threshold_type": "percentage",
                "threshold": 0.1,
                "severity": "error",
            }
        ]
        detector = RegressionDetector(rules)
        baseline = {"mean": 1.0}
        current = {"mean": 1.2}  # 20% increase
        regressions = detector.detect(baseline, current)
        assert len(regressions) == 1
        reg = regressions[0]
        assert reg["metric"] == "mean"
        assert reg["severity"] == "error"
        assert reg["change"] == pytest.approx(0.2)

    def test_absolute_regression(self):
        rules = [
            {
                "metric": "stddev",
                "threshold_type": "absolute",
                "threshold": 0.05,
                "severity": "warning",
            }
        ]
        detector = RegressionDetector(rules)
        baseline = {"stddev": 0.1}
        current = {"stddev": 0.16}  # 0.06 increase
        regressions = detector.detect(baseline, current)
        assert len(regressions) == 1
        reg = regressions[0]
        assert reg["metric"] == "stddev"
        assert reg["severity"] == "warning"
        assert reg["change"] == pytest.approx(0.06)

    def test_improvement_is_not_regression(self):
        rules = [{"metric": "mean", "threshold_type": "percentage", "threshold": 0.1}]
        detector = RegressionDetector(rules)
        baseline = {"mean": 1.0}
        current = {"mean": 0.8}  # 20% decrease (improvement)
        regressions = detector.detect(baseline, current)
        assert len(regressions) == 0

    def test_multiple_rules(self):
        rules = [
            {
                "metric": "mean",
                "threshold_type": "percentage",
                "threshold": 0.1,
                "severity": "error",
            },
            {
                "metric": "stddev",
                "threshold_type": "absolute",
                "threshold": 0.05,
                "severity": "warning",
            },
        ]
        detector = RegressionDetector(rules)
        baseline = {"mean": 1.0, "stddev": 0.1}
        current = {"mean": 1.2, "stddev": 0.16}
        regressions = detector.detect(baseline, current)
        assert len(regressions) == 2
        assert {"error", "warning"} == {r["severity"] for r in regressions}

    def test_missing_metric(self):
        rules = [{"metric": "p99", "threshold_type": "percentage", "threshold": 0.1}]
        detector = RegressionDetector(rules)
        baseline = {"mean": 1.0}
        current = {"mean": 1.2}
        regressions = detector.detect(baseline, current)
        assert len(regressions) == 0


class TestBenchmarkAnalyzer:
    def test_analyzer_with_regressions(self):
        rules = [{"metric": "mean", "threshold_type": "percentage", "threshold": 0.1}]
        analyzer = BenchmarkAnalyzer(rules)
        baseline_data = [
            {"name": "test_1", "stats": {"mean": 1.0}},
            {"name": "test_2", "stats": {"mean": 2.0}},
        ]
        current_data = [
            {"name": "test_1", "stats": {"mean": 1.2}},  # regression
            {"name": "test_2", "stats": {"mean": 2.1}},  # no regression
        ]
        results = analyzer.analyze_results(baseline_data, current_data)
        assert len(results["regressions"]) == 1
        assert results["regressions"][0]["name"] == "test_1"
        assert "test_1" in results["analysis"]
        assert "test_2" in results["analysis"]
        assert len(results["analysis"]["test_1"]["regressions"]) == 1

    def test_analyzer_new_benchmark(self):
        rules = [{"metric": "mean", "threshold_type": "percentage", "threshold": 0.1}]
        analyzer = BenchmarkAnalyzer(rules)
        baseline_data = [{"name": "test_1", "stats": {"mean": 1.0}}]
        current_data = [
            {"name": "test_1", "stats": {"mean": 1.0}},
            {"name": "new_test", "stats": {"mean": 3.0}},
        ]
        results = analyzer.analyze_results(baseline_data, current_data)
        assert len(results["regressions"]) == 0
        assert "new_test" in results["analysis"]
        assert results["analysis"]["new_test"]["baseline_stats"] is None

    def test_load_benchmark_data(self, temp_files):
        data = {
            "benchmarks": [
                {"name": "test_1", "stats": {"mean": 1.0}},
            ]
        }
        temp_file = create_temp_json_file(data)
        temp_files.append(temp_file)

        analyzer = BenchmarkAnalyzer([])
        loaded_data = analyzer.load_benchmark_data(temp_file)
        assert len(loaded_data) == 1
        assert loaded_data[0]["name"] == "test_1"

    def test_load_empty_or_missing_file(self):
        analyzer = BenchmarkAnalyzer([])
        # Missing file
        assert analyzer.load_benchmark_data("non_existent_file.json") == []
        # Empty file
        with tempfile.NamedTemporaryFile(mode="w", delete=True) as f:
            assert analyzer.load_benchmark_data(f.name) == []


class TestBenchmarkReporter:
    def test_report_with_regressions(self):
        analysis_results = {
            "analysis": {
                "test_benchmark_1": {
                    "baseline_stats": {"mean": 1.0, "stddev": 0.1},
                    "current_stats": {"mean": 1.2, "stddev": 0.11},
                    "regressions": [
                        {
                            "name": "test_benchmark_1",
                            "metric": "mean",
                            "threshold_type": "percentage",
                            "threshold": 0.1,
                            "baseline_value": 1.0,
                            "current_value": 1.2,
                            "change": 0.2,
                            "severity": "error",
                        }
                    ],
                },
                "test_benchmark_2": {
                    "baseline_stats": {"mean": 2.0, "stddev": 0.2},
                    "current_stats": {"mean": 2.1, "stddev": 0.22},
                    "regressions": [],
                },
            },
            "regressions": [
                {
                    "name": "test_benchmark_1",
                    "metric": "mean",
                    "threshold_type": "percentage",
                    "threshold": 0.1,
                    "baseline_value": 1.0,
                    "current_value": 1.2,
                    "change": 0.2,
                    "severity": "error",
                }
            ],
        }
        reporter = BenchmarkReporter()
        report = reporter.generate_report(analysis_results)

        assert "Performance Benchmark Report" in report
        assert "❗ Regressions Detected" in report
        assert "No Performance Regressions Detected" not in report
        assert "❌ ERROR" in report
        assert "`test_benchmark_1`" in report
        assert "+20.00%" in report

    def test_report_no_regressions(self):
        analysis_results = {
            "analysis": {
                "test_benchmark_1": {
                    "baseline_stats": {"mean": 1.0},
                    "current_stats": {"mean": 1.05},
                    "regressions": [],
                }
            },
            "regressions": [],
        }
        reporter = BenchmarkReporter()
        report = reporter.generate_report(analysis_results)
        assert "No Performance Regressions Detected" in report
        assert "❗ Regressions Detected" not in report

    def test_report_new_benchmark(self):
        analysis_results = {
            "analysis": {
                "new_benchmark": {
                    "baseline_stats": None,
                    "current_stats": {"mean": 1.0},
                    "regressions": [],
                }
            },
            "regressions": [],
        }
        reporter = BenchmarkReporter()
        report = reporter.generate_report(analysis_results)
        assert "`new_benchmark`" in report
        assert "N/A" in report  # For baseline and change
