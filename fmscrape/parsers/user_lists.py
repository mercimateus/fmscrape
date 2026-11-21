"""Parsers for user library lists, friends, and personal tags."""

from __future__ import annotations

from bs4 import BeautifulSoup

from fmscrape.errors import ParseError
from fmscrape.models import (
    AlbumEntry,
    AlbumListPage,
    ArtistEntry,
    ArtistListPage,
    ArtistRef,
    FriendsPage,
    LibraryPlays,
    PaginationAttr,
    TagsListResult,
    TrackEntry,
    TrackListPage,
    UserEntry,
    UserInfo,
)
from fmscrape.normalize import absolute_url, parse_int
from fmscrape.parsers.common import images_from_element, parse_pagination_total, parse_tags

CHARTLIST_ROW_SELECTOR = "tr.chartlist-row:not(.chartlist__placeholder-row)"
NAME_LINK_SELECTOR = "td.chartlist-name a"
ARTIST_LINK_SELECTOR = "td.chartlist-artist a"
COUNT_BAR_SELECTOR = "td.chartlist-bar .chartlist-count-bar-value"
INDEX_SELECTOR = "td.chartlist-index"
USER_LIST_ITEM_SELECTOR = ".user-list-item"
USER_LIST_LINK_SELECTOR = ".user-list-name a"


def parse_user_top_artists(
    html: str,
    *,
    url: str,
    user: str,
    page: int = 1,
    limit: int | None = None,
) -> ArtistListPage:
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select(CHARTLIST_ROW_SELECTOR)
    if not rows and soup.select_one(".chartlist, .library-top-header") is None:
        raise ParseError("User top artists table not found", url=url, selector=CHARTLIST_ROW_SELECTOR)

    artists: list[ArtistEntry] = []
    for idx, row in enumerate(rows, start=1):
        name_el = row.select_one(NAME_LINK_SELECTOR)
        if name_el is None:
            raise ParseError("Missing artist name link", url=url, selector=NAME_LINK_SELECTOR)
        name = name_el.get_text(strip=True)
        href = name_el.get("href")
        count_el = row.select_one(COUNT_BAR_SELECTOR)
        playcount = parse_int(count_el.get_text(strip=True) if count_el else None)
        rank_el = row.select_one(INDEX_SELECTOR)
        rank = parse_int(rank_el.get_text(strip=True) if rank_el else None) or ((page - 1) * 50 + idx)
        artists.append(
            ArtistEntry(
                name=name,
                url=absolute_url(href if isinstance(href, str) else ""),
                images=images_from_element(row),
                playcount=playcount or 0,
                rank=rank,
            )
        )

    if limit is not None and limit >= 0:
        artists = artists[:limit]

    total_pages = parse_pagination_total(soup, page)
    per_page = limit if limit is not None else 50
    return ArtistListPage(
        artists=artists,
        attr=PaginationAttr(
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            total=total_pages * per_page,
            user=user,
        ),
        root_key="topartists",
    )


def parse_user_top_albums(
    html: str,
    *,
    url: str,
    user: str,
    page: int = 1,
    limit: int | None = None,
) -> AlbumListPage:
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select(CHARTLIST_ROW_SELECTOR)
    if not rows and soup.select_one(".chartlist, .library-top-header") is None:
        raise ParseError("User top albums table not found", url=url, selector=CHARTLIST_ROW_SELECTOR)

    albums: list[AlbumEntry] = []
    for idx, row in enumerate(rows, start=1):
        name_el = row.select_one(NAME_LINK_SELECTOR)
        artist_el = row.select_one(ARTIST_LINK_SELECTOR)
        if name_el is None:
            raise ParseError("Missing album name link", url=url, selector=NAME_LINK_SELECTOR)
        name = name_el.get_text(strip=True)
        href = name_el.get("href")
        artist_name = artist_el.get_text(strip=True) if artist_el else ""
        artist_href = artist_el.get("href") if artist_el else None
        count_el = row.select_one(COUNT_BAR_SELECTOR)
        playcount = parse_int(count_el.get_text(strip=True) if count_el else None)
        rank_el = row.select_one(INDEX_SELECTOR)
        rank = parse_int(rank_el.get_text(strip=True) if rank_el else None) or ((page - 1) * 50 + idx)
        albums.append(
            AlbumEntry(
                name=name,
                artist=ArtistRef(
                    name=artist_name,
                    url=absolute_url(artist_href if isinstance(artist_href, str) else ""),
                ),
                url=absolute_url(href if isinstance(href, str) else ""),
                images=images_from_element(row),
                playcount=playcount or 0,
                rank=rank,
            )
        )

    if limit is not None and limit >= 0:
        albums = albums[:limit]

    total_pages = parse_pagination_total(soup, page)
    per_page = limit if limit is not None else 50
    return AlbumListPage(
        albums=albums,
        attr=PaginationAttr(
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            total=total_pages * per_page,
            user=user,
        ),
        root_key="topalbums",
    )


