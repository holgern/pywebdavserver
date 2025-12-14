Command Line Interface
======================

PyWebDAV Server provides a command-line interface for managing the WebDAV server and backend configurations.

Main Commands
-------------

pywebdavserver
~~~~~~~~~~~~~~

The main entry point provides access to subcommands:

.. code-block:: bash

   pywebdavserver [OPTIONS] COMMAND [ARGS]...

**Options:**

- ``--version`` - Show version and exit
- ``--help`` - Show help message

**Commands:**

- ``serve`` - Start the WebDAV server
- ``server`` - Alias for serve
- ``config`` - Manage backend configurations
- ``obscure`` - Obscure passwords

serve Command
-------------

Start the WebDAV server.

Synopsis
~~~~~~~~

.. code-block:: bash

   pywebdavserver serve [OPTIONS]

Options
~~~~~~~

**Storage Options:**

``--backend TEXT``
  Backend name from config or backend type (local/drime).

  Default: ``local``

``--backend-config TEXT``
  Use a named backend from configuration file.

  Example: ``--backend-config drime-personal``

``--path PATH``
  Root directory path for local backend.

  Default: ``/tmp/webdav``

**Network Options:**

``--host TEXT``
  Host address to bind to.

  Default: ``127.0.0.1``

  Examples:

  - ``0.0.0.0`` - All interfaces
  - ``192.168.1.100`` - Specific IP
  - ``localhost`` - Localhost only

``--port INTEGER``
  Port number to listen on.

  Default: ``8080``

``--ssl-cert PATH``
  Path to SSL certificate file (for HTTPS).

  Required for HTTPS along with ``--ssl-key``.

``--ssl-key PATH``
  Path to SSL private key file (for HTTPS).

  Required for HTTPS along with ``--ssl-cert``.

**Authentication Options:**

``--no-auth``
  Disable authentication (allow anonymous access).

  **Use only for development/testing.**

``--username TEXT``
  WebDAV username for authentication.

  If omitted, anonymous access is allowed.

``--password TEXT``
  WebDAV password for authentication.

  Required when ``--username`` is specified.

**Repository Options:**

``--readonly``
  Enable read-only mode (no writes allowed).

  Prevents all write operations including uploads, deletes, and modifications.

**Drime Backend Options:**

``--workspace-id INTEGER``
  Workspace ID for Drime backend.

  - ``0`` = personal workspace (default)
  - Other values for team workspaces

``--cache-ttl FLOAT``
  Cache TTL in seconds for Drime backend.

  Default: ``30.0``

``--max-file-size INTEGER``
  Maximum file size in bytes.

  Default: ``524288000`` (500 MB)

**Debug Options:**

``-v, --verbose``
  Increase verbosity (can be repeated: -v, -vv, -vvv, etc.).

  - No flag: Warnings only
  - ``-v``: Info messages
  - ``-vvv``: Debug messages

Examples
~~~~~~~~

**Basic local server:**

.. code-block:: bash

   pywebdavserver serve --backend local --path /srv/webdav --no-auth

**Production server with authentication:**

.. code-block:: bash

   pywebdavserver serve \
       --backend local \
       --path /srv/webdav \
       --host 0.0.0.0 \
       --port 8080 \
       --username admin \
       --password secret123

**Server with HTTPS:**

.. code-block:: bash

   pywebdavserver serve \
       --backend local \
       --path /srv/webdav \
       --host 0.0.0.0 \
       --port 443 \
       --ssl-cert /etc/ssl/certs/webdav.crt \
       --ssl-key /etc/ssl/private/webdav.key \
       --username admin \
       --password secret123

**Read-only server:**

.. code-block:: bash

   pywebdavserver serve \
       --backend local \
       --path /srv/webdav \
       --readonly \
       --no-auth

**Drime cloud backend:**

.. code-block:: bash

   pywebdavserver serve \
       --backend-config drime-personal \
       --no-auth

config Command
--------------

Manage backend configurations interactively.

Synopsis
~~~~~~~~

.. code-block:: bash

   pywebdavserver config

Interactive Mode
~~~~~~~~~~~~~~~~

Run the command for interactive configuration:

.. code-block:: bash

   pywebdavserver config

This launches an interactive wizard with the following options:

1. **List backends** - Show all configured backends
2. **Add backend** - Create a new backend configuration
3. **Show backend** - Display detailed backend information
4. **Remove backend** - Delete a backend configuration
5. **Exit** - Leave the configuration manager

Adding a Backend
~~~~~~~~~~~~~~~~

When adding a backend, you'll be prompted for:

**Local Backend:**

- Backend name (identifier)
- Root directory path
- Read-only mode (yes/no)

**Drime Backend:**

- Backend name (identifier)
- Drime API key (hidden input)
- Workspace ID (0 for personal)
- Read-only mode (yes/no)
- Cache TTL (seconds)
- Max file size (MB)

Examples
~~~~~~~~

**Interactive session:**

.. code-block:: text

   $ pywebdavserver config

   PyWebDAV Server Configuration Manager

   Available commands:
     1. List backends
     2. Add backend
     3. Show backend
     4. Remove backend
     5. Exit

   Enter choice [5]: 2

   Add new backend
   Backend name: my-local-storage
   Backend type (local, drime): local
   Root directory path [/tmp/webdav]: /srv/webdav
   Read-only mode? [y/N]: n

   ✓ Backend 'my-local-storage' added successfully

