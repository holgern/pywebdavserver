"""Command-line interface for pywebdavserver."""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

import click
from rich.console import Console
from rich.logging import RichHandler

from .config import get_config_manager
from .constants import (
    DEFAULT_CACHE_TTL,
    DEFAULT_HOST,
    DEFAULT_MAX_FILE_SIZE,
    DEFAULT_PATH,
    DEFAULT_PORT,
)

console = Console()
logger = logging.getLogger(__name__)


@click.group(invoke_without_command=True)
@click.pass_context
@click.option(
    "--backend",
    help="Backend name from config or backend type (local/drime)",
)
@click.option(
    "--path",
    type=click.Path(),
    default=DEFAULT_PATH,
    help=f"Root directory path for local backend (default: {DEFAULT_PATH})",
)
@click.option(
    "--host",
    default=DEFAULT_HOST,
    help=f"Host address to bind to (default: {DEFAULT_HOST})",
)
@click.option(
    "--port",
    type=int,
    default=DEFAULT_PORT,
    help=f"Port number to listen on (default: {DEFAULT_PORT})",
)
@click.option(
    "--username",
    help="WebDAV username for authentication (omit for anonymous access)",
)
@click.option(
    "--password",
    help="WebDAV password for authentication",
)
@click.option(
    "--readonly",
    is_flag=True,
    default=False,
    help="Enable read-only mode (no writes allowed)",
)
@click.option(
    "--cache-ttl",
    type=float,
    default=DEFAULT_CACHE_TTL,
    help=f"Cache TTL in seconds for Drime backend (default: {DEFAULT_CACHE_TTL})",
)
@click.option(
    "--max-file-size",
    type=int,
    default=DEFAULT_MAX_FILE_SIZE,
    help=f"Maximum file size in bytes (default: {DEFAULT_MAX_FILE_SIZE})",
)
@click.option(
    "--workspace-id",
    type=int,
    default=0,
    help="Workspace ID for Drime backend (0 = personal, default: 0)",
)
@click.option(
    "--ssl-cert",
    type=click.Path(exists=True),
    help="Path to SSL certificate file (for HTTPS)",
)
@click.option(
    "--ssl-key",
    type=click.Path(exists=True),
    help="Path to SSL private key file (for HTTPS)",
)
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Increase verbosity (can be repeated: -v, -vv, -vvv, etc.)",
)
@click.option(
    "--no-auth",
    is_flag=True,
    default=False,
    help="Disable authentication (allow anonymous access)",
)
@click.version_option()
def cli(
    ctx: click.Context,
    backend: str | None,
    path: str,
    host: str,
    port: int,
    username: str | None,
    password: str | None,
    readonly: bool,
    cache_ttl: float,
    max_file_size: int,
    workspace_id: int,
    ssl_cert: str | None,
    ssl_key: str | None,
    verbose: int,
    no_auth: bool,
) -> None:
    """PyWebDAV Server - WebDAV server with pluggable storage backends.

    Supports local filesystem and Drime Cloud storage backends with
    named backend configurations for easy management.

    \b
    Examples:
        # Start with a configured backend
        pywebdavserver --backend drime-personal

        # Start with local filesystem backend (anonymous access)
        pywebdavserver --backend local --no-auth

        # Start with Drime Cloud backend (legacy env vars)
        export DRIME_EMAIL="user@example.com"
        export DRIME_PASSWORD="password"
        pywebdavserver --backend drime --workspace-id 0 --no-auth

        # Manage backend configurations
        pywebdavserver config add drime-work
        pywebdavserver config list
    """
    # If a subcommand is invoked, don't start the server
    if ctx.invoked_subcommand is not None:
        return

    # Default backend if not specified
    if backend is None:
        backend = "local"

    # Setup logging
    log_level = logging.WARNING
    if verbose >= 3:
        log_level = logging.DEBUG
    elif verbose >= 1:
        log_level = logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )

    # Handle authentication flags
    if no_auth:
        username = None
        password = None
    elif username and not password:
        console.print(
            "[yellow]Warning: Username provided but no password. Using anonymous access.[/yellow]"
        )
        username = None
    elif not username and password:
        console.print(
            "[yellow]Warning: Password provided but no username. Using anonymous access.[/yellow]"
        )
        password = None

    # Check if backend is a named config
    config_manager = get_config_manager()
    backend_config = config_manager.get_backend(backend)

    if backend_config:
        # Use configured backend
        console.print(f"[blue]Loading backend '{backend}' from config...[/blue]")
        _start_from_config(
            backend_config=backend_config,
            host=host,
            port=port,
            username=username,
            password=password,
            ssl_cert=ssl_cert,
            ssl_key=ssl_key,
            verbose=verbose,
        )
    else:
        # Legacy mode: backend is a type (local/drime)
        _start_from_type(
            backend_type=backend,
            path=path,
            host=host,
            port=port,
            username=username,
            password=password,
            readonly=readonly,
            cache_ttl=cache_ttl,
            max_file_size=max_file_size,
            workspace_id=workspace_id,
            ssl_cert=ssl_cert,
            ssl_key=ssl_key,
            verbose=verbose,
        )


