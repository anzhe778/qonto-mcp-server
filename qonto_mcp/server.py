import os
from dotenv import load_dotenv
import argparse
import logging
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

# Load environment variables
load_dotenv()

# Setup Qonto API configuration
qonto_mcp.setup_qonto_config()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # --- argument parsing ---------------------------------------------------
    parser = argparse.ArgumentParser(
        description="Run the MCP server with a selectable transport."
    )
    parser.add_argument(
        "--transport",
        choices=["streamable-http", "stdio"],
        default="stdio",
        help="Communication transport to use (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="HTTP bind host (overrides env). Default: 127.0.0.1",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="HTTP bind port (overrides env). Default: 8000",
    )
    args = parser.parse_args()

    # --- security notice ----------------------------------------------------
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

    # --- resolve host/port: CLI > env (multiple variants) > default ---------
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

    # Mutate mcp.settings if available (covers most SDK versions)
    if args.transport == "streamable-http":
        try:
            mcp.settings.host = bind_host
            mcp.settings.port = bind_port
            logger.info("Applied bind via mcp.settings.")
        except Exception as e:
            logger.warning(f"Could not set mcp.settings host/port: {e}")

    # Run — try with kwargs first (newer SDKs), fall back to bare call
    try:
        if args.transport == "streamable-http":
            mcp.run(transport=args.transport, host=bind_host, port=bind_port)
        else:
            mcp.run(transport=args.transport)
    except TypeError as e:
        logger.warning(
            f"mcp.run() rejected host/port kwargs ({e}); falling back to settings-only."
        )
        mcp.run(transport=args.transport)
