import argparse
from typing import Any

from llm_task_framework.reporting.benchmark_analyzer import BenchmarkAnalyzer
from llm_task_framework.reporting.benchmark_reporter import BenchmarkReporter


def main() -> None:
    """
    Analyzes benchmark results and generates a report.
    """
    parser = argparse.ArgumentParser(
        description="Analyze benchmark results and generate a report."
    )
    parser.add_argument(
        "--baseline", required=True, help="Path to the baseline benchmark JSON file."
    )
    parser.add_argument(
        "--current", required=True, help="Path to the current benchmark JSON file."
    )
    parser.add_argument(
        "--regression-threshold",
        type=float,
        default=0.1,
        help="Regression threshold (percentage).",
    )
    args: argparse.Namespace = parser.parse_args()

    analyzer = BenchmarkAnalyzer(regression_threshold=args.regression_threshold)
    reporter = BenchmarkReporter()

    baseline_data: list[dict[str, Any]] = analyzer.load_benchmark_data(args.baseline)
    current_data: list[dict[str, Any]] = analyzer.load_benchmark_data(args.current)

    analysis_results: dict[str, Any] = analyzer.analyze_results(baseline_data, current_data)
    report: str = reporter.generate_report(analysis_results)

    print(report)


if __name__ == "__main__":
    main()
