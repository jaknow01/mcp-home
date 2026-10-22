"""`mcp-home` command line: `serve` (default) runs the MCP server."""

import argparse

from jarvis_mcp_kit import run, setup_logging

from mcp_home.server import server


def create_app():
    from mcp_home import tools  # noqa: F401  (registers the tools on `server`)

    return server.app()


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="mcp-home")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("serve", help="run the MCP server (default)")
    args = parser.parse_args(argv)
    setup_logging()
    if args.cmd in (None, "serve"):
        run(create_app())


if __name__ == "__main__":
    main()
