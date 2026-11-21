"""Parsers for Last.fm artist pages (/music/<artist>, +similar, +albums, +tracks, +tags, search)."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from fmscrape.errors import ParseError
from fmscrape.models import (
    AlbumEntry,
    AlbumListPage,
    ArtistEntry,
    ArtistInfo,
    ArtistListPage,
    ArtistRef,
    PaginationAttr,
    SearchResultsPage,
    TagsListResult,
    TrackEntry,
    TrackListPage,
)
from fmscrape.normalize import absolute_url, expand_images, parse_int
from fmscrape.parsers.common import (
    images_from_element,
    parse_pagination_total,
    parse_stats_intabbr,
    parse_tags,
    parse_wiki,
)

HEADER_TITLE_SELECTOR = "h1.header-new-title, h1.header-title, h1"
SIMILAR_ITEM_SELECTOR = ".similar-artists-item"
SIMILAR_SIDEBAR_SELECTOR = ".artist-similar-artists-sidebar-item"
ALBUM_ITEM_SELECTOR = ".resource-list--release-list-item"
TRACK_ROW_SELECTOR = "tr.chartlist-row:not(.chartlist__placeholder-row)"
SEARCH_ITEM_SELECTOR = "li.artist-result"

_BG_URL_RE = re.compile(r"url\((['\"]?)(.*?)\1\)")


def _extract_header_images(soup: BeautifulSoup) -> list[dict[str, str]]:
    bg = soup.select_one(".header-new-background-image")
    if bg is not None:
        style = bg.get("style")
        if isinstance(style, str):
            m = _BG_URL_RE.search(style)
            if m:
                return expand_images(m.group(2))
    og = soup.select_one('meta[property="og:image"]')
    if og is not None:
        content = og.get("content")
        if isinstance(content, str):
            return expand_images(content)
    return expand_images(None)


def parse_artist_info(html: str, *, url: str) -> ArtistInfo:
    soup = BeautifulSoup(html, "lxml")
    title_el = soup.select_one(HEADER_TITLE_SELECTOR)
    if title_el is None:
        raise ParseError("Artist title not found", url=url, selector=HEADER_TITLE_SELECTOR)
    name = title_el.get_text(strip=True)

    canonical_el = soup.select_one('link[rel="canonical"]')
    canonical_href = canonical_el.get("href") if canonical_el else None
    canonical_url = canonical_href if isinstance(canonical_href, str) and canonical_href else url

    from fmscrape.models import Image

    images = [Image(url=i["#text"], size=i["size"]) for i in _extract_header_images(soup)]
    stats = parse_stats_intabbr(soup)
    tags = parse_tags(soup)
    wiki = parse_wiki(soup)

    similar: list[ArtistEntry] = []
    for item in soup.select(f"{SIMILAR_SIDEBAR_SELECTOR}, {SIMILAR_ITEM_SELECTOR}"):
        link = item.select_one("h3 a, .artist-similar-artists-sidebar-item-name a, a.link-block-target")
        if link is None:
            continue
        href = link.get("href")
        similar.append(
            ArtistEntry(
                name=link.get_text(strip=True),
                url=absolute_url(href if isinstance(href, str) else ""),
                images=images_from_element(item),
            )
        )

    return ArtistInfo(
        name=name,
        url=canonical_url,
        images=images,
        stats=stats,
        similar=similar,
        tags=tags,
        bio=wiki,
    )


def parse_artist_similar(
    html: str,
    *,
    url: str,
    artist: str,
    page: int = 1,
    limit: int | None = None,
) -> ArtistListPage:
    soup = BeautifulSoup(html, "lxml")
    items = soup.select(SIMILAR_ITEM_SELECTOR)
    if not items and soup.select_one("h1") is None:
        raise ParseError("Similar artists list not found", url=url, selector=SIMILAR_ITEM_SELECTOR)

    artists: list[ArtistEntry] = []
    for idx, item in enumerate(items, start=1):
        link = item.select_one("h3.similar-artists-item-name a, a.link-block-target")
        if link is None:
            continue
        href = link.get("href")
        listeners_el = item.select_one(".similar-artists-item-listeners")
        listeners = parse_int(listeners_el.get_text(strip=True) if listeners_el else None)
        artists.append(
            ArtistEntry(
                name=link.get_text(strip=True),
                url=absolute_url(href if isinstance(href, str) else ""),
                images=images_from_element(item),
                listeners=listeners,
                rank=(page - 1) * 20 + idx,
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
            artist=artist,
        ),
        root_key="similarartists",
    )


def parse_artist_top_albums(
    html: str,
    *,
    url: str,
    artist: str,
    page: int = 1,
    limit: int | None = None,
) -> AlbumListPage:
    soup = BeautifulSoup(html, "lxml")
    items = soup.select(ALBUM_ITEM_SELECTOR)
    if not items and soup.select_one("h1") is None:
        raise ParseError("Artist albums list not found", url=url, selector=ALBUM_ITEM_SELECTOR)

    albums: list[AlbumEntry] = []
    for idx, item in enumerate(items, start=1):
        link = item.select_one("h3.resource-list--release-list-item-name a")
        if link is None:
            continue
        href = link.get("href")
        listeners_el = item.select_one(".resource-list--release-list-item-listeners")
        listeners = parse_int(listeners_el.get_text(strip=True) if listeners_el else None)
        albums.append(
            AlbumEntry(
                name=link.get_text(strip=True),
                artist=ArtistRef(name=artist),
                url=absolute_url(href if isinstance(href, str) else ""),
                images=images_from_element(item),
                listeners=listeners,
                playcount=listeners,
                rank=(page - 1) * 24 + idx,
            )
        )

    if limit is not None and limit >= 0:
        albums = albums[:limit]

    total_pages = parse_pagination_total(soup, page)
    per_page = limit if limit is not None else max(len(albums), 1)
    return AlbumListPage(
        albums=albums,
        attr=PaginationAttr(
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            total=total_pages * per_page,
            artist=artist,
        ),
        root_key="topalbums",
    )


def parse_artist_top_tracks(
    html: str,
    *,
    url: str,
    artist: str,
    page: int = 1,
    limit: int | None = None,
) -> TrackListPage:
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select(TRACK_ROW_SELECTOR)
    if not rows and soup.select_one("h1") is None:
        raise ParseError("Artist tracks table not found", url=url, selector=TRACK_ROW_SELECTOR)

    tracks: list[TrackEntry] = []
    for idx, row in enumerate(rows, start=1):
        name_el = row.select_one("td.chartlist-name a")
        if name_el is None:
            continue
        href = name_el.get("href")
        count_el = row.select_one("td.chartlist-bar .chartlist-count-bar-value")
        listeners = parse_int(count_el.get_text(strip=True) if count_el else None)
        rank_el = row.select_one("td.chartlist-index")
        rank = parse_int(rank_el.get_text(strip=True) if rank_el else None) or ((page - 1) * 50 + idx)
        tracks.append(
            TrackEntry(
                name=name_el.get_text(strip=True),
                artist=ArtistRef(name=artist),
                url=absolute_url(href if isinstance(href, str) else ""),
                images=images_from_element(row),
                listeners=listeners,
                playcount=listeners,
                rank=rank,
            )
        )

    if limit is not None and limit >= 0:
        tracks = tracks[:limit]

    total_pages = parse_pagination_total(soup, page)
    per_page = limit if limit is not None else 50
    return TrackListPage(
        tracks=tracks,
        attr=PaginationAttr(
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            total=total_pages * per_page,
            artist=artist,
        ),
        root_key="toptracks",
    )


def parse_artist_top_tags(html: str, *, url: str) -> TagsListResult:
    soup = BeautifulSoup(html, "lxml")
    if soup.select_one("h1") is None:
        raise ParseError("Artist tags page invalid", url=url, selector="h1")
    return TagsListResult(tags=parse_tags(soup), root_key="toptags")


def parse_artist_search(
    html: str,
    *,
    url: str,
    page: int = 1,
    limit: int | None = None,
) -> SearchResultsPage:
    soup = BeautifulSoup(html, "lxml")
    items = soup.select(SEARCH_ITEM_SELECTOR)
    if not items and soup.select_one("h1, .search-results") is None:
        raise ParseError("Artist search results not found", url=url, selector=SEARCH_ITEM_SELECTOR)

    artists: list[ArtistEntry] = []
    for item in items:
        link = item.select_one("h4.artist-result-heading a, a.link-block-target")
        if link is None:
            continue
        href = link.get("href")
        listeners_el = item.select_one(".artist-result-listeners")
        listeners = parse_int(listeners_el.get_text(strip=True) if listeners_el else None)
        artists.append(
            ArtistEntry(
                name=link.get_text(strip=True),
                url=absolute_url(href if isinstance(href, str) else ""),
                images=images_from_element(item),
                listeners=listeners,
            )
        )

    if limit is not None and limit >= 0:
        artists = artists[:limit]

    total_pages = parse_pagination_total(soup, page)
    per_page = limit if limit is not None else 20
    return SearchResultsPage(
        items=artists,
        attr=PaginationAttr(
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            total=total_pages * per_page,
        ),
        match_key="artistmatches",
        item_key="artist",
    )
