# USDi MCP Server (v1)

A Python MCP (Model Context Protocol) server that lets any MCP-compatible
agent — Claude Desktop, Claude Code, or other MCP clients — query USDi
directly instead of scraping web pages.

## v1 scope (core only)

- `get_usdi_exchange_rate` — live on-chain exchange rate via `getExchangeRate()`
- `get_usdi_contract_info` — network, token contract, pool address, issuer/fund manager, disambiguation from "Interest Protocol"
- `get_usdi_mint_redeem_info` — valuation mechanism, backing, retail/institutional mint-redeem process, risk note

Deferred to a later version: liquidity/pool depth (Uniswap V3 QuoterV2),
fund composition detail, audit document retrieval.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate          # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Set your RPC endpoint. Using Alchemy (matches your existing infra):

```bash
export ALCHEMY_API_KEY="your-alchemy-key"
```

Or point at any Ethereum JSON-RPC endpoint directly:

```bash
export RPC_URL="https://your-rpc-endpoint"
```

## Run it standalone (sanity check)

```bash
python3 server.py
```

This starts an HTTP server on port 8000 (override with `PORT`), speaking
MCP's streamable-http transport at `/mcp`. It's not a page you visit in a
browser — it's a JSON-RPC endpoint MCP clients POST to. Ctrl+C to stop.

You do **not** need this for your own local Claude Desktop — this
transport is specifically for making USDi reachable by *other* people's
agents over the network. (If you ever also want it available to your own
local Claude Desktop, that's a separate, simpler stdio config — ask if you
want that added back as an option.)

## Getting found by third-party agentic finance agents

This is two separate steps: hosting, then listing.

### 1. Host it: deploying to Render (recommended — no card, no billing risk)

Render's free tier requires no credit card and has hard resource caps
rather than usage-based billing — it cannot surprise-bill you, because
there's no billing account attached until you explicitly choose to
upgrade. This scaffold includes `render.yaml` alongside the same
`Dockerfile`.

```bash
# No CLI install needed — Render deploys from a Git repo.
# 1. Push this usdi_mcp_server/ folder to a GitHub repo.
# 2. In the Render dashboard: New -> Blueprint -> connect that repo.
#    Render will read render.yaml automatically.
# 3. Set ALCHEMY_API_KEY in the Render dashboard's environment variables
#    (render.yaml intentionally leaves it unset so the key never sits in
#    a file you might commit).
# 4. Deploy.
```

That gives you a public `https://usdi-mcp.onrender.com/mcp` endpoint —
free, TLS-terminated. **Trade-off:** the free plan spins the service down
after 15 minutes of inactivity; the next request wakes it, with roughly
30-60 seconds of added latency on that first call. For an endpoint agents
query occasionally rather than continuously, that's a reasonable price
for zero financial exposure. If cold starts become a problem once this
sees real traffic, Render's paid tier removes spin-down for $7/month —
but that's a decision to make once you can see actual usage, not before.

**Custom domain:** once deployed, add `mcp.usdicoin.com` as a custom
domain in the Render dashboard and point a CNAME at the `.onrender.com`
address it gives you — agents and registries will trust `usdicoin.com`'s
own domain more than a third-party one.

**Note:** I don't have Docker available to fully build-test this image in
this environment — the Dockerfile is a standard minimal Python setup and
the server script itself is verified working (streamable-http handshake
tested locally), but build it locally yourself before deploying to catch
anything environment-specific.

<details>
<summary>Alternative: Fly.io (skip unless you specifically want its global edge network)</summary>

`fly.toml` is still included in this scaffold if you change your mind
later. The reason it's not the primary recommendation: Fly requires a
card on file and, per their own docs, does not support hard billing caps
or even billing alerts — a prepaid-credit balance can roll straight into
automatic billing once exhausted rather than stopping. Fine for infra
you're actively monitoring; not a fit for a "set it up and don't think
about it" public endpoint. If you ever do want it (e.g. for lower
latency across regions), the steps from earlier in this project still
apply: `fly launch --no-deploy`, `fly secrets set`, `fly deploy`.

</details>

### 2. List it where agents and their builders look

As of mid-2026 the registries that matter for MCP discovery are:
[mcp.so](https://mcp.so), [smithery.ai](https://smithery.ai),
[glama.ai/mcp](https://glama.ai/mcp), and the
[punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers)
GitHub list (submitted via pull request). Submitting to all four is the
current going advice — beyond that, returns diminish fast and a listing
with a dead link costs more trust than it's worth, so only submit once
the hosted URL is actually stable.

Each wants roughly the same metadata: server name, one-line description,
the public endpoint URL, transport type (`streamable-http`), and a
contact/maintainer link — worth preparing once and reusing across all
four submissions.

### 3. Cross-link it from `llms.txt`

Once hosted, add a line to `usdicoin.com/llms.txt` pointing at the MCP
endpoint directly — agents that already read `llms.txt` for background on
an asset will then have a direct, structured path to the live tools
instead of just the prose description. Say the word and I'll add that
section to the file we already built.

## ⚠️ Before trusting the exchange rate output

`RATE_DECIMALS` in `server.py` is currently set to `18` — the common
18-decimal fixed-point convention. **This is an assumption, not a confirmed
fact about USDi's contract.** If `getExchangeRate()` actually returns a
value scaled differently (e.g. 8 decimals, or a raw CPI-index-style number
like `315605`), the reported rate will be off by a power of ten. Check this
against a known-good rate (e.g. cross-reference against the Uniswap pool
price) before relying on it, and adjust `RATE_DECIMALS` accordingly.

## Wiring into Claude Desktop

Add to your Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "usdi": {
      "command": "/absolute/path/to/venv/bin/python3",
      "args": ["/absolute/path/to/usdi_mcp_server/server.py"],
      "env": {
        "ALCHEMY_API_KEY": "your-alchemy-key"
      }
    }
  }
}
```

Restart Claude Desktop afterward. USDi's three tools should then appear
available to Claude in any conversation.

## Next steps (v2 candidates)

- Add Uniswap V3 QuoterV2 calls for live liquidity depth / slippage estimates
- Expose fund backing composition and audit status as a tool once there's
  a machine-readable source for it (currently that lives in PDFs/prose)
- Consider a hosted (not just local stdio) deployment so third-party agents
  — not just your own Claude Desktop — can reach it, e.g. via the same
  MCP-over-HTTP pattern used by hosted connectors