def parse_user_friends(
    html: str,
    *,
    url: str,
    user: str,
    page: int = 1,
    limit: int | None = None,
) -> FriendsPage:
    soup = BeautifulSoup(html, "lxml")
    items = soup.select(USER_LIST_ITEM_SELECTOR)
    if not items and soup.select_one(".user-list, .content-top") is None:
        raise ParseError("User friends list not found", url=url, selector=USER_LIST_ITEM_SELECTOR)

    friends: list[UserEntry] = []
    for item in items:
        link = item.select_one(USER_LIST_LINK_SELECTOR)
        if link is None:
            continue
        name = link.get_text(strip=True)
        href = link.get("href")
        real_el = item.select_one(".user-list-description p")
        friends.append(
            UserEntry(
                name=name,
                url=absolute_url(href if isinstance(href, str) else ""),
                images=images_from_element(item),
                realname=real_el.get_text(strip=True) if real_el else "",
            )
        )

    if limit is not None and limit >= 0:
        friends = friends[:limit]

    total_pages = parse_pagination_total(soup, page)
    per_page = limit if limit is not None else max(len(friends), 1)
    return FriendsPage(
        friends=friends,
        attr=PaginationAttr(
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            total=total_pages * per_page,
            user=user,
        ),
    )


def parse_user_personal_tags(
    html: str,
    *,
    url: str,
    user: str,
    tag: str,
    tagging_type: str = "artist",
    page: int = 1,
    limit: int | None = None,
) -> ArtistListPage | AlbumListPage | TrackListPage:
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select(CHARTLIST_ROW_SELECTOR)
    if not rows and soup.select_one(".chartlist, .content-top") is None:
        raise ParseError("Personal tags table not found", url=url, selector=CHARTLIST_ROW_SELECTOR)

    total_pages = parse_pagination_total(soup, page)
    per_page = limit if limit is not None else 20

    if tagging_type == "album":
        albums: list[AlbumEntry] = []
        for row in rows:
            name_el = row.select_one(NAME_LINK_SELECTOR)
            if name_el is None:
                continue
            artist_el = row.select_one(ARTIST_LINK_SELECTOR)
            href = name_el.get("href")
            ahref = artist_el.get("href") if artist_el else None
            albums.append(
                AlbumEntry(
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
            albums = albums[:limit]
        return AlbumListPage(
            albums=albums,
            attr=PaginationAttr(page=page, per_page=per_page, total_pages=total_pages, total=len(albums), user=user, tag=tag),
            root_key="taggings",
        )

    if tagging_type == "track":
        tracks: list[TrackEntry] = []
        for row in rows:
            name_el = row.select_one(NAME_LINK_SELECTOR)
            if name_el is None:
                continue
            artist_el = row.select_one(ARTIST_LINK_SELECTOR)
            href = name_el.get("href")
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
        return TrackListPage(
            tracks=tracks,
            attr=PaginationAttr(page=page, per_page=per_page, total_pages=total_pages, total=len(tracks), user=user, tag=tag),
            root_key="taggings",
        )

    artists: list[ArtistEntry] = []
    for row in rows:
        name_el = row.select_one(NAME_LINK_SELECTOR)
        if name_el is None:
            continue
        href = name_el.get("href")
        artists.append(
            ArtistEntry(
                name=name_el.get_text(strip=True),
                url=absolute_url(href if isinstance(href, str) else ""),
                images=images_from_element(row),
            )
        )
    if limit is not None and limit >= 0:
        artists = artists[:limit]
    return ArtistListPage(
        artists=artists,
        attr=PaginationAttr(page=page, per_page=per_page, total_pages=total_pages, total=len(artists), user=user, tag=tag),
        root_key="taggings",
    )


def parse_user_info(html: str, *, url: str) -> UserInfo:
    """Parse `/user/<username>` profile page into `UserInfo`."""
    soup = BeautifulSoup(html, "lxml")
    title_el = soup.select_one("h1.header-title, h1")
    if title_el is None:
        raise ParseError("User profile title not found", url=url, selector="h1.header-title, h1")
    name = title_el.get_text(strip=True)

    realname = ""
    registered = ""
    sec_el = soup.select_one(".header-title-secondary")
    if sec_el is not None:
        sec_text = sec_el.get_text(" ", strip=True)
        if "scrobbling since" in sec_text:
            parts = sec_text.split("scrobbling since", 1)
            registered = parts[1].strip()
            realname = parts[0].replace("•", "").strip()
        else:
            realname = sec_text

    playcount = 0
    artist_count = 0
    for item in soup.select(".header-metadata-item"):
        text = item.get_text(" ", strip=True).lower()
        val = parse_int(text)
        if val is None:
            continue
        if "scrobble" in text:
            playcount = val
        elif "artist" in text:
            artist_count = val

    avatar = soup.select_one(".header-avatar")
    return UserInfo(
        name=name,
        url=url,
        realname=realname,
        images=images_from_element(avatar),
        playcount=playcount,
        artist_count=artist_count,
        registered=registered,
    )


def parse_user_top_tracks(
    html: str,
    *,
    url: str,
    user: str,
    page: int = 1,
    limit: int | None = None,
    root_key: str = "toptracks",
) -> TrackListPage:
    """Parse `/user/<user>/library/tracks` or `/user/<user>/loved` into `TrackListPage`."""
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select(CHARTLIST_ROW_SELECTOR)
    if not rows and soup.select_one(".chartlist, .library-top-header, h1") is None:
        raise ParseError("User tracks table not found", url=url, selector=CHARTLIST_ROW_SELECTOR)

    tracks: list[TrackEntry] = []
    for idx, row in enumerate(rows, start=1):
        name_el = row.select_one(NAME_LINK_SELECTOR)
        if name_el is None:
            continue
        href = name_el.get("href")
        artist_el = row.select_one(ARTIST_LINK_SELECTOR)
        ahref = artist_el.get("href") if artist_el else None
        count_el = row.select_one(COUNT_BAR_SELECTOR)
        playcount = parse_int(count_el.get_text(strip=True) if count_el else None)
        rank_el = row.select_one(INDEX_SELECTOR)
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
                playcount=playcount,
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
            user=user,
        ),
        root_key=root_key,
    )


