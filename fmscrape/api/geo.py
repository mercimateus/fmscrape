"""Geo API endpoints (`geo.*`) — unavailable on current public site."""

from __future__ import annotations

from typing import Any

from fmscrape.errors import NotSupportedError


class GeoAPI:
    """`geo.*` methods raise NotSupportedError as `/place/<country>/...` returns 404."""

    def get_top_artists(self, country: str, **kwargs: Any) -> Any:
        raise NotSupportedError(
            "geo.get_top_artists has no public equivalent on last.fm (/place/<country>/artists returns 404)."
        )

    def get_top_tracks(self, country: str, **kwargs: Any) -> Any:
        raise NotSupportedError(
            "geo.get_top_tracks has no public equivalent on last.fm (/place/<country>/tracks returns 404)."
        )

