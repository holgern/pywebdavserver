# pywebdavserver

A WebDAV server with pluggable storage backends - support for local filesystem and Drime
Cloud storage.

## Features

- **Multiple Storage Backends:**

  - **Local Filesystem** (default): Standard filesystem-based WebDAV access
  - **Drime Cloud** (optional): Access Drime Cloud storage via WebDAV

- **Full WebDAV Support:**

  - Read and write files
  - Create and delete folders
  - Move and copy resources
  - File locking for collaborative editing
  - WebDAV properties
  - Directory browser

- **Flexible Authentication:**

  - Optional HTTP Basic/Digest authentication
  - Anonymous access support
  - Per-server credentials

- **Easy Configuration:**
  - **Named backend configurations** (rclone-style) - no more CLI flag overload!
  - Simple CLI with sensible defaults
  - Programmatic API for custom integrations
  - SSL/TLS support
  - Secure password obscuring (rclone-compatible)

## Installation

### Basic Installation (Local Filesystem Only)

```bash
pip install pywebdavserver
```

### With Drime Cloud Support

```bash
pip install pywebdavserver[drime]
```

### Full Installation (with config encryption)

```bash
pip install pywebdavserver[drime]
pip install cryptography  # For password obscuring
```

### Development Installation

```bash
git clone <repository>
cd pywebdavserver
pip install -e ".[dev,drime]"
```

## Quick Start

### Using Named Backend Configurations (Recommended)

The best way to use pywebdavserver is with named backend configurations - similar to how
rclone works:

```bash
# Add a backend configuration (interactive wizard)
pywebdavserver config add drime-personal

# Start server with the configured backend
pywebdavserver --backend drime-personal --no-auth

# List all configured backends
pywebdavserver config list

# Show backend details
pywebdavserver config show drime-personal

# Remove a backend
pywebdavserver config remove drime-personal
```

**Benefits:**

- No need to remember API keys or workspace IDs
- Passwords are securely obscured in config file
- Easily switch between multiple cloud accounts
- Clean CLI without flag overload
- Ready for future cloud providers (Nextcloud, S3, etc.)

### Local Filesystem Backend

Start a WebDAV server with local filesystem storage:

```bash
# Anonymous access (no authentication)
pywebdavserver --no-auth

# With authentication
pywebdavserver --username admin --password secret

# Custom path and port
pywebdavserver --path /data/webdav --port 9000 --no-auth

# Read-only mode
pywebdavserver --readonly --no-auth

# With SSL/TLS
pywebdavserver --ssl-cert cert.pem --ssl-key key.pem --no-auth

# Or configure a named backend
pywebdavserver config add local-docs
# Then start with: pywebdavserver --backend local-docs --no-auth
```

### Drime Cloud Backend

```bash
# Method 1: Using named backend (recommended)
pywebdavserver config add drime-work
pywebdavserver --backend drime-work --no-auth

# Method 2: Using environment variables (legacy)
export DRIME_API_KEY="your-api-key-here"
pywebdavserver --backend drime --workspace-id 0 --no-auth
```

## Backend Configuration

### Configuration File Location

Backend configurations are stored in TOML format at:

- Linux/macOS: `~/.config/pywebdavserver/backends.toml`
- Windows: `%USERPROFILE%\.config\pywebdavserver\backends.toml`

### Config Commands

```bash
# Interactive wizard to add a backend
pywebdavserver config add <name>

# List all backends
pywebdavserver config list

# Show backend details (with obscured passwords)
pywebdavserver config show <name>

# Show backend details (reveal passwords)
pywebdavserver config show <name> --reveal-passwords

# Remove a backend
pywebdavserver config remove <name>

# Get config file path
pywebdavserver config path

# Edit config file manually
pywebdavserver config edit

# Obscure a password for manual editing
pywebdavserver config obscure
# Or from stdin: echo "mypassword" | pywebdavserver config obscure -

# Reveal an obscured password
pywebdavserver config reveal <obscured-password>
```

