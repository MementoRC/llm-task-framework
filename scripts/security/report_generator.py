import argparse
import json


def generate_report(report_file: str, output_markdown: str) -> None:
    """
    Generates a human-readable security report in Markdown format from a JSON report file.

    Args:
        report_file (str): Path to the JSON report file.
        output_markdown (str): Path to the output Markdown file.
    """
    try:
        with open(report_file) as f:
            report_data = json.load(f)

        markdown_content = generate_markdown(report_data)

        with open(output_markdown, "w") as f:
            f.write(markdown_content)

    except FileNotFoundError:
        print(f"::error:: Report file not found: {report_file}")
        exit(1)
    except json.JSONDecodeError:
        print(f"::error:: Invalid JSON format in report file: {report_file}")
        exit(1)
    except Exception as e:
        print(f"::error:: An unexpected error occurred: {e}")
        exit(1)


def generate_markdown(report_data: dict) -> str:
    """
    Generates a Markdown string from the report data.

    Args:
        report_data (dict): The report data.

    Returns:
        str: A Markdown string.
    """
    markdown = "## Security Scan Report\n\n"

    status = report_data.get("status", "unknown")
    markdown += f"**Status:** {status}\n\n"

    comparison_status = report_data.get("comparison_status", "unknown")
    markdown += f"**Comparison Status:** {comparison_status}\n\n"

    results = report_data.get("results", {})

    markdown += "### Dependency Scan Results\n\n"
    dependency_scan_results = results.get("dependency_scan", {})
    markdown += format_dependency_scan_results(dependency_scan_results)

    markdown += "### Secret Detection Results\n\n"
    secret_detection_results = results.get("secret_detection", {})
    markdown += format_secret_detection_results(secret_detection_results)

    return markdown


def format_dependency_scan_results(dependency_scan_results: dict) -> str:
    """
    Formats the dependency scan results into a Markdown string.

    Args:
        dependency_scan_results (dict): The dependency scan results.

    Returns:
        str: A Markdown string.
    """
    markdown = ""
    for tool, result in dependency_scan_results.items():
        markdown += f"#### {tool.capitalize()} Results\n\n"
        if isinstance(result, list):  # Safety and pip-audit return lists
            if not result:
                markdown += "No issues found.\n\n"
            else:
                markdown += "| Vulnerability | Severity | Description |\n"
                markdown += "|---------------|----------|-------------|\n"
                for issue in result:
                    if tool == "safety":
                        markdown += f"| {issue['vulnerability_id']} | {issue['severity']} | {issue['message']} |\n"
                    elif tool == "pip_audit":
                        markdown += f"| {issue['vuln_id']} | {issue['severity']} | {issue['advisory']} |\n"
        elif isinstance(result, dict):  # Bandit returns a dict
            if "errors" in result and result["errors"]:
                markdown += "Errors occurred during the scan:\n"
                for error in result["errors"]:
                    markdown += f"- {error['message']}\n"
            elif "results" in result and result["results"]:
                markdown += "| Test ID | Severity | Message |\n"
                markdown += "|---------|----------|---------|\n"
                for issue in result["results"]:
                    markdown += f"| {issue['test_id']} | {issue['issue_severity']} | {issue['issue_text']} |\n"
            else:
                markdown += "No issues found.\n\n"
        else:
            markdown += "No results found.\n\n"
    return markdown


def format_secret_detection_results(secret_detection_results: dict) -> str:
    """
    Formats the secret detection results into a Markdown string.

    Args:
        secret_detection_results (dict): The secret detection results.

    Returns:
        str: A Markdown string.
    """
    markdown = ""
    for tool, result in secret_detection_results.items():
        markdown += f"#### {tool.capitalize()} Results\n\n"
        # The result from detect-secrets is a string containing the output
        if isinstance(result, str):
            if "No secrets detected" in result:
                markdown += "No secrets detected.\n\n"
            else:
                markdown += "```text\n" + result + "\n```\n\n"
        else:
            markdown += "No results found.\n\n"
    return markdown


def main() -> None:
    """
    Main function to generate the security report.
    """
    parser = argparse.ArgumentParser(
        description="Generate a security report in Markdown format."
    )
    parser.add_argument(
        "--report-file", required=True, help="Path to the JSON report file."
    )
    parser.add_argument(
        "--output-markdown", required=True, help="Path to the output Markdown file."
    )
    args = parser.parse_args()

    generate_report(args.report_file, args.output_markdown)


if __name__ == "__main__":
    main()
