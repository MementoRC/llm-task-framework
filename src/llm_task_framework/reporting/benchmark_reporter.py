from typing import Any


class BenchmarkReporter:
    """
    Generates benchmark reports.
    """

    def generate_report(self, analysis_results: dict[str, Any]) -> str:
        """
        Generates a report showing current vs historical performance.

        Args:
            analysis_results: A dictionary containing analysis results.

        Returns:
            A string containing the report.
        """
        report = "## Performance Benchmark Report\n\n"
        report += "| Benchmark | Baseline (mean) | Current (mean) | % Change |\n"
        report += "|-----------|-----------------|----------------|----------|\n"

        analysis = analysis_results["analysis"]
        regressions = analysis_results["regressions"]

        for name, result in analysis.items():
            baseline = result["baseline"]
            current = result["current"]
            percentage_change = result["percentage_change"]

            baseline_str = f"{baseline:.6f}" if baseline is not None else "N/A"
            current_str = f"{current:.6f}"
            percentage_change_str = f"{percentage_change:.2%}" if percentage_change is not None else "N/A"

            report += f"| {name} | {baseline_str} | {current_str} | {percentage_change_str} |\n"

        if regressions:
            report += "\n### Regressions Detected\n"
            for regression in regressions:
                report += f"- {regression['name']}: {regression['percentage_change']:.2%} change (Baseline: {regression['baseline_mean']:.6f}, Current: {regression['current_mean']:.6f})\n"
        else:
            report += "\nNo performance regressions detected.\n"

        return report
