"""Custom exceptions for fmscrape."""

from __future__ import annotations


class FmScrapeError(Exception):
    """Base exception for all fmscrape errors."""


class NotFoundError(FmScrapeError):
    """Raised when the requested Last.fm resource does not exist (HTTP 404)."""


class RateLimitError(FmScrapeError):
    """Raised when Last.fm rate-limits requests (HTTP 429 or 600) after retries."""


class NetworkError(FmScrapeError):
    """Raised on network/transport failures or unexpected 5xx responses after retries."""


class ParseError(FmScrapeError):
    """Raised when expected HTML structure or selector cannot be parsed."""

    def __init__(self, message: str, *, url: str, selector: str) -> None:
        self.url = url
        self.selector = selector
        super().__init__(f"{message} (url={url!r}, selector={selector!r})")


class NotSupportedError(FmScrapeError):
    """Raised for methods requiring authentication or unavailable on public pages."""


class RobotsDisallowedError(FmScrapeError):
    """Raised when robots.txt disallows fetching the target URL."""

