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

    # Concise, LLM-optimized descriptions keyed by operationId
    short_descriptions: dict[str, str] = {
        # Stock - List
        "stock_list_symbols": "List all traded stock symbols. Updated overnight.",
        "stock_list_dates": "List available data dates for a stock by request type and symbol.",
        # Stock - Snapshot (real-time current day)
        "stock_snapshot_ohlc": "Real-time current-day OHLC for a stock.",
        "stock_snapshot_trade": "Real-time last trade for a stock.",
        "stock_snapshot_quote": "Real-time last BBO/NBBO quote for a stock.",
        "stock_snapshot_market_value": (
            "Real-time market value derived from last quote for a stock."
        ),
        # Stock - History
        "stock_history_eod": "End-of-day report for a stock. Generated at 17:15 ET daily.",
        "stock_history_ohlc": "Historical OHLC bars for a stock. Max 1 month per request.",
        "stock_history_trade": "Tick-level trade history for a stock. Max 1 month per request.",
        "stock_history_quote": (
            "NBBO quote history for a stock. Supports interval aggregation. "
            "Max 1 month per request."
        ),
        "stock_history_trade_quote": (
            "Trade history paired with contemporaneous BBO quotes. Max 1 month per request."
        ),
        # Stock - At Time
        "stock_at_time_trade": "Last trade at a specific time of day for a stock.",
        "stock_at_time_quote": "Last quote at a specific time of day for a stock.",
        # Option - List
        "option_list_symbols": "List all traded option underlying symbols. Updated overnight.",
        "option_list_dates": (
            "List available data dates for an option by symbol, request type, and expiration."
        ),
        "option_list_expirations": (
            "List available expiration dates for an option symbol. Updated overnight."
        ),
        "option_list_strikes": (
            "List available strikes for an option symbol and expiration. Updated overnight."
        ),
        "option_list_contracts": (
            "List contracts traded or quoted on a date. Supports symbol filtering. Real-time."
        ),
        # Option - Snapshot (real-time current day)
        "option_snapshot_ohlc": "Real-time current-day OHLC for an option contract.",
        "option_snapshot_trade": "Real-time last trade for an option contract.",
        "option_snapshot_quote": "Real-time last NBBO quote for an option contract.",
        "option_snapshot_open_interest": (
            "Last open interest for an option contract. Reported ~06:30 ET daily."
        ),
        "option_snapshot_market_value": (
            "Real-time market value from last NBBO quote for an option contract."
        ),
        "option_snapshot_greeks_implied_volatility": (
            "Real-time implied volatility from bid, mid, and ask prices."
        ),
        "option_snapshot_greeks_all": (
            "Real-time greeks for all contracts on an expiration. Use expiration=* for all."
        ),
        "option_snapshot_greeks_first_order": (
            "Real-time first-order greeks (delta, gamma, theta, vega, rho) "
            "for all contracts on an expiration."
        ),
        "option_snapshot_greeks_second_order": (
            "Real-time second-order greeks for all contracts on an expiration."
        ),
        "option_snapshot_greeks_third_order": (
            "Real-time third-order greeks for all contracts on an expiration."
        ),
        # Option - History
        "option_history_eod": "End-of-day report for options. Generated at 17:15 ET daily.",
        "option_history_ohlc": "Historical OHLC bars for options. Max 1 month per request.",
        "option_history_trade": (
            "Tick-level trade history for options. Max 1 month, requires expiration."
        ),
        "option_history_quote": (
            "NBBO quote history for options. Supports interval aggregation. "
            "Max 1 month, requires expiration."
        ),
        "option_history_trade_quote": (
            "Trade history paired with contemporaneous NBBO quotes for options. "
            "Max 1 month, requires expiration."
        ),
        "option_history_open_interest": (
            "Historical open interest for options. Reported ~06:30 ET, reflects prior day."
        ),
        "option_history_greeks_eod": (
            "EOD greeks for all contracts by symbol and expiration. Use expiration=* for all."
        ),
        "option_history_greeks_all": (
            "Historical greeks (all orders) from midpoint prices. Max 1 month per request."
        ),
        "option_history_trade_greeks_all": (
            "Greeks calculated at each trade. Max 1 month, requires expiration."
        ),
        "option_history_greeks_first_order": (
            "Historical first-order greeks from midpoint prices. Max 1 month per request."
        ),
        "option_history_trade_greeks_first_order": (
            "First-order greeks at each trade. Max 1 month, requires expiration."
        ),
        "option_history_greeks_second_order": (
            "Historical second-order greeks from midpoint prices. Max 1 month per request."
        ),
        "option_history_trade_greeks_second_order": (
            "Second-order greeks at each trade. Max 1 month, requires expiration."
        ),
        "option_history_greeks_third_order": (
            "Historical third-order greeks from midpoint prices. Max 1 month per request."
        ),
        "option_history_trade_greeks_third_order": (
            "Third-order greeks at each trade. Max 1 month, requires expiration."
        ),
        "option_history_greeks_implied_volatility": (
            "Historical IV from bid, mid, and ask prices. Max 1 month per request."
        ),
        "option_history_trade_greeks_implied_volatility": (
            "IV calculated at each trade. Max 1 month, requires expiration."
        ),
        # Option - At Time
        "option_at_time_trade": "Last option trade at a specific time of day.",
        "option_at_time_quote": "Last option NBBO quote at a specific time of day.",
        # Index - List
        "index_list_symbols": "List all index symbols. Updated overnight.",
        "index_list_dates": "List available data dates for an index by request type and symbol.",
        # Index - Snapshot
        "index_snapshot_ohlc": "Real-time current-day OHLC for an index.",
        "index_snapshot_price": "Real-time last price for an index.",
        "index_snapshot_market_value": "Real-time market value for an index.",
        # Index - History
        "index_history_eod": "End-of-day report for an index. Generated at 17:15 ET daily.",
        "index_history_ohlc": "Historical OHLC bars for an index.",
        "index_history_price": "Historical price reports for an index. Max 1 month per request.",
        # Index - At Time
        "index_at_time_price": "Index price at a specific time of day.",
        # Calendar
        "calendar_open_today": "Current day equity market schedule.",
        "calendar_on_date": "Equity market schedule for a given date.",
        "calendar_year": "Equity market holidays for a given year.",
    }

    # Define component customization function to add subscription tier tags
    def customize_components(
        route: HTTPRoute,
        component: OpenAPITool | OpenAPIResource | OpenAPIResourceTemplate,
    ) -> None:
        """Add subscription tier tags, concise descriptions, and override default format."""
        tier = extract_tier_from_spec(openapi_spec, route.path)
        tag = get_tier_tag(tier)
        component.tags.add(tag)

        # Replace verbose OpenAPI descriptions with concise LLM-optimized ones
        op_id = component.name
        if op_id in short_descriptions:
            desc = short_descriptions[op_id]
        else:
            desc = component.description or ""
        if tier:
            component.description = f"[{tier.upper()}] {desc}"
        else:
            component.description = desc

        # Strip output_schema to reduce tools/list payload size (~85KB savings)
        if isinstance(component, OpenAPITool):
            component.output_schema = None

        # Remove 'format' param from schemas — transport layer forces json_new
        if isinstance(component, OpenAPITool) and component.parameters:
            params = component.parameters
            if isinstance(params, dict):
                if "properties" in params:
                    params["properties"].pop("format", None)
                if "required" in params and "format" in params["required"]:
                    params["required"].remove("format")

    # Create the MCP server from the OpenAPI spec
    mcp = FastMCP.from_openapi(
        openapi_spec=openapi_spec,
        client=client,
        name="Theta Data MCP Server",
        mcp_component_fn=customize_components,
        route_maps=[
            # All endpoints become tools for broad MCP client compatibility
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
