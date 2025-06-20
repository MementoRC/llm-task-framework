"""Tests for CI reporting functionality."""

import json
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

from llm_task_framework.reporting.ci_reporter import (
    CIReporter,
    CoverageData,
    ExecutionTimes,
    OptimizationRecommendations,
    SecurityResults,
    TestExecutionResults,
)


class TestTestExecutionResults:
    """Test TestExecutionResults dataclass functionality."""

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        results = TestExecutionResults(total=100, passed=90, failed=5, skipped=5)
        assert results.success_rate == 90.0

        # Edge case: no tests
        empty_results = TestExecutionResults(total=0, passed=0, failed=0, skipped=0)
        assert empty_results.success_rate == 0.0

    def test_completion_rate_calculation(self):
        """Test completion rate calculation."""
        results = TestExecutionResults(total=100, passed=80, failed=10, skipped=10, errors=0)
        assert results.completion_rate == 90.0  # 80 + 10 completed out of 100

        # Edge case: no tests
        empty_results = TestExecutionResults(total=0, passed=0, failed=0, skipped=0)
        assert empty_results.completion_rate == 0.0


class TestCoverageData:
    """Test CoverageData dataclass functionality."""

    def test_coverage_grade_calculation(self):
        """Test coverage grade assignment."""
        assert CoverageData(total=95.0, line=95, branch=95).coverage_grade == "A"
        assert CoverageData(total=85.0, line=85, branch=85).coverage_grade == "B"
        assert CoverageData(total=75.0, line=75, branch=75).coverage_grade == "C"
        assert CoverageData(total=65.0, line=65, branch=65).coverage_grade == "D"
        assert CoverageData(total=45.0, line=45, branch=45).coverage_grade == "F"


class TestExecutionTimes:
    """Test ExecutionTimes dataclass functionality."""

    def test_breakdown_percentages(self):
        """Test time breakdown percentage calculation."""
        times = ExecutionTimes(
            total=100.0,
            setup=20.0,
            tests=50.0,
            quality_checks=20.0,
            security_scans=5.0,
            reporting=5.0
        )

        breakdown = times.get_breakdown_percentages()
        assert breakdown["setup"] == 20.0
        assert breakdown["tests"] == 50.0
        assert breakdown["quality_checks"] == 20.0
        assert breakdown["security_scans"] == 5.0
        assert breakdown["reporting"] == 5.0

    def test_breakdown_percentages_zero_total(self):
        """Test breakdown with zero total time."""
        times = ExecutionTimes(total=0, setup=0, tests=0, quality_checks=0, security_scans=0, reporting=0)
        breakdown = times.get_breakdown_percentages()

        for percentage in breakdown.values():
            assert percentage == 0.0


class TestSecurityResults:
    """Test SecurityResults dataclass functionality."""

    def test_total_issues_calculation(self):
        """Test total security issues calculation."""
        security = SecurityResults(
            bandit_issues=2,
            safety_vulnerabilities=1,
            pip_audit_vulnerabilities=3,
            secrets_detected=0
        )
        assert security.total_issues == 6

    def test_security_status_determination(self):
        """Test security status based on issue count."""
        assert SecurityResults().security_status == "🛡️ SECURE"
        assert SecurityResults(bandit_issues=3).security_status == "⚠️ MINOR ISSUES"
        assert SecurityResults(bandit_issues=10).security_status == "🚨 MODERATE RISK"
        assert SecurityResults(bandit_issues=20).security_status == "🔴 HIGH RISK"


class TestOptimizationRecommendations:
    """Test OptimizationRecommendations functionality."""

    def test_add_recommendation(self):
        """Test adding optimization recommendations."""
        recommendations = OptimizationRecommendations([])

        recommendations.add_recommendation("Optimize setup", 30.0)
        recommendations.add_recommendation("Parallelize tests", 45.0)

        assert len(recommendations.recommendations) == 2
        assert recommendations.potential_time_savings == 75.0


