"""Tests for the WebDAV server module."""

# pyright: reportAttributeAccessIssue=false

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestContentTypeFixMiddleware:
    """Tests for the ContentTypeFixMiddleware class."""

    def setup_method(self):
        """Set up test fixtures."""
        pass

    def _create_middleware(self, app):
        """Create a ContentTypeFixMiddleware wrapping the given app."""
        from pywebdavserver.server import ContentTypeFixMiddleware

        return ContentTypeFixMiddleware(app)

    def test_lock_request_fixes_content_type(self):
        """Test that LOCK request Content-Type is fixed."""

        # Mock app that returns broken Content-Type
        def mock_app(environ, start_response):
            start_response("200 OK", [("Content-Type", "application; charset=utf-8")])
            return [b"<response/>"]

        middleware = self._create_middleware(mock_app)
        environ = {"REQUEST_METHOD": "LOCK"}
        response_headers = []

        def capturing_start_response(status, headers, exc_info=None):
            response_headers.extend(headers)

        list(middleware(environ, capturing_start_response))

        # Should have fixed Content-Type
        content_types = [v for k, v in response_headers if k == "Content-Type"]
        assert len(content_types) == 1
        assert content_types[0] == "application/xml; charset=utf-8"

    def test_non_lock_request_unchanged(self):
        """Test that non-LOCK requests are not modified."""

        def mock_app(environ, start_response):
            start_response("200 OK", [("Content-Type", "text/plain")])
            return [b"content"]

        middleware = self._create_middleware(mock_app)
        environ = {"REQUEST_METHOD": "GET"}
        response_headers = []

        def capturing_start_response(status, headers, exc_info=None):
            response_headers.extend(headers)

        list(middleware(environ, capturing_start_response))

        content_types = [v for k, v in response_headers if k == "Content-Type"]
        assert len(content_types) == 1
        assert content_types[0] == "text/plain"

    def test_lock_with_correct_content_type_unchanged(self):
        """Test that LOCK with correct Content-Type is not modified."""

        def mock_app(environ, start_response):
            start_response(
                "200 OK", [("Content-Type", "application/xml; charset=utf-8")]
            )
            return [b"<response/>"]

        middleware = self._create_middleware(mock_app)
        environ = {"REQUEST_METHOD": "LOCK"}
        response_headers = []

        def capturing_start_response(status, headers, exc_info=None):
            response_headers.extend(headers)

        list(middleware(environ, capturing_start_response))

        content_types = [v for k, v in response_headers if k == "Content-Type"]
        assert len(content_types) == 1
        assert content_types[0] == "application/xml; charset=utf-8"


class TestCreateWebdavApp:
    """Tests for the create_webdav_app function."""

    def test_create_app_with_local_provider(self):
        """Test creating a WebDAV app with local storage provider."""
        from pywebdavserver.providers.local import LocalStorageProvider
        from pywebdavserver.server import ContentTypeFixMiddleware, create_webdav_app

        provider = LocalStorageProvider("/tmp/test_webdav", readonly=False)
        app = create_webdav_app(provider=provider)

        # App should be wrapped with middleware
        assert isinstance(app, ContentTypeFixMiddleware)

    def test_create_app_with_auth(self):
        """Test creating a WebDAV app with authentication."""
        from pywebdavserver.providers.local import LocalStorageProvider
        from pywebdavserver.server import create_webdav_app

        provider = LocalStorageProvider("/tmp/test_webdav")
        app = create_webdav_app(
            provider=provider,
            username="testuser",
            password="testpass",
        )

        # App should be created successfully
        assert app is not None

    def test_create_app_readonly(self):
        """Test creating a readonly WebDAV app."""
        from pywebdavserver.providers.local import LocalStorageProvider
        from pywebdavserver.server import create_webdav_app

        provider = LocalStorageProvider("/tmp/test_webdav", readonly=True)
        app = create_webdav_app(provider=provider)

        # App should be created successfully
        assert app is not None

    def test_create_app_anonymous_access(self):
        """Test creating a WebDAV app with anonymous access."""
        from pywebdavserver.providers.local import LocalStorageProvider
        from pywebdavserver.server import create_webdav_app

        provider = LocalStorageProvider("/tmp/test_webdav")
        app = create_webdav_app(provider=provider, username=None, password=None)

        assert app is not None


class TestRunWebdavServer:
    """Tests for the run_webdav_server function."""

    @patch("cheroot.wsgi.Server")
    def test_run_server_basic(self, mock_wsgi_server):
        """Test running the WebDAV server."""
        from pywebdavserver.providers.local import LocalStorageProvider
        from pywebdavserver.server import run_webdav_server

        provider = LocalStorageProvider("/tmp/test_webdav")
        mock_server = MagicMock()
        mock_wsgi_server.return_value = mock_server

        # Simulate keyboard interrupt to stop the server
        mock_server.start.side_effect = KeyboardInterrupt()

        run_webdav_server(
            provider=provider,
            host="127.0.0.1",
            port=8080,
        )

        mock_wsgi_server.assert_called_once()
        mock_server.start.assert_called_once()
        mock_server.stop.assert_called_once()

    @patch("cheroot.wsgi.Server")
    def test_run_server_custom_port(self, mock_wsgi_server):
        """Test running the WebDAV server on custom port."""
        from pywebdavserver.providers.local import LocalStorageProvider
        from pywebdavserver.server import run_webdav_server

        provider = LocalStorageProvider("/tmp/test_webdav")
        mock_server = MagicMock()
        mock_wsgi_server.return_value = mock_server
        mock_server.start.side_effect = KeyboardInterrupt()

        run_webdav_server(
            provider=provider,
            host="0.0.0.0",
            port=9999,
        )

        # Verify server was created with correct bind address
        call_kwargs = mock_wsgi_server.call_args[1]
        assert call_kwargs["bind_addr"] == ("0.0.0.0", 9999)

    @patch("cheroot.ssl.builtin.BuiltinSSLAdapter")
    @patch("cheroot.wsgi.Server")
    def test_run_server_with_ssl(self, mock_wsgi_server, mock_ssl_adapter):
        """Test running the WebDAV server with SSL."""
        from pywebdavserver.providers.local import LocalStorageProvider
        from pywebdavserver.server import run_webdav_server

        provider = LocalStorageProvider("/tmp/test_webdav")
        mock_server = MagicMock()
        mock_wsgi_server.return_value = mock_server
        mock_server.start.side_effect = KeyboardInterrupt()

        run_webdav_server(
            provider=provider,
            ssl_cert="/path/to/cert.pem",
            ssl_key="/path/to/key.pem",
        )

        # Verify SSL adapter was created
        mock_ssl_adapter.assert_called_once_with(
            "/path/to/cert.pem", "/path/to/key.pem"
        )