### Example Configuration File

```toml
# ~/.config/pywebdavserver/backends.toml

[local-docs]
type = "local"
path = "/home/user/Documents"
readonly = false

[local-readonly]
type = "local"
path = "/mnt/shared"
readonly = true

[drime-personal]
type = "drime"
api_key = "FZq5EuI..."  # Obscured with AES-CTR encryption
workspace_id = 0
readonly = false
cache_ttl = 30.0
max_file_size = 524288000

[drime-work]
type = "drime"
api_key = "zEYAL3o..."  # Different workspace, different key
workspace_id = 42
readonly = false
cache_ttl = 60.0
max_file_size = 1073741824
```

### Password Obscuring

Passwords are automatically obscured when using `pywebdavserver config add`. The
obscuring uses AES-CTR encryption (compatible with rclone's `obscure` command).

**This is NOT secure encryption!** It's designed to prevent casual "shoulder surfing" -
anyone with access to the code can decrypt the passwords. For true security, use file
system permissions (`chmod 600 ~/.config/pywebdavserver/backends.toml`).

### Mounting the WebDAV Server

#### macOS (Finder)

1. Open Finder
2. Go → Connect to Server (⌘K)
3. Enter: `http://localhost:8080`
4. Click Connect

#### Linux

```bash
# Install davfs2
sudo apt-get install davfs2  # Debian/Ubuntu
sudo yum install davfs2      # RHEL/CentOS

# Mount
sudo mount -t davfs http://localhost:8080 /mnt/webdav
```

#### Windows

1. Right-click "This PC"
2. Select "Map network drive..."
3. Enter: `http://localhost:8080`
4. Click Finish

## CLI Reference

```
Usage: pywebdavserver [OPTIONS]

  PyWebDAV Server - WebDAV server with pluggable storage backends.

Options:
  --backend [local|drime]        Storage backend (default: local)
  --path PATH                    Root directory for local backend
                                 (default: /tmp/webdav)
  --host TEXT                    Host address (default: 127.0.0.1)
  --port INTEGER                 Port number (default: 8080)
  --username TEXT                WebDAV username
  --password TEXT                WebDAV password
  --readonly                     Enable read-only mode
  --cache-ttl FLOAT              Cache TTL for Drime backend (default: 30.0)
  --max-file-size INTEGER        Max file size in bytes (default: 524288000)
  --workspace-id INTEGER         Workspace ID for Drime (default: 0)
  --ssl-cert PATH                SSL certificate file
  --ssl-key PATH                 SSL private key file
  -v, --verbose                  Increase verbosity (can repeat)
  --no-auth                      Disable authentication
  --version                      Show version and exit
  --help                         Show this message and exit
```

## Programmatic Usage

### Local Filesystem Provider

```python
from pywebdavserver.providers.local import LocalStorageProvider
from pywebdavserver.server import run_webdav_server

# Create provider
provider = LocalStorageProvider(
    root_path="/data/webdav",
    readonly=False
)

# Run server
run_webdav_server(
    provider=provider,
    host="0.0.0.0",
    port=8080,
    username="admin",
    password="secret",
    verbose=2
)
```

### Drime Cloud Provider

```python
from pydrime.api import DrimeClient
from pywebdavserver.providers.drime import DrimeDAVProvider
from pywebdavserver.server import run_webdav_server

# Create Drime client
client = DrimeClient(email="user@example.com", password="password")

# Create provider
provider = DrimeDAVProvider(
    client=client,
    workspace_id=0,
    readonly=False,
    cache_ttl=30.0,
    max_file_size=500 * 1024 * 1024
)

# Run server
run_webdav_server(
    provider=provider,
    host="0.0.0.0",
    port=8080,
    username="admin",
    password="secret",
    verbose=2
)
```

### Custom WSGI Integration

```python
from pywebdavserver.providers.local import LocalStorageProvider
from pywebdavserver.server import create_webdav_app

provider = LocalStorageProvider("/data/webdav")
app = create_webdav_app(
    provider=provider,
    username="admin",
    password="secret",
    verbose=1
)

# Use with any WSGI server (gunicorn, uWSGI, etc.)
```

## Architecture

### Storage Provider Interface

The `StorageProvider` base class defines the interface for storage backends. Each
provider must:

1. Inherit from `wsgidav.dav_provider.DAVProvider`
2. Implement WebDAV resource operations (get, list, create, delete, move, copy)
3. Provide metadata (size, modified time, ETags)
4. Support locking (optional but recommended)

### Available Providers

#### LocalStorageProvider

- **Backend**: Local filesystem
- **Dependencies**: None (uses wsgidav's FilesystemProvider)
- **Features**: Standard filesystem WebDAV access
- **Use Case**: Simple file sharing, local development

#### DrimeDAVProvider

- **Backend**: Drime Cloud API
- **Dependencies**: `pydrime>=0.1.0`
- **Features**: Cloud storage, eventual consistency handling, caching
- **Use Case**: Cloud file access, team collaboration

## Configuration Examples

### Development Server

```bash
# Quick local testing
pywebdavserver --no-auth --verbose
```

### Production Server

```bash
# Secure production setup
pywebdavserver \
  --path /var/www/webdav \
  --host 0.0.0.0 \
  --port 443 \
  --ssl-cert /etc/ssl/certs/server.crt \
  --ssl-key /etc/ssl/private/server.key \
  --username webdav \
  --password $(cat /etc/webdav/password) \
  --readonly
```

### Drime Cloud Gateway

```bash
# Expose Drime workspace via WebDAV
export DRIME_EMAIL="admin@company.com"
export DRIME_PASSWORD="$(cat ~/.drime/password)"

pywebdavserver \
  --backend drime \
  --workspace-id 123 \
  --host 0.0.0.0 \
  --port 8080 \
  --username teamlead \
  --password teampass \
  --cache-ttl 60
```

## Troubleshooting

### Connection Refused

- Check if the server is running: `netstat -an | grep 8080`
- Verify firewall settings
- Try binding to `0.0.0.0` instead of `127.0.0.1`

### Authentication Fails

- Ensure username and password are provided together
- Check WebDAV client supports Basic/Digest auth
- Try without authentication first (`--no-auth`)

### Drime Backend Errors

- Verify `DRIME_EMAIL` and `DRIME_PASSWORD` environment variables
- Check network connectivity to Drime Cloud
- Ensure `pydrime` is installed: `pip install pywebdavserver[drime]`

### File Locking Issues

- File locking requires a writable lock storage
- Check directory permissions
- Increase cache TTL for better lock handling

## Development

### Running Tests

```bash
pip install -e ".[dev]"
pytest tests/
```

### Code Formatting

```bash
ruff check .
ruff format .
```

### Building Documentation

```bash
# This README serves as the main documentation
```

## Comparison with Other WebDAV Servers

| Feature            | pywebdavserver | Apache mod_dav | WsgiDAV CLI  |
| ------------------ | -------------- | -------------- | ------------ |
| Local Filesystem   | ✅             | ✅             | ✅           |
| Cloud Storage      | ✅ (Drime)     | ❌             | ❌           |
| Python API         | ✅             | ❌             | ⚠️ (Limited) |
| File Locking       | ✅             | ✅             | ✅           |
| Easy Setup         | ✅             | ⚠️ (Complex)   | ✅           |
| Pluggable Backends | ✅             | ❌             | ⚠️ (Limited) |

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Credits

- Built on [WsgiDAV](https://github.com/mar10/wsgidav)
- Uses [Cheroot](https://github.com/cherrypy/cheroot) WSGI server
- Drime backend powered by [pydrime](https://github.com/your-repo/pydrime)

## Support

For issues and questions:

- GitHub Issues: <repository-url>/issues
- Documentation: This README
- WsgiDAV Docs: https://wsgidav.readthedocs.io/

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
