import argparse
import json
import sys
from typing import Any

from llm_task_framework.reporting.benchmark_analyzer import BenchmarkAnalyzer
from llm_task_framework.reporting.benchmark_reporter import BenchmarkReporter


def main() -> None:
    """
    Analyzes benchmark results and generates a report.
    """
    parser = argparse.ArgumentParser(
        description="Analyze benchmark results and generate a report.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--baseline", required=True, help="Path to the baseline benchmark JSON file."
    )
    parser.add_argument(
        "--current", required=True, help="Path to the current benchmark JSON file."
    )
    parser.add_argument(
        "--rules-file",
        help="Path to a JSON file containing regression detection rules.",
    )
    parser.add_argument(
        "--fail-on-severity",
        type=str,
        default="error",
        choices=["info", "warning", "error", "critical"],
        help="Fail CI if a regression of this severity or higher is detected.",
    )
    # Deprecated args, kept for backward compatibility but rules-file is preferred
    parser.add_argument(
        "--regression-threshold",
        type=float,
        help="DEPRECATED: Use --rules-file instead. Percentage threshold for mean.",
    )
    args: argparse.Namespace = parser.parse_args()

    if args.rules_file:
        with open(args.rules_file) as f:
            rules_data = json.load(f)
            # Support both a direct list and a dict with a "rules" key
            rules = rules_data.get("rules", rules_data)
    elif args.regression_threshold is not None:
        print(
            "Warning: --regression-threshold is deprecated. Use --rules-file for more control.",
            file=sys.stderr,
        )
        rules = [
            {
                "metric": "mean",
                "threshold_type": "percentage",
                "threshold": args.regression_threshold,
                "severity": "error",
            }
        ]
    else:
        # Default rules if nothing is provided
        rules = [
            {
                "metric": "mean",
                "threshold_type": "percentage",
                "threshold": 0.1,  # 10%
                "severity": "error",
            },
            {
                "metric": "stddev",
                "threshold_type": "percentage",
                "threshold": 0.5,  # 50%
                "severity": "warning",
            },
        ]

    analyzer = BenchmarkAnalyzer(regression_rules=rules)
    reporter = BenchmarkReporter()

    try:
        baseline_data: list[dict[str, Any]] = analyzer.load_benchmark_data(args.baseline)
    except FileNotFoundError:
        print(f"Baseline file not found at {args.baseline}. Assuming empty baseline.", file=sys.stderr)
        baseline_data = []

    current_data: list[dict[str, Any]] = analyzer.load_benchmark_data(args.current)

    if not current_data:
        print("No current benchmark data found. Skipping analysis.")
        return

    analysis_results: dict[str, Any] = analyzer.analyze_results(
        baseline_data, current_data
    )
    report: str = reporter.generate_report(analysis_results)

    print(report)

    # Fail CI if regressions meet the severity threshold
    severity_map = {"info": 0, "warning": 1, "error": 2, "critical": 3}
    fail_threshold = severity_map[args.fail_on_severity]

    has_critical_regression = any(
        severity_map.get(reg["severity"], 0) >= fail_threshold
        for reg in analysis_results["regressions"]
    )

    if has_critical_regression:
        print(
            f"\n❌ Failing CI due to regressions with severity '{args.fail_on_severity}' or higher.",
            file=sys.stderr,
        )
        sys.exit(1)
    else:
        print(
            f"\n✅ No regressions of severity '{args.fail_on_severity}' or higher detected."
        )


if __name__ == "__main__":
    main()
