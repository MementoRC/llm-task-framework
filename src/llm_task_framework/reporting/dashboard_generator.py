"""Dashboard generator for performance trend visualization."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .trend_analyzer import MATPLOTLIB_AVAILABLE, TrendAnalyzer


class DashboardGenerator:
    """Generates HTML dashboard for performance trend visualization."""

    def __init__(self, data_dir: str | Path = ".performance_trends"):
        """Initialize the dashboard generator.

        Args:
            data_dir: Directory containing historical performance data
        """
        self.trend_analyzer = TrendAnalyzer(data_dir)
        self.data_dir = Path(data_dir)

    def generate_dashboard(
        self,
        output_path: str | Path,
        benchmark_names: list[str] | None = None,
        include_charts: bool = True,
    ) -> None:
        """Generate a complete HTML dashboard.

        Args:
            output_path: Path to save the HTML dashboard
            benchmark_names: List of benchmark names to include, or None for all
            include_charts: Whether to include trend charts (requires matplotlib)
        """
        output_path = Path(output_path)

        # Get trend analysis
        analysis_results = self.trend_analyzer.analyze_trends(benchmark_names)

        # Generate HTML content
        html_content = self._generate_html(analysis_results, include_charts)

        # Write to file
        with open(output_path, "w") as f:
            f.write(html_content)

    def _generate_html(
        self, analysis_results: dict[str, Any], include_charts: bool
    ) -> str:
        """Generate the complete HTML dashboard content."""
        metadata = analysis_results["metadata"]
        trends = analysis_results["trends"]

        # Generate charts if requested and available
        charts_html = ""
        if include_charts and MATPLOTLIB_AVAILABLE:
            charts_html = self._generate_charts_section(trends)

        # Generate summary statistics
        summary_html = self._generate_summary_section(trends)

        # Generate detailed table
        table_html = self._generate_trends_table(trends)

        # Generate raw data section
        raw_data_html = self._generate_raw_data_section(analysis_results)

        # Combine into full HTML
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Performance Trend Dashboard</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #e9ecef;
            padding-bottom: 20px;
        }}
        .header h1 {{
            color: #2c3e50;
            margin: 0;
            font-size: 2.5em;
        }}
        .header .subtitle {{
            color: #6c757d;
            margin: 10px 0;
            font-size: 1.1em;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .summary-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            font-size: 2em;
        }}
        .summary-card p {{
            margin: 0;
            font-size: 1.1em;
            opacity: 0.9;
        }}
        .degrading {{ background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%); }}
        .improving {{ background: linear-gradient(135deg, #51cf66 0%, #40c057 100%); }}
        .stable {{ background: linear-gradient(135deg, #339af0 0%, #228be6 100%); }}
        .insufficient {{ background: linear-gradient(135deg, #9775fa 0%, #845ef7 100%); }}

        .section {{
            margin-bottom: 40px;
        }}
        .section h2 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #2c3e50;
        }}
        tr:hover {{
            background-color: #f8f9fa;
        }}

        .status-badge {{
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.9em;
            font-weight: 500;
        }}
        .status-degrading {{ background: #fee; color: #d73527; }}
        .status-improving {{ background: #efe; color: #2d7d32; }}
        .status-stable {{ background: #e3f2fd; color: #1976d2; }}
        .status-unknown {{ background: #f3e5f5; color: #7b1fa2; }}

        .chart-container {{
            margin: 20px 0;
            text-align: center;
            background: #fafafa;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #e9ecef;
        }}
        .chart-container img {{
            max-width: 100%;
            height: auto;
            border-radius: 4px;
        }}

        .timestamp {{
            color: #6c757d;
            font-size: 0.9em;
        }}

        .raw-data {{
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 20px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.9em;
            overflow-x: auto;
        }}

        .toggle-button {{
            background: #3498db;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9em;
            margin-top: 10px;
        }}
        .toggle-button:hover {{
            background: #2980b9;
        }}

        .hidden {{
            display: none;
        }}

        @media (max-width: 768px) {{
            .container {{
                padding: 15px;
                margin: 10px;
            }}
            .summary-grid {{
                grid-template-columns: 1fr;
            }}
            table {{
                font-size: 0.9em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📈 Performance Trend Dashboard</h1>
            <p class="subtitle">
                Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} |
                Metric: {metadata["metric"]} |
                History: {metadata["history_limit"]} entries
            </p>
        </div>

        {summary_html}

        {charts_html}

        {table_html}

        {raw_data_html}
    </div>

    <script>
        function toggleRawData() {{
            const element = document.getElementById('raw-data-content');
            const button = document.getElementById('toggle-raw-data');

            if (element.classList.contains('hidden')) {{
                element.classList.remove('hidden');
                button.textContent = 'Hide Raw Data';
            }} else {{
                element.classList.add('hidden');
                button.textContent = 'Show Raw Data';
            }}
        }}
    </script>
</body>
</html>
        """

        return html

    def _generate_summary_section(self, trends: dict[str, Any]) -> str:
        """Generate the summary statistics section."""
        total = len(trends)
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

        return f"""
        <div class="section">
            <h2>📊 Summary Statistics</h2>
            <div class="summary-grid">
                <div class="summary-card">
                    <h3>{total}</h3>
                    <p>Total Benchmarks</p>
                </div>
                <div class="summary-card degrading">
                    <h3>{degrading}</h3>
                    <p>Degrading ❌</p>
                </div>
                <div class="summary-card improving">
                    <h3>{improving}</h3>
                    <p>Improving ✅</p>
                </div>
                <div class="summary-card stable">
                    <h3>{stable}</h3>
                    <p>Stable ➡️</p>
                </div>
                <div class="summary-card insufficient">
                    <h3>{insufficient}</h3>
                    <p>Insufficient Data ❔</p>
                </div>
            </div>
        </div>
        """

    def _generate_trends_table(self, trends: dict[str, Any]) -> str:
        """Generate the detailed trends table."""
        table_rows = ""

        for name, trend in sorted(trends.items()):
            direction = trend.get("trend_direction", "unknown")
            confidence = trend.get("confidence", 0.0)
            change_ratio = trend.get("change_ratio", 0.0)
            data_points = trend.get("data_points", 0)
            latest_value = trend.get("latest_value")

            # Status badge
            status_class = f"status-{direction}"
            status_emoji = {
                "degrading": "❌",
                "improving": "✅",
                "stable": "➡️",
                "unknown": "❔",
            }.get(direction, "❔")

            change_str = f"{change_ratio:+.1%}" if change_ratio != 0 else "0.0%"
            confidence_str = f"{confidence:.1%}" if confidence > 0 else "N/A"
            latest_str = f"{latest_value:.6f}s" if latest_value is not None else "N/A"

            table_rows += f"""
            <tr>
                <td><code>{name}</code></td>
                <td><span class="status-badge {status_class}">{status_emoji} {direction.title()}</span></td>
                <td>{confidence_str}</td>
                <td>{change_str}</td>
                <td>{latest_str}</td>
                <td>{data_points}</td>
            </tr>
            """

        return f"""
        <div class="section">
            <h2>📈 Detailed Trends</h2>
            <table>
                <thead>
                    <tr>
                        <th>Benchmark</th>
                        <th>Trend Status</th>
                        <th>Confidence</th>
                        <th>Change</th>
                        <th>Latest Value</th>
                        <th>Data Points</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
        """

    def _generate_charts_section(self, trends: dict[str, Any]) -> str:
        """Generate the charts section with trend visualizations."""
        if not MATPLOTLIB_AVAILABLE:
            return """
            <div class="section">
                <h2>📊 Trend Charts</h2>
                <p>Charts are not available because matplotlib is not installed.</p>
                <p>Install matplotlib to enable trend visualization: <code>pip install matplotlib</code></p>
            </div>
            """

        charts_html = """
        <div class="section">
            <h2>📊 Trend Charts</h2>
        """

        # Generate charts for benchmarks with sufficient data
        chart_count = 0
        for name, trend in sorted(trends.items()):
            if trend.get("status") == "analyzed" and trend.get("data_points", 0) >= 2:
                try:
                    # Get historical data for this benchmark
                    history = self.trend_analyzer.data_store.get_benchmark_history(
                        name, limit=50
                    )
                    if len(history) >= 2:
                        if self.trend_analyzer.chart_generator is not None:
                            chart_data_url = self.trend_analyzer.chart_generator.generate_trend_chart(
                                name, history, metric="mean", width=10, height=5
                            )
                        else:
                            continue

                        charts_html += f"""
                        <div class="chart-container">
                            <h3>{name}</h3>
                            <img src="{chart_data_url}" alt="Trend chart for {name}">
                        </div>
                        """
                        chart_count += 1
                except Exception as e:
                    # Log the specific error and skip this chart
                    print(f"Warning: Failed to generate chart for {name}: {e}")
                    # Explicitly continue to next iteration

        if chart_count == 0:
            charts_html += "<p>No charts available. Need at least 2 data points per benchmark to generate trends.</p>"

        charts_html += "</div>"
        return charts_html

    def _generate_raw_data_section(self, analysis_results: dict[str, Any]) -> str:
        """Generate the raw data section."""
        raw_data_json = json.dumps(analysis_results, indent=2)

        return f"""
        <div class="section">
            <h2>🔧 Raw Data</h2>
            <p>Complete analysis results in JSON format for debugging and integration.</p>
            <button id="toggle-raw-data" class="toggle-button" onclick="toggleRawData()">Show Raw Data</button>
            <div id="raw-data-content" class="raw-data hidden">
                <pre>{raw_data_json}</pre>
            </div>
        </div>
        """
