"""Library API endpoints (`library.*`)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime, tzinfo
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from fmscrape.api.base import encode_music_part, iter_paginated, library_filter_params
from fmscrape.models import ArtistListPage
from fmscrape.parsers.user_lists import parse_library_plays, parse_user_top_artists

if TYPE_CHECKING:
    from fmscrape.client import AsyncLastFmClient, LastFmClient


class LibraryAPI:
    """Synchronous `library.*` methods."""

    def __init__(self, client: LastFmClient) -> None:
        self._client = client

    def _get_artists_page(
        self,
        user: str,
        *,
        period: str = "overall",
        from_ts: int | str | date | datetime | None = None,
        to_ts: int | str | date | datetime | None = None,
        tz: str | tzinfo | None = None,
        limit: int = 50,
        page: int = 1,
    ) -> ArtistListPage:
        path = f"/user/{quote(user, safe='')}/library/artists"
        params = library_filter_params(
            period=period,
            from_ts=from_ts,
            to_ts=to_ts,
            tz=tz,
            page=page,
            has_cookies=self._client.has_cookies,
            method="library.get_artists",
        )
        resp = self._client.get(path, params=params or None)
        res = parse_user_top_artists(resp.text, url=str(resp.url), user=user, page=page, limit=limit)
        res.root_key = "artists"
        return res

    def get_artists(
        self,
        user: str,
        *,
        period: str = "overall",
        from_ts: int | str | date | datetime | None = None,
        to_ts: int | str | date | datetime | None = None,
        tz: str | tzinfo | None = None,
        limit: int = 50,
        page: int = 1,
    ) -> Any:
        return self._client.format_result(
            self._get_artists_page(
                user, period=period, from_ts=from_ts, to_ts=to_ts, tz=tz, limit=limit, page=page
            )
        )

    def iter_artists(
        self,
        user: str,
        *,
        period: str = "overall",
        from_ts: int | str | date | datetime | None = None,
        to_ts: int | str | date | datetime | None = None,
        tz: str | tzinfo | None = None,
        limit: int = 50,
        start_page: int = 1,
        max_pages: int | None = None,
    ) -> Iterator[Any]:
        return iter_paginated(
            lambda p: self._get_artists_page(
                user, period=period, from_ts=from_ts, to_ts=to_ts, tz=tz, limit=limit, page=p
            ),
            lambda r: r.artists,
            start_page=start_page,
            max_pages=max_pages,
            raw_json=self._client.raw_json,
        )

    def get_artist_plays(
        self,
        user: str,
        artist: str,
        *,
        period: str | None = None,
        from_ts: int | str | date | datetime | None = None,
        to_ts: int | str | date | datetime | None = None,
        tz: str | tzinfo | None = None,
    ) -> Any:
        path = f"/user/{quote(user, safe='')}/library/music/{encode_music_part(artist)}"
        params = library_filter_params(
            period=period,
            from_ts=from_ts,
            to_ts=to_ts,
            tz=tz,
            has_cookies=self._client.has_cookies,
            method="library.get_artist_plays",
        )
        resp = self._client.get(path, params=params or None)
        return self._client.format_result(
            parse_library_plays(resp.text, url=str(resp.url), user=user, artist=artist)
        )

    def get_album_plays(
        self,
        user: str,
        artist: str,
        album: str,
        *,
        period: str | None = None,
        from_ts: int | str | date | datetime | None = None,
        to_ts: int | str | date | datetime | None = None,
        tz: str | tzinfo | None = None,
    ) -> Any:
        path = (
            f"/user/{quote(user, safe='')}/library/music/"
            f"{encode_music_part(artist)}/{encode_music_part(album)}"
        )
        params = library_filter_params(
            period=period,
            from_ts=from_ts,
            to_ts=to_ts,
            tz=tz,
            has_cookies=self._client.has_cookies,
            method="library.get_album_plays",
        )
        resp = self._client.get(path, params=params or None)
        return self._client.format_result(
            parse_library_plays(resp.text, url=str(resp.url), user=user, artist=artist, album=album)
        )

    def get_track_plays(
        self,
        user: str,
        artist: str,
        track: str,
        *,
        period: str | None = None,
        from_ts: int | str | date | datetime | None = None,
        to_ts: int | str | date | datetime | None = None,
        tz: str | tzinfo | None = None,
    ) -> Any:
        path = (
            f"/user/{quote(user, safe='')}/library/music/"
            f"{encode_music_part(artist)}/_/{encode_music_part(track)}"
        )
        params = library_filter_params(
            period=period,
            from_ts=from_ts,
            to_ts=to_ts,
            tz=tz,
            has_cookies=self._client.has_cookies,
            method="library.get_track_plays",
        )
        resp = self._client.get(path, params=params or None)
        return self._client.format_result(
            parse_library_plays(resp.text, url=str(resp.url), user=user, artist=artist, track=track)
        )


class AsyncLibraryAPI:
    """Asynchronous `library.*` methods."""

    def __init__(self, client: AsyncLastFmClient) -> None:
        self._client = client

    async def get_artists(
        self,
        user: str,
        *,
        period: str = "overall",
        from_ts: int | str | None = None,
        to_ts: int | str | None = None,
        limit: int = 50,
        page: int = 1,
    ) -> Any:
        path = f"/user/{quote(user, safe='')}/library/artists"
        params = library_filter_params(
            period=period,
            from_ts=from_ts,
            to_ts=to_ts,
            page=page,
            has_cookies=self._client.has_cookies,
            method="library.get_artists",
        )
        resp = await self._client.get(path, params=params or None)
        res = parse_user_top_artists(resp.text, url=str(resp.url), user=user, page=page, limit=limit)
        res.root_key = "artists"
        return self._client.format_result(res)

    async def get_artist_plays(
        self,
        user: str,
        artist: str,
        *,
        period: str | None = None,
        from_ts: int | str | None = None,
        to_ts: int | str | None = None,
    ) -> Any:
        path = f"/user/{quote(user, safe='')}/library/music/{encode_music_part(artist)}"
        params = library_filter_params(
            period=period,
            from_ts=from_ts,
            to_ts=to_ts,
            has_cookies=self._client.has_cookies,
            method="library.get_artist_plays",
        )
        resp = await self._client.get(path, params=params or None)
        return self._client.format_result(
            parse_library_plays(resp.text, url=str(resp.url), user=user, artist=artist)
        )

    async def get_album_plays(
        self,
        user: str,
        artist: str,
        album: str,
        *,
        period: str | None = None,
        from_ts: int | str | None = None,
        to_ts: int | str | None = None,
    ) -> Any:
        path = (
            f"/user/{quote(user, safe='')}/library/music/"
            f"{encode_music_part(artist)}/{encode_music_part(album)}"
        )
        params = library_filter_params(
            period=period,
            from_ts=from_ts,
            to_ts=to_ts,
            has_cookies=self._client.has_cookies,
            method="library.get_album_plays",
        )
        resp = await self._client.get(path, params=params or None)
        return self._client.format_result(
            parse_library_plays(resp.text, url=str(resp.url), user=user, artist=artist, album=album)
        )

    async def get_track_plays(
        self,
        user: str,
        artist: str,
        track: str,
        *,
        period: str | None = None,
        from_ts: int | str | None = None,
        to_ts: int | str | None = None,
    ) -> Any:
        path = (
            f"/user/{quote(user, safe='')}/library/music/"
            f"{encode_music_part(artist)}/_/{encode_music_part(track)}"
        )
        params = library_filter_params(
            period=period,
            from_ts=from_ts,
            to_ts=to_ts,
            has_cookies=self._client.has_cookies,
            method="library.get_track_plays",
        )
        resp = await self._client.get(path, params=params or None)
        return self._client.format_result(
            parse_library_plays(resp.text, url=str(resp.url), user=user, artist=artist, track=track)
        )
