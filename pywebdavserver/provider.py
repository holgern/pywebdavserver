"""Abstract base class for WebDAV storage providers.

This module provides a simple wrapper interface for creating WebDAV providers
that work with WsgiDAV. Concrete implementations should inherit from
wsgidav.dav_provider.DAVProvider and implement the required methods.
"""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wsgidav.dav_provider import DAVProvider  # type: ignore[import-untyped]


class StorageProvider(ABC):  # noqa: B024
    """Abstract base class for WebDAV storage providers.

    This is a marker class that indicates a provider implementation
    should inherit from wsgidav.dav_provider.DAVProvider and implement
    the required WebDAV operations.

    Concrete implementations should provide:
    - get_resource_inst(path, environ): Return DAV resource for path
    - is_readonly(): Check if provider is read-only

    And their resource classes should implement:
    - File operations (read, write, delete)
    - Folder operations (list, create, delete)
    - Metadata (size, modified time, ETags)
    - Copy/move operations
    - Locking support (optional)
    """

    def get_dav_provider(self) -> DAVProvider:
        """Return the underlying WsgiDAV DAVProvider instance.

        Returns:
            The DAVProvider instance that handles WebDAV protocol operations
        """
        # This should be implemented by concrete classes
        # For most cases, the concrete class itself will be the DAVProvider
        return self  # type: ignore[return-value]
