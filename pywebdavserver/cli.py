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
@click.version_option()
def cli(ctx: click.Context) -> None:
    """PyWebDAV Server - WebDAV server with pluggable storage backends.

    Run 'pywebdavserver serve' to start the server.
    Run 'pywebdavserver config' for configuration management.
    """
    # If no subcommand, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
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
@click.option(
    "--backend-config",
    default=None,
    help="backend configuration name (from config file)",
)
def serve(
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
    backend_config: str | None,
) -> None:
    """Start the WebDAV server.

    \b
    Examples:
        # Start with a configured backend
        pywebdavserver serve --backend-config drime-personal

        # Start with local filesystem backend (anonymous access)
        pywebdavserver serve --backend local --no-auth

        # Start with Drime Cloud backend (legacy env vars)
        export DRIME_API_KEY="your-api-key"
        pywebdavserver serve --backend drime --workspace-id 0 --no-auth

        # Manage backend configurations
        pywebdavserver config
    """
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
            "[yellow]Warning: Username provided but no password. "
            "Using anonymous access.[/yellow]"
        )
        username = None
    elif not username and password:
        console.print(
            "[yellow]Warning: Password provided but no username. "
            "Using anonymous access.[/yellow]"
        )
        password = None

    # Check if backend_config is specified
    if backend_config:
        config_manager = get_config_manager()
        backend_cfg = config_manager.get_backend(backend_config)

        if not backend_cfg:
            console.print(f"[red]Backend config '{backend_config}' not found.[/red]")
            console.print("Available backends:")
            for name in config_manager.list_backends():
                console.print(f"  - {name}")
            sys.exit(1)

        # Use configured backend
        console.print(f"[blue]Loading backend '{backend_config}' from config...[/blue]")
        _start_from_config(
            backend_config=backend_cfg,
            host=host,
            port=port,
            username=username,
            password=password,
            ssl_cert=ssl_cert,
            ssl_key=ssl_key,
            verbose=verbose,
        )
    else:
        # Check if backend is a named config (for backwards compatibility)
        config_manager = get_config_manager()
        backend_cfg = config_manager.get_backend(backend)

        if backend_cfg:
            # Use configured backend
            console.print(f"[blue]Loading backend '{backend}' from config...[/blue]")
            _start_from_config(
                backend_config=backend_cfg,
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
                    "[red]Error: Drime backend requires pydrime to be "
                    "installed.[/red]\n"
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
                f"[blue]Connecting to Drime Cloud "
                f"(workspace: {workspace_id_config})...[/blue]"
            )
            client = DrimeClient(api_key=api_key)

            provider = DrimeDAVProvider(
                client=client,
                workspace_id=workspace_id_config,
                readonly=readonly,
                cache_ttl=cache_ttl,
                max_file_size=max_file_size,
            )
            server_name = (
                f"PyWebDAV Server ({backend_config.name}: "
                f"workspace {workspace_id_config})"
            )

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
                    "[red]Error: Drime backend requires pydrime to be "
                    "installed.[/red]\n"
                    "Install it with: pip install 'pywebdavserver[drime]'"
                )
                sys.exit(1)

            # Get Drime credentials from environment
            api_key = os.environ.get("DRIME_API_KEY")

            if not api_key:
                console.print(
                    "[red]Error: Drime backend requires DRIME_API_KEY "
                    "environment variable.[/red]\n"
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


@cli.command()
def config() -> None:
    """Enter an interactive configuration session.

    Allows you to manage backend configurations interactively.
    """
    config_manager = get_config_manager()

    console.print("\n[bold cyan]PyWebDAV Server Configuration Manager[/bold cyan]\n")

    while True:
        console.print("[bold]Available commands:[/bold]")
        console.print("  1. List backends")
        console.print("  2. Add backend")
        console.print("  3. Show backend")
        console.print("  4. Remove backend")
        console.print("  5. Exit")

        choice = click.prompt("\nEnter choice", type=int, default=5)

        if choice == 1:
            # List backends
            backends = config_manager.list_backends()
            if not backends:
                console.print("\n[yellow]No backends configured[/yellow]\n")
            else:
                console.print("\n[bold]Configured backends:[/bold]")
                for name in backends:
                    backend = config_manager.get_backend(name)
                    if backend:
                        console.print(f"  • {name} ({backend.backend_type})")
                console.print()

        elif choice == 2:
            # Add backend
            console.print("\n[bold]Add new backend[/bold]")
            name = click.prompt("Backend name")
            backend_type = click.prompt(
                "Backend type", type=click.Choice(["local", "drime"])
            )

            config_data: dict[str, Any] = {}

            if backend_type == "local":
                path = click.prompt("Root directory path", default=DEFAULT_PATH)
                readonly = click.confirm("Read-only mode?", default=False)
                config_data["path"] = path
                config_data["readonly"] = readonly

            elif backend_type == "drime":
                console.print("\nYou'll need a Drime API key. Get one from:")
                console.print("  https://app.drime.cloud/settings/api-keys")
                console.print()
                api_key = click.prompt("Drime API key", hide_input=True)
                workspace_id = click.prompt(
                    "Workspace ID (0 for personal)", type=int, default=0
                )
                readonly = click.confirm("Read-only mode?", default=False)
                cache_ttl = click.prompt(
                    "Cache TTL (seconds)", type=float, default=DEFAULT_CACHE_TTL
                )
                max_file_size = click.prompt(
                    "Max file size (MB)",
                    type=int,
                    default=DEFAULT_MAX_FILE_SIZE // (1024 * 1024),
                )
                config_data["api_key"] = api_key
                config_data["workspace_id"] = workspace_id
                config_data["readonly"] = readonly
                config_data["cache_ttl"] = cache_ttl
                config_data["max_file_size"] = max_file_size * 1024 * 1024

            config_manager.add_backend(
                name, backend_type, config_data, obscure_passwords=True
            )
            console.print(f"\n[green]✓[/green] Backend '{name}' added successfully\n")

        elif choice == 3:
            # Show backend
            name = click.prompt("\nBackend name")
            backend = config_manager.get_backend(name)

            if not backend:
                console.print(f"\n[red]Error:[/red] Backend '{name}' not found\n")
            else:
                console.print(f"\n[bold]Backend: {name}[/bold]")
                console.print(f"Type: {backend.backend_type}")
                console.print("\nConfiguration:")
                config_data = backend.get_all()
                for key, value in config_data.items():
                    # Hide sensitive values
                    if key in ("api_key", "password"):
                        console.print(f"  {key}: [dim]<hidden>[/dim]")
                    else:
                        console.print(f"  {key}: {value}")
                console.print()

        elif choice == 4:
            # Remove backend
            name = click.prompt("\nBackend name")
            if config_manager.has_backend(name):
                if click.confirm(f"Remove backend '{name}'?"):
                    config_manager.remove_backend(name)
                    console.print(f"\n[green]✓[/green] Backend '{name}' removed\n")
            else:
                console.print(f"\n[red]Error:[/red] Backend '{name}' not found\n")

        elif choice == 5:
            console.print("\nExiting configuration manager.\n")
            break


@cli.command(name="obscure")
@click.argument("password", required=False)
def obscure_cmd(password: str | None) -> None:
    """Obscure a password for use in the pywebdavserver config file.

    If PASSWORD is not provided, will prompt for it interactively.
    """
    # Import inside function to avoid issues
    import pywebdavserver.obscure as obscure_module

    if not obscure_module.HAS_CRYPTOGRAPHY:
        console.print(
            "[red]Error: Password obscuring requires the 'cryptography' library.[/red]"
        )
        console.print("Install it with: [cyan]pip install cryptography[/cyan]")
        sys.exit(1)

    if password is None:
        password = click.prompt("Enter password to obscure", hide_input=True)

    if not password:
        console.print("[red]Error: Password cannot be empty[/red]")
        sys.exit(1)

    obscured = obscure_module.obscure(password)
    console.print(f"\n[green]Obscured password:[/green] {obscured}")
    console.print("\n[yellow]Note:[/yellow] This can be used in the config file.")
    console.print(
        "The password will be automatically revealed when the config is loaded."
    )


# Add 'server' as an alias for 'serve' for compatibility
@cli.command(name="server")
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
@click.option(
    "--backend-config",
    default=None,
    help="backend configuration name (from config file)",
)
def server(
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
    backend_config: str | None,
) -> None:
    """Start the WebDAV server (alias for 'serve')."""
    # Just call serve with the same parameters
    ctx = click.get_current_context()
    ctx.invoke(
        serve,
        backend=backend,
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
        no_auth=no_auth,
        backend_config=backend_config,
    )


# For backwards compatibility with existing entry point
def main() -> None:
    """Entry point for backwards compatibility."""
    cli()


if __name__ == "__main__":
    main()
