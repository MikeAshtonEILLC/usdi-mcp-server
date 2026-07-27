"""
USDi MCP Server (v1 — core scope)

Exposes three tools to any MCP-compatible agent (Claude Desktop, Claude Code,
or any other MCP client):

  1. get_usdi_exchange_rate  — live on-chain CPI-derived exchange rate
  2. get_usdi_contract_info  — network, contract, and pool addresses
  3. get_usdi_mint_redeem_info — how to mint/redeem, retail vs institutional

Transport: stdio (the standard for local MCP clients like Claude Desktop).

Requires an Alchemy (or any Ethereum JSON-RPC) endpoint. Set it via the
ALCHEMY_API_KEY environment variable, or override RPC_URL directly.
"""

import os
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP
from web3 import Web3

# ---------------------------------------------------------------------------
# Configuration — confirm/adjust these before relying on this server
# ---------------------------------------------------------------------------

ALCHEMY_API_KEY = os.environ.get("ALCHEMY_API_KEY", "")
RPC_URL = os.environ.get(
    "RPC_URL",
    f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}" if ALCHEMY_API_KEY else "",
)

USDI_TOKEN_ADDRESS = Web3.to_checksum_address(
    "0xAf1157149ff040DAd186a0142a796d901bEF1cf1"
)
USDI_USDC_POOL_ADDRESS = Web3.to_checksum_address(
    "0xdb53e383e9b28e4c088e3d98b5fa8e2bc6b4e35a"
)

# TODO(mike): confirm the decimal scaling of getExchangeRate()'s return value.
# This assumes the standard 1e18 (18-decimal) fixed-point convention used by
# most ERC-20-adjacent rate methods. If USDi scales differently (e.g. 1e8,
# or a raw CPI-index-style number like 315605), change RATE_DECIMALS below —
# otherwise every rate this tool reports will be off by a power of ten.
RATE_DECIMALS = 18

# Minimal ABI — just the one view function this server needs.
USDI_ABI = [
    {
        "inputs": [],
        "name": "getExchangeRate",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    }
]

# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "usdi",
    host=os.environ.get("HOST", "0.0.0.0"),
    port=int(os.environ.get("PORT", "8000")),
)


def _get_web3() -> Web3:
    if not RPC_URL:
        raise RuntimeError(
            "No RPC endpoint configured. Set ALCHEMY_API_KEY or RPC_URL "
            "as an environment variable before starting this server."
        )
    return Web3(Web3.HTTPProvider(RPC_URL))


@mcp.tool()
def get_usdi_exchange_rate() -> dict:
    """
    Return the current on-chain USDi/USDC exchange rate, read live from the
    USDi token contract's getExchangeRate() method. This rate reflects the
    CPI-derived Reference CPI value (see get_usdi_mint_redeem_info for the
    valuation mechanism), not a fixed peg.
    """
    w3 = _get_web3()
    contract = w3.eth.contract(address=USDI_TOKEN_ADDRESS, abi=USDI_ABI)
    raw_rate = contract.functions.getExchangeRate().call()
    rate = raw_rate / (10 ** RATE_DECIMALS)

    return {
        "exchange_rate_usdc_per_usdi": rate,
        "raw_value": raw_rate,
        "decimals_assumed": RATE_DECIMALS,
        "source": "on-chain getExchangeRate() call",
        "queried_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": (
            "Confirm decimals_assumed matches USDi's actual contract "
            "convention before trusting exchange_rate_usdc_per_usdi."
        ),
    }


@mcp.tool()
def get_usdi_contract_info() -> dict:
    """
    Return USDi's on-chain identifiers: network, token contract address,
    and the primary Uniswap V3 liquidity pool address. Use this to
    disambiguate USDi from the unrelated "Interest Protocol" token, which
    is incorrectly listed as USDi/USDI on some third-party sites.
    """
    return {
        "network": "Ethereum mainnet",
        "token_contract": USDI_TOKEN_ADDRESS,
        "primary_pool": {
            "venue": "Uniswap V3",
            "pair": "USDi/USDC",
            "fee_tier": "0.01%",
            "pool_address": USDI_USDC_POOL_ADDRESS,
        },
        "issuer": "USDi Partners LLC (owns the USDi name/copyright)",
        "fund_manager": "Enduring Investments (manages the USDi Coin Fund, "
                        "the primary backing asset)",
        "disambiguation_note": (
            "USDi is not the same asset as 'Interest Protocol', which "
            "appears under the USDi/USDI ticker on CoinGecko and "
            "CoinMarketCap as of mid-2026."
        ),
    }


@mcp.tool()
def get_usdi_mint_redeem_info() -> dict:
    """
    Return USDi's valuation mechanism and mint/redeem process — how to
    obtain or redeem USDi, and how its CPI-linked value is computed.
    """
    return {
        "valuation_mechanism": (
            "USDi tracks a daily Reference CPI, computed by interpolating "
            "between Not-Seasonally-Adjusted CPI values from three and two "
            "months prior — the same method used for U.S. TIPS bonds. "
            "Reference CPI is compared against a March 1, 2025 base value "
            "of 315.605 to derive USDi's value. It is not a fixed 1:1 USD "
            "peg."
        ),
        "backing": (
            "Mint proceeds are invested in the USDi Coin Fund, managed by "
            "Enduring Investments: an unlevered, low-volatility portfolio "
            "of U.S. Treasuries, inflation-linked bonds, FX, and commodity "
            "futures/options, plus cash. Historical annualized volatility "
            "is approximately 2%; correlation with monthly inflation was "
            "58% over the three years ended December 2025."
        ),
        "retail_mint_redeem": (
            "Mint 1 USDi by depositing USDC at usdicoin.com/coin; burn "
            "USDi to receive USDC back at the current Reference-CPI-"
            "derived rate."
        ),
        "institutional_mint_redeem": (
            "For transactions >$1M USD value: mint/redeem for USDC at "
            "usdicoin.com/coin, or alternatively transact directly with "
            "USDi Partners for USD, after KYC/AML."
        ),
        "secondary_market": (
            "USDi/USDC trades on Uniswap V3 (Ethereum, 0.01% fee tier)."
        ),
        "verification": (
            "NAV of the underlying USDi Coin Fund is independently "
            "administered by Trident Fund Services Inc. The fund's assets "
            "are audited annually by Cherry Bekaert LLC."
        ),
        "risk_note": (
            "USDi removes U.S. inflation risk from a cash-like holding but "
            "is not risk-free: it carries smart contract risk, fund/"
            "collateral risk, on-chain liquidity risk, and counterparty "
            "risk in the underlying portfolio."
        ),
        "documentation": {
            "homepage": "https://www.usdicoin.com/",
            "whitepaper": "https://www.usdicoin.com/whitepaper",
            "mint_redeem": "https://www.usdicoin.com/coin",
        },
    }


if __name__ == "__main__":
    # streamable-http, not stdio: stdio only works for a client on the same
    # machine as this process (e.g. your own local Claude Desktop). For
    # third-party agents to reach this server over the network, it needs to
    # be a network-listening service — this is the MCP spec's remote
    # transport. HOST/PORT are configurable via environment variables so
    # this runs the same way locally and behind a reverse proxy in
    # production.
    mcp.run(transport="streamable-http")