**List configured backends:**

.. code-block:: text

   Enter choice [5]: 1

   Configured backends:
     • my-local-storage (local)
     • drime-personal (drime)

**Show backend details:**

.. code-block:: text

   Enter choice [5]: 3

   Backend name: my-local-storage

   Backend: my-local-storage
   Type: local

   Configuration:
     path: /srv/webdav
     readonly: False

obscure Command
---------------

Obscure a password for use in configuration files.

Synopsis
~~~~~~~~

.. code-block:: bash

   pywebdavserver obscure [PASSWORD]

Description
~~~~~~~~~~~

Obscures a password using PyWebDAV Server's custom cipher key. The obscured password can be used in configuration files.

**Note:** This is obfuscation, not encryption. It prevents casual viewing but is not cryptographically secure.

Interactive Mode
~~~~~~~~~~~~~~~~

Without arguments, prompts for password:

.. code-block:: bash

   pywebdavserver obscure
   Enter password to obscure: ********

   Obscured password: qO-l2HqnGGNrZM3ga4UI50iwySHFTmVl1pe2NW0oOxKQqBZWUw4

   Note: This can be used in the config file.
   The password will be automatically revealed when the config is loaded.

With Argument
~~~~~~~~~~~~~

Pass password as argument (less secure - visible in shell history):

.. code-block:: bash

   pywebdavserver obscure "my-password"

Environment Variables
---------------------

PyWebDAV Server respects the following environment variables:

Drime Backend
~~~~~~~~~~~~~

``DRIME_API_KEY``
  Drime API authentication key.

Configuration
~~~~~~~~~~~~~

``PYWEBDAVSERVER_CONFIG_DIR``
  Override default configuration directory.

  Default: ``~/.config/pywebdavserver``

Exit Codes
----------

PyWebDAV Server uses standard exit codes:

- ``0`` - Success
- ``1`` - General error
- ``2`` - Command-line usage error
- ``130`` - Interrupted by Ctrl+C

Integration Examples
--------------------

systemd Service
~~~~~~~~~~~~~~~

Create a systemd service file (``/etc/systemd/system/pywebdavserver.service``):

.. code-block:: ini

   [Unit]
   Description=PyWebDAV Server - WebDAV server with pluggable backends
   After=network.target

   [Service]
   Type=simple
   User=webdav
   Group=webdav
   ExecStart=/usr/local/bin/pywebdavserver serve \
       --backend local \
       --path /srv/webdav \
       --host 0.0.0.0 \
       --port 8080 \
       --username admin \
       --password secret123
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target

Enable and start:

.. code-block:: bash

   sudo systemctl enable pywebdavserver
   sudo systemctl start pywebdavserver
   sudo systemctl status pywebdavserver

Docker
~~~~~~

Example Dockerfile:

.. code-block:: dockerfile

   FROM python:3.11-slim

   RUN pip install pywebdavserver

   RUN useradd -r -s /bin/false webdav
   USER webdav

   EXPOSE 8080

   ENTRYPOINT ["pywebdavserver", "serve"]
   CMD ["--backend", "local", "--path", "/data", "--host", "0.0.0.0", "--no-auth"]

Run container:

.. code-block:: bash

   docker build -t pywebdavserver .

   docker run -d \
       -p 8080:8080 \
       -v /srv/webdav:/data \
       --name pywebdavserver \
       pywebdavserver

Docker Compose
~~~~~~~~~~~~~~

Example ``docker-compose.yml``:

.. code-block:: yaml

   version: '3.8'

   services:
     pywebdavserver:
       image: pywebdavserver:latest
       ports:
         - "8080:8080"
       volumes:
         - ./data:/data
       environment:
         - WEBDAV_USERNAME=admin
         - WEBDAV_PASSWORD=secret123
       command:
         - --backend
         - local
         - --path
         - /data
         - --host
         - 0.0.0.0
         - --username
         - admin
         - --password
         - secret123
       restart: unless-stopped

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Server won't start:**

.. code-block:: bash

   # Check if port is in use
   sudo netstat -tulpn | grep 8080

   # Try a different port
   pywebdavserver serve --port 8081

**Authentication fails:**

.. code-block:: bash

   # Test with no auth
   pywebdavserver serve --no-auth

**SSL certificate errors:**

.. code-block:: bash

   # Verify certificate files exist
   ls -l /etc/ssl/certs/webdav.crt /etc/ssl/private/webdav.key

   # Check certificate validity
   openssl x509 -in /etc/ssl/certs/webdav.crt -text -noout

**Permission denied:**

.. code-block:: bash

   # Check data directory permissions
   ls -ld /srv/webdav

   # Fix ownership
   sudo chown -R webdav:webdav /srv/webdav

Enable Debug Mode
~~~~~~~~~~~~~~~~~

For detailed troubleshooting:

.. code-block:: bash

   pywebdavserver serve --backend local --path /srv/webdav -vvv

This outputs all debug information to stdout.

Next Steps
----------

- Review :doc:`configuration` for detailed setup
- Check :doc:`security` for production best practices
- See :doc:`backends` for storage options
