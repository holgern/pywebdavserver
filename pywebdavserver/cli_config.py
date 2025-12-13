"""Configuration management CLI commands."""

from __future__ import annotations

import sys
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from .config import BackendType, get_config_manager
from .obscure import HAS_CRYPTOGRAPHY, obscure, reveal

console = Console()


@click.group(name="config")
def config_group() -> None:
    """Manage backend configurations.

    Store and manage multiple cloud storage backend configurations
    without cluttering the command line with flags.

    \b
    Examples:
        # Add a new Drime backend
        pywebdavserver config add drime-personal

        # List all backends
        pywebdavserver config list

        # Show details of a backend
        pywebdavserver config show drime-personal

        # Remove a backend
        pywebdavserver config remove drime-personal

        # Obscure a password for manual editing
        pywebdavserver config obscure
    """
    pass


@config_group.command(name="list")
def config_list() -> None:
    """List all configured backends."""
    manager = get_config_manager()
    backends = manager.list_backends()

    if not backends:
        console.print("[yellow]No backends configured yet.[/yellow]")
        console.print(
            "\nAdd a backend with: [cyan]pywebdavserver config add <name>[/cyan]"
        )
        return

    table = Table(title="Configured Backends")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Type", style="green")
    table.add_column("Details", style="dim")

    for name in sorted(backends):
        backend = manager.get_backend(name)
        if backend:
            # Build details string (without revealing passwords)
            details = []
            config = backend._config
            if backend.backend_type == "local":
                path = config.get("path", "")
                readonly = config.get("readonly", False)
                details.append(f"path={path}")
                if readonly:
                    details.append("readonly")
            elif backend.backend_type == "drime":
                workspace_id = config.get("workspace_id", 0)
                readonly = config.get("readonly", False)
                has_api_key = "api_key" in config
                has_email = "email" in config

                details.append(f"workspace={workspace_id}")
                if has_api_key:
                    details.append("auth=api_key")
                elif has_email:
                    details.append("auth=email/password")
                if readonly:
                    details.append("readonly")

            details_str = ", ".join(details) if details else ""
            table.add_row(name, backend.backend_type, details_str)

    console.print(table)


@config_group.command(name="show")
@click.argument("name")
@click.option("--reveal-passwords", is_flag=True, help="Show passwords in plain text")
def config_show(name: str, reveal_passwords: bool) -> None:
    """Show details of a backend configuration.

    NAME: Backend name to show
    """
    manager = get_config_manager()
    backend = manager.get_backend(name)

    if not backend:
        console.print(f"[red]Backend '{name}' not found.[/red]")
        console.print("\nAvailable backends:")
        for backend_name in manager.list_backends():
            console.print(f"  - {backend_name}")
        sys.exit(1)

    console.print(f"\n[bold]Backend: {name}[/bold]")
    console.print(f"Type: [cyan]{backend.backend_type}[/cyan]\n")

    table = Table(show_header=True)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")

    for key, value in sorted(backend._config.items()):
        # Handle sensitive fields
        if key in ("password", "api_key", "drime_password"):
            if reveal_passwords:
                try:
                    plain_value = reveal(value) if isinstance(value, str) else value
                    table.add_row(key, f"[red]{plain_value}[/red] (revealed)")
                except Exception:
                    table.add_row(key, str(value))
            else:
                table.add_row(key, "[dim]<obscured>[/dim]")
        else:
            table.add_row(key, str(value))

    console.print(table)

    if not reveal_passwords and any(
        k in backend._config for k in ("password", "api_key", "drime_password")
    ):
        console.print(
            "\n[dim]Use --reveal-passwords to show passwords in plain text[/dim]"
        )


