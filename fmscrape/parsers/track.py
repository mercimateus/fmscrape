"""Parsers for Last.fm track pages (/music/<artist>/_/<track>, +tags, search)."""

from __future__ import annotations

from bs4 import BeautifulSoup

from fmscrape.errors import ParseError
from fmscrape.models import (
    AlbumRef,
    ArtistRef,
    PaginationAttr,
    SearchResultsPage,
    TagsListResult,
    TrackEntry,
    TrackInfo,
    TrackListPage,
)
from fmscrape.normalize import absolute_url
from fmscrape.parsers.common import (
    images_from_element,
    parse_duration_ms,
    parse_pagination_total,
    parse_stats_intabbr,
    parse_tags,
    parse_wiki,
)

HEADER_TITLE_SELECTOR = "h1.header-new-title, h1.header-title, h1"
HEADER_ARTIST_SELECTOR = ".header-new-crumb a, .header-title-secondary a"
SIMILAR_TRACK_SELECTOR = ".track-similar-tracks-item, .similar-tracks-item"
SEARCH_ROW_SELECTOR = "tr.chartlist-row:not(.chartlist__placeholder-row)"


def parse_track_info(html: str, *, url: str) -> TrackInfo:
    soup = BeautifulSoup(html, "lxml")
    title_el = soup.select_one(HEADER_TITLE_SELECTOR)
    if title_el is None:
        raise ParseError("Track title not found", url=url, selector=HEADER_TITLE_SELECTOR)
    name = title_el.get_text(strip=True)

    artist_el = soup.select_one(HEADER_ARTIST_SELECTOR)
    artist_name = artist_el.get_text(strip=True) if artist_el else ""
    artist_href = artist_el.get("href") if artist_el else None

    canonical_el = soup.select_one('link[rel="canonical"]')
    canonical_href = canonical_el.get("href") if canonical_el else None
    canonical_url = canonical_href if isinstance(canonical_href, str) and canonical_href else url

    stats = parse_stats_intabbr(soup)
    tags = parse_tags(soup)
    wiki = parse_wiki(soup)

    duration_ms = 0
    for dt, dd in zip(
        soup.select(".catalogue-metadata-heading"),
        soup.select(".catalogue-metadata-description"),
    ):
        if "length" in dt.get_text(strip=True).lower():
            duration_ms = parse_duration_ms(dd.get_text(strip=True))
            break

    album_ref: AlbumRef | None = None
    album_el = soup.select_one(".featured-item-heading a, .source-album-name a")
    if album_el is not None:
        ahref = album_el.get("href")
        album_ref = AlbumRef(
            name=album_el.get_text(strip=True),
            url=absolute_url(ahref if isinstance(ahref, str) else ""),
        )

    return TrackInfo(
        name=name,
        artist=ArtistRef(
            name=artist_name,
            url=absolute_url(artist_href if isinstance(artist_href, str) else ""),
        ),
        url=canonical_url,
        duration=duration_ms,
        listeners=stats.listeners,
        playcount=stats.playcount,
        album=album_ref,
        toptags=tags,
        wiki=wiki,
    )


def parse_track_similar(
    html: str,
    *,
    url: str,
    artist: str,
    limit: int | None = None,
) -> TrackListPage:
    soup = BeautifulSoup(html, "lxml")
    if soup.select_one(HEADER_TITLE_SELECTOR) is None:
        raise ParseError("Track page invalid", url=url, selector=HEADER_TITLE_SELECTOR)

    tracks: list[TrackEntry] = []
    for idx, item in enumerate(soup.select(SIMILAR_TRACK_SELECTOR), start=1):
        name_el = item.select_one(".track-similar-tracks-item-name a, .similar-tracks-item-name a, h3 a")
        if name_el is None:
            continue
        href = name_el.get("href")
        artist_el = item.select_one(".track-similar-tracks-item-artist a, .similar-tracks-item-artist a")
        ahref = artist_el.get("href") if artist_el else None
        tracks.append(
            TrackEntry(
                name=name_el.get_text(strip=True),
                artist=ArtistRef(
                    name=artist_el.get_text(strip=True) if artist_el else artist,
                    url=absolute_url(ahref if isinstance(ahref, str) else ""),
                ),
                url=absolute_url(href if isinstance(href, str) else ""),
                images=images_from_element(item),
                rank=idx,
            )
        )

    if limit is not None and limit >= 0:
        tracks = tracks[:limit]

    return TrackListPage(
        tracks=tracks,
        attr=PaginationAttr(page=1, per_page=len(tracks) or 1, total_pages=1, total=len(tracks), artist=artist),
        root_key="similartracks",
    )


def parse_track_top_tags(html: str, *, url: str) -> TagsListResult:
    soup = BeautifulSoup(html, "lxml")
    if soup.select_one("h1") is None:
        raise ParseError("Track tags page invalid", url=url, selector="h1")
    return TagsListResult(tags=parse_tags(soup), root_key="toptags")


def parse_track_search(
    html: str,
    *,
    url: str,
    page: int = 1,
    limit: int | None = None,
) -> SearchResultsPage:
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select(SEARCH_ROW_SELECTOR)
    if not rows and soup.select_one("h1, .search-results") is None:
        raise ParseError("Track search results not found", url=url, selector=SEARCH_ROW_SELECTOR)

    tracks: list[TrackEntry] = []
    for row in rows:
        name_el = row.select_one("td.chartlist-name a")
        if name_el is None:
            continue
        href = name_el.get("href")
        artist_el = row.select_one("td.chartlist-artist a")
        ahref = artist_el.get("href") if artist_el else None
        tracks.append(
            TrackEntry(
                name=name_el.get_text(strip=True),
                artist=ArtistRef(
                    name=artist_el.get_text(strip=True) if artist_el else "",
                    url=absolute_url(ahref if isinstance(ahref, str) else ""),
                ),
                url=absolute_url(href if isinstance(href, str) else ""),
                images=images_from_element(row),
            )
        )

    if limit is not None and limit >= 0:
        tracks = tracks[:limit]

    total_pages = parse_pagination_total(soup, page)
    per_page = limit if limit is not None else 30
    return SearchResultsPage(
        items=tracks,
        attr=PaginationAttr(
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            total=total_pages * per_page,
        ),
        match_key="trackmatches",
        item_key="track",
    )

