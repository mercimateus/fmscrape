"""User API endpoints (`user.*`)."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import date, datetime, tzinfo
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from fmscrape.api.base import (
    aiter_paginated,
    iter_paginated,
    library_filter_params,
    validate_period,
)
from fmscrape.errors import NotSupportedError
from fmscrape.models import (
    AlbumListPage,
    ArtistListPage,
    FriendsPage,
    RecentTracksPage,
    TrackListPage,
)
from fmscrape.parsers.user_lists import (
    parse_user_friends,
    parse_user_info,
    parse_user_personal_tags,
    parse_user_top_albums,
    parse_user_top_artists,
    parse_user_top_tags,
    parse_user_top_tracks,
)
from fmscrape.parsers.user_recent import parse_user_recent_tracks

if TYPE_CHECKING:
    from fmscrape.client import AsyncLastFmClient, LastFmClient


def _require_cookies(has_cookies: bool, method: str) -> None:
    if not has_cookies:
        raise NotSupportedError(
            f"{method} requires user cookies on last.fm (to pass Client Challenge or login gate). "
            "Initialize LastFmClient(cookies=...) with your browser session cookies."
        )


def _date_range_params(
    from_ts: int | str | None,
    to_ts: int | str | None,
    *,
    has_cookies: bool,
    method: str,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if from_ts is not None or to_ts is not None:
        _require_cookies(has_cookies, method)
        if from_ts is not None:
            params["from"] = str(from_ts)
        if to_ts is not None:
            params["to"] = str(to_ts)
    return params


class UserAPI:
    """Synchronous `user.*` methods."""

    def __init__(self, client: LastFmClient) -> None:
        self._client = client

    def get_info(self, user: str) -> Any:
        _require_cookies(self._client.has_cookies, "user.get_info")
        path = f"/user/{quote(user, safe='')}"
        resp = self._client.get(path)
        return self._client.format_result(parse_user_info(resp.text, url=str(resp.url)))

    def _get_recent_tracks_page(
        self,
        user: str,
        *,
        limit: int = 50,
        page: int = 1,
        from_ts: int | None = None,
        to_ts: int | None = None,
    ) -> RecentTracksPage:
        params = _date_range_params(
            from_ts, to_ts, has_cookies=self._client.has_cookies, method="user.get_recent_tracks"
        )
        if page > 1:
            params["page"] = page
        use_overview = (
            self._client.has_cookies
            and page == 1
            and from_ts is None
            and to_ts is None
            and limit <= 10
        )
        path = f"/user/{quote(user, safe='')}" if use_overview else f"/user/{quote(user, safe='')}/library"
        resp = self._client.get(path, params=params or None)
        return parse_user_recent_tracks(resp.text, url=str(resp.url), user=user, page=page, limit=limit)

    def get_recent_tracks(
        self,
        user: str,
        *,
        limit: int = 50,
        page: int = 1,
        from_ts: int | None = None,
        to_ts: int | None = None,
    ) -> Any:
        return self._client.format_result(
            self._get_recent_tracks_page(user, limit=limit, page=page, from_ts=from_ts, to_ts=to_ts)
        )

    def iter_recent_tracks(
        self,
        user: str,
        *,
        limit: int = 50,
        start_page: int = 1,
        max_pages: int | None = None,
    ) -> Iterator[Any]:
        return iter_paginated(
            lambda p: self._get_recent_tracks_page(user, limit=limit, page=p),
            lambda r: r.tracks,
            start_page=start_page,
            max_pages=max_pages,
            raw_json=self._client.raw_json,
        )

    def _get_top_artists_page(
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
        params = library_filter_params(
            period=period,
            from_ts=from_ts,
            to_ts=to_ts,
            tz=tz,
            page=page,
            has_cookies=self._client.has_cookies,
            method="user.get_top_artists",
        )
        path = f"/user/{quote(user, safe='')}/library/artists"
        resp = self._client.get(path, params=params or None)
        return parse_user_top_artists(resp.text, url=str(resp.url), user=user, page=page, limit=limit)

    def get_top_artists(
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
            self._get_top_artists_page(
                user, period=period, from_ts=from_ts, to_ts=to_ts, tz=tz, limit=limit, page=page
            )
        )

    def iter_top_artists(
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
            lambda p: self._get_top_artists_page(
                user, period=period, from_ts=from_ts, to_ts=to_ts, tz=tz, limit=limit, page=p
            ),
            lambda r: r.artists,
            start_page=start_page,
            max_pages=max_pages,
            raw_json=self._client.raw_json,
        )

    def _get_top_albums_page(
        self,
        user: str,
        *,
        period: str = "overall",
        from_ts: int | str | date | datetime | None = None,
        to_ts: int | str | date | datetime | None = None,
        tz: str | tzinfo | None = None,
        limit: int = 50,
        page: int = 1,
    ) -> AlbumListPage:
        params = library_filter_params(
            period=period,
            from_ts=from_ts,
            to_ts=to_ts,
            tz=tz,
            page=page,
            has_cookies=self._client.has_cookies,
            method="user.get_top_albums",
        )
        path = f"/user/{quote(user, safe='')}/library/albums"
        resp = self._client.get(path, params=params or None)
        return parse_user_top_albums(resp.text, url=str(resp.url), user=user, page=page, limit=limit)

    def get_top_albums(
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
            self._get_top_albums_page(
                user, period=period, from_ts=from_ts, to_ts=to_ts, tz=tz, limit=limit, page=page
            )
        )

    def iter_top_albums(
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
            lambda p: self._get_top_albums_page(
                user, period=period, from_ts=from_ts, to_ts=to_ts, tz=tz, limit=limit, page=p
            ),
            lambda r: r.albums,
            start_page=start_page,
            max_pages=max_pages,
            raw_json=self._client.raw_json,
        )

    def _get_top_tracks_page(
        self,
        user: str,
        *,
        period: str = "overall",
        from_ts: int | str | date | datetime | None = None,
        to_ts: int | str | date | datetime | None = None,
        tz: str | tzinfo | None = None,
        limit: int = 50,
        page: int = 1,
    ) -> TrackListPage:
        _require_cookies(self._client.has_cookies, "user.get_top_tracks")
        params = library_filter_params(
            period=period,
            from_ts=from_ts,
            to_ts=to_ts,
            tz=tz,
            page=page,
            has_cookies=self._client.has_cookies,
            method="user.get_top_tracks",
        )
        path = f"/user/{quote(user, safe='')}/library/tracks"
        resp = self._client.get(path, params=params or None)
        return parse_user_top_tracks(resp.text, url=str(resp.url), user=user, page=page, limit=limit)

    def get_top_tracks(
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
            self._get_top_tracks_page(
                user, period=period, from_ts=from_ts, to_ts=to_ts, tz=tz, limit=limit, page=page
            )
        )

    def iter_top_tracks(
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
            lambda p: self._get_top_tracks_page(
                user, period=period, from_ts=from_ts, to_ts=to_ts, tz=tz, limit=limit, page=p
            ),
            lambda r: r.tracks,
            start_page=start_page,
            max_pages=max_pages,
            raw_json=self._client.raw_json,
        )

    def _get_loved_tracks_page(self, user: str, *, limit: int = 50, page: int = 1) -> TrackListPage:
        _require_cookies(self._client.has_cookies, "user.get_loved_tracks")
        path = f"/user/{quote(user, safe='')}/loved"
        params = {"page": page} if page > 1 else None
        resp = self._client.get(path, params=params)
        return parse_user_top_tracks(
            resp.text, url=str(resp.url), user=user, page=page, limit=limit, root_key="lovedtracks"
        )

    def get_loved_tracks(self, user: str, *, limit: int = 50, page: int = 1) -> Any:
        return self._client.format_result(self._get_loved_tracks_page(user, limit=limit, page=page))

    def iter_loved_tracks(
        self,
        user: str,
        *,
        limit: int = 50,
        start_page: int = 1,
        max_pages: int | None = None,
    ) -> Iterator[Any]:
        return iter_paginated(
            lambda p: self._get_loved_tracks_page(user, limit=limit, page=p),
            lambda r: r.tracks,
            start_page=start_page,
            max_pages=max_pages,
            raw_json=self._client.raw_json,
        )

    def get_top_tags(self, user: str, *, limit: int | None = None) -> Any:
        _require_cookies(self._client.has_cookies, "user.get_top_tags")
        path = f"/user/{quote(user, safe='')}/tags"
        resp = self._client.get(path)
        return self._client.format_result(parse_user_top_tags(resp.text, url=str(resp.url), limit=limit))

    def _get_friends_page(self, user: str, *, limit: int = 50, page: int = 1) -> FriendsPage:
        path = f"/user/{quote(user, safe='')}/following"
        params = {"page": page} if page > 1 else None
        resp = self._client.get(path, params=params)
        return parse_user_friends(resp.text, url=str(resp.url), user=user, page=page, limit=limit)

    def get_friends(self, user: str, *, limit: int = 50, page: int = 1) -> Any:
        return self._client.format_result(self._get_friends_page(user, limit=limit, page=page))

    def iter_friends(
        self,
        user: str,
        *,
        limit: int = 50,
        start_page: int = 1,
        max_pages: int | None = None,
    ) -> Iterator[Any]:
        return iter_paginated(
            lambda p: self._get_friends_page(user, limit=limit, page=p),
            lambda r: r.friends,
            start_page=start_page,
            max_pages=max_pages,
            raw_json=self._client.raw_json,
        )

    def get_weekly_artist_chart(
        self,
        user: str,
        *,
        from_ts: int | None = None,
        to_ts: int | None = None,
        limit: int = 50,
        page: int = 1,
    ) -> Any:
        _require_cookies(self._client.has_cookies, "user.get_weekly_artist_chart")
        params = _date_range_params(
            from_ts, to_ts, has_cookies=self._client.has_cookies, method="user.get_weekly_artist_chart"
        )
        if page > 1:
            params["page"] = page
        path = f"/user/{quote(user, safe='')}/library/artists"
        resp = self._client.get(path, params=params or None)
        res = parse_user_top_artists(resp.text, url=str(resp.url), user=user, page=page, limit=limit)
        res.root_key = "weeklyartistchart"
        return self._client.format_result(res)

    def get_weekly_album_chart(
        self,
        user: str,
        *,
        from_ts: int | None = None,
        to_ts: int | None = None,
        limit: int = 50,
        page: int = 1,
    ) -> Any:
        _require_cookies(self._client.has_cookies, "user.get_weekly_album_chart")
        params = _date_range_params(
            from_ts, to_ts, has_cookies=self._client.has_cookies, method="user.get_weekly_album_chart"
        )
        if page > 1:
            params["page"] = page
        path = f"/user/{quote(user, safe='')}/library/albums"
        resp = self._client.get(path, params=params or None)
        res = parse_user_top_albums(resp.text, url=str(resp.url), user=user, page=page, limit=limit)
        res.root_key = "weeklyalbumchart"
        return self._client.format_result(res)

    def get_weekly_track_chart(
        self,
        user: str,
        *,
        from_ts: int | None = None,
        to_ts: int | None = None,
        limit: int = 50,
        page: int = 1,
    ) -> Any:
        _require_cookies(self._client.has_cookies, "user.get_weekly_track_chart")
        params = _date_range_params(
            from_ts, to_ts, has_cookies=self._client.has_cookies, method="user.get_weekly_track_chart"
        )
        if page > 1:
            params["page"] = page
        path = f"/user/{quote(user, safe='')}/library/tracks"
        resp = self._client.get(path, params=params or None)
        return self._client.format_result(
            parse_user_top_tracks(
                resp.text,
                url=str(resp.url),
                user=user,
                page=page,
                limit=limit,
                root_key="weeklytrackchart",
            )
        )

    def get_weekly_chart_list(self, user: str) -> Any:
        raise NotSupportedError("user.get_weekly_chart_list has no public equivalent on last.fm.")

    def get_personal_tags(
        self,
        user: str,
        tag: str,
        *,
        tagging_type: str = "artist",
        limit: int = 50,
        page: int = 1,
    ) -> Any:
        path = f"/user/{quote(user, safe='')}/tags/{quote(tag, safe='')}"
        params: dict[str, Any] = {}
        if tagging_type in ("artist", "album", "track"):
            params["tagging_type"] = tagging_type
        if page > 1:
            params["page"] = page
        resp = self._client.get(path, params=params or None)
        return self._client.format_result(
            parse_user_personal_tags(
                resp.text,
                url=str(resp.url),
                user=user,
                tag=tag,
                tagging_type=tagging_type,
                page=page,
                limit=limit,
            )
        )


class AsyncUserAPI:
    """Asynchronous `user.*` methods."""

    def __init__(self, client: AsyncLastFmClient) -> None:
        self._client = client

    async def get_info(self, user: str) -> Any:
        _require_cookies(self._client.has_cookies, "user.get_info")
        path = f"/user/{quote(user, safe='')}"
        resp = await self._client.get(path)
        return self._client.format_result(parse_user_info(resp.text, url=str(resp.url)))

    async def _get_recent_tracks_page(
        self,
        user: str,
        *,
        limit: int = 50,
        page: int = 1,
        from_ts: int | None = None,
        to_ts: int | None = None,
    ) -> RecentTracksPage:
        params = _date_range_params(
            from_ts, to_ts, has_cookies=self._client.has_cookies, method="user.get_recent_tracks"
        )
        if page > 1:
            params["page"] = page
        path = f"/user/{quote(user, safe='')}/library"
        resp = await self._client.get(path, params=params or None)
        return parse_user_recent_tracks(resp.text, url=str(resp.url), user=user, page=page, limit=limit)

    async def get_recent_tracks(
        self,
        user: str,
        *,
        limit: int = 50,
        page: int = 1,
        from_ts: int | None = None,
        to_ts: int | None = None,
    ) -> Any:
        return self._client.format_result(
            await self._get_recent_tracks_page(
                user, limit=limit, page=page, from_ts=from_ts, to_ts=to_ts
            )
        )

    def iter_recent_tracks(
        self,
        user: str,
        *,
        limit: int = 50,
        start_page: int = 1,
        max_pages: int | None = None,
    ) -> AsyncIterator[Any]:
        return aiter_paginated(
            lambda p: self._get_recent_tracks_page(user, limit=limit, page=p),
            lambda r: r.tracks,
            start_page=start_page,
            max_pages=max_pages,
            raw_json=self._client.raw_json,
        )

    async def get_top_artists(
        self, user: str, *, period: str = "overall", limit: int = 50, page: int = 1
    ) -> Any:
        date_preset = validate_period(
            period, method="user.get_top_artists", has_cookies=self._client.has_cookies
        )
        params: dict[str, Any] = {}
        if date_preset is not None:
            params["date_preset"] = date_preset
        if page > 1:
            params["page"] = page
        path = f"/user/{quote(user, safe='')}/library/artists"
        resp = await self._client.get(path, params=params or None)
        return self._client.format_result(
            parse_user_top_artists(resp.text, url=str(resp.url), user=user, page=page, limit=limit)
        )

    async def get_top_albums(
        self, user: str, *, period: str = "overall", limit: int = 50, page: int = 1
    ) -> Any:
        date_preset = validate_period(
            period, method="user.get_top_albums", has_cookies=self._client.has_cookies
        )
        params: dict[str, Any] = {}
        if date_preset is not None:
            params["date_preset"] = date_preset
        if page > 1:
            params["page"] = page
        path = f"/user/{quote(user, safe='')}/library/albums"
        resp = await self._client.get(path, params=params or None)
        return self._client.format_result(
            parse_user_top_albums(resp.text, url=str(resp.url), user=user, page=page, limit=limit)
        )

    async def get_top_tracks(
        self, user: str, *, period: str = "overall", limit: int = 50, page: int = 1
    ) -> Any:
        _require_cookies(self._client.has_cookies, "user.get_top_tracks")
        date_preset = validate_period(
            period, method="user.get_top_tracks", has_cookies=self._client.has_cookies
        )
        params: dict[str, Any] = {}
        if date_preset is not None:
            params["date_preset"] = date_preset
        if page > 1:
            params["page"] = page
        path = f"/user/{quote(user, safe='')}/library/tracks"
        resp = await self._client.get(path, params=params or None)
        return self._client.format_result(
            parse_user_top_tracks(resp.text, url=str(resp.url), user=user, page=page, limit=limit)
        )

    async def get_loved_tracks(self, user: str, *, limit: int = 50, page: int = 1) -> Any:
        _require_cookies(self._client.has_cookies, "user.get_loved_tracks")
        path = f"/user/{quote(user, safe='')}/loved"
        params = {"page": page} if page > 1 else None
        resp = await self._client.get(path, params=params)
        return self._client.format_result(
            parse_user_top_tracks(
                resp.text, url=str(resp.url), user=user, page=page, limit=limit, root_key="lovedtracks"
            )
        )

    async def get_top_tags(self, user: str, *, limit: int | None = None) -> Any:
        _require_cookies(self._client.has_cookies, "user.get_top_tags")
        path = f"/user/{quote(user, safe='')}/tags"
        resp = await self._client.get(path)
        return self._client.format_result(parse_user_top_tags(resp.text, url=str(resp.url), limit=limit))

    async def get_friends(self, user: str, *, limit: int = 50, page: int = 1) -> Any:
        path = f"/user/{quote(user, safe='')}/following"
        params = {"page": page} if page > 1 else None
        resp = await self._client.get(path, params=params)
        return self._client.format_result(
            parse_user_friends(resp.text, url=str(resp.url), user=user, page=page, limit=limit)
        )

    async def get_personal_tags(
        self,
        user: str,
        tag: str,
        *,
        tagging_type: str = "artist",
        limit: int = 50,
        page: int = 1,
    ) -> Any:
        path = f"/user/{quote(user, safe='')}/tags/{quote(tag, safe='')}"
        params: dict[str, Any] = {}
        if tagging_type in ("artist", "album", "track"):
            params["tagging_type"] = tagging_type
        if page > 1:
            params["page"] = page
        resp = await self._client.get(path, params=params or None)
        return self._client.format_result(
            parse_user_personal_tags(
                resp.text,
                url=str(resp.url),
                user=user,
                tag=tag,
                tagging_type=tagging_type,
                page=page,
                limit=limit,
            )
        )
