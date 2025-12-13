"""Tests for the local filesystem WebDAV provider."""

# pyright: reportAttributeAccessIssue=false

from __future__ import annotations

import tempfile
from pathlib import Path


class TestLocalStorageProvider:
    """Tests for the LocalStorageProvider class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.root_path = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_creates_directory(self):
        """Test that initialization creates the root directory."""
        from pywebdavserver.providers.local import LocalStorageProvider

        new_path = self.root_path / "new_webdav"
        _ = LocalStorageProvider(str(new_path))

        assert new_path.exists()
        assert new_path.is_dir()

    def test_init_with_existing_directory(self):
        """Test initialization with existing directory."""
        from pywebdavserver.providers.local import LocalStorageProvider

        # Directory already exists from setup_method
        provider = LocalStorageProvider(str(self.root_path))

        assert provider.root_path == self.root_path

    def test_readonly_mode(self):
        """Test that readonly mode is set correctly."""
        from pywebdavserver.providers.local import LocalStorageProvider

        provider = LocalStorageProvider(str(self.root_path), readonly=True)

        assert provider.is_readonly() is True

    def test_readwrite_mode(self):
        """Test that read-write mode is default."""
        from pywebdavserver.providers.local import LocalStorageProvider

        provider = LocalStorageProvider(str(self.root_path), readonly=False)

        assert provider.is_readonly() is False

    def test_get_dav_provider(self):
        """Test that get_dav_provider returns self."""
        from pywebdavserver.providers.local import LocalStorageProvider

        provider = LocalStorageProvider(str(self.root_path))
        dav_provider = provider.get_dav_provider()

        assert dav_provider is provider

    def test_root_path_property(self):
        """Test the root_path property."""
        from pywebdavserver.providers.local import LocalStorageProvider

        provider = LocalStorageProvider(str(self.root_path))

        assert provider.root_path == self.root_path


class TestLocalProviderFileOperations:
    """Tests for file operations through LocalStorageProvider."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.root_path = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_provider_serves_existing_files(self):
        """Test that the provider can access existing files."""
        from pywebdavserver.providers.local import LocalStorageProvider

        # Create a test file
        test_file = self.root_path / "test.txt"
        test_file.write_text("Hello, World!")

        provider = LocalStorageProvider(str(self.root_path))
        environ = {"wsgidav.provider": provider}

        # Get the resource
        resource = provider.get_resource_inst("/test.txt", environ)

        assert resource is not None
        assert resource.get_display_name() == "test.txt"
        assert resource.get_content_length() == len("Hello, World!")

    def test_provider_lists_directory_contents(self):
        """Test that the provider can list directory contents."""
        from pywebdavserver.providers.local import LocalStorageProvider

        # Create test files and folders
        (self.root_path / "file1.txt").write_text("Content 1")
        (self.root_path / "file2.txt").write_text("Content 2")
        (self.root_path / "subfolder").mkdir()

        provider = LocalStorageProvider(str(self.root_path))
        environ = {"wsgidav.provider": provider}

        # Get the root collection
        collection = provider.get_resource_inst("/", environ)

        assert collection is not None
        member_names = collection.get_member_names()

        assert "file1.txt" in member_names
        assert "file2.txt" in member_names
        assert "subfolder" in member_names

    def test_provider_handles_nonexistent_resource(self):
        """Test that the provider returns None for nonexistent resources."""
        from pywebdavserver.providers.local import LocalStorageProvider

        provider = LocalStorageProvider(str(self.root_path))
        environ = {"wsgidav.provider": provider}

        resource = provider.get_resource_inst("/nonexistent.txt", environ)

        assert resource is None

    def test_provider_with_nested_paths(self):
        """Test that the provider handles nested paths correctly."""
        from pywebdavserver.providers.local import LocalStorageProvider

        # Create nested structure
        nested_dir = self.root_path / "folder1" / "folder2"
        nested_dir.mkdir(parents=True)
        test_file = nested_dir / "nested.txt"
        test_file.write_text("Nested content")

        provider = LocalStorageProvider(str(self.root_path))
        environ = {"wsgidav.provider": provider}

        # Get the nested resource
        resource = provider.get_resource_inst("/folder1/folder2/nested.txt", environ)

        assert resource is not None
        assert resource.get_display_name() == "nested.txt"


class TestLocalProviderReadonly:
    """Tests for readonly behavior of LocalStorageProvider."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.root_path = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_readonly_provider_reports_readonly(self):
        """Test that readonly provider reports is_readonly as True."""
        from pywebdavserver.providers.local import LocalStorageProvider

        provider = LocalStorageProvider(str(self.root_path), readonly=True)

        assert provider.is_readonly() is True

    def test_readwrite_provider_reports_not_readonly(self):
        """Test that read-write provider reports is_readonly as False."""
        from pywebdavserver.providers.local import LocalStorageProvider

        provider = LocalStorageProvider(str(self.root_path), readonly=False)

        assert provider.is_readonly() is False
