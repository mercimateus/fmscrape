"""Album API endpoints (`album.*`)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fmscrape.api.base import build_music_path
from fmscrape.errors import NotSupportedError
from fmscrape.parsers.album import (
    parse_album_info,
    parse_album_search,
    parse_album_top_tags,
)

if TYPE_CHECKING:
    from fmscrape.client import AsyncLastFmClient, LastFmClient


class _AlbumWriteNotSupported:
    def add_tags(self, artist: str, album: str, tags: list[str] | str) -> Any:
        raise NotSupportedError("album.add_tags requires Last.fm authentication.")

    def remove_tag(self, artist: str, album: str, tag: str) -> Any:
        raise NotSupportedError("album.remove_tag requires Last.fm authentication.")


class AlbumAPI(_AlbumWriteNotSupported):
    """Synchronous `album.*` methods."""

    def __init__(self, client: LastFmClient) -> None:
        self._client = client

    def get_info(
        self, artist: str, album: str, *, autocorrect: int = 1, lang: str | None = None
    ) -> Any:
        path = build_music_path(artist, album, autocorrect=autocorrect, lang=lang)
        resp = self._client.get(path)
        return self._client.format_result(parse_album_info(resp.text, url=str(resp.url)))

    def get_top_tags(self, artist: str, album: str, *, autocorrect: int = 1) -> Any:
        path = build_music_path(artist, album, autocorrect=autocorrect, suffix="/+tags")
        resp = self._client.get(path)
        return self._client.format_result(parse_album_top_tags(resp.text, url=str(resp.url)))

    def search(self, album: str, *, limit: int = 30, page: int = 1) -> Any:
        params: dict[str, Any] = {"q": album}
        if page > 1:
            params["page"] = page
        resp = self._client.get("/search/albums", params=params)
        return self._client.format_result(
            parse_album_search(resp.text, url=str(resp.url), page=page, limit=limit)
        )


class AsyncAlbumAPI(_AlbumWriteNotSupported):
    """Asynchronous `album.*` methods."""

    def __init__(self, client: AsyncLastFmClient) -> None:
        self._client = client

    async def get_info(
        self, artist: str, album: str, *, autocorrect: int = 1, lang: str | None = None
    ) -> Any:
        path = build_music_path(artist, album, autocorrect=autocorrect, lang=lang)
        resp = await self._client.get(path)
        return self._client.format_result(parse_album_info(resp.text, url=str(resp.url)))

    async def get_top_tags(self, artist: str, album: str, *, autocorrect: int = 1) -> Any:
        path = build_music_path(artist, album, autocorrect=autocorrect, suffix="/+tags")
        resp = await self._client.get(path)
        return self._client.format_result(parse_album_top_tags(resp.text, url=str(resp.url)))

    async def search(self, album: str, *, limit: int = 30, page: int = 1) -> Any:
        params: dict[str, Any] = {"q": album}
        if page > 1:
            params["page"] = page
        resp = await self._client.get("/search/albums", params=params)
        return self._client.format_result(
            parse_album_search(resp.text, url=str(resp.url), page=page, limit=limit)
        )
