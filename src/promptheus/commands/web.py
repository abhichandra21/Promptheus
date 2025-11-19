"""Web command for Promptheus CLI."""
import argparse
from typing import Optional

from promptheus.web.server import start_web_server, find_available_port


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for the web command."""
    parser.add_argument(
        "--port",
        type=int,
        help="Port to run the web server on (default: auto-find available port)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind the web server to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't automatically open browser after starting server"
    )


def web_command(port: Optional[int], host: str, no_browser: bool) -> None:
    """Handle the web command."""
    start_web_server(
        port=port if port else find_available_port(),
        host=host,
        no_browser=no_browser
    )