def _start_from_config(
    backend_config: Any,
    host: str,
    port: int,
    username: str | None,
    password: str | None,
    ssl_cert: str | None,
    ssl_key: str | None,
    verbose: int,
) -> None:
    """Start server using a configured backend."""
    from .server import run_webdav_server

    backend_type = backend_config.backend_type
    config = backend_config.get_all()

    try:
        if backend_type == "local":
            from .providers.local import LocalStorageProvider

            root_path = config.get("path", DEFAULT_PATH)
            readonly = config.get("readonly", False)

            console.print(
                f"[blue]Initializing local filesystem provider at: {root_path}[/blue]"
            )
            provider = LocalStorageProvider(root_path=root_path, readonly=readonly)
            server_name = f"PyWebDAV Server ({backend_config.name}: {root_path})"

        elif backend_type == "drime":
            try:
                from pydrime.api import DrimeClient

                from .providers.drime import DrimeDAVProvider
            except ImportError:
                console.print(
                    "[red]Error: Drime backend requires pydrime to be installed.[/red]\n"
                    "Install it with: pip install 'pywebdavserver[drime]'"
                )
                sys.exit(1)

            # Get Drime configuration from config (not CLI args)
            api_key = config.get("api_key")
            workspace_id_config = config.get("workspace_id", 0)
            readonly = config.get("readonly", False)
            cache_ttl = config.get("cache_ttl", DEFAULT_CACHE_TTL)
            max_file_size = config.get("max_file_size", DEFAULT_MAX_FILE_SIZE)

            if not api_key:
                console.print(
                    "[red]Error: Drime backend requires api_key in config.[/red]\n"
                    f"Reconfigure with: pywebdavserver config add {backend_config.name}"
                )
                sys.exit(1)

            console.print(
                f"[blue]Connecting to Drime Cloud (workspace: {workspace_id_config})...[/blue]"
            )
            client = DrimeClient(api_key=api_key)

            provider = DrimeDAVProvider(
                client=client,
                workspace_id=workspace_id_config,
                readonly=readonly,
                cache_ttl=cache_ttl,
                max_file_size=max_file_size,
            )
            server_name = f"PyWebDAV Server ({backend_config.name}: workspace {workspace_id_config})"

        else:
            console.print(f"[red]Error: Unknown backend type '{backend_type}'[/red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error initializing {backend_type} provider: {e}[/red]")
        logger.exception("Provider initialization failed")
        sys.exit(1)

    # Display server info
    console.print("\n[bold green]Starting PyWebDAV Server[/bold green]")
    console.print(
        f"  Backend: [cyan]{backend_config.name}[/cyan] (type: {backend_type})"
    )
    console.print(f"  Address: [cyan]{host}:{port}[/cyan]")

    # Get readonly status from config
    readonly = config.get("readonly", False)
    console.print(f"  Mode: [cyan]{'Read-only' if readonly else 'Read-write'}[/cyan]")

    if username:
        console.print(f"  Auth: [cyan]Enabled (user: {username})[/cyan]")
    else:
        console.print("  Auth: [yellow]Disabled (anonymous access)[/yellow]")
    if ssl_cert and ssl_key:
        console.print("  SSL: [cyan]Enabled[/cyan]")
    console.print()

    # Start the server
    try:
        run_webdav_server(
            provider=provider,
            host=host,
            port=port,
            username=username,
            password=password,
            verbose=verbose + 1,
            ssl_cert=ssl_cert,
            ssl_key=ssl_key,
            server_name=server_name,
        )
    except Exception as e:
        console.print(f"\n[red]Error running server: {e}[/red]")
        logger.exception("Server error")
        sys.exit(1)


