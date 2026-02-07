#!/usr/bin/env python3
"""Generate endpoints_by_subscription markdown files from OpenAPI spec.

Reads the x-min-subscription field from the OpenAPI spec and generates
markdown documentation showing which endpoints are available at each
subscription tier.
"""

import argparse
from collections import defaultdict
from pathlib import Path

import yaml


def load_openapi_spec(spec_path: Path) -> dict:
    """Load the OpenAPI spec from YAML file."""
    with open(spec_path, "r") as f:
        return yaml.safe_load(f)


def extract_endpoints_by_tier(openapi_spec: dict) -> dict:
    """Extract endpoints grouped by subscription tier.

    Args:
        openapi_spec: The loaded OpenAPI specification.

    Returns:
        Dictionary mapping tier name to list of endpoint info dicts.
    """
    tiers = defaultdict(list)
    paths = openapi_spec.get("paths", {})

    for path, path_item in paths.items():
        # Skip if not a valid path item
        if not isinstance(path_item, dict):
            continue

        # Get x-min-subscription from path level
        tier = path_item.get("x-min-subscription")

        # Get operations and their info
        operations = []
        for method in ["get", "post", "put", "delete", "patch"]:
            if method in path_item:
                operation = path_item[method]
                if isinstance(operation, dict):
                    # Check for operation-level x-min-subscription
                    op_tier = operation.get("x-min-subscription", tier)
                    summary = operation.get("summary", "")
                    description = operation.get("description", "").strip()

                    # Use first line of description if no summary
                    display_name = summary
                    if not display_name and description:
                        display_name = description.split("\n")[0][:80]

                    operations.append(
                        {
                            "method": method.upper(),
                            "tier": op_tier,
                            "summary": display_name,
                        }
                    )

        # If no operations found, try to use path-level tier
        if not operations and tier:
            operations.append(
                {
                    "method": "GET",  # Assume GET for path-level only
                    "tier": tier,
                    "summary": "",
                }
            )

        # Group by tier
        for op in operations:
            if op["tier"]:
                tiers[op["tier"]].append(
                    {
                        "path": path,
                        "method": op["method"],
                        "summary": op["summary"],
                    }
                )

    return dict(tiers)


def generate_markdown(tier: str, endpoints: list) -> str:
    """Generate markdown content for a subscription tier.

    Args:
        tier: The subscription tier name.
        endpoints: List of endpoint info dicts.

    Returns:
        Markdown content string.
    """
    lines = [
        f"# API Endpoints {tier.capitalize()} Tier",
        "",
    ]

    # Group endpoints by category (e.g., Stock, Option, etc.)
    categories = defaultdict(list)
    for endpoint in endpoints:
        # Extract category from path (e.g., /stock/list/symbols -> Stock)
        path_parts = endpoint["path"].strip("/").split("/")
        if path_parts:
            category = path_parts[0].capitalize()
            categories[category].append(endpoint)

    # Define desired category order
    category_order = ["Stock", "Option", "Index", "Calendar"]

    # Sort categories and generate sections
    for category in category_order:
        if category not in categories:
            continue
        lines.extend(
            [
                f"#### {category} Endpoints",
                "",
            ]
        )

        # Sort endpoints within category
        category_endpoints = sorted(categories[category], key=lambda x: x["path"])

        for endpoint in category_endpoints:
            path = endpoint["path"]
            summary = endpoint["summary"]

            if summary:
                lines.append(f"- `{path}` - {summary}")
            else:
                lines.append(f"- `{path}`")

        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate endpoints_by_subscription markdown from OpenAPI spec"
    )
    parser.add_argument(
        "--spec",
        type=Path,
        default=Path("openapiv3.yaml"),
        help="Path to OpenAPI spec file (default: openapiv3.yaml)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("endpoints_by_subscription"),
        help="Output directory for markdown files (default: endpoints_by_subscription)",
    )
    parser.add_argument(
        "--tiers",
        nargs="+",
        default=["free", "value", "standard", "professional"],
        help="Subscription tiers to generate (default: free value standard professional)",
    )

    args = parser.parse_args()

    # Load OpenAPI spec
    spec = load_openapi_spec(args.spec)

    # Extract endpoints by tier
    endpoints_by_tier = extract_endpoints_by_tier(spec)

    # Define tier hierarchy (ascending order)
    tier_hierarchy = ["free", "value", "standard", "professional"]

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Generate markdown for each tier with cumulative endpoints
    cumulative_endpoints = []
    for tier in tier_hierarchy:
        if tier in endpoints_by_tier:
            # Add this tier's endpoints to cumulative list
            cumulative_endpoints.extend(endpoints_by_tier[tier])
            # Generate markdown with all endpoints up to this tier
            content = generate_markdown(tier, cumulative_endpoints.copy())
            output_file = args.output_dir / f"endpoints_{tier}.md"
            output_file.write_text(content)
            print(f"Generated {output_file} ({len(cumulative_endpoints)} total endpoints)")
        else:
            print(f"No endpoints found for tier: {tier}")

    # Print summary
    total = sum(len(endpoints) for endpoints in endpoints_by_tier.values())
    print(f"\nTotal endpoints across all tiers: {total}")


if __name__ == "__main__":
    main()
