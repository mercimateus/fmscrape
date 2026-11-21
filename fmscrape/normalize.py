"""Normalization helpers for numbers, UTC timestamps, URLs, and Last.fm images."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urljoin

BASE_URL = "https://www.last.fm"

_IMAGE_SIZE_RE = re.compile(
    r"^(https?://[^/]+/i/u/)([^/]+)(/[^/?#]+(?:\.[a-zA-Z0-9]+)?)$"
)

_IMAGE_SIZES: list[tuple[str, str]] = [
    ("small", "34s"),
    ("medium", "64s"),
    ("large", "174s"),
    ("extralarge", "300x300"),
]

_DATE_FORMATS = (
    "%A %d %b %Y, %I:%M%p",  # Wednesday 18 Nov 2026, 7:18pm
    "%d %b %Y, %I:%M%p",     # 18 Nov 2026, 7:18pm
    "%d %b %Y, %H:%M",       # 18 Nov 2026, 19:18
    "%d %B %Y",              # 16 April 1997
)


def absolute_url(path_or_url: str | None) -> str:
    """Resolve a Last.fm relative path to an absolute URL."""
    if not path_or_url:
        return ""
    if path_or_url.startswith(("http://", "https://")):
        return path_or_url
    return urljoin(BASE_URL, path_or_url)


def parse_int(value: str | None) -> int | None:
    """Parse formatted integer strings like '1,234,567' into int."""
    if not value:
        return None
    cleaned = re.sub(r"[^\d]", "", value)
    if not cleaned:
        return None
    return int(cleaned)


def parse_utc_timestamp(text: str | None) -> tuple[int, str] | None:
    """Parse Last.fm date strings into (unix_timestamp_utc, formatted_api_text)."""
    if not text:
        return None
    cleaned = " ".join(text.strip().split())
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(cleaned, fmt).replace(tzinfo=timezone.utc)
            uts = int(dt.timestamp())
            api_text = dt.strftime("%d %b %Y, %H:%M")
            return uts, api_text
        except ValueError:
            continue
    return None


def expand_images(src: str | None) -> list[dict[str, str]]:
    """Build Last.fm API-style image list (small/medium/large/extralarge) from an image URL."""
    if not src:
        return [
            {"#text": "", "size": size}
            for size, _ in _IMAGE_SIZES
        ]
    match = _IMAGE_SIZE_RE.match(src)
    if not match:
        return [{"#text": src, "size": size} for size, _ in _IMAGE_SIZES]
    prefix, _, suffix = match.groups()
    return [
        {"#text": f"{prefix}{token}{suffix}", "size": size}
        for size, token in _IMAGE_SIZES
    ]

