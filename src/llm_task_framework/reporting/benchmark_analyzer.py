import json
from typing import Any


class BenchmarkAnalyzer:
    """
    Analyzes benchmark results and detects regressions.
    """

    def __init__(self, regression_threshold: float = 0.1):
        """
        Initializes the analyzer with a regression threshold.

        Args:
            regression_threshold: Percentage threshold for regression detection.
        """
        self.regression_threshold = regression_threshold

    def analyze_results(self, baseline_data: list[dict[str, Any]], current_data: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Analyzes benchmark results and detects regressions.

        Args:
            baseline_data: List of baseline benchmark results.
            current_data: List of current benchmark results.

        Returns:
            A dictionary containing analysis results, including detected regressions.
        """
        analysis = {}
        regressions = []

        # Index baseline data by benchmark name
        baseline_index = {item["name"]: item for item in baseline_data}

        for current_result in current_data:
            name = current_result["name"]
            if name in baseline_index:
                baseline_result = baseline_index[name]
                # Compare mean execution times
                baseline_mean = baseline_result["stats"]["mean"]
                current_mean = current_result["stats"]["mean"]
                percentage_change = (current_mean - baseline_mean) / baseline_mean

                if abs(percentage_change) > self.regression_threshold:
                    regressions.append({
                        "name": name,
                        "percentage_change": percentage_change,
                        "baseline_mean": baseline_mean,
                        "current_mean": current_mean,
                    })

                analysis[name] = {
                    "baseline": baseline_mean,
                    "current": current_mean,
                    "percentage_change": percentage_change,
                }
            else:
                analysis[name] = {
                    "baseline": None,
                    "current": current_result["stats"]["mean"],
                    "percentage_change": None,
                }

        return {
            "analysis": analysis,
            "regressions": regressions,
        }

    def load_benchmark_data(self, json_file: str) -> list[dict[str, Any]]:
        """
        Loads benchmark data from a JSON file.

        Args:
            json_file: Path to the JSON file containing benchmark data.

        Returns:
            A list of benchmark results.
        """
        with open(json_file) as f:
            data = json.load(f)
        return data["benchmarks"]
