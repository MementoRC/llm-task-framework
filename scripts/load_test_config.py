"""
Load testing configuration management for LLM Task Framework.

This script provides a centralized way to manage load testing profiles
(light, medium, heavy) and retrieve their settings.

Usage:
    python scripts/load_test_config.py --profile [light|medium|heavy] --get [users|spawn_rate|run_time]
"""

import argparse
import json
from typing import Any, Dict

# Define load testing profiles
PROFILES: Dict[str, Dict[str, Any]] = {
    "light": {
        "users": 5,
        "spawn_rate": 1,
        "run_time": "1m",
        "description": "Light load testing for development and quick checks.",
    },
    "medium": {
        "users": 20,
        "spawn_rate": 5,
        "run_time": "5m",
        "description": "Medium load testing for staging or pre-release validation.",
    },
    "heavy": {
        "users": 50,
        "spawn_rate": 10,
        "run_time": "10m",
        "description": "Heavy load testing for performance validation and stress testing.",
    },
}


def get_config(profile: str, key: str | None = None) -> Any:
    """
    Retrieves configuration for a given profile.

    Args:
        profile: The name of the load test profile (e.g., 'light').
        key: The specific configuration key to retrieve.

    Returns:
        The configuration value or the entire profile dictionary if key is None.
    """
    profile_config = PROFILES.get(profile.lower())
    if not profile_config:
        raise ValueError(
            f"Profile '{profile}' not found. Available profiles: {list(PROFILES.keys())}"
        )

    if key:
        if key not in profile_config:
            raise ValueError(
                f"Key '{key}' not found in profile '{profile}'. Available keys: {list(profile_config.keys())}"
            )
        return profile_config[key]

    return profile_config


def main() -> None:
    """Main function to handle command-line arguments."""
    parser = argparse.ArgumentParser(description="Get load testing configuration.")
    parser.add_argument(
        "--profile",
        type=str,
        required=True,
        choices=PROFILES.keys(),
        help="The load test profile to use.",
    )
    parser.add_argument(
        "--get",
        type=str,
        help="The specific configuration key to retrieve.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output the entire profile configuration as a JSON string.",
    )

    args = parser.parse_args()

    if args.json:
        config = get_config(args.profile)
        print(json.dumps(config))
    elif args.get:
        value = get_config(args.profile, args.get)
        print(value)
    else:
        # Default behavior: print the description
        config = get_config(args.profile)
        print(config.get("description", "No description available."))


if __name__ == "__main__":
    main()