def _start_from_type(
    backend_type: str,
    path: str,
    host: str,
    port: int,
    username: str | None,
    password: str | None,
    readonly: bool,
    cache_ttl: float,
    max_file_size: int,
    workspace_id: int,
    ssl_cert: str | None,
    ssl_key: str | None,
    verbose: int,
) -> None:
    """Start server using legacy backend type specification."""
    from .server import run_webdav_server

    # Create the appropriate provider based on backend type
    try:
        if backend_type.lower() == "local":
            from .providers.local import LocalStorageProvider

            console.print(
                f"[blue]Initializing local filesystem provider at: {path}[/blue]"
            )
            provider = LocalStorageProvider(root_path=path, readonly=readonly)
            server_name = f"PyWebDAV Server (Local: {path})"

        elif backend_type.lower() == "drime":
            # Import Drime-specific dependencies
            try:
                from pydrime.api import DrimeClient

                from .providers.drime import DrimeDAVProvider
            except ImportError:
                console.print(
                    "[red]Error: Drime backend requires pydrime to be installed.[/red]\n"
                    "Install it with: pip install 'pywebdavserver[drime]'"
                )
                sys.exit(1)

            # Get Drime credentials from environment
            api_key = os.environ.get("DRIME_API_KEY")

            if not api_key:
                console.print(
                    "[red]Error: Drime backend requires DRIME_API_KEY environment variable.[/red]\n"
                    "Set it with:\n"
                    "  export DRIME_API_KEY='your-api-key'\n\n"
                    "Or configure a named backend:\n"
                    "  pywebdavserver config add drime-personal"
                )
                sys.exit(1)

            console.print(
                f"[blue]Connecting to Drime Cloud (workspace: {workspace_id})...[/blue]"
            )
            client = DrimeClient(api_key=api_key)

            provider = DrimeDAVProvider(
                client=client,
                workspace_id=workspace_id,
                readonly=readonly,
                cache_ttl=cache_ttl,
                max_file_size=max_file_size,
            )
            server_name = f"PyWebDAV Server (Drime: workspace {workspace_id})"

        else:
            console.print(f"[red]Error: Unknown backend '{backend_type}'[/red]")
            console.print("\nAvailable backends: local, drime")
            console.print("\nOr use a configured backend:")
            config_manager = get_config_manager()
            for name in config_manager.list_backends():
                console.print(f"  - {name}")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error initializing {backend_type} provider: {e}[/red]")
        logger.exception("Provider initialization failed")
        sys.exit(1)

    # Display server info
    console.print("\n[bold green]Starting PyWebDAV Server[/bold green]")
    console.print(f"  Backend: [cyan]{backend_type}[/cyan]")
    console.print(f"  Address: [cyan]{host}:{port}[/cyan]")
    console.print(f"  Mode: [cyan]{'Read-only' if readonly else 'Read-write'}[/cyan]")
    if username:
        console.print(f"  Auth: [cyan]Enabled (user: {username})[/cyan]")
    else:
        console.print("  Auth: [yellow]Disabled (anonymous access)[/yellow]")
    if ssl_cert and ssl_key:
        console.print("  SSL: [cyan]Enabled[/cyan]")
    console.print()

    # Start the server
    try:
        run_webdav_server(
            provider=provider,
            host=host,
            port=port,
            username=username,
            password=password,
            verbose=verbose + 1,
            ssl_cert=ssl_cert,
            ssl_key=ssl_key,
            server_name=server_name,
        )
    except Exception as e:
        console.print(f"\n[red]Error running server: {e}[/red]")
        logger.exception("Server error")
        sys.exit(1)


# Import and register config subcommand
from .cli_config import config_group

cli.add_command(config_group)


# For backwards compatibility with existing entry point
def main() -> None:
    """Entry point for backwards compatibility."""
    cli()


if __name__ == "__main__":
    main()
