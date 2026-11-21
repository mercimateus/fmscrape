"""Parser for Last.fm user recent tracks page (/user/<username>/library)."""

from __future__ import annotations

from bs4 import BeautifulSoup, Tag

from fmscrape.errors import ParseError
from fmscrape.models import (
    AlbumRef,
    ArtistRef,
    DateInfo,
    Image,
    PaginationAttr,
    RecentTrack,
    RecentTracksPage,
)
from fmscrape.normalize import (
    absolute_url,
    expand_images,
    parse_int,
    parse_utc_timestamp,
)

# Isolated CSS selectors for /user/<user>/library
ROW_SELECTOR = "tr.chartlist-row:not(.chartlist__placeholder-row)"
TRACK_LINK_SELECTOR = "td.chartlist-name a"
PLAY_LINK_SELECTOR = "a.chartlist-play-button"
ARTIST_LINK_SELECTOR = "td.chartlist-artist a"
ALBUM_COVER_SELECTOR = "td.chartlist-image a.cover-art"
ALBUM_IMG_SELECTOR = "td.chartlist-image img"
LOVED_STATE_SELECTOR = "td.chartlist-loved [data-toggle-button-current-state]"
TIMESTAMP_SELECTOR = "td.chartlist-timestamp span[title], td.chartlist-timestamp a"
NOW_PLAYING_ROW_CLASS = "chartlist-row--now-scrobbling"
TOTAL_SCROBBLES_SELECTOR = ".metadata-display"
PAGINATION_PAGE_SELECTOR = ".pagination-page"


def _parse_images(row: Tag) -> list[Image]:
    img_el = row.select_one(ALBUM_IMG_SELECTOR)
    src = img_el.get("src") if img_el else None
    raw_src = src if isinstance(src, str) else None
    return [Image(url=item["#text"], size=item["size"]) for item in expand_images(raw_src)]


def _parse_row(row: Tag, *, url: str) -> RecentTrack:
    track_link = row.select_one(TRACK_LINK_SELECTOR)
    play_link = row.select_one(PLAY_LINK_SELECTOR)
    artist_link = row.select_one(ARTIST_LINK_SELECTOR)

    track_name = ""
    track_url = ""
    if track_link is not None:
        track_name = track_link.get_text(strip=True)
        href = track_link.get("href")
        track_url = absolute_url(href if isinstance(href, str) else "")
    elif play_link is not None:
        tn = play_link.get("data-track-name")
        tu = play_link.get("data-track-url")
        track_name = tn if isinstance(tn, str) else ""
        track_url = absolute_url(tu if isinstance(tu, str) else "")

    if not track_name:
        raise ParseError(
            "Could not extract track name from recent tracks row",
            url=url,
            selector=TRACK_LINK_SELECTOR,
        )

    artist_name = ""
    artist_url = ""
    if artist_link is not None:
        artist_name = artist_link.get_text(strip=True)
        ahref = artist_link.get("href")
        artist_url = absolute_url(ahref if isinstance(ahref, str) else "")
    elif play_link is not None:
        an = play_link.get("data-artist-name")
        au = play_link.get("data-artist-url")
        artist_name = an if isinstance(an, str) else ""
        artist_url = absolute_url(au if isinstance(au, str) else "")

    if not artist_name:
        raise ParseError(
            "Could not extract artist name from recent tracks row",
            url=url,
            selector=ARTIST_LINK_SELECTOR,
        )

    album_name = ""
    album_url = ""
    album_cover = row.select_one(ALBUM_COVER_SELECTOR)
    album_img = row.select_one(ALBUM_IMG_SELECTOR)
    if album_cover is not None:
        chref = album_cover.get("href")
        album_url = absolute_url(chref if isinstance(chref, str) else "")
    if album_img is not None:
        alt = album_img.get("alt")
        if isinstance(alt, str) and alt.strip():
            album_name = alt.strip()

    loved_el = row.select_one(LOVED_STATE_SELECTOR)
    loved = (
        loved_el is not None
        and loved_el.get("data-toggle-button-current-state") == "loved"
    )

    row_classes = row.get("class") or []
    ts_el = row.select_one(TIMESTAMP_SELECTOR)
    ts_title = ts_el.get("title") if ts_el else None
    ts_text = ts_el.get_text(strip=True) if ts_el else ""
    now_playing = (
        NOW_PLAYING_ROW_CLASS in row_classes
        or "scrobbling now" in ts_text.lower()
    )

    date_info: DateInfo | None = None
    if not now_playing:
        raw_date = ts_title if isinstance(ts_title, str) and ts_title.strip() else ts_text
        parsed_dt = parse_utc_timestamp(raw_date)
        if parsed_dt is not None:
            date_info = DateInfo(uts=parsed_dt[0], text=parsed_dt[1])

    return RecentTrack(
        name=track_name,
        artist=ArtistRef(name=artist_name, url=artist_url),
        album=AlbumRef(name=album_name, url=album_url),
        url=track_url,
        images=_parse_images(row),
        date=date_info,
        loved=loved,
        now_playing=now_playing,
    )


def _parse_total_pages(soup: BeautifulSoup, current_page: int) -> int:
    max_page = current_page
    for el in soup.select(PAGINATION_PAGE_SELECTOR):
        val = parse_int(el.get_text(strip=True))
        if val is not None and val > max_page:
            max_page = val
    return max_page


def _parse_total_scrobbles(soup: BeautifulSoup, row_count: int) -> int:
    el = soup.select_one(TOTAL_SCROBBLES_SELECTOR)
    if el is not None:
        val = parse_int(el.get_text(strip=True))
        if val is not None:
            return val
    return row_count


def parse_user_recent_tracks(
    html: str,
    *,
    url: str,
    user: str,
    page: int = 1,
    limit: int | None = None,
) -> RecentTracksPage:
    """Parse `/user/<user>/library` HTML into a `RecentTracksPage`."""
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select(ROW_SELECTOR)
    if not rows:
        # Check if it's genuinely an empty library or a broken page/layout
        if soup.select_one("section.library-scrobbles, .library-top-header, .chartlist") is None:
            raise ParseError(
                "Recent tracks table not found on page",
                url=url,
                selector=ROW_SELECTOR,
            )

    tracks = [_parse_row(row, url=url) for row in rows]
    if limit is not None and limit >= 0:
        tracks = tracks[:limit]

    total_pages = _parse_total_pages(soup, current_page=page)
    total = _parse_total_scrobbles(soup, row_count=len(tracks))
    per_page = limit if limit is not None else 50

    return RecentTracksPage(
        tracks=tracks,
        attr=PaginationAttr(
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            total=total,
            user=user,
        ),
    )

