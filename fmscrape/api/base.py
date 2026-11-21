"""Shared pagination, URL encoding, and period validation helpers for API modules."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from datetime import date, datetime, timezone, tzinfo
from typing import Any, TypeVar
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

from fmscrape.errors import NotSupportedError

VALID_PERIODS = ("overall", "7day", "1month", "3month", "6month", "12month")

PERIOD_TO_DATE_PRESET: dict[str, str] = {
    "overall": "ALL",
    "7day": "LAST_7_DAYS",
    "1month": "LAST_30_DAYS",
    "3month": "LAST_90_DAYS",
    "6month": "LAST_180_DAYS",
    "12month": "LAST_365_DAYS",
}

_T = TypeVar("_T")


def ts_to_date_str(ts: int) -> str:
    """Convert a UTC unix timestamp into Last.fm's YYYY-MM-DD query format."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def encode_music_part(value: str) -> str:
    """Encode an artist, album, or track name using Last.fm's `+` space convention."""
    return quote_plus(value.strip())


def lang_prefix(lang: str | None) -> str:
    """Return optional Last.fm language path prefix (e.g. '/pt') for non-English locales."""
    if not lang or lang.lower() in ("en", "en-us", "en-gb"):
        return ""
    clean = lang.strip().lower().split("-")[0]
    return f"/{clean}"


def build_music_path(
    *parts: str,
    autocorrect: int = 1,
    lang: str | None = None,
    suffix: str = "",
) -> str:
    """Build a `/music/...` URL path with optional lang prefix, noredirect, and suffix."""
    prefix = lang_prefix(lang)
    encoded = "/".join(p if p == "_" else encode_music_part(p) for p in parts)
    base = f"{prefix}/music/+noredirect/{encoded}" if autocorrect == 0 else f"{prefix}/music/{encoded}"
    return f"{base}{suffix}"


def validate_period(period: str, *, method: str, has_cookies: bool) -> str | None:
    """Validate period and return date_preset query value (or None for default overall)."""
    if period not in VALID_PERIODS:
        raise ValueError(f"Invalid period {period!r}; expected one of {VALID_PERIODS}")
    if period == "overall":
        return None
    if not has_cookies:
        raise NotSupportedError(
            f"{method} with period={period!r} redirects to Last.fm login on the public site; "
            "pass user cookies to LastFmClient(cookies=...) or use period='overall'."
        )
    return PERIOD_TO_DATE_PRESET[period]


def normalize_timestamp(
    value: int | str | date | datetime | None,
    tz: str | tzinfo | None = None,
) -> int | None:
    """Convert int, ISO date/datetime string, date, or datetime to a UTC Unix timestamp."""
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
        dt = datetime.fromisoformat(stripped)
    elif isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime(value.year, value.month, value.day)
    else:
        raise TypeError(f"Unsupported timestamp value: {value!r}")

    if dt.tzinfo is None:
        zone: tzinfo = timezone.utc
        if isinstance(tz, str):
            zone = ZoneInfo(tz)
        elif tz is not None:
            zone = tz
        dt = dt.replace(tzinfo=zone)
    return int(dt.astimezone(timezone.utc).timestamp())


def library_filter_params(
    *,
    period: str | None = None,
    from_ts: int | str | date | datetime | None = None,
    to_ts: int | str | date | datetime | None = None,
    tz: str | tzinfo | None = None,
    page: int = 1,
    has_cookies: bool,
    method: str,
) -> dict[str, Any]:
    """Build query parameters for Last.fm library endpoints (date_preset, Unix GMT from/to, page)."""
    params: dict[str, Any] = {}
    if from_ts is not None or to_ts is not None:
        if not has_cookies:
            raise NotSupportedError(
                f"{method} with from_ts/to_ts requires user cookies on last.fm."
            )
        f_uts = normalize_timestamp(from_ts, tz=tz)
        t_uts = normalize_timestamp(to_ts, tz=tz)
        if f_uts is not None:
            params["from"] = str(f_uts)
        if t_uts is not None:
            params["to"] = str(t_uts)
    elif period is not None:
        preset = validate_period(period, method=method, has_cookies=has_cookies)
        if preset is not None:
            params["date_preset"] = preset
    if page > 1:
        params["page"] = page
    return params


def iter_paginated(
    fetch_page: Callable[[int], Any],
    extract_items: Callable[[Any], list[_T]],
    *,
    start_page: int = 1,
    max_pages: int | None = None,
    raw_json: bool = True,
) -> Iterator[Any]:
    """Synchronously iterate across paginated Last.fm results."""
    page = start_page
    fetched = 0
    while True:
        result = fetch_page(page)
        items = extract_items(result)
        if not items:
            break
        for item in items:
            yield item.to_dict() if raw_json and hasattr(item, "to_dict") else item
        fetched += 1
        if max_pages is not None and fetched >= max_pages:
            break
        if page >= result.attr.total_pages:
            break
        page += 1


async def aiter_paginated(
    fetch_page: Callable[[int], Awaitable[Any]],
    extract_items: Callable[[Any], list[_T]],
    *,
    start_page: int = 1,
    max_pages: int | None = None,
    raw_json: bool = True,
) -> AsyncIterator[Any]:
    """Asynchronously iterate across paginated Last.fm results."""
    page = start_page
    fetched = 0
    while True:
        result = await fetch_page(page)
        items = extract_items(result)
        if not items:
            break
        for item in items:
            yield item.to_dict() if raw_json and hasattr(item, "to_dict") else item
        fetched += 1
        if max_pages is not None and fetched >= max_pages:
            break
        if page >= result.attr.total_pages:
            break
        page += 1