class TestCIReporter:
    """Test CIReporter functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.reporter = CIReporter(str(self.temp_dir))

        # Sample test data
        self.test_results = TestExecutionResults(total=100, passed=90, failed=5, skipped=5, errors=0)
        self.coverage_data = CoverageData(total=85.0, line=88.0, branch=82.0, missing_lines=150)
        self.execution_times = ExecutionTimes(
            total=300.0, setup=60.0, tests=180.0, quality_checks=30.0, security_scans=20.0, reporting=10.0
        )
        self.security_results = SecurityResults(bandit_issues=2, safety_vulnerabilities=0, pip_audit_vulnerabilities=1)

    def test_generate_ci_summary_basic(self):
        """Test basic CI summary generation."""
        summary = self.reporter.generate_ci_summary(
            self.test_results, self.coverage_data, self.execution_times
        )

        assert "CI Execution Summary" in summary
        assert "Test Results" in summary
        assert "Coverage Report" in summary
        assert "Execution Time Analysis" in summary
        assert "90.0%" in summary  # Success rate
        assert "85.0%" in summary  # Coverage
        assert "300.00s" in summary  # Total time

    def test_generate_ci_summary_with_security(self):
        """Test CI summary generation with security results."""
        summary = self.reporter.generate_ci_summary(
            self.test_results, self.coverage_data, self.execution_times, self.security_results
        )

        assert "Security Scan Results" in summary
        assert "⚠️ MINOR ISSUES" in summary
        assert "Static Analysis (Bandit)" in summary
        assert "Package Audit (pip-audit)" in summary

    def test_generate_ci_summary_with_benchmarks(self):
        """Test CI summary generation with benchmark results."""
        benchmark_results = {
            "regressions": [{"name": "test_benchmark", "severity": "warning"}],
            "analysis": {"benchmark1": {}, "benchmark2": {}}
        }

        summary = self.reporter.generate_ci_summary(
            self.test_results, self.coverage_data, self.execution_times,
            benchmark_results=benchmark_results
        )

        assert "Performance Benchmarks" in summary
        assert "1 Performance Regression(s) Detected" in summary
        assert "Benchmarks Executed:** 2" in summary

    def test_generate_ci_summary_with_environment(self):
        """Test CI summary generation with environment info."""
        env_info = {
            "python_version": "3.11.0",
            "runner_os": "ubuntu-latest",
            "ci_system": "GitHub Actions"
        }

        summary = self.reporter.generate_ci_summary(
            self.test_results, self.coverage_data, self.execution_times,
            environment_info=env_info
        )

        assert "Environment Information" in summary
        assert "Python Version" in summary
        assert "3.11.0" in summary
        assert "ubuntu-latest" in summary

    def test_optimization_recommendations_generation(self):
        """Test optimization recommendations generation."""
        # Create conditions that should trigger recommendations
        slow_setup_times = ExecutionTimes(
            total=500.0, setup=200.0, tests=200.0, quality_checks=50.0, security_scans=40.0, reporting=10.0
        )
        high_skip_results = TestExecutionResults(total=100, passed=70, failed=5, skipped=25, errors=0)

        summary = self.reporter.generate_ci_summary(
            high_skip_results, self.coverage_data, slow_setup_times
        )

        assert "Optimization Opportunities" in summary
        assert "Setup Time High" in summary  # Should trigger setup optimization
        assert "High Skip Rate" in summary  # Should trigger skip rate optimization

    def test_save_summary_to_file(self):
        """Test saving summary to file."""
        summary = "Test CI Summary"
        output_path = self.reporter.save_summary_to_file(summary, "test-summary.md")

        assert output_path.exists()
        assert output_path.read_text() == summary

    @patch.dict('os.environ', {'GITHUB_STEP_SUMMARY': '/tmp/test_step_summary'})
    @patch('builtins.open', new_callable=mock_open)
    def test_save_summary_to_github_step(self, mock_file):
        """Test saving summary to GitHub step summary."""
        summary = "Test CI Summary"
        self.reporter.save_summary_to_github_step(summary)

        mock_file.assert_called_once_with("/tmp/test_step_summary", "a", encoding="utf-8")
        mock_file().write.assert_called_once_with("\nTest CI Summary\n")

    def test_generate_metrics_json(self):
        """Test generating machine-readable metrics."""
        metrics = self.reporter.generate_metrics_json(
            self.test_results, self.coverage_data, self.execution_times, self.security_results
        )

        assert "timestamp" in metrics
        assert "test_results" in metrics
        assert "coverage_data" in metrics
        assert "execution_times" in metrics
        assert "security_results" in metrics
        assert "performance_metrics" in metrics

        # Check nested data
        assert metrics["test_results"]["total"] == 100
        assert metrics["coverage_data"]["total"] == 85.0
        assert metrics["performance_metrics"]["test_success_rate"] == 90.0
        assert metrics["performance_metrics"]["coverage_grade"] == "B"

    def test_load_test_results_from_pytest_json(self):
        """Test loading test results from pytest JSON report."""
        # Create mock pytest JSON report
        pytest_data = {
            "summary": {
                "total": 150,
                "passed": 140,
                "failed": 5,
                "skipped": 5,
                "error": 0
            }
        }

        json_file = self.temp_dir / "pytest-report.json"
        with open(json_file, "w") as f:
            json.dump(pytest_data, f)

        results = self.reporter.load_test_results_from_pytest_json(json_file)

        assert results.total == 150
        assert results.passed == 140
        assert results.failed == 5
        assert results.skipped == 5
        assert results.errors == 0

    def test_load_test_results_missing_file(self):
        """Test loading test results from missing file."""
        missing_file = self.temp_dir / "missing.json"
        results = self.reporter.load_test_results_from_pytest_json(missing_file)

        # Should return zero results
        assert results.total == 0
        assert results.passed == 0
        assert results.failed == 0
        assert results.skipped == 0
        assert results.errors == 0

    def test_load_coverage_from_xml_missing_file(self):
        """Test loading coverage from missing XML file."""
        missing_file = self.temp_dir / "missing.xml"
        coverage = self.reporter.load_coverage_from_xml(missing_file)

        # Should return zero coverage
        assert coverage.total == 0.0
        assert coverage.line == 0.0
        assert coverage.branch == 0.0
        assert coverage.missing_lines == 0

    def test_load_security_results_from_reports(self):
        """Test loading security results from report files."""
        # Create mock security reports
        bandit_data = {"results": [{"issue": "test1"}, {"issue": "test2"}]}
        safety_data = [{"vulnerability": "test1"}]
        pip_audit_data = {"vulnerabilities": [{"package": "test1"}, {"package": "test2"}]}

        reports_dir = self.temp_dir / "security_reports"
        reports_dir.mkdir()

        with open(reports_dir / "bandit-report.json", "w") as f:
            json.dump(bandit_data, f)
        with open(reports_dir / "safety-report.json", "w") as f:
            json.dump(safety_data, f)
        with open(reports_dir / "pip-audit-report.json", "w") as f:
            json.dump(pip_audit_data, f)

        security_results = self.reporter.load_security_results_from_reports(reports_dir)

        assert security_results.bandit_issues == 2
        assert security_results.safety_vulnerabilities == 1
        assert security_results.pip_audit_vulnerabilities == 2
        assert security_results.secrets_detected == 0

    def test_load_security_results_empty_directory(self):
        """Test loading security results from empty directory."""
        empty_dir = self.temp_dir / "empty"
        empty_dir.mkdir()

        security_results = self.reporter.load_security_results_from_reports(empty_dir)

        assert security_results.bandit_issues == 0
        assert security_results.safety_vulnerabilities == 0
        assert security_results.pip_audit_vulnerabilities == 0
        assert security_results.secrets_detected == 0

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)


class TestCIReporterIntegration:
    """Integration tests for CI reporting functionality."""

    def test_full_workflow_with_sample_data(self):
        """Test complete CI reporting workflow with sample data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            reporter = CIReporter(temp_dir)

            # Create comprehensive test data (all passing for successful CI)
            test_results = TestExecutionResults(total=200, passed=195, failed=0, skipped=5, errors=0)
            coverage_data = CoverageData(total=92.5, line=94.0, branch=91.0, missing_lines=45)
            execution_times = ExecutionTimes(
                total=420.0, setup=80.0, tests=250.0, quality_checks=60.0, security_scans=20.0, reporting=10.0
            )
            security_results = SecurityResults(bandit_issues=0, safety_vulnerabilities=0, pip_audit_vulnerabilities=0)
            benchmark_results = {"regressions": [], "analysis": {"test1": {}, "test2": {}}}
            environment_info = {"python_version": "3.11.5", "ci_system": "GitHub Actions"}

            # Generate summary
            summary = reporter.generate_ci_summary(
                test_results=test_results,
                coverage_data=coverage_data,
                execution_times=execution_times,
                security_results=security_results,
                benchmark_results=benchmark_results,
                environment_info=environment_info
            )

            # Verify summary content
            assert "✅ PASSING" in summary  # Overall status
            assert "97.5%" in summary  # Success rate (195/200)
            assert "A Grade" in summary  # Coverage grade
            assert "🛡️ SECURE" in summary  # Security status
            assert "No Performance Regressions" in summary  # Benchmarks
            assert "420.00s" in summary  # Total time
            assert "7.0 minutes" in summary  # Total time in minutes
            assert "Python Version" in summary  # Environment

            # Save and verify files
            summary_path = reporter.save_summary_to_file(summary)
            assert summary_path.exists()
            assert len(summary_path.read_text()) > 0

            # Generate and verify metrics JSON
            metrics = reporter.generate_metrics_json(test_results, coverage_data, execution_times, security_results)
            assert isinstance(metrics, dict)
            assert metrics["performance_metrics"]["test_success_rate"] == 97.5
            assert metrics["performance_metrics"]["coverage_grade"] == "A"
