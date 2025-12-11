"""Storage provider implementations."""

from typing import Any


def __getattr__(name: str) -> Any:
    """Lazy import to avoid loading heavy dependencies."""
    if name == "LocalStorageProvider":
        from .local import LocalStorageProvider

        return LocalStorageProvider
    elif name == "DrimeStorageProvider":
        from .drime import DrimeStorageProvider

        return DrimeStorageProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "LocalStorageProvider",
    "DrimeStorageProvider",
]
