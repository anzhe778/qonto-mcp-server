"""
Qonto MCP server entry point.

Customisations vs. upstream:

1. Host/port are read from CLI args first, then from FASTMCP_/MCP_ env-var
   variants, then default. Pokes `mcp.settings` so older AND newer mcp[cli]
   releases pick up the bind correctly.

2. ASGI middleware rewrites incoming path "/mcp" to "/mcp/" before routing.
   The MCP streamable-http endpoint is registered at "/mcp/" (with slash);
   without rewriting, "/mcp" gets a 307 redirect, which Anthropic's custom-
   connector validator does not follow (it strips trailing slashes when
   registering URLs). The middleware lets both /mcp and /mcp/ work without
   any redirect.
"""

import os
import logging
import argparse

import qonto_mcp
from qonto_mcp import mcp

# Side-effect imports (tool registrations)
import qonto_mcp.tools.organization
import qonto_mcp.tools.transactions
import qonto_mcp.tools.transfers
import qonto_mcp.tools.beneficiaries
import qonto_mcp.tools.attachments
import qonto_mcp.tools.labels
import qonto_mcp.tools.memberships
import qonto_mcp.tools.invoices
import qonto_mcp.tools.statements
import qonto_mcp.tools.clients
import qonto_mcp.tools.requests

from dotenv import load_dotenv

load_dotenv()
qonto_mcp.setup_qonto_config()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _try_set(obj, name, value):
    try:
        setattr(obj, name, value)
        return True
    except Exception:
        return False


class AppendSlashMCP:
    """ASGI middleware: rewrite path '/mcp' to '/mcp/' so the inner Starlette
    router doesn't 307-redirect. Pass everything else through untouched."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http" and scope.get("path") == "/mcp":
            scope["path"] = "/mcp/"
            if "raw_path" in scope and isinstance(scope["raw_path"], (bytes, bytearray)):
                # raw_path may include query string; only rewrite the path part
                rp = scope["raw_path"]
                qmark = rp.find(b"?")
                if qmark == -1:
                    scope["raw_path"] = b"/mcp/"
                else:
                    scope["raw_path"] = b"/mcp/" + rp[qmark:]
        await self.app(scope, receive, send)


def _resolve_streamable_http_app():
    """Find FastMCP's streamable-http ASGI app across SDK variants."""
    for attr in (
        "streamable_http_app",
        "create_streamable_http_app",
        "_streamable_http_app",
        "streamable_http_asgi_app",
    ):
        if hasattr(mcp, attr):
            obj = getattr(mcp, attr)
            try:
                return obj() if callable(obj) else obj
            except Exception as e:
                logger.warning(f"mcp.{attr} raised: {e}")
                continue
    raise RuntimeError(
        "Could not find a streamable_http_app entry point on this mcp[cli] version. "
        "Run `pip show mcp` inside the container and report the version."
    )


def _run_streamable_http_with_middleware(bind_host: str, bind_port: int):
    import uvicorn

    _try_set(mcp.settings, "host", bind_host)
    _try_set(mcp.settings, "port", bind_port)
    for n in ("allowed_hosts", "trusted_hosts", "streamable_http_allowed_hosts"):
        _try_set(mcp.settings, n, ["*"])
    for n in ("validate_host_header", "host_validation", "dns_rebinding_protection"):
        _try_set(mcp.settings, n, False)

    inner = _resolve_streamable_http_app()
    app = AppendSlashMCP(inner)

    logger.info(
        f"Starting uvicorn on {bind_host}:{bind_port} with /mcp -> /mcp/ rewrite"
    )
    uvicorn.run(app, host=bind_host, port=bind_port, log_level="info")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the Qonto MCP server with a selectable transport."
    )
    parser.add_argument(
        "--transport",
        choices=["streamable-http", "stdio"],
        default="stdio",
    )
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    logger.info("⚠️🔒 SECURITY NOTICE")
    logger.info(
        "The MCP (Model Context Provider) protocol gives AI models access to additional functionality."
    )
    logger.info(
        "While this brings powerful integration capabilities, it also introduces important security considerations."
    )
    logger.info(
        "A malicious MCP server can secretly steal credentials and maliciously exploit other trusted MCP servers."
    )
    logger.info(
        "We recommend to only use MCP servers you trust, just as you would with any software you install."
    )
    logger.info("Find out more details in the `README.md` of this repository.")

    bind_host = (
        args.host
        or os.getenv("FASTMCP_HOST")
        or os.getenv("FASTMCP_SERVER_HOST")
        or os.getenv("MCP_HOST")
        or "127.0.0.1"
    )
    bind_port = args.port or int(
        os.getenv("FASTMCP_PORT")
        or os.getenv("FASTMCP_SERVER_PORT")
        or os.getenv("MCP_PORT")
        or "8000"
    )
    logger.info(
        f"Configured bind: host={bind_host} port={bind_port} transport={args.transport}"
    )

    if args.transport == "streamable-http":
        _run_streamable_http_with_middleware(bind_host, bind_port)
    else:
        mcp.run(transport=args.transport)
