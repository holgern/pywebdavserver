"""Backend configuration management using vaultconfig.

This module provides a thin adapter layer over vaultconfig for managing
pywebdavserver backend configurations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from vaultconfig import ConfigManager, obscure

# Backend types specific to pywebdavserver
BackendType = Literal["local", "drime"]

# Configuration paths
CONFIG_DIR = Path.home() / ".config" / "pywebdavserver"
BACKENDS_FILE = CONFIG_DIR / "backends.toml"


class BackendConfig:
    """Adapter for vaultconfig ConfigEntry to maintain backward compatibility."""

    def __init__(self, name: str, backend_type: BackendType, config: dict[str, Any]):
        """Initialize backend config.

        Args:
            name: Backend name
            backend_type: Backend type
            config: Configuration dict
        """
        self.name = name
        self.backend_type = backend_type
        self._config = config

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.

        Args:
            key: Configuration key
            default: Default value

        Returns:
            Configuration value (with passwords revealed if obscured)
        """
        value = self._config.get(key, default)

        # Reveal obscured passwords
        if isinstance(value, str) and key in ("password", "api_key", "drime_password"):
            try:
                return obscure.reveal(value)
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
                    result[key] = obscure.reveal(value)
                except ValueError:
                    result[key] = value
            else:
                result[key] = value
        return result


class PyWebDAVConfigManager:
    """Adapter for vaultconfig ConfigManager for pywebdavserver backends."""

    def __init__(self, config_file: Path = BACKENDS_FILE):
        """Initialize config manager.

        Args:
            config_file: Path to config file (for compatibility)
        """
        self.config_file = config_file
        self._config_dir = config_file.parent

        # Use vaultconfig ConfigManager
        self._manager = ConfigManager(
            config_dir=self._config_dir, format="toml", password=None
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

        return BackendConfig(name, backend_type, data)

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

        # Manually obscure passwords since we don't use schema here
        if obscure_passwords:
            full_config = full_config.copy()
            for key in ("password", "api_key", "drime_password"):
                if key in full_config and isinstance(full_config[key], str):
                    if not obscure.is_obscured(full_config[key]):
                        full_config[key] = obscure.obscure(full_config[key])

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
