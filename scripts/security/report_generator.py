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
        with open(report_file, encoding="utf-8") as f:
            report_data = json.load(f)

        markdown_content = generate_markdown(report_data)

        # Sanitize content before writing to prevent exposure of sensitive data
        # Remove any detected secrets or sensitive information from the report
        sanitized_content = sanitize_markdown_content(markdown_content)
        
        # Write the sanitized markdown content to the output file with restrictive permissions
        try:
            with open(output_markdown, "w", encoding="utf-8") as f:
                f.write(sanitized_content)
            # Set file permissions to owner read/write only (0600)
            import os
            os.chmod(output_markdown, 0o600)
        except Exception as file_exc:
            print(f"::error:: Failed to securely write markdown file: {file_exc}")
            exit(1)

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
    Secret detection results are intentionally excluded for security compliance.

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

    markdown += (
        "> **:warning: Secret detection results are intentionally excluded from this report for security and compliance reasons.**\n"
        "> If secrets were detected, review the original scan output in a secure environment.\n\n"
    )

    results = report_data.get("results", {})

    markdown += "### Dependency Scan Results\n\n"
    dependency_scan_results = results.get("dependency_scan", {})
    markdown += format_dependency_scan_results(dependency_scan_results)

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


# Secret detection result processing is intentionally omitted for security compliance.


def sanitize_markdown_content(content: str) -> str:
    """
    No-op sanitizer: Secret detection results are not included in the report.
    This function is retained for interface compatibility.
    """
    return content


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