@config_group.command(name="add")
@click.argument("name")
@click.option(
    "--type",
    "backend_type",
    type=click.Choice(["local", "drime"], case_sensitive=False),
    help="Backend type (will prompt if not specified)",
)
def config_add(name: str, backend_type: BackendType | None) -> None:
    """Add or update a backend configuration.

    NAME: Backend name (e.g., 'drime-personal', 'local-sync')
    """
    if not HAS_CRYPTOGRAPHY:
        console.print(
            "[red]Error: Password obscuring requires the 'cryptography' library.[/red]"
        )
        console.print("Install it with: [cyan]pip install cryptography[/cyan]")
        sys.exit(1)

    manager = get_config_manager()

    # Check if backend already exists
    existing = manager.get_backend(name)
    if existing:
        console.print(
            f"[yellow]Backend '{name}' already exists. This will overwrite it.[/yellow]"
        )
        if not click.confirm("Continue?", default=False):
            console.print("Cancelled.")
            return
        backend_type = backend_type or existing.backend_type  # type: ignore

    # Prompt for backend type if not specified
    if not backend_type:
        console.print("\nSelect backend type:")
        console.print("  1. local  - Local filesystem")
        console.print("  2. drime  - Drime Cloud storage")
        choice = click.prompt("Enter choice", type=click.IntRange(1, 2))
        backend_type = "local" if choice == 1 else "drime"

    config: dict[str, Any] = {}

    # Collect backend-specific configuration
    if backend_type == "local":
        console.print("\n[bold]Local Filesystem Configuration[/bold]")
        path = click.prompt("Root directory path", default="/tmp/webdav")
        readonly = click.confirm("Read-only mode?", default=False)

        config["path"] = path
        config["readonly"] = readonly

    elif backend_type == "drime":
        console.print("\n[bold]Drime Cloud Configuration[/bold]")
        console.print("\nYou'll need a Drime API key. Get one from:")
        console.print("  https://app.drime.cloud/settings/api-keys")
        console.print()

        api_key = click.prompt("API Key", hide_input=True)
        config["api_key"] = api_key

        workspace_id = click.prompt("Workspace ID (0 = personal)", type=int, default=0)
        readonly = click.confirm("Read-only mode?", default=False)
        cache_ttl = click.prompt("Cache TTL (seconds)", type=float, default=30.0)
        max_file_size = click.prompt("Max file size (MB)", type=int, default=500)

        config["workspace_id"] = workspace_id
        config["readonly"] = readonly
        config["cache_ttl"] = cache_ttl
        config["max_file_size"] = max_file_size * 1024 * 1024  # Convert to bytes

    # Save backend
    try:
        manager.add_backend(name, backend_type, config, obscure_passwords=True)
        console.print(f"\n[green]✓[/green] Backend '{name}' configured successfully!")
        console.print(f"\nConfiguration saved to: [cyan]{manager.config_file}[/cyan]")
        console.print(
            f"\nStart server with: [cyan]pywebdavserver --backend {name}[/cyan]"
        )
    except Exception as e:
        console.print(f"\n[red]Error saving backend: {e}[/red]")
        sys.exit(1)


@config_group.command(name="remove")
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def config_remove(name: str, yes: bool) -> None:
    """Remove a backend configuration.

    NAME: Backend name to remove
    """
    manager = get_config_manager()

    if not manager.has_backend(name):
        console.print(f"[red]Backend '{name}' not found.[/red]")
        sys.exit(1)

    if not yes:
        if not click.confirm(f"Remove backend '{name}'?", default=False):
            console.print("Cancelled.")
            return

    manager.remove_backend(name)
    console.print(f"[green]✓[/green] Backend '{name}' removed.")


