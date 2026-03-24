"""Stim MCP Server - main entry point."""

from __future__ import annotations

import logging
import os

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

from mcp.server.fastmcp import FastMCP

from .circuit_store import CircuitStore
from .tools import analysis, circuit_management, health, simulation, visualization
from . import resources

mcp = FastMCP(
    "stim-mcp-server",
    instructions=(
        "This server exposes Google's Stim quantum stabilizer circuit simulator as MCP tools. "
        "Use create_circuit to start a session, then sample_circuit, analyze_errors, "
        "get_circuit_diagram, inject_noise, and append_operation to explore and refine circuits."
    ),
)

_store = CircuitStore()

health.register(mcp, _store)
circuit_management.register(mcp, _store)
simulation.register(mcp, _store)
analysis.register(mcp, _store)
visualization.register(mcp, _store)
resources.register(mcp, _store)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "stdio")

    if transport == "stdio":
        mcp.run(transport="stdio")
    else:
        from starlette.middleware.cors import CORSMiddleware
        from mcp.server.streamable_http import TransportSecuritySettings
        import uvicorn

        host = os.environ.get("MCP_HOST", "0.0.0.0")
        port = int(os.environ.get("MCP_PORT", "8080"))

        mcp.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
        )

        app = mcp.streamable_http_app()
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
        uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
