import argparse
import json

import requests


def main() -> None:
    """
    Posts benchmark results as a comment to a GitHub Pull Request.
    """
    parser = argparse.ArgumentParser(
        description="Post benchmark results as a comment to a GitHub Pull Request."
    )
    parser.add_argument(
        "--report", required=True, help="Path to the benchmark report file."
    )
    parser.add_argument(
        "--repo", required=True, help="The GitHub repository (owner/repo)."
    )
    parser.add_argument(
        "--pr", required=True, type=int, help="The Pull Request number."
    )
    parser.add_argument("--github-token", required=True, help="GitHub API token.")
    args: argparse.Namespace = parser.parse_args()

    with open(args.report) as f:
        report_body: str = f.read()

    # Construct the API endpoint for creating a PR comment
    api_url: str = f"https://api.github.com/repos/{args.repo}/issues/{args.pr}/comments"

    # Create the comment payload
    payload: dict[str, str] = {"body": report_body}

    # Set the headers, including the authorization token
    headers: dict[str, str] = {
        "Authorization": f"token {args.github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Make the API request to create the comment
    response: requests.Response = requests.post(api_url, headers=headers, data=json.dumps(payload), timeout=30)

    # Check if the request was successful
    if response.status_code == 201:
        print("✅ Benchmark report posted as a comment to the PR.")
    else:
        print(
            f"❌ Failed to post comment. Status code: {response.status_code}, Response: {response.text}"
        )


if __name__ == "__main__":
    main()
