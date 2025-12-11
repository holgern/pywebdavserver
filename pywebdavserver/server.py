"""WebDAV server runner using WsgiDAV and Cheroot."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from wsgidav.dav_provider import DAVProvider  # type: ignore[import-untyped]

    from .provider import StorageProvider

logger = logging.getLogger(__name__)


class ContentTypeFixMiddleware:
    """Middleware to fix WsgiDAV bug with Content-Type header in LOCK responses.

    WsgiDAV 4.3.3 has a bug where LOCK responses have Content-Type: "application"
    instead of "application/xml". This causes litmus and other WebDAV clients
    to fail parsing the response.

    See: https://github.com/mar10/wsgidav/issues/XXX (to be reported)
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    def __call__(self, environ: dict, start_response: Any) -> Any:
        request_method = environ.get("REQUEST_METHOD", "")

        def fixed_start_response(
            status: str, headers: list[tuple[str, str]], exc_info: Any = None
        ) -> Any:
            # Fix Content-Type for LOCK responses
            if request_method == "LOCK":
                fixed_headers = []
                for name, value in headers:
                    if (
                        name.lower() == "content-type"
                        and value == "application; charset=utf-8"
                    ):
                        # Fix the broken Content-Type
                        fixed_headers.append(
                            ("Content-Type", "application/xml; charset=utf-8")
                        )
                    else:
                        fixed_headers.append((name, value))
                return start_response(status, fixed_headers, exc_info)
            return start_response(status, headers, exc_info)

        return self.app(environ, fixed_start_response)


def create_webdav_app(
    provider: StorageProvider | DAVProvider,
    username: str | None = None,
    password: str | None = None,
    verbose: int = 1,
    server_name: str = "PyWebDAV Server",
) -> Any:
    """Create a WsgiDAV application with the given storage provider.

    Args:
        provider: Storage provider instance (must implement DAVProvider interface)
        username: WebDAV username for authentication (None for anonymous)
        password: WebDAV password for authentication
        verbose: WsgiDAV verbosity level (0-5)
        server_name: Display name for the server

    Returns:
        WsgiDAVApp instance wrapped with ContentTypeFixMiddleware
    """
    from wsgidav.wsgidav_app import WsgiDAVApp  # type: ignore[import-untyped]

    # Get the underlying DAVProvider if the provider is a StorageProvider wrapper
    if hasattr(provider, "get_dav_provider"):
        dav_provider = provider.get_dav_provider()
    else:
        dav_provider = provider

    # Build configuration
    config: dict[str, Any] = {
        "provider_mapping": {"/": dav_provider},
        "verbose": verbose,
        "logging": {
            "enable": verbose > 0,
            "enable_loggers": [],
        },
        # Enable directory browser for web access
        "dir_browser": {
            "enable": True,
            "response_trailer": (
                f"<p>{server_name} | "
                f"{'Read-only' if dav_provider.is_readonly() else 'Read-write'}</p>"
            ),
        },
        # Lock storage (required for write operations and file locking)
        "lock_storage": True,
        # Property manager for WebDAV properties
        "property_manager": True,
    }

    # Configure pywebdavserver logging based on verbosity
    if verbose >= 5:
        logging.getLogger("pywebdavserver").setLevel(logging.DEBUG)
    elif verbose >= 3:
        logging.getLogger("pywebdavserver").setLevel(logging.INFO)
    elif verbose >= 1:
        logging.getLogger("pywebdavserver").setLevel(logging.WARNING)

    # Configure authentication
    if username and password:
        config["http_authenticator"] = {
            "domain_controller": None,  # Use SimpleDomainController
            "accept_basic": True,
            "accept_digest": True,
            "default_to_digest": True,
        }
        config["simple_dc"] = {
            "user_mapping": {
                "*": {
                    username: {
                        "password": password,
                    }
                }
            }
        }
    else:
        # Anonymous access
        config["http_authenticator"] = {
            "domain_controller": None,
            "accept_basic": False,
            "accept_digest": False,
        }
        config["simple_dc"] = {
            "user_mapping": {
                "*": True  # Allow anonymous access
            }
        }

    app = WsgiDAVApp(config)

    # Wrap with middleware to fix WsgiDAV Content-Type bug in LOCK responses
    return ContentTypeFixMiddleware(app)


def run_webdav_server(
    provider: StorageProvider | DAVProvider,
    host: str = "127.0.0.1",
    port: int = 8080,
    username: str | None = None,
    password: str | None = None,
    verbose: int = 1,
    ssl_cert: str | None = None,
    ssl_key: str | None = None,
    server_name: str = "PyWebDAV Server",
) -> None:
    """Run the WebDAV server.

    Args:
        provider: Storage provider instance
        host: Host address to bind to
        port: Port number to listen on
        username: WebDAV username for authentication (None for anonymous)
        password: WebDAV password for authentication
        verbose: WsgiDAV verbosity level (0-5)
        ssl_cert: Path to SSL certificate file (for HTTPS)
        ssl_key: Path to SSL private key file (for HTTPS)
        server_name: Display name for the server
    """
    from cheroot import wsgi

    # Create the WSGI application
    app = create_webdav_app(
        provider=provider,
        username=username,
        password=password,
        verbose=verbose,
        server_name=server_name,
    )

    # Configure the server
    server_args: dict[str, Any] = {
        "bind_addr": (host, port),
        "wsgi_app": app,
    }

    # Configure SSL if certificates provided
    if ssl_cert and ssl_key:
        from cheroot.ssl.builtin import BuiltinSSLAdapter

        server_args["ssl_adapter"] = BuiltinSSLAdapter(ssl_cert, ssl_key)

    # Create and start the server
    server = wsgi.Server(**server_args)

    # Set server timeouts
    server.timeout = 300  # 5 minutes
    server.shutdown_timeout = 5

    protocol = "https" if (ssl_cert and ssl_key) else "http"
    logger.info(f"Starting {server_name} at {protocol}://{host}:{port}/")

    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    finally:
        server.stop()
        logger.info("WebDAV server stopped.")
