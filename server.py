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
    OpenAPIResource,
    OpenAPIResourceTemplate,
    OpenAPITool,
)
from fastmcp.server.openapi.routing import HTTPRoute, MCPType, RouteMap

from subscription import extract_tier_from_spec, get_tier_tag


def load_openapi_spec() -> dict:
    """Load the OpenAPI spec from the local YAML file."""
    spec_path = Path(__file__).parent / "openapiv3_updated.yaml"
    with open(spec_path) as f:
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
    base_url = base_url or os.getenv("THETADATA_BASE_URL", "http://127.0.0.1:25503/v3")
    timeout = timeout or float(os.getenv("THETADATA_TIMEOUT", "30.0"))

    # Create HTTP client for the Theta Data API
    client = httpx.AsyncClient(
        base_url=base_url,
        timeout=timeout,
    )

    # Wrap the client's transport to transform date parameters
    original_transport = client._transport

    class DateTransformTransport:
        def __init__(self, transport):
            self._transport = transport

        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            import datetime
            from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

            # Parse the full URL
            parsed = urlparse(str(request.url))
            params = parse_qs(parsed.query, keep_blank_values=True)
            # Convert from lists to single values
            params = {k: v[0] if len(v) == 1 else v for k, v in params.items()}

            # If no dates provided, default to yesterday (YYYY-MM-DD format)
            yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            has_start = "start_date" in params
            has_end = "end_date" in params

            modified = False

            if not has_start and not has_end:
                # No dates provided - use yesterday for both start and end
                params["start_date"] = yesterday
                params["end_date"] = yesterday
                modified = True
            elif has_start and not has_end:
                # Only start_date - use it for end_date too
                params["end_date"] = params["start_date"]
                modified = True
            elif has_end and not has_start:
                # Only end_date - use it for start_date too
                params["start_date"] = params["end_date"]
                modified = True
            # If both provided, keep as-is (allows multi-day queries)

            # Ensure format is set to json_new for row-oriented JSON
            if "format" not in params:
                params["format"] = "json_new"
                modified = True
            elif params.get("format") == "json":
                params["format"] = "json_new"
                modified = True

            # Rebuild URL with modified params
            if modified:
                new_query = urlencode(params)
                new_parts = parsed._replace(query=new_query)
                new_url = urlunparse(new_parts)

                # Create new request with modified URL
                request = httpx.Request(
                    method=request.method,
                    url=new_url,
                    headers=dict(request.headers),
                    content=request.content,
                )

            response = await self._transport.handle_async_request(request)

            # Unwrap response if it's wrapped in a "response" field
            content_type = response.headers.get("content-type", "")
            if "json" in content_type:
                import json

                try:
                    body = await response.aread()
                    data = json.loads(body)
                    if isinstance(data, dict) and "response" in data and len(data) == 1:
                        # Unwrap the response field
                        new_body = json.dumps(data["response"]).encode()
                        return httpx.Response(
                            status_code=response.status_code,
                            headers=response.headers,
                            content=new_body,
                        )
                except Exception:
                    pass

            return response

    client._transport = DateTransformTransport(original_transport)

    # Load the OpenAPI specification
    openapi_spec = load_openapi_spec()

    # Define component customization function to add subscription tier tags
    def customize_components(
        route: HTTPRoute,
        component: OpenAPITool | OpenAPIResource | OpenAPIResourceTemplate,
    ) -> None:
        """Add subscription tier tags to MCP components and override default format."""
        tier = extract_tier_from_spec(openapi_spec, route.path)
        tag = get_tier_tag(tier)
        component.tags.add(tag)

        # Also append tier info to description for visibility
        if tier:
            component.description = f"[{tier.upper()}] {component.description}"

        # Override default format from 'csv' to 'json' for better AI compatibility
        if isinstance(component, OpenAPITool) and component.parameters:
            # Handle both dict and Pydantic model structures
            params = component.parameters
            if isinstance(params, dict):
                # Parameters is a dict
                if "properties" in params and "format" in params["properties"]:
                    format_prop = params["properties"]["format"]
                    if isinstance(format_prop, dict) and format_prop.get("default") == "csv":
                        format_prop["default"] = "json"
            elif hasattr(params, "properties"):
                # Parameters is a Pydantic model-like object
                for param_name, param_info in params.properties.items():
                    if param_name == "format" and hasattr(param_info, "default"):
                        if param_info.default == "csv":
                            param_info.default = "json"

    # Create the MCP server from the OpenAPI spec
    mcp = FastMCP.from_openapi(
        openapi_spec=openapi_spec,
        client=client,
        name="Theta Data MCP Server",
        mcp_component_fn=customize_components,
        route_maps=[
            # Map GET requests to RESOURCES so they appear in list resources
            RouteMap(methods=["GET"], mcp_type=MCPType.RESOURCE),
            # All other methods become TOOLS
            RouteMap(mcp_type=MCPType.TOOL),
        ],
    )

    return mcp


def main():
    """Run the Theta Data MCP server."""
    parser = argparse.ArgumentParser(description="Theta Data MCP Server")
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
