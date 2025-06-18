"""Performance trend analysis and visualization module."""

import base64
import io
import json
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import matplotlib.dates as mdates  # type: ignore[import-not-found]
    import matplotlib.pyplot as plt  # type: ignore[import-not-found]

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class TrendDataStore:
    """Stores and retrieves historical performance data."""

    def __init__(self, data_dir: str | Path = ".performance_trends"):
        """Initialize the trend data store.

        Args:
            data_dir: Directory to store historical performance data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

    def store_benchmark_data(
        self, benchmark_data: list[dict[str, Any]], timestamp: str | None = None
    ) -> None:
        """Store benchmark data with timestamp.

        Args:
            benchmark_data: List of benchmark results from pytest-benchmark
            timestamp: ISO timestamp string, defaults to current time
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        # Create timestamped file
        filename = f"benchmark_{timestamp.replace(':', '-').replace('.', '-')}.json"
        filepath = self.data_dir / filename

        with open(filepath, "w") as f:
            json.dump(
                {"timestamp": timestamp, "benchmarks": benchmark_data}, f, indent=2
            )

    def get_historical_data(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Get historical benchmark data sorted by timestamp.

        Args:
            limit: Maximum number of historical entries to return

        Returns:
            List of historical data entries, most recent first
        """
        files = sorted(self.data_dir.glob("benchmark_*.json"), reverse=True)

        if limit:
            files = files[:limit]

        historical_data = []
        for file_path in files:
            try:
                with open(file_path) as f:
                    data = json.load(f)
                historical_data.append(data)
            except (json.JSONDecodeError, KeyError):
                continue

        return historical_data

    def get_benchmark_history(
        self, benchmark_name: str, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Get historical data for a specific benchmark.

        Args:
            benchmark_name: Name of the benchmark to get history for
            limit: Maximum number of historical entries to return

        Returns:
            List of historical entries for the benchmark, most recent first
        """
        historical_data = self.get_historical_data(limit)
        benchmark_history = []

        for entry in historical_data:
            for benchmark in entry.get("benchmarks", []):
                if benchmark.get("name") == benchmark_name:
                    benchmark_history.append(
                        {
                            "timestamp": entry["timestamp"],
                            "stats": benchmark.get("stats", {}),
                        }
                    )
                    break

        return benchmark_history


class TrendChartGenerator:
    """Generates trend charts for performance data."""

    def __init__(self) -> None:
        """Initialize the chart generator."""
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib is required for trend chart generation")

    def generate_trend_chart(
        self,
        test_name: str,
        historical_data: list[dict[str, Any]],
        metric: str = "mean",
        width: int = 12,
        height: int = 6,
    ) -> str:
        """Generate a trend chart showing performance over time.

        Args:
            test_name: Name of the test/benchmark
            historical_data: Historical data entries with timestamp and stats
            metric: Metric to plot (mean, min, max, stddev)
            width: Chart width in inches
            height: Chart height in inches

        Returns:
            Base64 encoded PNG image as data URL
        """
        if not historical_data:
            return self._generate_no_data_chart(test_name, width, height)

        # Extract data
        timestamps = []
        values = []
        stddevs = []

        for entry in reversed(historical_data):  # Oldest to newest for plotting
            try:
                timestamp = datetime.fromisoformat(entry["timestamp"])
                value = entry["stats"].get(metric)
                stddev = entry["stats"].get("stddev", 0)

                if value is not None:
                    timestamps.append(timestamp)
                    values.append(value)
                    stddevs.append(stddev)
            except (ValueError, KeyError):
                continue

        if not values:
            return self._generate_no_data_chart(test_name, width, height)

        # Create chart
        fig, ax = plt.subplots(figsize=(width, height))

        # Main trend line
        ax.plot(
            timestamps,
            values,
            "b-",
            linewidth=2,
            label=f"{metric.title()} Execution Time",
            marker="o",
        )

        # Confidence interval (if stddev available and metric is mean)
        if metric == "mean" and any(s > 0 for s in stddevs):
            upper_bound = [v + s for v, s in zip(values, stddevs, strict=False)]
            lower_bound = [v - s for v, s in zip(values, stddevs, strict=False)]
            ax.fill_between(
                timestamps,
                lower_bound,
                upper_bound,
                color="blue",
                alpha=0.2,
                label="Standard Deviation",
            )

        # Formatting
        ax.set_title(f"Performance Trend: {test_name}", fontsize=14, fontweight="bold")
        ax.set_xlabel("Date", fontsize=12)
        ax.set_ylabel(f"{metric.title()} Time (seconds)", fontsize=12)
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Format x-axis dates
        if len(timestamps) > 1:
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
            ax.xaxis.set_major_locator(
                mdates.DayLocator(interval=max(1, len(timestamps) // 10))
            )
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")

        # Add trend indicators
        if len(values) >= 2:
            # Simple linear trend
            recent_avg = sum(values[-3:]) / min(3, len(values))
            older_avg = sum(values[:3]) / min(3, len(values))

            if recent_avg > older_avg * 1.1:
                ax.text(
                    0.02,
                    0.98,
                    "📈 Trend: Degrading",
                    transform=ax.transAxes,
                    verticalalignment="top",
                    color="red",
                    fontweight="bold",
                )
            elif recent_avg < older_avg * 0.9:
                ax.text(
                    0.02,
                    0.98,
                    "📉 Trend: Improving",
                    transform=ax.transAxes,
                    verticalalignment="top",
                    color="green",
                    fontweight="bold",
                )
            else:
                ax.text(
                    0.02,
                    0.98,
                    "➡️ Trend: Stable",
                    transform=ax.transAxes,
                    verticalalignment="top",
                    color="blue",
                    fontweight="bold",
                )

        plt.tight_layout()

        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        plt.close(fig)

        return f"data:image/png;base64,{image_base64}"

    def _generate_no_data_chart(self, test_name: str, width: int, height: int) -> str:
        """Generate a placeholder chart when no data is available."""
        fig, ax = plt.subplots(figsize=(width, height))

        ax.text(
            0.5,
            0.5,
            f"No historical data available\nfor {test_name}",
            horizontalalignment="center",
            verticalalignment="center",
            transform=ax.transAxes,
            fontsize=14,
            color="gray",
        )

        ax.set_title(f"Performance Trend: {test_name}", fontsize=14, fontweight="bold")
        ax.set_xlabel("Date", fontsize=12)
        ax.set_ylabel("Time (seconds)", fontsize=12)
        ax.grid(True, alpha=0.3)

        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        plt.close(fig)

        return f"data:image/png;base64,{image_base64}"


class TrendAnalyzer:
    """Main class for performance trend analysis."""

    def __init__(self, data_dir: str | Path = ".performance_trends"):
        """Initialize the trend analyzer.

        Args:
            data_dir: Directory to store historical performance data
        """
        self.data_store = TrendDataStore(data_dir)
        self.chart_generator = TrendChartGenerator() if MATPLOTLIB_AVAILABLE else None

    def analyze_trends(
        self,
        benchmark_names: list[str] | None = None,
        metric: str = "mean",
        history_limit: int = 50,
    ) -> dict[str, Any]:
        """Analyze performance trends for benchmarks.

        Args:
            benchmark_names: List of benchmark names to analyze, or None for all
            metric: Metric to analyze (mean, min, max, stddev)
            history_limit: Maximum number of historical entries to consider

        Returns:
            Dictionary containing trend analysis results
        """
        if benchmark_names is None:
            # Get all unique benchmark names from recent history
            recent_data = self.data_store.get_historical_data(limit=5)
            benchmark_names_set: set[str] = set()
            for entry in recent_data:
                for benchmark in entry.get("benchmarks", []):
                    name = benchmark.get("name")
                    if name:
                        benchmark_names_set.add(name)
            benchmark_names = list(benchmark_names_set)

        analysis_results = {
            "metadata": {
                "metric": metric,
                "history_limit": history_limit,
                "analysis_timestamp": datetime.now().isoformat(),
            },
            "trends": {},
        }

        for benchmark_name in benchmark_names:
            history = self.data_store.get_benchmark_history(
                benchmark_name, history_limit
            )

            if len(history) < 2:
                trend_result = {
                    "status": "insufficient_data",
                    "data_points": len(history),
                    "trend_direction": "unknown",
                    "confidence": 0.0,
                }
            else:
                trend_result = self._analyze_single_trend(history, metric)

            analysis_results["trends"][benchmark_name] = trend_result

        return analysis_results

    def _analyze_single_trend(
        self, history: list[dict[str, Any]], metric: str
    ) -> dict[str, Any]:
        """Analyze trend for a single benchmark."""
        values = []
        timestamps = []

        for entry in history:
            value = entry["stats"].get(metric)
            if value is not None:
                values.append(value)
                timestamps.append(entry["timestamp"])

        if len(values) < 2:
            return {
                "status": "insufficient_data",
                "data_points": len(values),
                "trend_direction": "unknown",
                "confidence": 0.0,
            }

        # Simple trend analysis
        # Note: values are in reverse chronological order (most recent first)
        recent_count = min(3, len(values))  # Take up to 3 most recent
        older_count = min(3, len(values))  # Take up to 3 oldest

        recent_values = values[:recent_count]  # Most recent
        older_values = (
            values[-older_count:]
            if len(values) > recent_count
            else values[recent_count:]
        )  # Oldest

        # If we don't have enough separation, use all data split in half
        if len(older_values) == 0:
            split_point = len(values) // 2
            recent_values = values[:split_point] if split_point > 0 else values
            older_values = (
                values[split_point:] if split_point < len(values) else [values[-1]]
            )

        recent_avg = sum(recent_values) / len(recent_values)
        older_avg = sum(older_values) / len(older_values)

        change_ratio = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0

        # Determine trend direction and confidence
        if abs(change_ratio) < 0.02:  # Less than 2% change
            direction = "stable"
            confidence = 1.0 - abs(change_ratio) / 0.02
        elif change_ratio > 0:
            direction = "degrading"
            confidence = min(1.0, abs(change_ratio) / 0.1)  # Normalize to 10% change
        else:
            direction = "improving"
            confidence = min(1.0, abs(change_ratio) / 0.1)

        return {
            "status": "analyzed",
            "data_points": len(values),
            "trend_direction": direction,
            "confidence": confidence,
            "change_ratio": change_ratio,
            "recent_average": recent_avg,
            "baseline_average": older_avg,
            "latest_value": values[0] if values else None,
            "oldest_value": values[-1] if values else None,
        }

    def generate_trend_report(self, analysis_results: dict[str, Any]) -> str:
        """Generate a markdown report from trend analysis results.

        Args:
            analysis_results: Results from analyze_trends()

        Returns:
            Markdown formatted report
        """
        report = "# 📈 Performance Trend Analysis Report\n\n"

        metadata = analysis_results["metadata"]
        trends = analysis_results["trends"]

        report += f"**Analysis Date:** {metadata['analysis_timestamp']}\n"
        report += f"**Metric Analyzed:** {metadata['metric']}\n"
        report += f"**History Limit:** {metadata['history_limit']} entries\n\n"

        # Summary statistics
        total_benchmarks = len(trends)
        degrading = sum(
            1 for t in trends.values() if t.get("trend_direction") == "degrading"
        )
        improving = sum(
            1 for t in trends.values() if t.get("trend_direction") == "improving"
        )
        stable = sum(1 for t in trends.values() if t.get("trend_direction") == "stable")
        insufficient = sum(
            1 for t in trends.values() if t.get("status") == "insufficient_data"
        )

        report += "## 📊 Summary\n\n"
        report += f"- **Total Benchmarks:** {total_benchmarks}\n"
        report += f"- **Degrading:** {degrading} ❌\n"
        report += f"- **Improving:** {improving} ✅\n"
        report += f"- **Stable:** {stable} ➡️\n"
        report += f"- **Insufficient Data:** {insufficient} ❔\n\n"

        # Detailed trends
        report += "## 📈 Detailed Trends\n\n"
        report += "| Benchmark | Status | Trend | Confidence | Change | Data Points |\n"
        report += "|-----------|--------|-------|------------|--------|-------------|\n"

        for name, trend in sorted(trends.items()):
            status_emoji = {
                "degrading": "❌",
                "improving": "✅",
                "stable": "➡️",
                "unknown": "❔",
            }.get(trend.get("trend_direction", "unknown"), "❔")

            status = trend.get("status", "unknown")
            direction = trend.get("trend_direction", "unknown")
            confidence = trend.get("confidence", 0.0)
            change_ratio = trend.get("change_ratio", 0.0)
            data_points = trend.get("data_points", 0)

            change_str = f"{change_ratio:+.1%}" if change_ratio != 0 else "0.0%"
            confidence_str = f"{confidence:.1%}" if confidence > 0 else "N/A"

            report += f"| `{name}` | {status} | {status_emoji} {direction} | {confidence_str} | {change_str} | {data_points} |\n"

        return report
