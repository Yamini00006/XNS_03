"""
Security helpers for the Customer Data Platform.

Member 4 owns platform-level security configuration.
Authentication itself is handled by Member 2.
"""

from __future__ import annotations

import os
from typing import Iterable


def get_allowed_hosts() -> list[str]:
    """Return allowed hosts from the environment."""
    value = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1")

    return [
        host.strip()
        for host in value.split(",")
        if host.strip()
    ]


def get_cors_allowed_origins() -> list[str]:
    """Return allowed CORS origins from the environment."""
    value = os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )

    return [
        origin.strip()
        for origin in value.split(",")
        if origin.strip()
    ]


def security_settings(debug: bool) -> dict:
    """
    Return Django security settings appropriate for the environment.

    Development keeps HTTPS-only settings disabled.
    Production enables the important security controls.
    """
    if debug:
        return {
            "SECURE_SSL_REDIRECT": False,
            "SESSION_COOKIE_SECURE": False,
            "CSRF_COOKIE_SECURE": False,
            "SECURE_HSTS_SECONDS": 0,
            "SECURE_HSTS_INCLUDE_SUBDOMAINS": False,
            "SECURE_HSTS_PRELOAD": False,
        }

    return {
        "SECURE_SSL_REDIRECT": True,
        "SESSION_COOKIE_SECURE": True,
        "CSRF_COOKIE_SECURE": True,
        "SECURE_HSTS_SECONDS": 31536000,
        "SECURE_HSTS_INCLUDE_SUBDOMAINS": True,
        "SECURE_HSTS_PRELOAD": True,
    }