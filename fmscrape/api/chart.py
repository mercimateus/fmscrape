"""Chart API endpoints (`chart.*`)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from fmscrape.api.base import iter_paginated
from fmscrape.errors import NotSupportedError
from fmscrape.models import ArtistListPage
from fmscrape.parsers.chart import parse_chart_top_artists, parse_chart_top_tracks

if TYPE_CHECKING:
    from fmscrape.client import AsyncLastFmClient, LastFmClient


class _ChartNotSupportedMixin:
    def get_top_tags(self, **kwargs: Any) -> Any:
        raise NotSupportedError("chart.get_top_tags is not available on Last.fm public /charts pages.")


class ChartAPI(_ChartNotSupportedMixin):
    """Synchronous `chart.*` methods."""

    def __init__(self, client: LastFmClient) -> None:
        self._client = client

    def _get_top_artists_page(self, *, limit: int = 50, page: int = 1) -> ArtistListPage:
        params = {"page": page} if page > 1 else None
        resp = self._client.get("/charts/weekly", params=params)
        return parse_chart_top_artists(resp.text, url=str(resp.url), page=page, limit=limit)

    def get_top_artists(self, *, limit: int = 50, page: int = 1) -> Any:
        return self._client.format_result(self._get_top_artists_page(limit=limit, page=page))

    def iter_top_artists(
        self, *, limit: int = 50, start_page: int = 1, max_pages: int | None = None
    ) -> Iterator[Any]:
        return iter_paginated(
            lambda p: self._get_top_artists_page(limit=limit, page=p),
            lambda r: r.artists,
            start_page=start_page,
            max_pages=max_pages,
            raw_json=self._client.raw_json,
        )

    def get_top_tracks(self, *, limit: int = 50, page: int = 1) -> Any:
        resp = self._client.get("/charts")
        return self._client.format_result(
            parse_chart_top_tracks(resp.text, url=str(resp.url), limit=limit)
        )


class AsyncChartAPI(_ChartNotSupportedMixin):
    """Asynchronous `chart.*` methods."""

    def __init__(self, client: AsyncLastFmClient) -> None:
        self._client = client

    async def get_top_artists(self, *, limit: int = 50, page: int = 1) -> Any:
        params = {"page": page} if page > 1 else None
        resp = await self._client.get("/charts/weekly", params=params)
        return self._client.format_result(
            parse_chart_top_artists(resp.text, url=str(resp.url), page=page, limit=limit)
        )

    async def get_top_tracks(self, *, limit: int = 50, page: int = 1) -> Any:
        resp = await self._client.get("/charts")
        return self._client.format_result(
            parse_chart_top_tracks(resp.text, url=str(resp.url), limit=limit)
        )
