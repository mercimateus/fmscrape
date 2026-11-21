"""HTTP client with rate limiting, robots.txt compliance, TTL cache, and exponential backoff."""

from __future__ import annotations

import asyncio
import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urljoin, urlparse

import httpx

from fmscrape.errors import (
    NetworkError,
    NotFoundError,
    NotSupportedError,
    RateLimitError,
    RobotsDisallowedError,
)
from fmscrape.normalize import BASE_URL

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

_RETRYABLE_STATUSES = {429, 500, 502, 503, 504, 600}


def _build_url(path: str, params: dict[str, Any] | None = None) -> str:
    base = path if path.startswith(("http://", "https://")) else urljoin(BASE_URL, path)
    if not params:
        return base
    clean_params = {k: v for k, v in params.items() if v is not None}
    if not clean_params:
        return base
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}{urlencode(clean_params)}"


_USEFUL_COOKIES = frozenset({"sessionid", "csrftoken", "fsuid", "lfmanon"})


def _filter_useful_cookies(cookies: dict[str, str]) -> dict[str, str]:
    useful = {k: v for k, v in cookies.items() if k in _USEFUL_COOKIES}
    return useful if useful else cookies


def _parse_cookie_string(raw: str) -> dict[str, str]:
    cookies: dict[str, str] = {}
    for part in raw.replace("\n", ";").split(";"):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        key = k.strip()
        if key:
            cookies[key] = v.strip().strip("'\"")
    return _filter_useful_cookies(cookies)


