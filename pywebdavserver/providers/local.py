"""Local filesystem WebDAV provider.

This provider uses the local filesystem as the storage backend.
It's built on top of WsgiDAV's FilesystemProvider for standard WebDAV compliance.
"""

from __future__ import annotations

import logging
from pathlib import Path

from wsgidav.fs_dav_provider import FilesystemProvider  # type: ignore[import-untyped]

from ..provider import StorageProvider

logger = logging.getLogger(__name__)


class LocalStorageProvider(FilesystemProvider, StorageProvider):
    """WebDAV provider that uses local filesystem storage.

    This provider wraps WsgiDAV's FilesystemProvider to provide standard
    filesystem-based WebDAV access. It supports:
    - Reading and writing files
    - Creating and deleting folders
    - Moving and copying resources
    - File locking
    - WebDAV properties

    Args:
        root_path: Root directory path for WebDAV storage
        readonly: If True, only allow read operations (default: False)
    """

    def __init__(self, root_path: str, readonly: bool = False) -> None:
        """Initialize the local filesystem provider.

        Args:
            root_path: Root directory path for WebDAV storage
            readonly: If True, only allow read operations
        """
        # Ensure the root directory exists
        root = Path(root_path)
        root.mkdir(parents=True, exist_ok=True)

        # Initialize FilesystemProvider with the root path
        super().__init__(str(root.absolute()), readonly=readonly)

        self._root_path = root.absolute()
        self._readonly = readonly

        logger.info(f"Initialized LocalStorageProvider at {self._root_path}")

    def get_dav_provider(self) -> FilesystemProvider:
        """Return the underlying WsgiDAV DAVProvider instance.

        Returns:
            Self, as this class is already a DAVProvider
        """
        return self

    def is_readonly(self) -> bool:
        """Check if the provider is in read-only mode.

        Returns:
            True if read-only mode is enabled
        """
        return self._readonly

    @property
    def root_path(self) -> Path:
        """Get the root directory path.

        Returns:
            Path object for the root directory
        """
        return self._root_path
