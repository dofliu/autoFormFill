"""
Shared pytest fixtures and configuration.

Sets AUTH_ENABLED=False by default so all existing tests continue to work
without authentication. Tests that specifically test auth should override
this via monkeypatch or direct settings mutation.
"""

import os

# Ensure AUTH_ENABLED=False before any app module is imported.
# This allows anonymous access in test mode (dev-mode behavior).
os.environ.setdefault("AUTH_ENABLED", "False")
