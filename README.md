# Theta Data MCP Server

A local MCP (Model Context Protocol) wrapper for the Theta Data API, providing AI models with access to real-time and historic stock, options, and index data.

## Overview

This MCP server is generated from the Theta Data OpenAPI specification using [FastMCP](https://github.com/jlowin/fastmcp). It exposes API endpoints as MCP tools, allowing AI assistants to query market data directly.

### Supported Data Types

- **Stocks**: Symbols, EOD data, OHLC, trades, quotes, snapshots
- **Options**: Symbols, expirations, strikes, contracts, Greeks, implied volatility
- **Indices**: Symbols, prices, OHLC, market values
- **Calendar**: Market open dates

## Prerequisites

1. Python 3.10+
2. [uv](https://github.com/astral-sh/uv) for package management
3. Theta Data terminal running locally (default: `http://127.0.0.1:25503`)
4. A Theta Data subscription ([subscribe here](https://www.thetadata.net/))

## Installation

```bash
# Create virtual environment and install all dependencies (including dev)
uv sync
```

## Usage

### Running the Server

```bash
# Run with stdio transport (default)
uv run server.py

# Run with SSE transport
uv run server.py --transport sse

# Custom base URL
uv run server.py --base-url http://localhost:25503/v3

# Custom timeout
uv run server.py --timeout 60.0
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `THETADATA_BASE_URL` | Theta Data API base URL | `http://127.0.0.1:25503/v3` |
| `THETADATA_TIMEOUT` | Request timeout in seconds | `30.0` |

### MCP Client Configuration

Add the following to your MCP client config, replacing `/path/to/thetadata-mcp` with the actual path to this repository:

```json
{
  "mcpServers": {
    "thetadata": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/thetadata-mcp",
        "run",
        "server.py"
      ],
      "env": {
        "THETADATA_BASE_URL": "http://127.0.0.1:25503/v3",
        "THETADATA_TIMEOUT": "30.0"
      }
    }
  }
}
```

## Available Tools

The server exposes all Theta Data v3 API endpoints as MCP tools, including:

**Stock Data**
- `stock_list_symbols` - List all stock symbols
- `stock_list_dates` - List available dates for a request type
- `stock_snapshot_ohlc` - Real-time OHLC data
- `stock_snapshot_trade` - Real-time trade data
- `stock_snapshot_quote` - Real-time quote data
- `stock_history_eod` - Historic EOD data
- `stock_history_ohlc` - Historic OHLC bars
- `stock_history_trade` - Historic trade data
- `stock_history_quote` - Historic quote data

**Options Data**
- `option_list_symbols` - List optionable symbols
- `option_list_expirations` - List expirations for a symbol
- `option_list_strikes` - List strikes for an expiration
- `option_list_contracts` - List option contracts
- `option_snapshot_ohlc` - Real-time option OHLC
- `option_snapshot_greeks_all` - All Greeks (delta, gamma, theta, vega, rho)
- `option_snapshot_greeks_implied_volatility` - Implied volatility
- `option_history_eod` - Historic option EOD data
- `option_history_greeks_all` - Historic Greeks data

**Index Data**
- `index_list_symbols` - List index symbols
- `index_snapshot_price` - Real-time index prices
- `index_history_eod` - Historic index EOD data

**Calendar**
- `calendar_open_today` - Check if market is open today
- `calendar_on_date` - Check if market is open on a specific date

See the [Theta Data API documentation](https://www.thetadata.net/) for full details on parameters and responses.

## Example Queries

Once connected to an MCP client, you can ask:

- "List all available stock symbols"
- "Get the current OHLC data for AAPL"
- "What are the available option expirations for SPY?"
- "Show me the Greeks for the SPY 500 call expiring next Friday"
- "Is the market open today?"

## Development

### Pre-commit Hooks

This project uses [pre-commit](https://pre-commit.com/) to run `ruff` linting and formatting automatically on every commit.

**Setup (one-time per clone):**
```bash
uv run pre-commit install
```

The hook will now automatically check and fix code formatting when you commit changes.

### Manual Development Commands

```bash
# Run linting with uv
uv run ruff check .

# Format code with uv
uv run ruff format .

# Regenerate endpoints_by_subscription documentation
uv run python generate_endpoint_docs.py
```

### Regenerating Endpoint Documentation

The `generate_endpoint_docs.py` script reads the `x-min-subscription` field from `openapiv3_updated.yaml` and regenerates the markdown files in `endpoints_by_subscription/`. Each tier file shows all endpoints available at that subscription level and below (cumulative):

- `endpoints_free.md` - Free tier endpoints
- `endpoints_value.md` - Free + Value tier endpoints
- `endpoints_standard.md` - Free + Value + Standard tier endpoints
- `endpoints_professional.md` - All endpoints

## License

MIT License - See LICENSE file for details.

## Resources

- [FastMCP Documentation](https://gofastmcp.com/)
- [Theta Data API](https://www.thetadata.net/)
- [MCP Protocol](https://modelcontextprotocol.io/)
