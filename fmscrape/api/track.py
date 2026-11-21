"""Track API endpoints (`track.*`)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fmscrape.api.base import build_music_path
from fmscrape.errors import NotSupportedError
from fmscrape.models import CorrectionResult
from fmscrape.parsers.track import (
    parse_track_info,
    parse_track_search,
    parse_track_similar,
    parse_track_top_tags,
)

if TYPE_CHECKING:
    from fmscrape.client import AsyncLastFmClient, LastFmClient


class _TrackWriteNotSupported:
    def scrobble(self, *args: Any, **kwargs: Any) -> Any:
        raise NotSupportedError("track.scrobble requires Last.fm authentication.")

    def love(self, artist: str, track: str) -> Any:
        raise NotSupportedError("track.love requires Last.fm authentication.")

    def unlove(self, artist: str, track: str) -> Any:
        raise NotSupportedError("track.unlove requires Last.fm authentication.")

    def update_now_playing(self, *args: Any, **kwargs: Any) -> Any:
        raise NotSupportedError("track.update_now_playing requires Last.fm authentication.")

    def add_tags(self, artist: str, track: str, tags: list[str] | str) -> Any:
        raise NotSupportedError("track.add_tags requires Last.fm authentication.")

    def remove_tag(self, artist: str, track: str, tag: str) -> Any:
        raise NotSupportedError("track.remove_tag requires Last.fm authentication.")


class TrackAPI(_TrackWriteNotSupported):
    """Synchronous `track.*` methods."""

    def __init__(self, client: LastFmClient) -> None:
        self._client = client

    def get_info(
        self, artist: str, track: str, *, autocorrect: int = 1, lang: str | None = None
    ) -> Any:
        path = build_music_path(artist, "_", track, autocorrect=autocorrect, lang=lang)
        resp = self._client.get(path)
        return self._client.format_result(parse_track_info(resp.text, url=str(resp.url)))

    def get_similar(
        self, artist: str, track: str, *, limit: int = 50, autocorrect: int = 1
    ) -> Any:
        path = build_music_path(artist, "_", track, autocorrect=autocorrect)
        resp = self._client.get(path)
        return self._client.format_result(
            parse_track_similar(resp.text, url=str(resp.url), artist=artist, limit=limit)
        )

    def get_top_tags(self, artist: str, track: str, *, autocorrect: int = 1) -> Any:
        path = build_music_path(artist, "_", track, autocorrect=autocorrect, suffix="/+tags")
        resp = self._client.get(path)
        return self._client.format_result(parse_track_top_tags(resp.text, url=str(resp.url)))

    def get_correction(self, artist: str, track: str) -> Any:
        path = build_music_path(artist, "_", track, autocorrect=1)
        resp = self._client.get(path)
        info = parse_track_info(resp.text, url=str(resp.url))
        return self._client.format_result(
            CorrectionResult(
                name=info.name,
                url=info.url,
                artist_name=info.artist.name,
                artist_url=info.artist.url,
            )
        )

    def search(
        self, track: str, *, artist: str | None = None, limit: int = 30, page: int = 1
    ) -> Any:
        query = f"{artist} {track}".strip() if artist else track
        params: dict[str, Any] = {"q": query}
        if page > 1:
            params["page"] = page
        resp = self._client.get("/search/tracks", params=params)
        return self._client.format_result(
            parse_track_search(resp.text, url=str(resp.url), page=page, limit=limit)
        )


class AsyncTrackAPI(_TrackWriteNotSupported):
    """Asynchronous `track.*` methods."""

    def __init__(self, client: AsyncLastFmClient) -> None:
        self._client = client

    async def get_info(
        self, artist: str, track: str, *, autocorrect: int = 1, lang: str | None = None
    ) -> Any:
        path = build_music_path(artist, "_", track, autocorrect=autocorrect, lang=lang)
        resp = await self._client.get(path)
        return self._client.format_result(parse_track_info(resp.text, url=str(resp.url)))

    async def get_similar(
        self, artist: str, track: str, *, limit: int = 50, autocorrect: int = 1
    ) -> Any:
        path = build_music_path(artist, "_", track, autocorrect=autocorrect)
        resp = await self._client.get(path)
        return self._client.format_result(
            parse_track_similar(resp.text, url=str(resp.url), artist=artist, limit=limit)
        )

    async def get_top_tags(self, artist: str, track: str, *, autocorrect: int = 1) -> Any:
        path = build_music_path(artist, "_", track, autocorrect=autocorrect, suffix="/+tags")
        resp = await self._client.get(path)
        return self._client.format_result(parse_track_top_tags(resp.text, url=str(resp.url)))

    async def get_correction(self, artist: str, track: str) -> Any:
        path = build_music_path(artist, "_", track, autocorrect=1)
        resp = await self._client.get(path)
        info = parse_track_info(resp.text, url=str(resp.url))
        return self._client.format_result(
            CorrectionResult(
                name=info.name,
                url=info.url,
                artist_name=info.artist.name,
                artist_url=info.artist.url,
            )
        )

    async def search(
        self, track: str, *, artist: str | None = None, limit: int = 30, page: int = 1
    ) -> Any:
        query = f"{artist} {track}".strip() if artist else track
        params: dict[str, Any] = {"q": query}
        if page > 1:
            params["page"] = page
        resp = await self._client.get("/search/tracks", params=params)
        return self._client.format_result(
            parse_track_search(resp.text, url=str(resp.url), page=page, limit=limit)
        )