def _parse_cookie_file(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    if text.startswith(("{", "[")):
        data = json.loads(text)
        if isinstance(data, dict):
            return _filter_useful_cookies({str(k): str(v) for k, v in data.items()})
        if isinstance(data, list):
            cookies = {
                str(item["name"]): str(item["value"])
                for item in data
                if isinstance(item, dict) and "name" in item and "value" in item
            }
            return _filter_useful_cookies(cookies)

    # Netscape cookies.txt (7 tab-separated columns) or key=value lines
    netscape: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        cols = line.split("\t")
        if len(cols) >= 7:
            netscape[cols[5].strip()] = cols[6].strip()
    if netscape:
        return _filter_useful_cookies(netscape)
    return _parse_cookie_string(text)


def load_cookies(cookies: dict[str, str] | str | Path | None) -> dict[str, str] | None:
    """Resolve cookies from dict, raw header string, file path, or cwd cookies.txt/cookies.json."""
    if cookies is None:
        for candidate in ("cookies.txt", "cookies.json"):
            p = Path.cwd() / candidate
            if p.is_file():
                parsed = _parse_cookie_file(p)
                return parsed or None
        return None
    if isinstance(cookies, Path):
        return _parse_cookie_file(cookies) or None
    if isinstance(cookies, str):
        p = Path(cookies)
        if "\n" not in cookies and ";" not in cookies and "=" not in cookies and p.is_file():
            return _parse_cookie_file(p) or None
        return _parse_cookie_string(cookies) or None
    return _filter_useful_cookies(cookies) or None


class _BaseClient:
    """Shared configuration, caching, and response validation logic."""

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        user_agent: str = DEFAULT_USER_AGENT,
        cookies: dict[str, str] | str | Path | None = None,
        rate_limit: float = 1.0,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        cache_ttl: float = 0.0,
        respect_robots: bool = True,
        raw_json: bool = True,
        timeout: float = 20.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.cookies: dict[str, str] | None = load_cookies(cookies)
        self.min_interval = 1.0 / rate_limit if rate_limit > 0 else 0.0
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.cache_ttl = cache_ttl
        self.respect_robots = respect_robots
        self.raw_json = raw_json
        self.timeout = timeout

        self._cache: dict[str, tuple[float, httpx.Response]] = {}
        self._disallow_patterns: list[re.Pattern[str]] = []
        self._allow_patterns: list[re.Pattern[str]] = []
        self._robots_loaded = False

    @property
    def has_cookies(self) -> bool:
        """Whether user-supplied cookies are configured on this client."""
        return bool(self.cookies)

    def format_result(self, result: Any) -> Any:
        """Return JSON-compatible dict when `raw_json=True`, otherwise the dataclass."""
        if self.raw_json and hasattr(result, "to_dict"):
            return result.to_dict()
        return result

    def _default_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def _get_cached(self, url: str) -> httpx.Response | None:
        if self.cache_ttl <= 0:
            return None
        entry = self._cache.get(url)
        if entry is None:
            return None
        ts, resp = entry
        if (time.monotonic() - ts) <= self.cache_ttl:
            return resp
        self._cache.pop(url, None)
        return None

    def _set_cached(self, url: str, resp: httpx.Response) -> None:
        if self.cache_ttl > 0:
            self._cache[url] = (time.monotonic(), resp)

    @staticmethod
    def _compile_robots_pattern(pattern: str) -> re.Pattern[str]:
        parts = [re.escape(p) for p in pattern.split("*")]
        regex = "^" + ".*".join(parts)
        if regex.endswith(r"\$"):
            regex = regex[:-2] + "$"
        return re.compile(regex)

    def _load_robots_text(self, text: str) -> None:
        disallow: list[re.Pattern[str]] = []
        allow: list[re.Pattern[str]] = []
        in_wildcard_group = False
        for raw_line in text.splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line or ":" not in line:
                continue
            key, val = (p.strip() for p in line.split(":", 1))
            key_lower = key.lower()
            if key_lower == "user-agent":
                in_wildcard_group = val == "*"
            elif in_wildcard_group and key_lower == "disallow" and val:
                disallow.append(self._compile_robots_pattern(val))
            elif in_wildcard_group and key_lower == "allow" and val:
                allow.append(self._compile_robots_pattern(val))
        self._disallow_patterns = disallow
        self._allow_patterns = allow
        self._robots_loaded = True

    def _check_robots(self, url: str) -> None:
        if not self.respect_robots or not self._robots_loaded:
            return
        parsed = urlparse(url)
        path_with_query = parsed.path or "/"
        if parsed.query:
            path_with_query = f"{path_with_query}?{parsed.query}"
        longest_allow = max(
            (len(p.pattern) for p in self._allow_patterns if p.match(path_with_query)),
            default=-1,
        )
        longest_disallow = max(
            (len(p.pattern) for p in self._disallow_patterns if p.match(path_with_query)),
            default=-1,
        )
        if longest_disallow >= 0 and longest_disallow > longest_allow:
            raise RobotsDisallowedError(
                f"URL disallowed by robots.txt for User-Agent {self.user_agent!r}: {url}"
            )

    def _validate_response(self, resp: httpx.Response, requested_url: str) -> httpx.Response:
        final_url = str(resp.url)
        if "/login" in final_url and "/login" not in requested_url:
            raise NotSupportedError(
                f"Last.fm redirected {requested_url} to login ({final_url}); "
                "this endpoint/filter requires authentication."
            )
        if resp.status_code == 404:
            raise NotFoundError(f"Resource not found (404): {requested_url}")
        if resp.status_code in (429, 600):
            if "Client Challenge" in resp.text or "/_fs-ch-" in resp.text:
                raise RateLimitError(
                    f"Blocked by Last.fm anti-bot Client Challenge (HTTP {resp.status_code}): {requested_url}"
                )
            raise RateLimitError(
                f"Rate limited by Last.fm (HTTP {resp.status_code}): {requested_url}"
            )
        if resp.status_code >= 500:
            raise NetworkError(
                f"Server error from Last.fm (HTTP {resp.status_code}): {requested_url}"
            )
        if resp.status_code >= 400:
            raise NetworkError(
                f"Unexpected HTTP {resp.status_code} for {requested_url}"
            )
        if "Client Challenge" in resp.text and "/_fs-ch-" in resp.text:
            raise RateLimitError(
                f"Blocked by Last.fm anti-bot Client Challenge: {requested_url}"
            )
        return resp

    def _retry_delay(self, attempt: int, resp: httpx.Response | None = None) -> float:
        if resp is not None:
            retry_after = resp.headers.get("Retry-After")
            if retry_after is not None:
                try:
                    return max(0.0, float(retry_after))
                except ValueError:
                    pass
        return float(self.backoff_base * (2**attempt))


class LastFmClient(_BaseClient):
    """Synchronous Last.fm HTML scraper client."""

    def __init__(
        self,
        *,
        transport: httpx.BaseTransport | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._client = httpx.Client(
            base_url=self.base_url,
            headers=self._default_headers(),
            cookies=self.cookies,
            follow_redirects=True,
            timeout=self.timeout,
            transport=transport,
        )
        self._last_request_at = 0.0

        from fmscrape.api.album import AlbumAPI
        from fmscrape.api.artist import ArtistAPI
        from fmscrape.api.auth import AuthAPI
        from fmscrape.api.chart import ChartAPI
        from fmscrape.api.geo import GeoAPI
        from fmscrape.api.library import LibraryAPI
        from fmscrape.api.tag import TagAPI
        from fmscrape.api.track import TrackAPI
        from fmscrape.api.user import UserAPI

        self.user = UserAPI(self)
        self.artist = ArtistAPI(self)
        self.album = AlbumAPI(self)
        self.track = TrackAPI(self)
        self.tag = TagAPI(self)
        self.chart = ChartAPI(self)
        self.geo = GeoAPI()
        self.library = LibraryAPI(self)
        self.auth = AuthAPI()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> LastFmClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _wait_rate_limit(self) -> None:
        if self.min_interval <= 0:
            return
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request_at = time.monotonic()

    def _ensure_robots(self) -> None:
        if not self.respect_robots or self._robots_loaded:
            return
        try:
            self._wait_rate_limit()
            resp = self._client.get("/robots.txt")
            if resp.status_code == 200:
                self._load_robots_text(resp.text)
            else:
                self._robots_loaded = True
        except httpx.HTTPError:
            self._robots_loaded = True

    def get(self, path: str, *, params: dict[str, Any] | None = None) -> httpx.Response:
        url = _build_url(path, params)
        cached = self._get_cached(url)
        if cached is not None:
            return cached

        self._ensure_robots()
        self._check_robots(url)

        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            self._wait_rate_limit()
            try:
                resp = self._client.get(path, params={k: v for k, v in (params or {}).items() if v is not None})
            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    time.sleep(self._retry_delay(attempt))
                    continue
                raise NetworkError(f"Network error fetching {url}: {exc}") from exc

            if resp.status_code in _RETRYABLE_STATUSES and attempt < self.max_retries:
                time.sleep(self._retry_delay(attempt, resp))
                continue

            validated = self._validate_response(resp, url)
            self._set_cached(url, validated)
            return validated

        raise NetworkError(f"Failed to fetch {url}: {last_exc}")


class AsyncLastFmClient(_BaseClient):
    """Asynchronous Last.fm HTML scraper client."""

    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._default_headers(),
            cookies=self.cookies,
            follow_redirects=True,
            timeout=self.timeout,
            transport=transport,
        )
        self._last_request_at = 0.0
        self._lock = asyncio.Lock()

        from fmscrape.api.album import AsyncAlbumAPI
        from fmscrape.api.artist import AsyncArtistAPI
        from fmscrape.api.auth import AuthAPI
        from fmscrape.api.chart import AsyncChartAPI
        from fmscrape.api.geo import GeoAPI
        from fmscrape.api.library import AsyncLibraryAPI
        from fmscrape.api.tag import AsyncTagAPI
        from fmscrape.api.track import AsyncTrackAPI
        from fmscrape.api.user import AsyncUserAPI

        self.user = AsyncUserAPI(self)
        self.artist = AsyncArtistAPI(self)
        self.album = AsyncAlbumAPI(self)
        self.track = AsyncTrackAPI(self)
        self.tag = AsyncTagAPI(self)
        self.chart = AsyncChartAPI(self)
        self.geo = GeoAPI()
        self.library = AsyncLibraryAPI(self)
        self.auth = AuthAPI()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncLastFmClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    async def _wait_rate_limit(self) -> None:
        if self.min_interval <= 0:
            return
        async with self._lock:
            elapsed = time.monotonic() - self._last_request_at
            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)
            self._last_request_at = time.monotonic()

    async def _ensure_robots(self) -> None:
        if not self.respect_robots or self._robots_loaded:
            return
        try:
            await self._wait_rate_limit()
            resp = await self._client.get("/robots.txt")
            if resp.status_code == 200:
                self._load_robots_text(resp.text)
            else:
                self._robots_loaded = True
        except httpx.HTTPError:
            self._robots_loaded = True

    async def get(self, path: str, *, params: dict[str, Any] | None = None) -> httpx.Response:
        url = _build_url(path, params)
        cached = self._get_cached(url)
        if cached is not None:
            return cached

        await self._ensure_robots()
        self._check_robots(url)

        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            await self._wait_rate_limit()
            try:
                resp = await self._client.get(path, params={k: v for k, v in (params or {}).items() if v is not None})
            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    await asyncio.sleep(self._retry_delay(attempt))
                    continue
                raise NetworkError(f"Network error fetching {url}: {exc}") from exc

            if resp.status_code in _RETRYABLE_STATUSES and attempt < self.max_retries:
                await asyncio.sleep(self._retry_delay(attempt, resp))
                continue

            validated = self._validate_response(resp, url)
            self._set_cached(url, validated)
            return validated

        raise NetworkError(f"Failed to fetch {url}: {last_exc}")

