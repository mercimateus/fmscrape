"""Artist API endpoints (`artist.*`)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from bs4 import BeautifulSoup

from fmscrape.api.base import build_music_path, iter_paginated
from fmscrape.errors import FmScrapeError, NotSupportedError
from fmscrape.models import (
    AlbumListPage,
    ArtistInfo,
    CorrectionResult,
    TrackListPage,
)
from fmscrape.parsers.artist import (
    parse_artist_info,
    parse_artist_search,
    parse_artist_similar,
    parse_artist_top_albums,
    parse_artist_top_tags,
    parse_artist_top_tracks,
)
from fmscrape.parsers.common import parse_wiki

if TYPE_CHECKING:
    from fmscrape.client import AsyncLastFmClient, LastFmClient


class _ArtistWriteNotSupported:
    def add_tags(self, artist: str, tags: list[str] | str) -> Any:
        raise NotSupportedError("artist.add_tags requires Last.fm authentication.")

    def remove_tag(self, artist: str, tag: str) -> Any:
        raise NotSupportedError("artist.remove_tag requires Last.fm authentication.")


def _merge_full_wiki(info: ArtistInfo, wiki_html: str) -> ArtistInfo:
    full_wiki = parse_wiki(BeautifulSoup(wiki_html, "lxml"), is_full_page=True)
    if full_wiki.content:
        info.bio.content = full_wiki.content
    if full_wiki.published:
        info.bio.published = full_wiki.published
    return info


class ArtistAPI(_ArtistWriteNotSupported):
    """Synchronous `artist.*` methods."""

    def __init__(self, client: LastFmClient) -> None:
        self._client = client

    def _get_info_model(
        self,
        artist: str,
        *,
        autocorrect: int = 1,
        lang: str | None = None,
        fetch_full_bio: bool = True,
    ) -> ArtistInfo:
        path = build_music_path(artist, autocorrect=autocorrect, lang=lang)
        resp = self._client.get(path)
        info = parse_artist_info(resp.text, url=str(resp.url))
        if fetch_full_bio:
            try:
                wiki_resp = self._client.get(f"{path}/+wiki")
                _merge_full_wiki(info, wiki_resp.text)
            except FmScrapeError:
                pass
        return info

    def get_info(
        self,
        artist: str,
        *,
        autocorrect: int = 1,
        lang: str | None = None,
        fetch_full_bio: bool = True,
    ) -> Any:
        return self._client.format_result(
            self._get_info_model(
                artist, autocorrect=autocorrect, lang=lang, fetch_full_bio=fetch_full_bio
            )
        )

    def get_similar(
        self,
        artist: str,
        *,
        limit: int = 50,
        page: int = 1,
        autocorrect: int = 1,
    ) -> Any:
        path = build_music_path(artist, autocorrect=autocorrect, suffix="/+similar")
        params = {"page": page} if page > 1 else None
        resp = self._client.get(path, params=params)
        return self._client.format_result(
            parse_artist_similar(resp.text, url=str(resp.url), artist=artist, page=page, limit=limit)
        )

    def _get_top_albums_page(
        self, artist: str, *, limit: int = 50, page: int = 1, autocorrect: int = 1
    ) -> AlbumListPage:
        path = build_music_path(artist, autocorrect=autocorrect, suffix="/+albums")
        params = {"page": page} if page > 1 else None
        resp = self._client.get(path, params=params)
        return parse_artist_top_albums(resp.text, url=str(resp.url), artist=artist, page=page, limit=limit)

    def get_top_albums(
        self, artist: str, *, limit: int = 50, page: int = 1, autocorrect: int = 1
    ) -> Any:
        return self._client.format_result(
            self._get_top_albums_page(artist, limit=limit, page=page, autocorrect=autocorrect)
        )

    def iter_top_albums(
        self,
        artist: str,
        *,
        limit: int = 50,
        start_page: int = 1,
        max_pages: int | None = None,
        autocorrect: int = 1,
    ) -> Iterator[Any]:
        return iter_paginated(
            lambda p: self._get_top_albums_page(artist, limit=limit, page=p, autocorrect=autocorrect),
            lambda r: r.albums,
            start_page=start_page,
            max_pages=max_pages,
            raw_json=self._client.raw_json,
        )

    def _get_top_tracks_page(
        self, artist: str, *, limit: int = 50, page: int = 1, autocorrect: int = 1
    ) -> TrackListPage:
        path = build_music_path(artist, autocorrect=autocorrect, suffix="/+tracks")
        params = {"page": page} if page > 1 else None
        resp = self._client.get(path, params=params)
        return parse_artist_top_tracks(resp.text, url=str(resp.url), artist=artist, page=page, limit=limit)

    def get_top_tracks(
        self, artist: str, *, limit: int = 50, page: int = 1, autocorrect: int = 1
    ) -> Any:
        return self._client.format_result(
            self._get_top_tracks_page(artist, limit=limit, page=page, autocorrect=autocorrect)
        )

    def iter_top_tracks(
        self,
        artist: str,
        *,
        limit: int = 50,
        start_page: int = 1,
        max_pages: int | None = None,
        autocorrect: int = 1,
    ) -> Iterator[Any]:
        return iter_paginated(
            lambda p: self._get_top_tracks_page(artist, limit=limit, page=p, autocorrect=autocorrect),
            lambda r: r.tracks,
            start_page=start_page,
            max_pages=max_pages,
            raw_json=self._client.raw_json,
        )

    def get_top_tags(self, artist: str, *, autocorrect: int = 1) -> Any:
        path = build_music_path(artist, autocorrect=autocorrect, suffix="/+tags")
        resp = self._client.get(path)
        return self._client.format_result(parse_artist_top_tags(resp.text, url=str(resp.url)))

    def get_correction(self, artist: str) -> Any:
        info = self._get_info_model(artist, autocorrect=1, fetch_full_bio=False)
        return self._client.format_result(CorrectionResult(name=info.name, url=info.url))

    def search(self, artist: str, *, limit: int = 20, page: int = 1) -> Any:
        params: dict[str, Any] = {"q": artist}
        if page > 1:
            params["page"] = page
        resp = self._client.get("/search/artists", params=params)
        return self._client.format_result(
            parse_artist_search(resp.text, url=str(resp.url), page=page, limit=limit)
        )


class AsyncArtistAPI(_ArtistWriteNotSupported):
    """Asynchronous `artist.*` methods."""

    def __init__(self, client: AsyncLastFmClient) -> None:
        self._client = client

    async def _get_info_model(
        self,
        artist: str,
        *,
        autocorrect: int = 1,
        lang: str | None = None,
        fetch_full_bio: bool = True,
    ) -> ArtistInfo:
        path = build_music_path(artist, autocorrect=autocorrect, lang=lang)
        resp = await self._client.get(path)
        info = parse_artist_info(resp.text, url=str(resp.url))
        if fetch_full_bio:
            try:
                wiki_resp = await self._client.get(f"{path}/+wiki")
                _merge_full_wiki(info, wiki_resp.text)
            except FmScrapeError:
                pass
        return info

    async def get_info(
        self,
        artist: str,
        *,
        autocorrect: int = 1,
        lang: str | None = None,
        fetch_full_bio: bool = True,
    ) -> Any:
        return self._client.format_result(
            await self._get_info_model(
                artist, autocorrect=autocorrect, lang=lang, fetch_full_bio=fetch_full_bio
            )
        )

    async def get_similar(self, artist: str, *, limit: int = 50, page: int = 1, autocorrect: int = 1) -> Any:
        path = build_music_path(artist, autocorrect=autocorrect, suffix="/+similar")
        params = {"page": page} if page > 1 else None
        resp = await self._client.get(path, params=params)
        return self._client.format_result(
            parse_artist_similar(resp.text, url=str(resp.url), artist=artist, page=page, limit=limit)
        )

    async def get_top_albums(self, artist: str, *, limit: int = 50, page: int = 1, autocorrect: int = 1) -> Any:
        path = build_music_path(artist, autocorrect=autocorrect, suffix="/+albums")
        params = {"page": page} if page > 1 else None
        resp = await self._client.get(path, params=params)
        return self._client.format_result(
            parse_artist_top_albums(resp.text, url=str(resp.url), artist=artist, page=page, limit=limit)
        )

    async def get_top_tracks(self, artist: str, *, limit: int = 50, page: int = 1, autocorrect: int = 1) -> Any:
        path = build_music_path(artist, autocorrect=autocorrect, suffix="/+tracks")
        params = {"page": page} if page > 1 else None
        resp = await self._client.get(path, params=params)
        return self._client.format_result(
            parse_artist_top_tracks(resp.text, url=str(resp.url), artist=artist, page=page, limit=limit)
        )

    async def get_top_tags(self, artist: str, *, autocorrect: int = 1) -> Any:
        path = build_music_path(artist, autocorrect=autocorrect, suffix="/+tags")
        resp = await self._client.get(path)
        return self._client.format_result(parse_artist_top_tags(resp.text, url=str(resp.url)))

    async def get_correction(self, artist: str) -> Any:
        info = await self._get_info_model(artist, autocorrect=1, fetch_full_bio=False)
        return self._client.format_result(CorrectionResult(name=info.name, url=info.url))

    async def search(self, artist: str, *, limit: int = 20, page: int = 1) -> Any:
        params: dict[str, Any] = {"q": artist}
        if page > 1:
            params["page"] = page
        resp = await self._client.get("/search/artists", params=params)
        return self._client.format_result(
            parse_artist_search(resp.text, url=str(resp.url), page=page, limit=limit)
        )
