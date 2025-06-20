from typing import Any


class BenchmarkReporter:
    """
    Generates benchmark reports.
    """

    def _format_value(self, value: float | None, precision: int = 6) -> str:
        """Formats a float value or returns 'N/A' if None."""
        return f"{value:.{precision}f}" if value is not None else "N/A"

    def _format_change(self, change: float, threshold_type: str) -> str:
        """Formats the change value based on its type."""
        if threshold_type == "percentage":
            return f"{change:+.2%}"
        return f"{change:+.6f}"

    def _get_severity_emoji(self, severity: str) -> str:
        """Returns an emoji for the given severity level."""
        return {"warning": "⚠️", "error": "❌", "critical": "🚨"}.get(
            severity.lower(), ""
        )

    def generate_report(self, analysis_results: dict[str, Any]) -> str:
        """
        Generates a report showing current vs historical performance.

        Args:
            analysis_results: A dictionary containing analysis results.

        Returns:
            A string containing the report in Markdown format.
        """
        report = "## 🚀 Performance Benchmark Report\n\n"
        analysis = analysis_results["analysis"]
        regressions = analysis_results["regressions"]

        # Summary Table
        report += "### 📊 Benchmark Summary\n"
        report += "| Benchmark | Metric | Baseline | Current | Change |\n"
        report += "|-----------|--------|----------|---------|--------|\n"

        for name, result in sorted(analysis.items()):
            current_stats = result["current_stats"]
            baseline_stats = result["baseline_stats"]

            # For simplicity, we'll show the mean in the summary table.
            # The regressions section will have details on what triggered.
            metric_to_display = "mean"
            current_val = current_stats.get(metric_to_display)
            baseline_val = (
                baseline_stats.get(metric_to_display) if baseline_stats else None
            )

            change_str = "N/A"
            if (
                current_val is not None
                and baseline_val is not None
                and baseline_val > 0
            ):
                change = (current_val - baseline_val) / baseline_val
                change_str = f"{change:+.2%}"

            report += (
                f"| `{name}` | {metric_to_display} | "
                f"{self._format_value(baseline_val)} | {self._format_value(current_val)} | "
                f"{change_str} |\n"
            )

        # Regressions Section
        if regressions:
            report += "\n### ❗ Regressions Detected\n"
            report += "| Severity | Benchmark | Metric | Threshold | Baseline | Current | Change |\n"
            report += "|----------|-----------|--------|-----------|----------|---------|--------|\n"

            sorted_regressions = sorted(regressions, key=lambda r: r["name"])
            for reg in sorted_regressions:
                severity_emoji = self._get_severity_emoji(reg["severity"])
                threshold_str = (
                    f">{reg['threshold']:.2%}"
                    if reg["threshold_type"] == "percentage"
                    else f">{reg['threshold']}"
                )
                change_str = self._format_change(reg["change"], reg["threshold_type"])

                report += (
                    f"| {severity_emoji} {reg['severity'].upper()} | `{reg['name']}` | "
                    f"`{reg['metric']}` | {threshold_str} ({reg['threshold_type']}) | "
                    f"{self._format_value(reg['baseline_value'])} | {self._format_value(reg['current_value'])} | "
                    f"{change_str} |\n"
                )
        else:
            report += "\n### ✅ No Performance Regressions Detected\n"
            report += (
                "All benchmarks are within the configured performance thresholds.\n"
            )

        return report
