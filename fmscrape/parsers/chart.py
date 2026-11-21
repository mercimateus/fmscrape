"""Parsers for Last.fm global charts (/charts and /charts/weekly)."""

from __future__ import annotations

from bs4 import BeautifulSoup

from fmscrape.errors import ParseError
from fmscrape.models import (
    ArtistEntry,
    ArtistListPage,
    ArtistRef,
    PaginationAttr,
    TrackEntry,
    TrackListPage,
)
from fmscrape.normalize import absolute_url, parse_int
from fmscrape.parsers.common import images_from_element, parse_pagination_total

WEEKLY_ARTIST_ROW_SELECTOR = "table.weeklychart tr.weeklychart-item"
GLOBAL_CHART_ROW_SELECTOR = "table.globalchart tr.globalchart-item"


def parse_chart_top_artists(
    html: str,
    *,
    url: str,
    page: int = 1,
    limit: int | None = None,
) -> ArtistListPage:
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select(WEEKLY_ARTIST_ROW_SELECTOR)
    if not rows:
        rows = soup.select("table.globalchart tr.globalchart-item")
    if not rows:
        raise ParseError("Chart artists table not found", url=url, selector=WEEKLY_ARTIST_ROW_SELECTOR)

    artists: list[ArtistEntry] = []
    for idx, row in enumerate(rows, start=1):
        name_el = row.select_one("td.weeklychart-name a, td.globalchart-name a")
        if name_el is None:
            continue
        href = name_el.get("href")
        rank_el = row.select_one("td.weeklychart-rank, td.globalchart-rank")
        rank = parse_int(rank_el.get_text(strip=True) if rank_el else None) or ((page - 1) * 50 + idx)
        artists.append(
            ArtistEntry(
                name=name_el.get_text(strip=True),
                url=absolute_url(href if isinstance(href, str) else ""),
                images=images_from_element(row),
                rank=rank,
            )
        )

    if limit is not None and limit >= 0:
        artists = artists[:limit]

    total_pages = parse_pagination_total(soup, page)
    per_page = limit if limit is not None else max(len(artists), 1)
    return ArtistListPage(
        artists=artists,
        attr=PaginationAttr(
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            total=total_pages * per_page,
        ),
        root_key="artists",
    )


def parse_chart_top_tracks(
    html: str,
    *,
    url: str,
    limit: int | None = None,
) -> TrackListPage:
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select(GLOBAL_CHART_ROW_SELECTOR)
    if not rows:
        raise ParseError("Global chart tracks table not found", url=url, selector=GLOBAL_CHART_ROW_SELECTOR)

    tracks: list[TrackEntry] = []
    for idx, row in enumerate(rows, start=1):
        name_el = row.select_one("td.globalchart-name a")
        if name_el is None:
            continue
        href = name_el.get("href")
        artist_el = row.select_one("td.globalchart-track-artist-name a")
        ahref = artist_el.get("href") if artist_el else None
        rank_el = row.select_one("td.globalchart-rank")
        rank = parse_int(rank_el.get_text(strip=True) if rank_el else None) or idx
        tracks.append(
            TrackEntry(
                name=name_el.get_text(strip=True),
                artist=ArtistRef(
                    name=artist_el.get_text(strip=True) if artist_el else "",
                    url=absolute_url(ahref if isinstance(ahref, str) else ""),
                ),
                url=absolute_url(href if isinstance(href, str) else ""),
                images=images_from_element(row),
                rank=rank,
            )
        )

    if limit is not None and limit >= 0:
        tracks = tracks[:limit]

    return TrackListPage(
        tracks=tracks,
        attr=PaginationAttr(
            page=1,
            per_page=limit if limit is not None else len(tracks),
            total_pages=1,
            total=len(tracks),
        ),
        root_key="tracks",
    )

