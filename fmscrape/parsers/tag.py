"""Parsers for Last.fm tag pages (/tag/<tag>, /artists, /albums, /tracks)."""

from __future__ import annotations

from bs4 import BeautifulSoup

from fmscrape.errors import ParseError
from fmscrape.models import (
    AlbumEntry,
    AlbumListPage,
    ArtistEntry,
    ArtistListPage,
    ArtistRef,
    PaginationAttr,
    TagDetails,
    TagsListResult,
    TrackEntry,
    TrackListPage,
)
from fmscrape.normalize import absolute_url, parse_int
from fmscrape.parsers.common import (
    images_from_element,
    parse_pagination_total,
    parse_tags,
    parse_wiki,
)

ARTIST_ITEM_SELECTOR = ".big-artist-list-item"
ALBUM_ITEM_SELECTOR = ".resource-list--release-list-item"
TRACK_ROW_SELECTOR = "tr.chartlist-row:not(.chartlist__placeholder-row)"


def parse_tag_info(html: str, *, url: str, tag: str) -> TagDetails:
    soup = BeautifulSoup(html, "lxml")
    if soup.select_one("h1") is None:
        raise ParseError("Tag page invalid", url=url, selector="h1")
    return TagDetails(
        name=tag,
        url=url,
        wiki=parse_wiki(soup),
    )


def parse_tag_similar(html: str, *, url: str) -> TagsListResult:
    soup = BeautifulSoup(html, "lxml")
    if soup.select_one("h1") is None:
        raise ParseError("Tag page invalid", url=url, selector="h1")
    return TagsListResult(tags=parse_tags(soup), root_key="similartags")


def parse_tag_top_artists(
    html: str,
    *,
    url: str,
    tag: str,
    page: int = 1,
    limit: int | None = None,
) -> ArtistListPage:
    soup = BeautifulSoup(html, "lxml")
    items = soup.select(ARTIST_ITEM_SELECTOR)
    if not items and soup.select_one("h1") is None:
        raise ParseError("Tag top artists not found", url=url, selector=ARTIST_ITEM_SELECTOR)

    artists: list[ArtistEntry] = []
    for idx, item in enumerate(items, start=1):
        link = item.select_one("h3.big-artist-list-title a, a.link-block-target")
        if link is None:
            continue
        href = link.get("href")
        listeners_el = item.select_one(".big-artist-list-listeners")
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
            tag=tag,
        ),
        root_key="topartists",
    )


def parse_tag_top_albums(
    html: str,
    *,
    url: str,
    tag: str,
    page: int = 1,
    limit: int | None = None,
) -> AlbumListPage:
    soup = BeautifulSoup(html, "lxml")
    items = soup.select(ALBUM_ITEM_SELECTOR)
    if not items and soup.select_one("h1") is None:
        raise ParseError("Tag top albums not found", url=url, selector=ALBUM_ITEM_SELECTOR)

    albums: list[AlbumEntry] = []
    for idx, item in enumerate(items, start=1):
        link = item.select_one("h3.resource-list--release-list-item-name a")
        if link is None:
            continue
        href = link.get("href")
        artist_el = item.select_one(".resource-list--release-list-item-artist a")
        ahref = artist_el.get("href") if artist_el else None
        listeners_el = item.select_one(".resource-list--release-list-item-listeners")
        listeners = parse_int(listeners_el.get_text(strip=True) if listeners_el else None)
        albums.append(
            AlbumEntry(
                name=link.get_text(strip=True),
                artist=ArtistRef(
                    name=artist_el.get_text(strip=True) if artist_el else "",
                    url=absolute_url(ahref if isinstance(ahref, str) else ""),
                ),
                url=absolute_url(href if isinstance(href, str) else ""),
                images=images_from_element(item),
                listeners=listeners,
                rank=(page - 1) * 20 + idx,
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
            tag=tag,
        ),
        root_key="albums",
    )


def parse_tag_top_tracks(
    html: str,
    *,
    url: str,
    tag: str,
    page: int = 1,
    limit: int | None = None,
) -> TrackListPage:
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select(TRACK_ROW_SELECTOR)
    if not rows and soup.select_one("h1") is None:
        raise ParseError("Tag top tracks not found", url=url, selector=TRACK_ROW_SELECTOR)

    tracks: list[TrackEntry] = []
    for idx, row in enumerate(rows, start=1):
        name_el = row.select_one("td.chartlist-name a")
        if name_el is None:
            continue
        href = name_el.get("href")
        artist_el = row.select_one("td.chartlist-artist a")
        ahref = artist_el.get("href") if artist_el else None
        rank_el = row.select_one("td.chartlist-index")
        rank = parse_int(rank_el.get_text(strip=True) if rank_el else None) or ((page - 1) * 50 + idx)
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

    total_pages = parse_pagination_total(soup, page)
    per_page = limit if limit is not None else 50
    return TrackListPage(
        tracks=tracks,
        attr=PaginationAttr(
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            total=total_pages * per_page,
            tag=tag,
        ),
        root_key="tracks",
    )

