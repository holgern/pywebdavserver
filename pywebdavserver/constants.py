"""Shared constants for WebDAV server."""

# Default server configuration
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
DEFAULT_PATH = "/tmp/webdav"
DEFAULT_CACHE_TTL = 30.0  # seconds
DEFAULT_MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB

# WebDAV-specific constants
WEBDAV_CONTENT_TYPE = "application/xml; charset=utf-8"
