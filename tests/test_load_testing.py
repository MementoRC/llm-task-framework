"""
Tests for the load testing scripts and configuration.
"""

import json
import sys
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from load_test_analysis import (
    compare_summaries,
    generate_markdown_summary,
    get_stats_summary,
    parse_locust_report,
)
from load_test_config import get_config


@pytest.fixture
def mock_locust_report_data() -> dict:
    """Provides a mock Locust report dictionary."""
    return {
        "stats": [
            {
                "name": "Aggregated",
                "num_requests": 100,
                "num_failures": 5,
                "avg_response_time": 150.5,
                "median_response_time": 120,
                "min_response_time": 50,
                "max_response_time": 500,
                "total_rps": 10.1,
            }
        ],
        "total_rps": 10.1,
        "fail_ratio": 0.05,
    }


class TestLoadTestConfig:
    """Tests for the load test configuration script."""

    def test_get_light_profile(self):
        """Test retrieving the light profile configuration."""
        config = get_config("light")
        assert config["users"] == 5
        assert config["run_time"] == "1m"

    def test_get_specific_key(self):
        """Test retrieving a specific key from a profile."""
        users = get_config("heavy", "users")
        assert users == 50

    def test_get_invalid_profile(self):
        """Test that getting an invalid profile raises an error."""
        with pytest.raises(ValueError, match="Profile 'invalid' not found"):
            get_config("invalid")

    def test_get_invalid_key(self):
        """Test that getting an invalid key raises an error."""
        with pytest.raises(ValueError, match="Key 'invalid_key' not found"):
            get_config("light", "invalid_key")


class TestLoadTestAnalysis:
    """Tests for the load test analysis script."""

    def test_parse_locust_report(self, mock_locust_report_data):
        """Test parsing a valid Locust JSON report."""
        report_json = json.dumps(mock_locust_report_data)
        m = mock_open(read_data=report_json)
        with patch("builtins.open", m), patch("pathlib.Path.exists", return_value=True):
            data = parse_locust_report(Path("dummy.json"))
            assert data == mock_locust_report_data

    def test_parse_missing_report(self):
        """Test parsing a non-existent report returns None."""
        assert parse_locust_report(Path("non_existent_file.json")) is None

    def test_get_stats_summary(self, mock_locust_report_data):
        """Test extracting summary statistics from report data."""
        summary = get_stats_summary(mock_locust_report_data)
        assert summary["total_requests"] == 100
        assert summary["total_failures"] == 5
        assert summary["failure_rate"] == 0.05
        assert summary["avg_response_time"] == 150.5
        assert summary["rps"] == 10.1

    def test_compare_summaries_no_regression(self):
        """Test comparison with no performance regression."""
        current = {"avg_response_time": 100, "failure_rate": 0.01, "rps": 50}
        baseline = {"avg_response_time": 105, "failure_rate": 0.01, "rps": 48}
        result = compare_summaries(current, baseline)
        assert not result["regressions"]
        assert "avg_response_time" in result["comparison"]

    def test_compare_summaries_with_regression(self):
        """Test comparison that detects performance regressions."""
        current = {"avg_response_time": 150, "failure_rate": 0.02, "rps": 30}
        baseline = {"avg_response_time": 100, "failure_rate": 0.01, "rps": 50}
        result = compare_summaries(current, baseline)
        assert len(result["regressions"]) == 3
        assert "Average response time increased" in result["regressions"][0]
        assert "Failure rate increased" in result["regressions"][1]
        assert "Requests per second (RPS) decreased" in result["regressions"][2]

    def test_generate_markdown_summary(self):
        """Test generating a markdown summary without comparison."""
        summary_data = {"total_requests": 1000, "avg_response_time": 250.7}
        markdown = generate_markdown_summary(summary_data)
        assert "### 📈 Load Test Results" in markdown
        assert "| Total Requests | 1,000 |" in markdown
        assert "| Avg Response Time | 250.70 ms |" in markdown
        assert "Baseline Comparison" not in markdown

    def test_generate_markdown_summary_with_comparison(self):
        """Test generating a markdown summary with baseline comparison."""
        current = {"avg_response_time": 150, "rps": 30}
        baseline = {"avg_response_time": 100, "rps": 50}
        comparison = compare_summaries(current, baseline)
        markdown = generate_markdown_summary(current, comparison)
        assert "### 📊 Baseline Comparison" in markdown
        assert "### ⚠️ Performance Regressions Detected" in markdown
        assert "| Avg Response Time | 150.00 ms | 100.00 ms | +50.00% |" in markdown
