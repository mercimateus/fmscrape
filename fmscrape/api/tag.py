"""Tag API endpoints (`tag.*`)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from bs4 import BeautifulSoup

from fmscrape.api.base import iter_paginated, lang_prefix
from fmscrape.errors import FmScrapeError, NotSupportedError
from fmscrape.models import AlbumListPage, ArtistListPage, TrackListPage
from fmscrape.parsers.common import parse_wiki
from fmscrape.parsers.tag import (
    parse_tag_info,
    parse_tag_similar,
    parse_tag_top_albums,
    parse_tag_top_artists,
    parse_tag_top_tracks,
)

if TYPE_CHECKING:
    from fmscrape.client import AsyncLastFmClient, LastFmClient


class _TagNotSupportedMixin:
    def get_top_tags(self) -> Any:
        raise NotSupportedError(
            "tag.get_top_tags has no public global directory on last.fm (/music/+tags returns 404)."
        )

    def get_weekly_chart_list(self, tag: str) -> Any:
        raise NotSupportedError("tag.get_weekly_chart_list has no public equivalent on last.fm.")


class TagAPI(_TagNotSupportedMixin):
    """Synchronous `tag.*` methods."""

    def __init__(self, client: LastFmClient) -> None:
        self._client = client

    def get_info(self, tag: str, *, lang: str | None = None, fetch_full_wiki: bool = True) -> Any:
        prefix = lang_prefix(lang)
        path = f"{prefix}/tag/{quote(tag, safe='')}"
        resp = self._client.get(path)
        info = parse_tag_info(resp.text, url=str(resp.url), tag=tag)
        if fetch_full_wiki:
            try:
                w_resp = self._client.get(f"{path}/wiki")
                full = parse_wiki(BeautifulSoup(w_resp.text, "lxml"), is_full_page=True)
                if full.content:
                    info.wiki.content = full.content
                if full.published:
                    info.wiki.published = full.published
            except FmScrapeError:
                pass
        return self._client.format_result(info)

    def get_similar(self, tag: str) -> Any:
        resp = self._client.get(f"/tag/{quote(tag, safe='')}")
        return self._client.format_result(parse_tag_similar(resp.text, url=str(resp.url)))

    def _get_top_artists_page(self, tag: str, *, limit: int = 50, page: int = 1) -> ArtistListPage:
        path = f"/tag/{quote(tag, safe='')}/artists"
        params = {"page": page} if page > 1 else None
        resp = self._client.get(path, params=params)
        return parse_tag_top_artists(resp.text, url=str(resp.url), tag=tag, page=page, limit=limit)

    def get_top_artists(self, tag: str, *, limit: int = 50, page: int = 1) -> Any:
        return self._client.format_result(self._get_top_artists_page(tag, limit=limit, page=page))

    def iter_top_artists(
        self, tag: str, *, limit: int = 50, start_page: int = 1, max_pages: int | None = None
    ) -> Iterator[Any]:
        return iter_paginated(
            lambda p: self._get_top_artists_page(tag, limit=limit, page=p),
            lambda r: r.artists,
            start_page=start_page,
            max_pages=max_pages,
            raw_json=self._client.raw_json,
        )

    def _get_top_albums_page(self, tag: str, *, limit: int = 50, page: int = 1) -> AlbumListPage:
        path = f"/tag/{quote(tag, safe='')}/albums"
        params = {"page": page} if page > 1 else None
        resp = self._client.get(path, params=params)
        return parse_tag_top_albums(resp.text, url=str(resp.url), tag=tag, page=page, limit=limit)

    def get_top_albums(self, tag: str, *, limit: int = 50, page: int = 1) -> Any:
        return self._client.format_result(self._get_top_albums_page(tag, limit=limit, page=page))

    def iter_top_albums(
        self, tag: str, *, limit: int = 50, start_page: int = 1, max_pages: int | None = None
    ) -> Iterator[Any]:
        return iter_paginated(
            lambda p: self._get_top_albums_page(tag, limit=limit, page=p),
            lambda r: r.albums,
            start_page=start_page,
            max_pages=max_pages,
            raw_json=self._client.raw_json,
        )

    def _get_top_tracks_page(self, tag: str, *, limit: int = 50, page: int = 1) -> TrackListPage:
        path = f"/tag/{quote(tag, safe='')}/tracks"
        params = {"page": page} if page > 1 else None
        resp = self._client.get(path, params=params)
        return parse_tag_top_tracks(resp.text, url=str(resp.url), tag=tag, page=page, limit=limit)

    def get_top_tracks(self, tag: str, *, limit: int = 50, page: int = 1) -> Any:
        return self._client.format_result(self._get_top_tracks_page(tag, limit=limit, page=page))

    def iter_top_tracks(
        self, tag: str, *, limit: int = 50, start_page: int = 1, max_pages: int | None = None
    ) -> Iterator[Any]:
        return iter_paginated(
            lambda p: self._get_top_tracks_page(tag, limit=limit, page=p),
            lambda r: r.tracks,
            start_page=start_page,
            max_pages=max_pages,
            raw_json=self._client.raw_json,
        )


class AsyncTagAPI(_TagNotSupportedMixin):
    """Asynchronous `tag.*` methods."""

    def __init__(self, client: AsyncLastFmClient) -> None:
        self._client = client

    async def get_info(self, tag: str, *, lang: str | None = None, fetch_full_wiki: bool = True) -> Any:
        prefix = lang_prefix(lang)
        path = f"{prefix}/tag/{quote(tag, safe='')}"
        resp = await self._client.get(path)
        info = parse_tag_info(resp.text, url=str(resp.url), tag=tag)
        if fetch_full_wiki:
            try:
                w_resp = await self._client.get(f"{path}/wiki")
                full = parse_wiki(BeautifulSoup(w_resp.text, "lxml"), is_full_page=True)
                if full.content:
                    info.wiki.content = full.content
                if full.published:
                    info.wiki.published = full.published
            except FmScrapeError:
                pass
        return self._client.format_result(info)

    async def get_similar(self, tag: str) -> Any:
        resp = await self._client.get(f"/tag/{quote(tag, safe='')}")
        return self._client.format_result(parse_tag_similar(resp.text, url=str(resp.url)))

    async def get_top_artists(self, tag: str, *, limit: int = 50, page: int = 1) -> Any:
        path = f"/tag/{quote(tag, safe='')}/artists"
        params = {"page": page} if page > 1 else None
        resp = await self._client.get(path, params=params)
        return self._client.format_result(
            parse_tag_top_artists(resp.text, url=str(resp.url), tag=tag, page=page, limit=limit)
        )

    async def get_top_albums(self, tag: str, *, limit: int = 50, page: int = 1) -> Any:
        path = f"/tag/{quote(tag, safe='')}/albums"
        params = {"page": page} if page > 1 else None
        resp = await self._client.get(path, params=params)
        return self._client.format_result(
            parse_tag_top_albums(resp.text, url=str(resp.url), tag=tag, page=page, limit=limit)
        )

    async def get_top_tracks(self, tag: str, *, limit: int = 50, page: int = 1) -> Any:
        path = f"/tag/{quote(tag, safe='')}/tracks"
        params = {"page": page} if page > 1 else None
        resp = await self._client.get(path, params=params)
        return self._client.format_result(
            parse_tag_top_tracks(resp.text, url=str(resp.url), tag=tag, page=page, limit=limit)
        )
