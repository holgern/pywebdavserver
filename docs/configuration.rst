Configuration
=============

PyWebDAV Server offers flexible configuration through command-line options, configuration files, and environment variables.

Backend Configuration
---------------------

PyWebDAV Server uses vaultconfig to manage backend configurations with secure password obscuring.

Configuration Location
~~~~~~~~~~~~~~~~~~~~~~

Backend configurations are stored in:

- Linux/macOS: ``~/.config/pywebdavserver/backends.toml``
- Windows: ``%APPDATA%\pywebdavserver\backends.toml``

Interactive Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

The easiest way to configure backends is using the interactive wizard:

.. code-block:: bash

   pywebdavserver config

This launches an interactive session where you can:

- Add new backends
- List existing backends
- Show backend details
- Remove backends

Managing Backends
~~~~~~~~~~~~~~~~~

**Add a backend interactively:**

.. code-block:: bash

   pywebdavserver config

Then select option 2 (Add backend) and follow the prompts:

.. code-block:: text

   Add new backend
   Backend name: my-local
   Backend type (local, drime): local
   Root directory path [/tmp/webdav]: /srv/webdav
   Read-only mode? [y/N]: n

   ✓ Backend 'my-local' added successfully

**List backends:**

.. code-block:: bash

   pywebdavserver config

Then select option 1 (List backends).

**Remove a backend:**

.. code-block:: bash

   pywebdavserver config

Then select option 4 (Remove backend) and enter the backend name.

**Show backend details:**

.. code-block:: bash

   pywebdavserver config

Then select option 3 (Show backend) and enter the backend name.

Password Obscuring
~~~~~~~~~~~~~~~~~~

PyWebDAV Server automatically obscures sensitive values (passwords, API keys) in configuration files using a custom cipher key.

**Important:** This is obfuscation, not encryption. It prevents casual viewing but is not cryptographically secure. For production security, use proper access controls and file permissions.

The obscuring uses a randomly generated cipher key unique to pywebdavserver:

.. code-block:: python

   # In pywebdavserver/config.py
   _PYWEBDAVSERVER_CIPHER_KEY = "..."

This means:

- Other applications cannot reveal pywebdavserver passwords
- Passwords are not stored in plain text
- The cipher key is embedded in the package

Manual Configuration
~~~~~~~~~~~~~~~~~~~~

You can also manually edit the TOML configuration file:

.. code-block:: toml

   [my-local]
   type = "local"
   path = "/srv/webdav"
   readonly = false

   [drime-personal]
   type = "drime"
   api_key = "qO-l2HqnGGNrZM3ga4UI50iwySHFTmVl1pe2NW0oOxKQqBZWUw4"  # Obscured
   workspace_id = 0
   readonly = false
   cache_ttl = 30.0
   max_file_size = 524288000

Server Configuration
--------------------

Command-Line Options
~~~~~~~~~~~~~~~~~~~~

The ``pywebdavserver serve`` command accepts various options:

**Storage Options:**

- ``--backend TEXT`` - Backend name or type (local/drime)
- ``--backend-config TEXT`` - Named backend from configuration
- ``--path PATH`` - Data directory for local backend

**Network Options:**

- ``--host TEXT`` - Host address (default: ``127.0.0.1``)
- ``--port INTEGER`` - Port number (default: ``8080``)
- ``--ssl-cert PATH`` - SSL certificate file
- ``--ssl-key PATH`` - SSL private key file

**Authentication:**

- ``--no-auth`` - Disable authentication
- ``--username TEXT`` - WebDAV username
- ``--password TEXT`` - WebDAV password

**Repository Options:**

- ``--readonly`` - Enable read-only mode (prevents writes)

**Drime Backend Options:**

- ``--workspace-id INTEGER`` - Workspace ID (0 = personal)
- ``--cache-ttl FLOAT`` - Cache TTL in seconds
- ``--max-file-size INTEGER`` - Maximum file size in bytes

**Debug:**

- ``-v, --verbose`` - Increase verbosity (repeat for more detail)

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

PyWebDAV Server respects several environment variables:

**Drime Backend:**

- ``DRIME_API_KEY`` - Drime API key

**Configuration:**

- ``PYWEBDAVSERVER_CONFIG_DIR`` - Override default config directory

Authentication Setup
--------------------

Basic Authentication
~~~~~~~~~~~~~~~~~~~~

PyWebDAV Server supports HTTP Basic Authentication:

.. code-block:: bash

   pywebdavserver serve \
       --backend local \
       --path /srv/webdav \
       --username admin \
       --password secret123

**Security Note:** Passwords are sent in base64 encoding (not encrypted). Always use HTTPS in production!

Anonymous Access
~~~~~~~~~~~~~~~~

For development or public access:

.. code-block:: bash

   pywebdavserver serve \
       --backend local \
       --path /srv/webdav \
       --no-auth

**Warning:** Only use ``--no-auth`` for development or when behind a secure gateway.

