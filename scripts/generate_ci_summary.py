#!/usr/bin/env python3
"""Script to generate comprehensive CI summary reports."""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from llm_task_framework.reporting.ci_reporter import (
    CIReporter,
    CoverageData,
    ExecutionTimes,
    SecurityResults,
    TestExecutionResults,
)


def load_execution_times_from_env() -> ExecutionTimes:
    """Load execution times from environment variables or defaults."""
    return ExecutionTimes(
        total=float(os.environ.get("CI_TOTAL_TIME", 0)),
        setup=float(os.environ.get("CI_SETUP_TIME", 0)),
        tests=float(os.environ.get("CI_TEST_TIME", 0)),
        quality_checks=float(os.environ.get("CI_QUALITY_TIME", 0)),
        security_scans=float(os.environ.get("CI_SECURITY_TIME", 0)),
        reporting=float(os.environ.get("CI_REPORTING_TIME", 0)),
    )


def load_environment_info() -> dict[str, str]:
    """Load environment information from GitHub Actions context."""
    env_info = {}

    # GitHub Actions environment variables
    if "GITHUB_ACTIONS" in os.environ:
        env_info.update(
            {
                "ci_system": "GitHub Actions",
                "runner_os": os.environ.get("RUNNER_OS", "Unknown"),
                "python_version": os.environ.get(
                    "PYTHON_VERSION", sys.version.split()[0]
                ),
                "github_ref": os.environ.get("GITHUB_REF", "Unknown"),
                "github_sha": os.environ.get("GITHUB_SHA", "Unknown")[:8],
                "workflow": os.environ.get("GITHUB_WORKFLOW", "Unknown"),
                "job": os.environ.get("GITHUB_JOB", "Unknown"),
            }
        )
    else:
        env_info.update(
            {
                "ci_system": "Local Development",
                "python_version": sys.version.split()[0],
                "platform": sys.platform,
            }
        )

    return env_info


def load_benchmark_results(benchmark_file: Path | None) -> dict | None:
    """Load benchmark results if available."""
    if not benchmark_file or not benchmark_file.exists():
        return None

    try:
        with open(benchmark_file) as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load benchmark results: {e}")
        return None


def create_sample_data() -> tuple[
    TestExecutionResults, CoverageData, ExecutionTimes, SecurityResults
]:
    """Create sample data for testing purposes."""
    test_results = TestExecutionResults(
        total=150, passed=142, failed=3, skipped=5, errors=0
    )

    coverage_data = CoverageData(total=85.7, line=88.2, branch=83.1, missing_lines=127)

    execution_times = ExecutionTimes(
        total=540.5,
        setup=120.3,
        tests=298.7,
        quality_checks=87.2,
        security_scans=25.8,
        reporting=8.5,
    )

    security_results = SecurityResults(
        bandit_issues=2,
        safety_vulnerabilities=0,
        pip_audit_vulnerabilities=1,
        secrets_detected=0,
    )

    return test_results, coverage_data, execution_times, security_results


def main() -> None:
    """Generate CI summary report."""
    parser = argparse.ArgumentParser(
        description="Generate comprehensive CI summary report",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--pytest-json", type=Path, help="Path to pytest JSON report file"
    )
    parser.add_argument(
        "--coverage-xml", type=Path, help="Path to coverage XML report file"
    )
    parser.add_argument(
        "--benchmark-json", type=Path, help="Path to benchmark JSON results file"
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default="reports",
        help="Directory containing security and other reports",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        help="Output file for CI summary (default: reports/ci-summary.md)",
    )
    parser.add_argument(
        "--metrics-json",
        type=Path,
        help="Output file for machine-readable metrics JSON",
    )
    parser.add_argument(
        "--github-step-summary",
        action="store_true",
        help="Write summary to GitHub Actions step summary",
    )
    parser.add_argument(
        "--sample-data",
        action="store_true",
        help="Generate report with sample data (for testing)",
    )
    parser.add_argument(
        "--execution-times",
        type=str,
        help="JSON string or file path containing execution times",
    )

    args = parser.parse_args()

    # Initialize reporter
    reporter = CIReporter(str(args.reports_dir))

    if args.sample_data:
        # Use sample data for testing
        test_results, coverage_data, execution_times, security_results = (
            create_sample_data()
        )
        print("Using sample data for demonstration...")
    else:
        # Load real data from files and environment
        test_results = TestExecutionResults(0, 0, 0, 0, 0)
        coverage_data = CoverageData(0.0, 0.0, 0.0, 0)
        security_results = SecurityResults()

        # Load test results
        if args.pytest_json:
            test_results = reporter.load_test_results_from_pytest_json(args.pytest_json)

        # Load coverage data
        if args.coverage_xml:
            coverage_data = reporter.load_coverage_from_xml(args.coverage_xml)

        # Load execution times
        if args.execution_times:
            try:
                if args.execution_times.startswith("{"):
                    # JSON string
                    times_data = json.loads(args.execution_times)
                else:
                    # File path
                    with open(Path(args.execution_times)) as f:
                        times_data = json.load(f)

                execution_times = ExecutionTimes(**times_data)
            except Exception as e:
                print(f"Warning: Could not load execution times: {e}")
                execution_times = load_execution_times_from_env()
        else:
            execution_times = load_execution_times_from_env()

        # Load security results
        if args.reports_dir.exists():
            security_results = reporter.load_security_results_from_reports(
                args.reports_dir
            )

    # Load optional data
    benchmark_results = load_benchmark_results(args.benchmark_json)
    environment_info = load_environment_info()

    # Generate CI summary
    start_time = time.time()

    summary = reporter.generate_ci_summary(
        test_results=test_results,
        coverage_data=coverage_data,
        execution_times=execution_times,
        security_results=security_results,
        benchmark_results=benchmark_results,
        environment_info=environment_info,
    )

    generation_time = time.time() - start_time
    print(f"CI summary generated in {generation_time:.2f}s")

    # Output summary
    print("\n" + "=" * 80)
    print("CI SUMMARY REPORT")
    print("=" * 80)
    print(summary)

    # Save to file
    output_file = args.output_file or (args.reports_dir / "ci-summary.md")
    output_path = reporter.save_summary_to_file(summary, output_file.name)
    print(f"\n📄 Summary saved to: {output_path}")

    # Save metrics JSON
    if args.metrics_json:
        metrics = reporter.generate_metrics_json(
            test_results, coverage_data, execution_times, security_results
        )
        with open(args.metrics_json, "w") as f:
            json.dump(metrics, f, indent=2)
        print(f"📊 Metrics saved to: {args.metrics_json}")

    # Write to GitHub step summary
    if args.github_step_summary:
        reporter.save_summary_to_github_step(summary)
        print("📝 Summary written to GitHub Actions step summary")

    # Exit with appropriate code based on results
    if test_results.failed > 0 or test_results.errors > 0:
        print(
            f"\n❌ CI failed with {test_results.failed} failed tests and {test_results.errors} errors"
        )
        sys.exit(1)
    elif security_results.total_issues > 10:
        print(
            f"\n⚠️ CI passed but {security_results.total_issues} security issues detected"
        )
        # Don't fail CI for security issues, but warn
    else:
        print("\n✅ CI passed successfully")


if __name__ == "__main__":
    main()
