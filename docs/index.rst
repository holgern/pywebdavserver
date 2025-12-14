PyWebDAV Server Documentation
==============================

**PyWebDAV Server** is a WebDAV server with pluggable storage backends, supporting local filesystem and cloud storage.

This package provides a Python implementation of the WebDAV protocol with support for multiple storage backends, including local filesystem and Drime Cloud storage.

.. image:: https://img.shields.io/pypi/v/pywebdavserver.svg
   :target: https://pypi.org/project/pywebdavserver/
   :alt: PyPI version

.. image:: https://img.shields.io/pypi/pyversions/pywebdavserver.svg
   :target: https://pypi.org/project/pywebdavserver/
   :alt: Python versions

Features
--------

- **WebDAV Protocol Support** - Full WebDAV implementation for file access
- **Pluggable storage backends** - Local filesystem and cloud storage (Drime)
- **Authentication** - HTTP Basic authentication support
- **Read-only mode** - Prevent writes to protect data
- **TLS/SSL support** - Secure communication with HTTPS
- **Flexible configuration** - Command-line, config files, and environment variables
- **Secure password storage** - Custom cipher keys for password obscuring

Quick Start
-----------

Install pywebdavserver:

.. code-block:: bash

   pip install pywebdavserver

Start a server with local storage:

.. code-block:: bash

   pywebdavserver serve --backend local --path /tmp/webdav --no-auth

Connect with a WebDAV client:

.. code-block:: bash

   # Using curl
   curl http://localhost:8080/

   # Using cadaver
   cadaver http://localhost:8080/

   # Mount in Linux
   sudo mount -t davfs http://localhost:8080/ /mnt/webdav

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   installation
   quickstart
   configuration
   backends
   security
   cli

.. toctree::
   :maxdepth: 2
   :caption: Developer Guide

   api
   architecture
   custom_backends

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/modules
   api/server
   api/providers
   api/config

.. toctree::
   :maxdepth: 1
   :caption: Additional Information

   changelog
   contributing
   license

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
