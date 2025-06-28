"""Tests for performance trend analysis and dashboard functionality."""

import json
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from llm_task_framework.reporting.dashboard_generator import DashboardGenerator
from llm_task_framework.reporting.trend_analyzer import (
    MATPLOTLIB_AVAILABLE,
    TrendAnalyzer,
    TrendChartGenerator,
    TrendDataStore,
)


class TestTrendDataStore:
    """Test the trend data storage functionality."""

    def test_store_and_retrieve_benchmark_data(self, tmp_path):
        """Test storing and retrieving benchmark data."""
        store = TrendDataStore(tmp_path)

        # Sample benchmark data
        benchmark_data = [
            {
                "name": "test_function_benchmark",
                "stats": {
                    "mean": 0.123456,
                    "stddev": 0.012345,
                    "min": 0.111111,
                    "max": 0.135791,
                },
            },
            {
                "name": "test_another_benchmark",
                "stats": {
                    "mean": 0.987654,
                    "stddev": 0.098765,
                    "min": 0.888888,
                    "max": 1.086420,
                },
            },
        ]

        # Store data
        timestamp = "2024-01-01T12:00:00"
        store.store_benchmark_data(benchmark_data, timestamp)

        # Verify file was created
        expected_file = tmp_path / "benchmark_2024-01-01T12-00-00.json"
        assert expected_file.exists()

        # Verify data was stored correctly
        with open(expected_file) as f:
            stored_data = json.load(f)

        assert stored_data["timestamp"] == timestamp
        assert stored_data["benchmarks"] == benchmark_data

    def test_get_historical_data(self, tmp_path):
        """Test retrieving historical data."""
        store = TrendDataStore(tmp_path)

        # Create multiple historical entries
        timestamps = [
            "2024-01-01T12:00:00",
            "2024-01-02T12:00:00",
            "2024-01-03T12:00:00",
        ]

        for i, timestamp in enumerate(timestamps):
            benchmark_data = [
                {"name": "test_benchmark", "stats": {"mean": 0.1 + i * 0.01}}
            ]
            store.store_benchmark_data(benchmark_data, timestamp)

        # Get all historical data
        historical_data = store.get_historical_data()
        assert len(historical_data) == 3

        # Should be sorted most recent first
        assert historical_data[0]["timestamp"] == "2024-01-03T12:00:00"
        assert historical_data[1]["timestamp"] == "2024-01-02T12:00:00"
        assert historical_data[2]["timestamp"] == "2024-01-01T12:00:00"

        # Test limit parameter
        limited_data = store.get_historical_data(limit=2)
        assert len(limited_data) == 2
        assert limited_data[0]["timestamp"] == "2024-01-03T12:00:00"

    def test_get_benchmark_history(self, tmp_path):
        """Test retrieving history for a specific benchmark."""
        store = TrendDataStore(tmp_path)

        # Create data with multiple benchmarks
        for i in range(3):
            benchmark_data = [
                {"name": "benchmark_a", "stats": {"mean": 0.1 + i * 0.01}},
                {"name": "benchmark_b", "stats": {"mean": 0.2 + i * 0.02}},
            ]
            timestamp = f"2024-01-0{i + 1}T12:00:00"
            store.store_benchmark_data(benchmark_data, timestamp)

        # Get history for specific benchmark
        history_a = store.get_benchmark_history("benchmark_a")
        assert len(history_a) == 3

        # Check that all entries are for benchmark_a
        for entry in history_a:
            assert "timestamp" in entry
            assert "stats" in entry
            assert entry["stats"]["mean"] >= 0.1

        # Most recent first
        assert abs(history_a[0]["stats"]["mean"] - 0.12) < 0.001  # Most recent
        assert abs(history_a[-1]["stats"]["mean"] - 0.1) < 0.001  # Oldest

        # Test with non-existent benchmark
        history_c = store.get_benchmark_history("benchmark_c")
        assert len(history_c) == 0


