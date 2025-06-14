"""Main CLI entry point for LLM Task Framework."""

import click
from click import Context

from llm_task_framework.__version__ import __version__


@click.group()
@click.version_option(version=__version__)
@click.pass_context
def main(ctx: Context) -> None:
    """LLM Task Framework - Generic framework for building LLM-powered task execution systems."""
    ctx.ensure_object(dict)


@main.command()
def version() -> None:
    """Show the version."""
    click.echo(f"LLM Task Framework {__version__}")


@main.command()
@click.option("--host", default="localhost", help="Host to bind the MCP server to")
@click.option("--port", default=8000, help="Port to bind the MCP server to")
@click.option(
    "--transport", default="stdio", help="Transport type (stdio, http, websocket)"
)
def serve(host: str, port: int, transport: str) -> None:
    """Start the MCP server."""
    click.echo(f"Starting MCP server on {host}:{port} with {transport} transport...")
    click.echo("(MCP server implementation coming soon)")


@main.command()
def list_tasks() -> None:
    """List available task types."""
    click.echo("Available task types:")
    click.echo("  • pytest_analysis - Analyze pytest failures and suggest fixes")
    click.echo("  • docstring_generation - Generate Python docstrings")
    click.echo("  • code_analysis - Analyze code structure and quality")
    click.echo("  • custom - Define your own task types")


if __name__ == "__main__":
    main()
