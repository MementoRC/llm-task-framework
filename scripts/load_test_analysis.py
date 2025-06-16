"""
Analyzes Locust load test results and generates a summary report.

This script parses the JSON output from a Locust run, calculates key metrics,
compares them against a baseline, and generates a markdown summary.

Usage:
    python scripts/load_test_analysis.py \
        --current-report <path_to_current_report.json> \
        --baseline-report <path_to_baseline_report.json> \
        --output-summary <path_to_summary.md>
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

# Thresholds for regression detection
REGRESSION_THRESHOLDS = {
    "avg_response_time": 1.2,  # 20% increase
    "failure_rate": 1.5,  # 50% increase (relative)
    "rps": 0.8,  # 20% decrease
}


def parse_locust_report(report_path: Path) -> Optional[Dict[str, Any]]:
    """Parses a Locust JSON report file."""
    if not report_path or not report_path.exists():
        return None
    try:
        with open(report_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def get_stats_summary(report_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts a summary of key statistics from the report."""
    stats = report_data.get("stats", [])
    total_stats = next((s for s in stats if s["name"] == "Aggregated"), None)

    if not total_stats:
        return {
            "total_requests": 0,
            "total_failures": 0,
            "avg_response_time": 0,
            "median_response_time": 0,
            "min_response_time": 0,
            "max_response_time": 0,
            "rps": 0,
            "failure_rate": 0,
        }

    total_requests = total_stats.get("num_requests", 0)
    total_failures = total_stats.get("num_failures", 0)
    failure_rate = (total_failures / total_requests) if total_requests > 0 else 0

    return {
        "total_requests": total_requests,
        "total_failures": total_failures,
        "avg_response_time": total_stats.get("avg_response_time", 0),
        "median_response_time": total_stats.get("median_response_time", 0),
        "min_response_time": total_stats.get("min_response_time", 0),
        "max_response_time": total_stats.get("max_response_time", 0),
        "rps": total_stats.get("total_rps", 0),
        "failure_rate": failure_rate,
    }


def compare_summaries(
    current: Dict[str, Any], baseline: Dict[str, Any]
) -> Dict[str, Any]:
    """Compares current summary with a baseline and detects regressions."""
    comparison = {}
    regressions = []

    for key in current:
        if key in baseline and isinstance(current[key], (int, float)):
            current_val = current[key]
            baseline_val = baseline[key]
            delta = current_val - baseline_val

            if baseline_val != 0:
                change_pct = (delta / baseline_val) * 100
            elif current_val != 0:
                change_pct = float("inf")
            else:
                change_pct = 0.0

            comparison[key] = {
                "current": current_val,
                "baseline": baseline_val,
                "delta": delta,
                "change_pct": change_pct,
            }

            # Regression checks
            if (
                key == "avg_response_time"
                and current_val > baseline_val * REGRESSION_THRESHOLDS["avg_response_time"]
            ):
                regressions.append(
                    f"Average response time increased by {change_pct:.2f}%"
                )
            if (
                key == "failure_rate"
                and current_val > 0
                and current_val > baseline_val * REGRESSION_THRESHOLDS["failure_rate"]
            ):
                regressions.append(f"Failure rate increased by {change_pct:.2f}%")
            if key == "rps" and current_val < baseline_val * REGRESSION_THRESHOLDS["rps"]:
                regressions.append(
                    f"Requests per second (RPS) decreased by {-change_pct:.2f}%"
                )

    return {"comparison": comparison, "regressions": regressions}


def generate_markdown_summary(
    current_summary: Dict[str, Any],
    comparison_results: Optional[Dict[str, Any]] = None,
) -> str:
    """Generates a markdown summary of the load test results."""

    def format_val(key: str, value: Any) -> str:
        if "time" in key:
            return f"{value:,.2f} ms"
        if "rate" in key:
            return f"{value:.2%}"
        if "rps" in key:
            return f"{value:,.2f}"
        return f"{value:,}"

    summary = "### 📈 Load Test Results\n\n"
    summary += "| Metric | Value |\n"
    summary += "|--------|-------|\n"
    for key, value in current_summary.items():
        metric_name = key.replace("_", " ").title()
        summary += f"| {metric_name} | {format_val(key, value)} |\n"

    if comparison_results and "comparison" in comparison_results:
        summary += "\n### 📊 Baseline Comparison\n\n"
        summary += "| Metric | Current | Baseline | Change |\n"
        summary += "|--------|---------|----------|--------|\n"
        for key, data in comparison_results["comparison"].items():
            metric_name = key.replace("_", " ").title()
            change_str = f"{data['change_pct']:+.2f}%"
            summary += f"| {metric_name} | {format_val(key, data['current'])} | {format_val(key, data['baseline'])} | {change_str} |\n"

    if comparison_results and comparison_results.get("regressions"):
        summary += "\n### ⚠️ Performance Regressions Detected\n\n"
        for reg in comparison_results["regressions"]:
            summary += f"- {reg}\n"
    elif comparison_results:
        summary += "\n### ✅ No Performance Regressions Detected\n"

    return summary


def main() -> None:
    """Main function to run the analysis."""
    parser = argparse.ArgumentParser(description="Analyze Locust load test results.")
    parser.add_argument(
        "--current-report",
        type=Path,
        required=True,
        help="Path to the current Locust JSON report.",
    )
    parser.add_argument(
        "--baseline-report",
        type=Path,
        help="Path to the baseline Locust JSON report for comparison.",
    )
    parser.add_argument(
        "--output-summary",
        type=Path,
        required=True,
        help="Path to write the output markdown summary.",
    )
    args = parser.parse_args()

    current_data = parse_locust_report(args.current_report)
    if not current_data:
        print(f"Error: Could not parse current report at {args.current_report}")
        return

    current_summary = get_stats_summary(current_data)
    comparison_results = None

    if args.baseline_report:
        baseline_data = parse_locust_report(args.baseline_report)
        if baseline_data:
            baseline_summary = get_stats_summary(baseline_data)
            comparison_results = compare_summaries(current_summary, baseline_summary)
        else:
            print(f"Warning: Could not parse baseline report at {args.baseline_report}")

    markdown_summary = generate_markdown_summary(current_summary, comparison_results)

    try:
        with open(args.output_summary, "w") as f:
            f.write(markdown_summary)
        print(f"Successfully generated summary at {args.output_summary}")
    except IOError as e:
        print(f"Error writing summary file: {e}")


if __name__ == "__main__":
    main()
