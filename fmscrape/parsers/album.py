"""Parsers for Last.fm album pages (/music/<artist>/<album>, +tags, search)."""

from __future__ import annotations

from bs4 import BeautifulSoup

from fmscrape.errors import ParseError
from fmscrape.models import (
    AlbumEntry,
    AlbumInfo,
    ArtistRef,
    PaginationAttr,
    SearchResultsPage,
    TagsListResult,
    TrackEntry,
)
from fmscrape.normalize import absolute_url, parse_int
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
TRACK_ROW_SELECTOR = "tr.chartlist-row:not(.chartlist__placeholder-row)"
SEARCH_ITEM_SELECTOR = "li.album-result"


def parse_album_info(html: str, *, url: str) -> AlbumInfo:
    soup = BeautifulSoup(html, "lxml")
    title_el = soup.select_one(HEADER_TITLE_SELECTOR)
    if title_el is None:
        raise ParseError("Album title not found", url=url, selector=HEADER_TITLE_SELECTOR)
    name = title_el.get_text(strip=True)

    artist_el = soup.select_one(HEADER_ARTIST_SELECTOR)
    artist_name = artist_el.get_text(strip=True) if artist_el else ""

    canonical_el = soup.select_one('link[rel="canonical"]')
    canonical_href = canonical_el.get("href") if canonical_el else None
    canonical_url = canonical_href if isinstance(canonical_href, str) and canonical_href else url

    stats = parse_stats_intabbr(soup)
    tags = parse_tags(soup)
    wiki = parse_wiki(soup)

    release_date = ""
    for dt, dd in zip(
        soup.select(".catalogue-metadata-heading"),
        soup.select(".catalogue-metadata-description"),
    ):
        if "release" in dt.get_text(strip=True).lower():
            release_date = dd.get_text(strip=True)
            break

    tracks: list[TrackEntry] = []
    for idx, row in enumerate(soup.select(TRACK_ROW_SELECTOR), start=1):
        link = row.select_one("td.chartlist-name a")
        if link is None:
            continue
        href = link.get("href")
        dur_el = row.select_one("td.chartlist-duration")
        duration_sec = parse_duration_ms(dur_el.get_text(strip=True) if dur_el else None) // 1000
        rank_el = row.select_one("td.chartlist-index")
        rank = parse_int(rank_el.get_text(strip=True) if rank_el else None) or idx
        tracks.append(
            TrackEntry(
                name=link.get_text(strip=True),
                artist=ArtistRef(name=artist_name),
                url=absolute_url(href if isinstance(href, str) else ""),
                duration=duration_sec,
                rank=rank,
            )
        )

    cover = soup.select_one(".header-new-background-image, .cover-art img")
    images = images_from_element(cover) if cover is not None else images_from_element(None)

    return AlbumInfo(
        name=name,
        artist=artist_name,
        url=canonical_url,
        images=images,
        listeners=stats.listeners,
        playcount=stats.playcount,
        tracks=tracks,
        tags=tags,
        wiki=wiki,
        release_date=release_date,
    )


def parse_album_top_tags(html: str, *, url: str) -> TagsListResult:
    soup = BeautifulSoup(html, "lxml")
    if soup.select_one("h1") is None:
        raise ParseError("Album tags page invalid", url=url, selector="h1")
    return TagsListResult(tags=parse_tags(soup), root_key="toptags")


def parse_album_search(
    html: str,
    *,
    url: str,
    page: int = 1,
    limit: int | None = None,
) -> SearchResultsPage:
    soup = BeautifulSoup(html, "lxml")
    items = soup.select(SEARCH_ITEM_SELECTOR)
    if not items and soup.select_one("h1, .search-results") is None:
        raise ParseError("Album search results not found", url=url, selector=SEARCH_ITEM_SELECTOR)

    albums: list[AlbumEntry] = []
    for item in items:
        link = item.select_one("h4.album-result-heading a, a.link-block-target")
        if link is None:
            continue
        href = link.get("href")
        artist_el = item.select_one(".album-result-artist a")
        ahref = artist_el.get("href") if artist_el else None
        albums.append(
            AlbumEntry(
                name=link.get_text(strip=True),
                artist=ArtistRef(
                    name=artist_el.get_text(strip=True) if artist_el else "",
                    url=absolute_url(ahref if isinstance(ahref, str) else ""),
                ),
                url=absolute_url(href if isinstance(href, str) else ""),
                images=images_from_element(item),
            )
        )

    if limit is not None and limit >= 0:
        albums = albums[:limit]

    total_pages = parse_pagination_total(soup, page)
    per_page = limit if limit is not None else 30
    return SearchResultsPage(
        items=albums,
        attr=PaginationAttr(
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            total=total_pages * per_page,
        ),
        match_key="albummatches",
        item_key="album",
    )