class TestTrendChartGenerator:
    """Test the trend chart generation functionality."""

    @pytest.mark.skipif(not MATPLOTLIB_AVAILABLE, reason="matplotlib not available")
    def test_generate_trend_chart(self):
        """Test trend chart generation."""
        generator = TrendChartGenerator()

        # Sample historical data
        historical_data = [
            {
                "timestamp": "2024-01-01T12:00:00",
                "stats": {"mean": 0.1, "stddev": 0.01},
            },
            {
                "timestamp": "2024-01-02T12:00:00",
                "stats": {"mean": 0.11, "stddev": 0.011},
            },
            {
                "timestamp": "2024-01-03T12:00:00",
                "stats": {"mean": 0.12, "stddev": 0.012},
            },
        ]

        # Generate chart
        chart_data_url = generator.generate_trend_chart(
            "test_benchmark", historical_data
        )

        # Should return a data URL with base64 encoded PNG
        assert chart_data_url.startswith("data:image/png;base64,")
        assert len(chart_data_url) > 100  # Should be substantial content

    @pytest.mark.skipif(not MATPLOTLIB_AVAILABLE, reason="matplotlib not available")
    def test_generate_chart_no_data(self):
        """Test chart generation with no data."""
        generator = TrendChartGenerator()

        chart_data_url = generator.generate_trend_chart("test_benchmark", [])

        # Should still return a valid chart (placeholder)
        assert chart_data_url.startswith("data:image/png;base64,")

    def test_chart_generator_requires_matplotlib(self):
        """Test that chart generator requires matplotlib."""
        with (
            patch(
                "llm_task_framework.reporting.trend_analyzer.MATPLOTLIB_AVAILABLE",
                False,
            ),
            pytest.raises(ImportError, match="matplotlib is required"),
        ):
            TrendChartGenerator()


class TestTrendAnalyzer:
    """Test the main trend analysis functionality."""

    def test_analyze_trends_insufficient_data(self, tmp_path):
        """Test trend analysis with insufficient data."""
        analyzer = TrendAnalyzer(tmp_path)

        # Store single data point
        benchmark_data = [{"name": "test_benchmark", "stats": {"mean": 0.1}}]
        analyzer.data_store.store_benchmark_data(benchmark_data)

        # Analyze trends
        results = analyzer.analyze_trends(["test_benchmark"])

        assert "trends" in results
        assert "test_benchmark" in results["trends"]

        trend = results["trends"]["test_benchmark"]
        assert trend["status"] == "insufficient_data"
        assert trend["data_points"] == 1
        assert trend["trend_direction"] == "unknown"

    def test_analyze_trends_with_data(self, tmp_path):
        """Test trend analysis with sufficient data."""
        analyzer = TrendAnalyzer(tmp_path)

        # Store multiple data points showing degradation
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        for i in range(5):
            benchmark_data = [
                {
                    "name": "test_benchmark",
                    "stats": {"mean": 0.1 + i * 0.03},  # Larger degradation (30% total)
                }
            ]
            timestamp = (base_time + timedelta(days=i)).isoformat()
            analyzer.data_store.store_benchmark_data(benchmark_data, timestamp)

        # Analyze trends
        results = analyzer.analyze_trends(["test_benchmark"])

        trend = results["trends"]["test_benchmark"]
        assert trend["status"] == "analyzed"
        assert trend["data_points"] == 5
        assert trend["trend_direction"] == "degrading"
        assert trend["confidence"] > 0.0
        assert trend["change_ratio"] > 0.0

    def test_analyze_trends_stable(self, tmp_path):
        """Test trend analysis with stable performance."""
        analyzer = TrendAnalyzer(tmp_path)

        # Store data points with minimal variation
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        for i in range(5):
            benchmark_data = [
                {
                    "name": "test_benchmark",
                    "stats": {"mean": 0.1 + i * 0.001},  # Very small variation
                }
            ]
            timestamp = (base_time + timedelta(days=i)).isoformat()
            analyzer.data_store.store_benchmark_data(benchmark_data, timestamp)

        results = analyzer.analyze_trends(["test_benchmark"])
        trend = results["trends"]["test_benchmark"]

        assert trend["trend_direction"] == "stable"
        assert abs(trend["change_ratio"]) < 0.05  # Small change

    def test_generate_trend_report(self, tmp_path):
        """Test trend report generation."""
        analyzer = TrendAnalyzer(tmp_path)

        # Mock analysis results
        analysis_results = {
            "metadata": {
                "metric": "mean",
                "history_limit": 50,
                "analysis_timestamp": "2024-01-01T12:00:00",
            },
            "trends": {
                "benchmark_a": {
                    "status": "analyzed",
                    "data_points": 10,
                    "trend_direction": "degrading",
                    "confidence": 0.8,
                    "change_ratio": 0.15,
                },
                "benchmark_b": {
                    "status": "analyzed",
                    "data_points": 8,
                    "trend_direction": "improving",
                    "confidence": 0.7,
                    "change_ratio": -0.12,
                },
            },
        }

        report = analyzer.generate_trend_report(analysis_results)

        # Check report content
        assert "Performance Trend Analysis Report" in report
        assert "benchmark_a" in report
        assert "benchmark_b" in report
        assert "degrading" in report
        assert "improving" in report
        assert "+15.0%" in report  # Change ratio formatting
        assert "-12.0%" in report


