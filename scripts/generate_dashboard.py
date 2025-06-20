#!/usr/bin/env python3
"""CLI script for generating performance trend dashboard."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from llm_task_framework.reporting.dashboard_generator import DashboardGenerator
from llm_task_framework.reporting.trend_analyzer import TrendAnalyzer


def main() -> None:
    """Generate performance trend dashboard."""
    parser = argparse.ArgumentParser(
        description="Generate performance trend dashboard from historical benchmark data.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    
    parser.add_argument(
        "--data-dir",
        default=".performance_trends",
        help="Directory containing historical performance data",
    )
    
    parser.add_argument(
        "--output",
        default="performance_dashboard.html",
        help="Output path for the HTML dashboard",
    )
    
    parser.add_argument(
        "--benchmarks",
        help="Comma-separated list of benchmark names to include (default: all)",
    )
    
    parser.add_argument(
        "--no-charts",
        action="store_true",
        help="Disable chart generation (useful if matplotlib is not available)",
    )
    
    parser.add_argument(
        "--store-current",
        help="Store current benchmark data from JSON file before generating dashboard",
    )
    
    parser.add_argument(
        "--metric",
        default="mean",
        choices=["mean", "min", "max", "stddev"],
        help="Metric to analyze for trends",
    )
    
    parser.add_argument(
        "--history-limit",
        type=int,
        default=50,
        help="Maximum number of historical entries to consider",
    )
    
    parser.add_argument(
        "--analysis-only",
        action="store_true",
        help="Only perform analysis and print results, don't generate dashboard",
    )
    
    args = parser.parse_args()
    
    # Initialize components
    data_dir = Path(args.data_dir)
    trend_analyzer = TrendAnalyzer(data_dir)
    
    # Store current benchmark data if provided
    if args.store_current:
        store_current_data(trend_analyzer, args.store_current)
    
    # Parse benchmark names
    benchmark_names = None
    if args.benchmarks:
        benchmark_names = [name.strip() for name in args.benchmarks.split(",")]
    
    # Perform trend analysis
    print("🔍 Analyzing performance trends...")
    analysis_results = trend_analyzer.analyze_trends(
        benchmark_names=benchmark_names,
        metric=args.metric,
        history_limit=args.history_limit
    )
    
    # Print summary
    print_analysis_summary(analysis_results)
    
    if args.analysis_only:
        # Just print detailed analysis
        report = trend_analyzer.generate_trend_report(analysis_results)
        print("\\n" + report)
        return
    
    # Generate dashboard
    print("📊 Generating dashboard...")
    dashboard_generator = DashboardGenerator(data_dir)
    
    try:
        dashboard_generator.generate_dashboard(
            output_path=args.output,
            benchmark_names=benchmark_names,
            include_charts=not args.no_charts
        )
        print(f"✅ Dashboard generated: {args.output}")
        
        # Print file size and preview info
        output_path = Path(args.output)
        if output_path.exists():
            size_kb = output_path.stat().st_size / 1024
            print(f"📁 File size: {size_kb:.1f} KB")
            print(f"🌐 Open in browser: file://{output_path.absolute()}")
            
    except Exception as e:
        print(f"❌ Failed to generate dashboard: {e}", file=sys.stderr)
        sys.exit(1)


def store_current_data(trend_analyzer: TrendAnalyzer, json_file: str) -> None:
    """Store current benchmark data from JSON file."""
    try:
        with open(json_file) as f:
            data = json.load(f)
        
        benchmarks = data.get("benchmarks", [])
        if not benchmarks:
            print(f"⚠️  No benchmarks found in {json_file}")
            return
        
        trend_analyzer.data_store.store_benchmark_data(benchmarks)
        print(f"📊 Stored {len(benchmarks)} benchmarks from {json_file}")
        
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ Failed to load benchmark data from {json_file}: {e}", file=sys.stderr)
        sys.exit(1)


def print_analysis_summary(analysis_results: dict[str, Any]) -> None:
    """Print a summary of the analysis results."""
    metadata = analysis_results["metadata"]
    trends = analysis_results["trends"]
    
    total = len(trends)
    degrading = sum(1 for t in trends.values() if t.get("trend_direction") == "degrading")
    improving = sum(1 for t in trends.values() if t.get("trend_direction") == "improving")
    stable = sum(1 for t in trends.values() if t.get("trend_direction") == "stable")
    insufficient = sum(1 for t in trends.values() if t.get("status") == "insufficient_data")
    
    print("📈 Analysis Summary:")
    print(f"   • Metric: {metadata['metric']}")
    print(f"   • History limit: {metadata['history_limit']} entries")
    print(f"   • Total benchmarks: {total}")
    print(f"   • Degrading: {degrading} ❌")
    print(f"   • Improving: {improving} ✅")
    print(f"   • Stable: {stable} ➡️")
    print(f"   • Insufficient data: {insufficient} ❔")
    
    # Highlight concerning trends
    if degrading > 0:
        print(f"\\n⚠️  {degrading} benchmark(s) showing performance degradation:")
        for name, trend in trends.items():
            if trend.get("trend_direction") == "degrading":
                change = trend.get("change_ratio", 0) * 100
                confidence = trend.get("confidence", 0) * 100
                print(f"   • {name}: {change:+.1f}% change (confidence: {confidence:.0f}%)")


if __name__ == "__main__":
    main()