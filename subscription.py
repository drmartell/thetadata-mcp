"""Subscription tier management for ThetaData MCP Server.

Extracts subscription tier information from the OpenAPI spec's x-min-subscription field.
"""

from typing import Optional


def extract_tier_from_spec(openapi_spec: dict, path: str) -> Optional[str]:
    """Extract the minimum subscription tier for an endpoint from the OpenAPI spec.

    Args:
        openapi_spec: The loaded OpenAPI specification dictionary.
        path: The endpoint path (e.g., '/stock/list/symbols').

    Returns:
        The minimum tier name (free, value, standard, professional) or None.
    """
    paths = openapi_spec.get("paths", {})
    
    # Try exact match first
    if path in paths:
        path_item = paths[path]
        # x-min-subscription is at the path level (applies to all methods)
        if "x-min-subscription" in path_item:
            return path_item["x-min-subscription"]
        # Check individual methods (GET, POST, etc.)
        for method in ["get", "post", "put", "delete", "patch"]:
            if method in path_item:
                operation = path_item[method]
                if "x-min-subscription" in operation:
                    return operation["x-min-subscription"]
    
    return None


def get_tier_tag(tier: Optional[str]) -> str:
    """Get the tag string for a subscription tier.

    Args:
        tier: The tier name or None.

    Returns:
        Tag string like 'tier:free' or 'tier:unknown' if tier is None.
    """
    if tier:
        return f"tier:{tier}"
    return "tier:unknown"