def parse_user_top_tags(html: str, *, url: str, limit: int | None = None) -> TagsListResult:
    """Parse `/user/<user>/tags` into `TagsListResult`."""
    soup = BeautifulSoup(html, "lxml")
    if soup.select_one("h1") is None:
        raise ParseError("User tags page invalid", url=url, selector="h1")
    tags = parse_tags(soup)
    if limit is not None and limit >= 0:
        tags = tags[:limit]
    return TagsListResult(tags=tags, root_key="toptags")


def parse_library_plays(
    html: str,
    *,
    url: str,
    user: str,
    artist: str,
    album: str | None = None,
    track: str | None = None,
) -> LibraryPlays:
    """Parse `/user/<user>/library/music/<artist>[/<album>|/_/<track>]` into `LibraryPlays`."""
    soup = BeautifulSoup(html, "lxml")
    if soup.select_one("h1, .metadata-item, .metadata-display") is None:
        raise ParseError("Library plays page invalid", url=url, selector=".metadata-item")

    playcount = 0
    for item in soup.select(".metadata-item"):
        text = item.get_text(" ", strip=True).lower()
        if "scrobble" in text:
            val = parse_int(text)
            if val is not None:
                playcount = val
                break
    if playcount == 0:
        disp = soup.select_one(".metadata-display")
        if disp is not None:
            val = parse_int(disp.get_text(strip=True))
            if val is not None:
                playcount = val

    tracks: list[TrackEntry] = []
    if track is None:
        for idx, row in enumerate(soup.select(CHARTLIST_ROW_SELECTOR), start=1):
            name_el = row.select_one(NAME_LINK_SELECTOR)
            if name_el is None:
                continue
            href = name_el.get("href")
            count_el = row.select_one(COUNT_BAR_SELECTOR)
            t_plays = parse_int(count_el.get_text(strip=True) if count_el else None)
            rank_el = row.select_one(INDEX_SELECTOR)
            rank = parse_int(rank_el.get_text(strip=True) if rank_el else None) or idx
            tracks.append(
                TrackEntry(
                    name=name_el.get_text(strip=True),
                    artist=ArtistRef(name=artist),
                    url=absolute_url(href if isinstance(href, str) else ""),
                    images=images_from_element(row),
                    playcount=t_plays,
                    rank=rank,
                )
            )

    return LibraryPlays(
        user=user,
        artist=artist,
        album=album,
        track=track,
        playcount=playcount,
        url=url,
        tracks=tracks,
    )