SSL/TLS Configuration
---------------------

Generate Self-Signed Certificate
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For testing:

.. code-block:: bash

   openssl req -x509 -newkey rsa:4096 \
       -keyout key.pem \
       -out cert.pem \
       -days 365 \
       -nodes \
       -subj "/CN=localhost"

Start Server with SSL
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pywebdavserver serve \
       --backend local \
       --path /srv/webdav \
       --ssl-cert cert.pem \
       --ssl-key key.pem \
       --username admin \
       --password secret123

Access the server:

.. code-block:: bash

   # With self-signed cert
   curl -k https://localhost:8080/ -u admin:secret123

Let's Encrypt
~~~~~~~~~~~~~

For production, use Let's Encrypt certificates:

.. code-block:: bash

   # Get certificate with certbot
   sudo certbot certonly --standalone -d webdav.example.com

   # Start server
   pywebdavserver serve \
       --backend local \
       --path /srv/webdav \
       --host 0.0.0.0 \
       --port 443 \
       --ssl-cert /etc/letsencrypt/live/webdav.example.com/fullchain.pem \
       --ssl-key /etc/letsencrypt/live/webdav.example.com/privkey.pem \
       --username admin \
       --password secret123

Read-Only Mode
--------------

In read-only mode, files can be read but not modified. This protects against:

- Accidental modification
- Unauthorized file changes
- Data corruption

Enable read-only mode:

.. code-block:: bash

   pywebdavserver serve \
       --backend local \
       --path /srv/webdav \
       --readonly

With read-only mode:

- ✅ ``GET`` (download) works
- ✅ ``PROPFIND`` (list) works
- ✅ ``HEAD`` (metadata) works
- ❌ ``PUT`` (upload) fails
- ❌ ``DELETE`` (delete) fails
- ❌ ``MKCOL`` (create directory) fails
- ❌ ``MOVE`` (rename) fails
- ❌ ``COPY`` (copy) fails

**Note:** Administrators can still modify files by accessing the storage directly.

Example Configuration Files
----------------------------

Production Setup
~~~~~~~~~~~~~~~~

**systemd service file** (``/etc/systemd/system/pywebdavserver.service``):

.. code-block:: ini

   [Unit]
   Description=PyWebDAV Server - WebDAV server with pluggable backends
   After=network.target

   [Service]
   Type=simple
   User=webdav
   Group=webdav
   ExecStart=/usr/local/bin/pywebdavserver serve \
       --backend-config production-local \
       --host 0.0.0.0 \
       --port 8080 \
       --username admin \
       --password secret123
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target

**Backend configuration** (``~/.config/pywebdavserver/backends.toml``):

.. code-block:: toml

   [production-local]
   type = "local"
   path = "/srv/webdav"
   readonly = false

   [production-drime]
   type = "drime"
   api_key = "qO-l2HqnGGNrZM3ga4UI50iwySHFTmVl1pe2NW0oOxKQqBZWUw4"
   workspace_id = 0
   readonly = false
   cache_ttl = 30.0
   max_file_size = 524288000

   [backup-readonly]
   type = "local"
   path = "/backup/webdav"
   readonly = true

Development Setup
~~~~~~~~~~~~~~~~~

For local development:

.. code-block:: bash

   #!/bin/bash
   # dev-server.sh

   pywebdavserver serve \
       --backend local \
       --path /tmp/webdav-dev \
       --no-auth \
       -vvv

WebDAV Clients
--------------

Linux
~~~~~

**davfs2:**

.. code-block:: bash

   # Install
   sudo apt-get install davfs2

   # Mount
   sudo mount -t davfs http://localhost:8080/ /mnt/webdav

   # With authentication
   sudo mount -t davfs -o username=admin,password=secret123 \
       http://localhost:8080/ /mnt/webdav

   # Add to /etc/fstab for automatic mounting
   echo "http://localhost:8080/ /mnt/webdav davfs user,noauto 0 0" | \
       sudo tee -a /etc/fstab

**cadaver:**

.. code-block:: bash

   # Install
   sudo apt-get install cadaver

   # Connect
   cadaver http://localhost:8080/

macOS
~~~~~

**Finder:**

1. Open Finder
2. Press Cmd+K (or Go → Connect to Server)
3. Enter: ``http://localhost:8080/``
4. Click Connect

**Command line:**

.. code-block:: bash

   # Mount
   mkdir ~/webdav
   mount_webdav http://localhost:8080/ ~/webdav

Windows
~~~~~~~

**Map Network Drive:**

1. Open File Explorer
2. Right-click "This PC"
3. Select "Map network drive"
4. Enter: ``http://localhost:8080/``
5. Check "Connect using different credentials" if needed

**Command line:**

.. code-block:: cmd

   net use W: http://localhost:8080/ /user:admin secret123

Next Steps
----------

- Learn about :doc:`backends` for storage options
- Read :doc:`security` for production deployment
- See :doc:`cli` for complete command reference