class TestDashboardGenerator:
    """Test the dashboard generation functionality."""

    def test_generate_dashboard_html(self, tmp_path):
        """Test HTML dashboard generation."""
        # Create some test data
        data_store = TrendDataStore(tmp_path)
        benchmark_data = [
            {"name": "test_benchmark", "stats": {"mean": 0.1, "stddev": 0.01}}
        ]

        for i in range(3):
            timestamp = f"2024-01-0{i + 1}T12:00:00"
            data_store.store_benchmark_data(benchmark_data, timestamp)

        # Generate dashboard
        generator = DashboardGenerator(tmp_path)
        output_file = tmp_path / "dashboard.html"

        generator.generate_dashboard(
            output_path=output_file,
            include_charts=False,  # Skip charts to avoid matplotlib dependency
        )

        # Verify file was created
        assert output_file.exists()

        # Check HTML content
        with open(output_file) as f:
            html_content = f.read()

        assert "<!DOCTYPE html>" in html_content
        assert "Performance Trend Dashboard" in html_content
        assert "test_benchmark" in html_content
        assert "Summary Statistics" in html_content

    def test_dashboard_with_specific_benchmarks(self, tmp_path):
        """Test dashboard generation with specific benchmark selection."""
        data_store = TrendDataStore(tmp_path)

        # Create data for multiple benchmarks
        benchmark_data = [
            {"name": "benchmark_a", "stats": {"mean": 0.1}},
            {"name": "benchmark_b", "stats": {"mean": 0.2}},
            {"name": "benchmark_c", "stats": {"mean": 0.3}},
        ]
        data_store.store_benchmark_data(benchmark_data)

        generator = DashboardGenerator(tmp_path)
        output_file = tmp_path / "dashboard.html"

        # Generate dashboard for specific benchmarks only
        generator.generate_dashboard(
            output_path=output_file,
            benchmark_names=["benchmark_a", "benchmark_c"],
            include_charts=False,
        )

        with open(output_file) as f:
            html_content = f.read()

        assert "benchmark_a" in html_content
        assert "benchmark_c" in html_content
        # benchmark_b should not be included
        assert "benchmark_b" not in html_content


class TestIntegration:
    """Integration tests for the complete dashboard system."""

    def test_full_workflow(self, tmp_path):
        """Test the complete workflow from data storage to dashboard generation."""
        # Initialize analyzer
        analyzer = TrendAnalyzer(tmp_path)

        # Simulate benchmark data collection over time
        benchmark_names = ["test_function_a", "test_function_b"]
        base_time = datetime(2024, 1, 1, 12, 0, 0)

        for day in range(7):  # One week of data
            benchmark_data = []
            for name in benchmark_names:
                # Simulate different trends
                if name == "test_function_a":
                    # Degrading performance (more significant change)
                    mean_time = 0.1 + day * 0.02
                else:
                    # Improving performance (more significant change)
                    mean_time = 0.2 - day * 0.015

                benchmark_data.append(
                    {
                        "name": name,
                        "stats": {
                            "mean": mean_time,
                            "stddev": mean_time * 0.1,
                            "min": mean_time * 0.9,
                            "max": mean_time * 1.1,
                        },
                    }
                )

            timestamp = (base_time + timedelta(days=day)).isoformat()
            analyzer.data_store.store_benchmark_data(benchmark_data, timestamp)

        # Analyze trends
        analysis_results = analyzer.analyze_trends()

        # Should detect trends for both benchmarks
        assert len(analysis_results["trends"]) == 2

        # Function A should be degrading
        trend_a = analysis_results["trends"]["test_function_a"]
        assert trend_a["trend_direction"] == "degrading"
        assert trend_a["confidence"] > 0.3  # Lower confidence threshold

        # Function B should be improving
        trend_b = analysis_results["trends"]["test_function_b"]
        assert trend_b["trend_direction"] == "improving"
        assert trend_b["confidence"] > 0.3  # Lower confidence threshold

        # Generate dashboard
        generator = DashboardGenerator(tmp_path)
        output_file = tmp_path / "integration_dashboard.html"

        generator.generate_dashboard(output_path=output_file, include_charts=False)

        # Verify dashboard was created successfully
        assert output_file.exists()

        with open(output_file) as f:
            html_content = f.read()

        # Check that both benchmarks and their trends are represented
        assert "test_function_a" in html_content
        assert "test_function_b" in html_content
        assert "Degrading" in html_content or "degrading" in html_content
        assert "Improving" in html_content or "improving" in html_content
