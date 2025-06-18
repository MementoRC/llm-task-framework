"""CI Execution Summary and Reporting Module."""

import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


def _ensure_windows_compatible_text(text: str) -> str:
    """Ensure text is compatible with Windows encodings by replacing problematic Unicode."""
    if sys.platform == "win32":
        # Replace Unicode emojis with ASCII equivalents for Windows compatibility
        emoji_replacements = {
            "🚀": "CI",
            "📊": "Status",
            "📈": "Coverage",
            "✅": "[PASS]",
            "❌": "[FAIL]",
            "⚠️": "[WARN]",
            "🔍": "Analysis",
            "🛡️": "Security",
            "💡": "Optimization",
            "🎉": "Success",
            "🎯": "Target",
            "🔧": "Fix",
            "📝": "Report",
            "📋": "Summary",
            "⏱️": "Time",
            "🏃": "Performance",
            "🌍": "Environment",
            "🔥": "Critical",
            "🚨": "Alert",
        }
        for emoji, replacement in emoji_replacements.items():
            text = text.replace(emoji, replacement)
    return text


@dataclass
class TestExecutionResults:
    """Test execution results summary."""

    total: int
    passed: int
    failed: int
    skipped: int
    errors: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate test success rate percentage."""
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100

    @property
    def completion_rate(self) -> float:
        """Calculate test completion rate (non-skipped) percentage."""
        if self.total == 0:
            return 0.0
        completed = self.passed + self.failed + self.errors
        return (completed / self.total) * 100


@dataclass
class CoverageData:
    """Code coverage metrics."""

    total: float
    line: float
    branch: float
    missing_lines: int = 0

    @property
    def coverage_grade(self) -> str:
        """Return coverage grade based on total coverage."""
        if self.total >= 90:
            return "A"
        elif self.total >= 80:
            return "B"
        elif self.total >= 70:
            return "C"
        elif self.total >= 60:
            return "D"
        else:
            return "F"


@dataclass
class ExecutionTimes:
    """CI execution time breakdown."""

    total: float
    setup: float
    tests: float
    quality_checks: float
    security_scans: float
    reporting: float

    def get_breakdown_percentages(self) -> dict[str, float]:
        """Get time breakdown as percentages."""
        if self.total == 0:
            return dict.fromkeys(
                ["setup", "tests", "quality_checks", "security_scans", "reporting"], 0.0
            )

        return {
            "setup": (self.setup / self.total) * 100,
            "tests": (self.tests / self.total) * 100,
            "quality_checks": (self.quality_checks / self.total) * 100,
            "security_scans": (self.security_scans / self.total) * 100,
            "reporting": (self.reporting / self.total) * 100,
        }


@dataclass
class SecurityResults:
    """Security scan results summary."""

    bandit_issues: int = 0
    safety_vulnerabilities: int = 0
    pip_audit_vulnerabilities: int = 0
    secrets_detected: int = 0

    @property
    def total_issues(self) -> int:
        """Total security issues found."""
        return (
            self.bandit_issues
            + self.safety_vulnerabilities
            + self.pip_audit_vulnerabilities
            + self.secrets_detected
        )

    @property
    def security_status(self) -> str:
        """Overall security status."""
        if self.total_issues == 0:
            return "🛡️ SECURE"
        elif self.total_issues <= 5:
            return "⚠️ MINOR ISSUES"
        elif self.total_issues <= 15:
            return "🚨 MODERATE RISK"
        else:
            return "🔴 HIGH RISK"


@dataclass
class OptimizationRecommendations:
    """CI optimization recommendations."""

    recommendations: list[str]
    potential_time_savings: float = 0.0

    def add_recommendation(
        self, recommendation: str, time_savings: float = 0.0
    ) -> None:
        """Add a new optimization recommendation."""
        self.recommendations.append(recommendation)
        self.potential_time_savings += time_savings


class CIReporter:
    """Generates comprehensive CI execution summaries and reports."""

    def __init__(self, reports_dir: str = "reports"):
        """Initialize CI reporter with reports directory."""
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(exist_ok=True)

    def generate_ci_summary(
        self,
        test_results: TestExecutionResults,
        coverage_data: CoverageData,
        execution_times: ExecutionTimes,
        security_results: SecurityResults | None = None,
        benchmark_results: dict[str, Any] | None = None,
        environment_info: dict[str, str] | None = None,
    ) -> str:
        """
        Generate comprehensive CI summary report.

        Args:
            test_results: Test execution results
            coverage_data: Code coverage metrics
            execution_times: CI execution time breakdown
            security_results: Security scan results (optional)
            benchmark_results: Performance benchmark results (optional)
            environment_info: Environment information (optional)

        Returns:
            Formatted markdown CI summary report
        """
        summary = []

        # Header
        summary.append("# 🚀 CI Execution Summary\n")

        # Quick status overview
        self._add_status_overview(
            summary, test_results, coverage_data, security_results
        )

        # Test results section
        self._add_test_results_section(summary, test_results)

        # Coverage section
        self._add_coverage_section(summary, coverage_data)

        # Execution time analysis
        self._add_execution_time_section(summary, execution_times)

        # Security results (if available)
        if security_results:
            self._add_security_section(summary, security_results)

        # Performance benchmarks (if available)
        if benchmark_results:
            self._add_benchmark_section(summary, benchmark_results)

        # Environment information
        if environment_info:
            self._add_environment_section(summary, environment_info)

        # Optimization recommendations
        recommendations = self._generate_optimization_recommendations(
            execution_times, test_results
        )
        self._add_optimization_section(summary, recommendations)

        # Ensure Windows compatibility
        result = "\n".join(summary)
        return _ensure_windows_compatible_text(result)

    def _add_status_overview(
        self,
        summary: list[str],
        test_results: TestExecutionResults,
        coverage_data: CoverageData,
        security_results: SecurityResults | None,
    ) -> None:
        """Add quick status overview section."""
        summary.append("## 📊 Quick Status Overview\n")

        # Overall status
        overall_status = (
            "✅ PASSING"
            if test_results.failed == 0 and test_results.errors == 0
            else "❌ FAILING"
        )
        coverage_status = (
            f"📈 {coverage_data.coverage_grade} Grade"
            if coverage_data.total > 0
            else "📉 No Coverage"
        )
        security_status = (
            security_results.security_status if security_results else "🔍 Not Scanned"
        )

        summary.extend(
            [
                f"**Overall Status:** {overall_status}",
                f"**Test Success Rate:** {test_results.success_rate:.1f}%",
                f"**Coverage Grade:** {coverage_status} ({coverage_data.total:.1f}%)",
                f"**Security Status:** {security_status}",
                "",
            ]
        )

    def _add_test_results_section(
        self, summary: list[str], test_results: TestExecutionResults
    ) -> None:
        """Add detailed test results section."""
        summary.extend(
            [
                "## 🧪 Test Results\n",
                "| Metric | Count | Percentage |",
                "|--------|-------|------------|",
                f"| **Total Tests** | {test_results.total} | 100.0% |",
                f"| **Passed** | {test_results.passed} | {test_results.success_rate:.1f}% |",
                f"| **Failed** | {test_results.failed} | {(test_results.failed / test_results.total * 100) if test_results.total > 0 else 0:.1f}% |",
                f"| **Skipped** | {test_results.skipped} | {(test_results.skipped / test_results.total * 100) if test_results.total > 0 else 0:.1f}% |",
                f"| **Errors** | {test_results.errors} | {(test_results.errors / test_results.total * 100) if test_results.total > 0 else 0:.1f}% |",
                "",
            ]
        )

        # Test health indicators
        if test_results.completion_rate < 90:
            summary.append(
                "⚠️ **High skip rate detected** - Consider reviewing skipped tests\n"
            )
        if test_results.success_rate < 95:
            summary.append("🚨 **Low success rate** - Immediate attention required\n")

    def _add_coverage_section(
        self, summary: list[str], coverage_data: CoverageData
    ) -> None:
        """Add code coverage analysis section."""
        summary.extend(
            [
                "## 📈 Coverage Report\n",
                "| Coverage Type | Percentage | Grade |",
                "|---------------|------------|-------|",
                f"| **Overall** | {coverage_data.total:.1f}% | {coverage_data.coverage_grade} |",
                f"| **Line Coverage** | {coverage_data.line:.1f}% | - |",
                f"| **Branch Coverage** | {coverage_data.branch:.1f}% | - |",
                "",
            ]
        )

        if coverage_data.missing_lines > 0:
            summary.append(
                f"📝 **Missing Lines:** {coverage_data.missing_lines} lines need coverage\n"
            )

        # Coverage recommendations
        if coverage_data.total < 80:
            summary.append(
                "🎯 **Recommendation:** Increase test coverage to reach 80% minimum threshold\n"
            )
        elif coverage_data.total < 90:
            summary.append(
                "🎯 **Recommendation:** Target 90% coverage for production-ready code\n"
            )

    def _add_execution_time_section(
        self, summary: list[str], execution_times: ExecutionTimes
    ) -> None:
        """Add execution time analysis section."""
        breakdown = execution_times.get_breakdown_percentages()

        summary.extend(
            [
                "## ⏱️ Execution Time Analysis\n",
                f"**Total CI Time:** {execution_times.total:.2f}s ({execution_times.total / 60:.1f} minutes)\n",
                "| Phase | Time (s) | Percentage |",
                "|-------|----------|------------|",
                f"| **Setup** | {execution_times.setup:.2f}s | {breakdown['setup']:.1f}% |",
                f"| **Tests** | {execution_times.tests:.2f}s | {breakdown['tests']:.1f}% |",
                f"| **Quality Checks** | {execution_times.quality_checks:.2f}s | {breakdown['quality_checks']:.1f}% |",
                f"| **Security Scans** | {execution_times.security_scans:.2f}s | {breakdown['security_scans']:.1f}% |",
                f"| **Reporting** | {execution_times.reporting:.2f}s | {breakdown['reporting']:.1f}% |",
                "",
            ]
        )

    def _add_security_section(
        self, summary: list[str], security_results: SecurityResults
    ) -> None:
        """Add security scan results section."""
        summary.extend(
            [
                "## 🛡️ Security Scan Results\n",
                f"**Overall Status:** {security_results.security_status}\n",
                "| Scan Type | Issues Found |",
                "|-----------|--------------|",
                f"| **Static Analysis (Bandit)** | {security_results.bandit_issues} |",
                f"| **Dependency Vulnerabilities (Safety)** | {security_results.safety_vulnerabilities} |",
                f"| **Package Audit (pip-audit)** | {security_results.pip_audit_vulnerabilities} |",
                f"| **Secrets Detection** | {security_results.secrets_detected} |",
                f"| **Total Issues** | **{security_results.total_issues}** |",
                "",
            ]
        )

        if security_results.total_issues > 0:
            summary.append(
                "🔍 **Action Required:** Review security artifacts for detailed issue reports\n"
            )

    def _add_benchmark_section(
        self, summary: list[str], benchmark_results: dict[str, Any]
    ) -> None:
        """Add performance benchmark results section."""
        summary.extend(["## 🏃 Performance Benchmarks\n"])

        if "regressions" in benchmark_results and benchmark_results["regressions"]:
            regression_count = len(benchmark_results["regressions"])
            summary.append(
                f"⚠️ **{regression_count} Performance Regression(s) Detected**\n"
            )
        else:
            summary.append("✅ **No Performance Regressions Detected**\n")

        if "analysis" in benchmark_results:
            analysis = benchmark_results["analysis"]
            benchmark_count = len(analysis)
            summary.append(f"📊 **Benchmarks Executed:** {benchmark_count}\n")

        summary.append("📋 See benchmark artifacts for detailed performance analysis\n")

    def _add_environment_section(
        self, summary: list[str], environment_info: dict[str, str]
    ) -> None:
        """Add environment information section."""
        summary.extend(
            [
                "## 🌍 Environment Information\n",
                "| Component | Version/Value |",
                "|-----------|---------------|",
            ]
        )

        for key, value in environment_info.items():
            summary.append(f"| **{key.replace('_', ' ').title()}** | {value} |")

        summary.append("")

    def _generate_optimization_recommendations(
        self, execution_times: ExecutionTimes, test_results: TestExecutionResults
    ) -> OptimizationRecommendations:
        """Generate CI optimization recommendations based on metrics."""
        recommendations = OptimizationRecommendations([])
        breakdown = execution_times.get_breakdown_percentages()

        # Setup time optimization
        if breakdown["setup"] > 30:
            recommendations.add_recommendation(
                "🔧 **Setup Time High:** Consider improving dependency caching or using pre-built environments",
                execution_times.setup * 0.3,
            )

        # Test execution optimization
        if breakdown["tests"] > 60 and execution_times.total > 300:  # > 5 minutes
            recommendations.add_recommendation(
                "🏃 **Test Suite Slow:** Consider parallel test execution or test suite optimization",
                execution_times.tests * 0.25,
            )

        # High skip rate
        if test_results.skipped > test_results.total * 0.2:  # > 20% skipped
            recommendations.add_recommendation(
                "🔍 **High Skip Rate:** Review and enable skipped tests or remove obsolete ones"
            )

        # Security scan time
        if breakdown["security_scans"] > 20:
            recommendations.add_recommendation(
                "🛡️ **Security Scans Slow:** Consider caching security databases or parallel scanning",
                execution_times.security_scans * 0.2,
            )

        # Overall CI time
        if execution_times.total > 900:  # > 15 minutes
            recommendations.add_recommendation(
                "⚡ **CI Pipeline Slow:** Consider splitting into parallel jobs or optimizing critical path"
            )

        return recommendations

    def _add_optimization_section(
        self, summary: list[str], recommendations: OptimizationRecommendations
    ) -> None:
        """Add optimization recommendations section."""
        summary.extend(["## 💡 Optimization Opportunities\n"])

        if not recommendations.recommendations:
            summary.append(
                "✅ **No immediate optimizations needed** - CI pipeline is performing well\n"
            )
            return

        if recommendations.potential_time_savings > 0:
            summary.append(
                f"⏱️ **Potential Time Savings:** {recommendations.potential_time_savings:.1f}s\n"
            )

        for rec in recommendations.recommendations:
            summary.append(f"- {rec}")

        summary.append("")

    def save_summary_to_github_step(
        self, summary: str, step_summary_file: str | None = None
    ) -> None:
        """
        Save CI summary to GitHub Actions step summary.

        Args:
            summary: The CI summary content
            step_summary_file: Path to GitHub step summary file (defaults to GITHUB_STEP_SUMMARY env var)
        """
        step_summary_path = step_summary_file or os.environ.get("GITHUB_STEP_SUMMARY")

        if step_summary_path:
            try:
                with open(step_summary_path, "a", encoding="utf-8") as f:
                    f.write("\n" + summary + "\n")
            except Exception as e:
                print(f"Warning: Could not write to GitHub step summary: {e}")
        else:
            print("GitHub step summary file not available")

    def save_summary_to_file(
        self, summary: str, filename: str = "ci-summary.md"
    ) -> Path:
        """
        Save CI summary to a file in the reports directory.

        Args:
            summary: The CI summary content
            filename: Output filename

        Returns:
            Path to the saved file
        """
        output_path = self.reports_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(summary)
        return output_path

    def generate_metrics_json(
        self,
        test_results: TestExecutionResults,
        coverage_data: CoverageData,
        execution_times: ExecutionTimes,
        security_results: SecurityResults | None = None,
    ) -> dict[str, Any]:
        """
        Generate machine-readable metrics in JSON format.

        Args:
            test_results: Test execution results
            coverage_data: Code coverage metrics
            execution_times: CI execution time breakdown
            security_results: Security scan results (optional)

        Returns:
            Dictionary containing all CI metrics
        """
        metrics = {
            "timestamp": time.time(),
            "test_results": asdict(test_results),
            "coverage_data": asdict(coverage_data),
            "execution_times": asdict(execution_times),
            "performance_metrics": {
                "total_ci_time": execution_times.total,
                "test_success_rate": test_results.success_rate,
                "coverage_grade": coverage_data.coverage_grade,
            },
        }

        if security_results:
            metrics["security_results"] = asdict(security_results)

        return metrics

    def load_test_results_from_pytest_json(
        self, json_file: Path
    ) -> TestExecutionResults:
        """
        Load test results from pytest JSON report.

        Args:
            json_file: Path to pytest JSON report file

        Returns:
            TestExecutionResults object
        """
        if not json_file.exists():
            return TestExecutionResults(0, 0, 0, 0, 0)

        try:
            with open(json_file) as f:
                data = json.load(f)

            summary = data.get("summary", {})
            return TestExecutionResults(
                total=summary.get("total", 0),
                passed=summary.get("passed", 0),
                failed=summary.get("failed", 0),
                skipped=summary.get("skipped", 0),
                errors=summary.get("error", 0),
            )
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not parse pytest JSON report: {e}")
            return TestExecutionResults(0, 0, 0, 0, 0)

    def load_coverage_from_xml(self, xml_file: Path) -> CoverageData:
        """
        Load coverage data from coverage XML report.

        Args:
            xml_file: Path to coverage XML report file

        Returns:
            CoverageData object
        """
        if not xml_file.exists():
            return CoverageData(0.0, 0.0, 0.0, 0)

        try:
            # Safe XML parsing for coverage data
            try:
                from defusedxml.ElementTree import parse as safe_parse

                tree = safe_parse(xml_file)
                root = tree.getroot()
            except ImportError:
                # Fallback to standard library with warning
                import xml.etree.ElementTree as ET  # nosec B405

                tree = ET.parse(xml_file)  # nosec B314
                root = tree.getroot()

            # Extract coverage percentages
            line_rate = float(root.get("line-rate", 0)) * 100
            branch_rate = float(root.get("branch-rate", 0)) * 100

            # Calculate overall coverage (weighted average)
            total_coverage = (line_rate + branch_rate) / 2

            return CoverageData(
                total=total_coverage,
                line=line_rate,
                branch=branch_rate,
                missing_lines=0,  # Would need more complex parsing
            )
        except Exception as e:
            print(f"Warning: Could not parse coverage XML report: {e}")
            return CoverageData(0.0, 0.0, 0.0, 0)

    def load_security_results_from_reports(self, reports_dir: Path) -> SecurityResults:
        """
        Load security results from multiple security report files.

        Args:
            reports_dir: Directory containing security report files

        Returns:
            SecurityResults object
        """
        security_results = SecurityResults()

        # Load Bandit results
        bandit_file = reports_dir / "bandit-report.json"
        if bandit_file.exists():
            try:
                with open(bandit_file) as f:
                    bandit_data = json.load(f)
                security_results.bandit_issues = len(bandit_data.get("results", []))
            except Exception as e:
                print(f"Warning: Could not parse Bandit report: {e}")

        # Load Safety results
        safety_file = reports_dir / "safety-report.json"
        if safety_file.exists():
            try:
                with open(safety_file) as f:
                    safety_data = json.load(f)
                # Safety format can vary, check for vulnerabilities
                if isinstance(safety_data, list):
                    security_results.safety_vulnerabilities = len(safety_data)
                elif isinstance(safety_data, dict):
                    security_results.safety_vulnerabilities = len(
                        safety_data.get("vulnerabilities", [])
                    )
            except Exception as e:
                print(f"Warning: Could not parse Safety report: {e}")

        # Load pip-audit results
        pip_audit_file = reports_dir / "pip-audit-report.json"
        if pip_audit_file.exists():
            try:
                with open(pip_audit_file) as f:
                    pip_audit_data = json.load(f)
                security_results.pip_audit_vulnerabilities = len(
                    pip_audit_data.get("vulnerabilities", [])
                )
            except Exception as e:
                print(f"Warning: Could not parse pip-audit report: {e}")

        return security_results
