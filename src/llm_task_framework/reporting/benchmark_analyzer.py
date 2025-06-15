import json
from typing import Any


class RegressionDetector:
    """Detects performance regressions based on configurable rules."""

    def __init__(self, rules: list[dict[str, Any]]):
        """
        Initializes the detector with a set of regression rules.

        Args:
            rules: A list of rule dictionaries. Each rule defines a metric,
                   thresholds, and severity.
                   Example:
                   [
                       {
                           "metric": "mean",
                           "threshold_type": "percentage",
                           "threshold": 0.1,
                           "severity": "error"
                       },
                       {
                           "metric": "stddev",
                           "threshold_type": "absolute",
                           "threshold": 0.05,
                           "severity": "warning"
                       }
                   ]
        """
        self.rules = rules

    def _get_metric(self, stats: dict[str, Any], metric: str) -> float | None:
        """Safely gets a metric from the stats dictionary."""
        # pytest-benchmark uses 'stddev' but we might want to call it 'std'
        metric_map = {"std": "stddev"}
        key = metric_map.get(metric, metric)
        return stats.get(key)

    def detect(
        self, baseline_stats: dict[str, Any], current_stats: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Detects regressions for a single benchmark result.

        Args:
            baseline_stats: The stats dictionary for the baseline benchmark.
            current_stats: The stats dictionary for the current benchmark.

        Returns:
            A list of detected regressions for this benchmark.
        """
        regressions = []
        for rule in self.rules:
            metric = rule["metric"]
            threshold_type = rule["threshold_type"]
            threshold = rule["threshold"]
            severity = rule.get("severity", "warning")

            baseline_value = self._get_metric(baseline_stats, metric)
            current_value = self._get_metric(current_stats, metric)

            if baseline_value is None or current_value is None:
                continue  # Cannot compare if a value is missing

            # We only care about regressions (performance getting worse)
            if current_value <= baseline_value:
                continue

            is_regression = False
            change = 0.0

            if threshold_type == "percentage":
                if baseline_value == 0:
                    continue  # Avoid division by zero
                change = (current_value - baseline_value) / baseline_value
                if change > threshold:
                    is_regression = True
            elif threshold_type == "absolute":
                change = current_value - baseline_value
                if change > threshold:
                    is_regression = True

            if is_regression:
                regressions.append(
                    {
                        "metric": metric,
                        "threshold_type": threshold_type,
                        "threshold": threshold,
                        "baseline_value": baseline_value,
                        "current_value": current_value,
                        "change": change,
                        "severity": severity,
                    }
                )
        return regressions


class BenchmarkAnalyzer:
    """
    Analyzes benchmark results and detects regressions using a RegressionDetector.
    """

    def __init__(self, regression_rules: list[dict[str, Any]]):
        """
        Initializes the analyzer with regression rules.

        Args:
            regression_rules: A list of rule dictionaries for the RegressionDetector.
        """
        self.detector = RegressionDetector(rules=regression_rules)

    def analyze_results(
        self, baseline_data: list[dict[str, Any]], current_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Analyzes benchmark results and detects regressions.

        Args:
            baseline_data: List of baseline benchmark results.
            current_data: List of current benchmark results.

        Returns:
            A dictionary containing analysis results, including detected regressions.
        """
        analysis: dict[str, Any] = {}
        all_regressions: list[dict[str, Any]] = []

        baseline_index = {item["name"]: item for item in baseline_data}

        for current_result in current_data:
            name = current_result["name"]
            current_stats = current_result["stats"]
            analysis[name] = {
                "current_stats": current_stats,
                "baseline_stats": None,
                "regressions": [],
            }

            if name in baseline_index:
                baseline_result = baseline_index[name]
                baseline_stats = baseline_result["stats"]
                analysis[name]["baseline_stats"] = baseline_stats

                regressions = self.detector.detect(baseline_stats, current_stats)
                if regressions:
                    for r in regressions:
                        r["name"] = name
                    analysis[name]["regressions"] = regressions
                    all_regressions.extend(regressions)

        return {
            "analysis": analysis,
            "regressions": all_regressions,
        }

    def load_benchmark_data(self, json_file: str) -> list[dict[str, Any]]:
        """
        Loads benchmark data from a JSON file.

        Args:
            json_file: Path to the JSON file containing benchmark data.

        Returns:
            A list of benchmark results.
        """
        try:
            with open(json_file) as f:
                data: dict[str, Any] = json.load(f)
            benchmarks: list[dict[str, Any]] = data.get("benchmarks", [])
            return benchmarks
        except (FileNotFoundError, json.JSONDecodeError):
            return []