@config_group.command(name="obscure")
@click.argument("password", required=False)
def config_obscure(password: str | None) -> None:
    """Obscure a password for use in config file.

    This is useful for manually editing the config file. The obscured
    password can be pasted directly into the config.

    \b
    PASSWORD: Password to obscure (will prompt if not provided)

    \b
    Examples:
        # Interactive (secure)
        pywebdavserver config obscure

        # From command line (less secure - visible in history)
        pywebdavserver config obscure "my_password"

        # From stdin
        echo "my_password" | pywebdavserver config obscure -
    """
    if not HAS_CRYPTOGRAPHY:
        console.print(
            "[red]Error: Password obscuring requires the 'cryptography' library.[/red]"
        )
        console.print("Install it with: [cyan]pip install cryptography[/cyan]")
        sys.exit(1)

    # Handle stdin
    if password == "-":
        password = sys.stdin.readline().rstrip("\n")

    # Prompt if not provided
    if not password:
        password = click.prompt("Enter password to obscure", hide_input=True)

    try:
        obscured = obscure(password)
        console.print(f"\nObscured password: [green]{obscured}[/green]")
        console.print("\n[dim]This can be pasted into your config file.[/dim]")
    except Exception as e:
        console.print(f"[red]Error obscuring password: {e}[/red]")
        sys.exit(1)


@config_group.command(name="reveal")
@click.argument("obscured_password", required=False)
def config_reveal(obscured_password: str | None) -> None:
    """Reveal an obscured password (for debugging).

    OBSCURED_PASSWORD: Obscured password to reveal (will prompt if not provided)
    """
    if not HAS_CRYPTOGRAPHY:
        console.print(
            "[red]Error: Password revealing requires the 'cryptography' library.[/red]"
        )
        console.print("Install it with: [cyan]pip install cryptography[/cyan]")
        sys.exit(1)

    # Handle stdin
    if obscured_password == "-":
        obscured_password = sys.stdin.readline().rstrip("\n")

    # Prompt if not provided
    if not obscured_password:
        obscured_password = click.prompt("Enter obscured password")

    try:
        revealed = reveal(obscured_password)
        console.print(f"\nRevealed password: [red]{revealed}[/red]")
        console.print(
            "\n[yellow]Warning: This password is now visible in your "
            "terminal history.[/yellow]"
        )
    except Exception as e:
        console.print(f"[red]Error revealing password: {e}[/red]")
        sys.exit(1)


@config_group.command(name="edit")
def config_edit() -> None:
    """Open the config file in your default editor.

    The config file will be created if it doesn't exist.
    Uses the $EDITOR environment variable, or falls back to common editors.
    """
    import os
    import subprocess

    manager = get_config_manager()
    config_file = manager.config_file

    # Create config directory if it doesn't exist
    config_file.parent.mkdir(parents=True, exist_ok=True)

    # Create empty config if it doesn't exist
    if not config_file.exists():
        config_file.write_text("# PyWebDAV Server Backend Configuration\n\n")

    # Find editor
    editor = os.environ.get("EDITOR")
    if not editor:
        # Try common editors
        for candidate in ["nano", "vim", "vi", "emacs"]:
            try:
                subprocess.run(["which", candidate], capture_output=True, check=True)
                editor = candidate
                break
            except subprocess.CalledProcessError:
                continue

    if not editor:
        console.print(
            "[yellow]No editor found. Set $EDITOR environment variable.[/yellow]"
        )
        console.print(f"\nConfig file location: [cyan]{config_file}[/cyan]")
        return

    # Open in editor
    try:
        subprocess.run([editor, str(config_file)])
        console.print(f"[green]✓[/green] Config file edited: {config_file}")
    except Exception as e:
        console.print(f"[red]Error opening editor: {e}[/red]")
        sys.exit(1)


@config_group.command(name="path")
def config_path() -> None:
    """Show the path to the config file."""
    manager = get_config_manager()
    console.print(f"Config file: [cyan]{manager.config_file}[/cyan]")

    if manager.config_file.exists():
        console.print("File exists: [green]Yes[/green]")
        console.print(
            f"Backends configured: [cyan]{len(manager.list_backends())}[/cyan]"
        )
    else:
        console.print(
            "File exists: [yellow]No (will be created when you add a backend)[/yellow]"
        )
