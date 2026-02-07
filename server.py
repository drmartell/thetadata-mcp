#!/usr/bin/env python3
"""Theta Data MCP Server.

An MCP server generated from the Theta Data OpenAPI specification,
providing AI models with access to real-time and historic stock,
options, and index data.
"""

import argparse
import os
from pathlib import Path

import httpx
import yaml
from fastmcp import FastMCP
from fastmcp.server.openapi import (
    HTTPRoute,
    OpenAPITool,
    OpenAPIResource,
    OpenAPIResourceTemplate,
)

from subscription import extract_tier_from_spec, get_tier_tag


def load_openapi_spec() -> dict:
    """Load the OpenAPI spec from the local YAML file."""
    spec_path = Path(__file__).parent / "openapiv3.yaml"
    with open(spec_path, "r") as f:
        return yaml.safe_load(f)


def create_mcp_server(
    base_url: str | None = None,
    timeout: float = 30.0,
) -> FastMCP:
    """Create the Theta Data MCP server from OpenAPI spec.

    Args:
        base_url: The base URL for the Theta Data API. Defaults to
            http://127.0.0.1:25503/v3 or the THETADATA_BASE_URL env var.
        timeout: Request timeout in seconds. Defaults to 30.0 or
            the THETADATA_TIMEOUT env var.

    Returns:
        A configured FastMCP server instance.
    """
    # Load configuration from environment or parameters
    base_url = base_url or os.getenv(
        "THETADATA_BASE_URL",
        "http://127.0.0.1:25503/v3"
    )
    timeout = timeout or float(os.getenv("THETADATA_TIMEOUT", "30.0"))

    # Create HTTP client for the Theta Data API
    client = httpx.AsyncClient(
        base_url=base_url,
        timeout=timeout,
    )

    # Load the OpenAPI specification
    openapi_spec = load_openapi_spec()

    # Define component customization function to add subscription tier tags
    def customize_components(
        route: HTTPRoute,
        component: OpenAPITool | OpenAPIResource | OpenAPIResourceTemplate,
    ) -> None:
        """Add subscription tier tags to MCP components."""
        tier = extract_tier_from_spec(openapi_spec, route.path)
        tag = get_tier_tag(tier)
        component.tags.add(tag)

        # Also append tier info to description for visibility
        if tier:
            component.description = f"[{tier.upper()}] {component.description}"

    # Create the MCP server from the OpenAPI spec
    mcp = FastMCP.from_openapi(
        openapi_spec=openapi_spec,
        client=client,
        name="Theta Data MCP Server",
        mcp_component_fn=customize_components,
    )

    return mcp


def main():
    """Run the Theta Data MCP server."""
    parser = argparse.ArgumentParser(
        description="Theta Data MCP Server"
    )
    parser.add_argument(
        "--base-url",
        help="Base URL for Theta Data API (default: http://127.0.0.1:25503/v3)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Request timeout in seconds (default: 30.0)",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport method (default: stdio)",
    )

    args = parser.parse_args()

    # Create the MCP server
    mcp = create_mcp_server(
        base_url=args.base_url,
        timeout=args.timeout,
    )

    # Run the server
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
