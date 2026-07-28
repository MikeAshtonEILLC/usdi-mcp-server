# USDi MCP Server

A Python MCP (Model Context Protocol) server that lets any MCP-compatible
agent — Claude, or other MCP clients — query USDi directly, instead of
scraping web pages for its data.

USDi is a CPI-indexed cryptocurrency issued by USDi Partners LLC. Details:
[usdicoin.com](https://www.usdicoin.com/).

## Live endpoint

```
https://usdi-mcp.onrender.com/mcp
```

Transport: Streamable HTTP. No authentication required (read-only public
data).

## Tools

- **get_usdi_exchange_rate** — live on-chain USDi/USDC exchange rate via
  `getExchangeRate()`
- **get_usdi_contract_info** — network, token contract, pool address,
  issuer/fund manager, and disambiguation from the unrelated "Interest
  Protocol" token
- **get_usdi_mint_redeem_info** — valuation mechanism, backing, retail and
  institutional mint/redeem process, risk characteristics

Deferred to a later version: liquidity/pool depth (Uniswap V3 QuoterV2),
fund composition detail, audit document retrieval.

## Using this server

Point any MCP-compatible client at the live endpoint above. For Claude
Desktop, add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "usdi": {
      "url": "https://usdi-mcp.onrender.com/mcp",
      "transport": "streamable-http"
    }
  }
}
```

## Running locally

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
export ALCHEMY_API_KEY="your-alchemy-key"   # or set RPC_URL directly
python3 server.py
```

Starts an HTTP server on port 8000 (override with `PORT`), serving MCP's
streamable-http transport at `/mcp`.

## Deployment

This repo includes a `Dockerfile` and `render.yaml` for deployment on
Render. See `render.yaml` for configuration.

## Known limitation

`RATE_DECIMALS` in `server.py` assumes an 18-decimal fixed-point
convention for `getExchangeRate()`'s return value. Verify this against a
known-good rate before relying on it in production.

## License / Contact

Issuer: USDi Partners LLC — [usdicoin.com](https://www.usdicoin.com/)
