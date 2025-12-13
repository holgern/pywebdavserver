"""Backend configuration management using vaultconfig.

This module provides a thin adapter layer over vaultconfig for managing
pywebdavserver backend configurations.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Any, Literal

from vaultconfig import ConfigManager, Obscurer, create_obscurer_from_hex

# Backend types specific to pywebdavserver
BackendType = Literal["local", "drime"]

# Configuration paths
CONFIG_DIR = Path.home() / ".config" / "pywebdavserver"
BACKENDS_FILE = CONFIG_DIR / "backends.toml"
CIPHER_KEY_FILE = CONFIG_DIR / ".cipher_key"

# Environment variables for custom cipher keys
ENV_CIPHER_KEY = "PYWEBDAVSERVER_CIPHER_KEY"
ENV_CIPHER_KEY_FILE = "PYWEBDAVSERVER_CIPHER_KEY_FILE"

# Hardcoded custom cipher key for pywebdavserver
# (generated using secrets.token_bytes(32))
# This provides application-specific password obscuring (NOT encryption).
# This key prevents casual viewing of passwords in config files but does not
# provide real security. Anyone with this key can reveal obscured passwords.
# For real encryption, use proper encryption mechanisms.
PYWEBDAVSERVER_CIPHER_KEY = bytes.fromhex(
    "9a6458e793a0bedbe5b78cd51e3aa7aef378d66628892a4dec618b57b8aab457"
)


def generate_cipher_key() -> bytes:
    """Generate a cryptographically secure random 32-byte cipher key.

    Returns:
        32-byte cipher key
    """
    return secrets.token_bytes(32)


def get_obscurer() -> Obscurer:
    """Get obscurer instance with custom cipher key.

    Priority:
    1. ENV_CIPHER_KEY_FILE environment variable (path to key file)
    2. ENV_CIPHER_KEY environment variable (hex key)
    3. Hardcoded PYWEBDAVSERVER_CIPHER_KEY (default)

    Returns:
        Obscurer instance with custom cipher key
    """
    # Try environment variable pointing to key file
    key_file_path = os.environ.get(ENV_CIPHER_KEY_FILE)
    if key_file_path:
        key_path = Path(key_file_path).expanduser()
        if key_path.exists():
            hex_key = key_path.read_text().strip()
            return create_obscurer_from_hex(hex_key)

    # Try environment variable with hex key directly
    hex_key = os.environ.get(ENV_CIPHER_KEY)
    if hex_key:
        return create_obscurer_from_hex(hex_key)

    # Use hardcoded cipher key (most secure - generated from secrets.token_bytes(32))
    return Obscurer(cipher_key=PYWEBDAVSERVER_CIPHER_KEY)


class BackendConfig:
    """Adapter for vaultconfig ConfigEntry to maintain backward compatibility."""

    def __init__(
        self,
        name: str,
        backend_type: BackendType,
        config: dict[str, Any],
        obscurer: Obscurer | None = None,
    ):
        """Initialize backend config.

        Args:
            name: Backend name
            backend_type: Backend type
            config: Configuration dict
            obscurer: Custom obscurer for password reveal (optional)
        """
        self.name = name
        self.backend_type = backend_type
        self._config = config
        self._obscurer = obscurer or get_obscurer()

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.

        Args:
            key: Configuration key
            default: Default value

        Returns:
            Configuration value (with passwords revealed if obscured)
        """
        value = self._config.get(key, default)

        # Reveal obscured passwords using custom obscurer
        if isinstance(value, str) and key in ("password", "api_key", "drime_password"):
            try:
                return self._obscurer.reveal(value)
            except ValueError:
                return value

        return value

    def get_all(self) -> dict[str, Any]:
        """Get all config values with passwords revealed.

        Returns:
            Dictionary of all configuration values
        """
        result = {}
        for key, value in self._config.items():
            if isinstance(value, str) and key in (
                "password",
                "api_key",
                "drime_password",
            ):
                try:
                    result[key] = self._obscurer.reveal(value)
                except ValueError:
                    result[key] = value
            else:
                result[key] = value
        return result


class PyWebDAVConfigManager:
    """Adapter for vaultconfig ConfigManager for pywebdavserver backends."""

    def __init__(
        self, config_file: Path = BACKENDS_FILE, obscurer: Obscurer | None = None
    ):
        """Initialize config manager.

        Args:
            config_file: Path to config file (for compatibility)
            obscurer: Custom obscurer for password encryption (optional)
        """
        self.config_file = config_file
        self._config_dir = config_file.parent

        # Get custom obscurer (will use env vars or generate new key)
        self._obscurer = obscurer or get_obscurer()

        # Use vaultconfig ConfigManager with custom obscurer
        self._manager = ConfigManager(
            config_dir=self._config_dir,
            format="toml",
            password=None,
            obscurer=self._obscurer,
        )

    def list_backends(self) -> list[str]:
        """List all backend names.

        Returns:
            List of backend names
        """
        return self._manager.list_configs()

    def get_backend(self, name: str) -> BackendConfig | None:
        """Get backend configuration.

        Args:
            name: Backend name

        Returns:
            BackendConfig or None if not found
        """
        config_entry = self._manager.get_config(name)
        if not config_entry:
            return None

        # Extract backend type and config
        data = config_entry.get_all(reveal_secrets=False)
        backend_type = data.pop("type", "local")

        return BackendConfig(name, backend_type, data, self._obscurer)

    def has_backend(self, name: str) -> bool:
        """Check if backend exists.

        Args:
            name: Backend name

        Returns:
            True if backend exists
        """
        return self._manager.has_config(name)

    def add_backend(
        self,
        name: str,
        backend_type: BackendType,
        config: dict[str, Any],
        obscure_passwords: bool = True,
    ) -> None:
        """Add or update backend.

        Args:
            name: Backend name
            backend_type: Backend type
            config: Configuration dict
            obscure_passwords: Whether to obscure passwords
        """
        # Add type to config
        full_config = {"type": backend_type, **config}

        # Manually obscure passwords using custom obscurer
        if obscure_passwords:
            full_config = full_config.copy()
            for key in ("password", "api_key", "drime_password"):
                if key in full_config and isinstance(full_config[key], str):
                    if not self._obscurer.is_obscured(full_config[key]):
                        full_config[key] = self._obscurer.obscure(full_config[key])

        self._manager.add_config(name, full_config, obscure_passwords=False)

    def remove_backend(self, name: str) -> bool:
        """Remove backend.

        Args:
            name: Backend name

        Returns:
            True if removed
        """
        return self._manager.remove_config(name)

    def get_backend_names_by_type(self, backend_type: BackendType) -> list[str]:
        """Get backend names by type.

        Args:
            backend_type: Backend type to filter

        Returns:
            List of backend names
        """
        result = []
        for name in self.list_backends():
            backend = self.get_backend(name)
            if backend and backend.backend_type == backend_type:
                result.append(name)
        return result


# Global config manager instance
_config_manager: PyWebDAVConfigManager | None = None


def get_config_manager() -> PyWebDAVConfigManager:
    """Get global config manager instance.

    Returns:
        PyWebDAVConfigManager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = PyWebDAVConfigManager()
    return _config_manager
