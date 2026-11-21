"""Auth API endpoints (`auth.*`) — out of scope, require authentication."""

from __future__ import annotations

from typing import Any

from fmscrape.errors import NotSupportedError


class AuthAPI:
    """All `auth.*` methods raise NotSupportedError."""

    def get_token(self, *args: Any, **kwargs: Any) -> Any:
        raise NotSupportedError("auth.get_token requires Last.fm API authentication and is out of scope.")

    def get_session(self, *args: Any, **kwargs: Any) -> Any:
        raise NotSupportedError("auth.get_session requires Last.fm API authentication and is out of scope.")

    def get_mobile_session(self, *args: Any, **kwargs: Any) -> Any:
        raise NotSupportedError("auth.get_mobile_session requires Last.fm API authentication and is out of scope.")

