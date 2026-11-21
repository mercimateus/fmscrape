"""Typed dataclasses mirroring Last.fm API v2 JSON structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Image:
    """Last.fm image entry with size and URL."""

    url: str
    size: str

    def to_dict(self) -> dict[str, str]:
        return {"#text": self.url, "size": self.size}


@dataclass(slots=True)
class DateInfo:
    """Scrobble timestamp in UTC."""

    uts: int
    text: str

    def to_dict(self) -> dict[str, str]:
        return {"uts": str(self.uts), "#text": self.text}


@dataclass(slots=True)
class ArtistRef:
    """Compact artist reference embedded inside track/album responses."""

    name: str
    url: str = ""
    mbid: str = ""

    def to_dict(self) -> dict[str, str]:
        data: dict[str, str] = {"mbid": self.mbid, "#text": self.name}
        if self.url:
            data["url"] = self.url
        return data


@dataclass(slots=True)
class AlbumRef:
    """Compact album reference embedded inside track responses."""

    name: str
    url: str = ""
    mbid: str = ""

    def to_dict(self) -> dict[str, str]:
        data: dict[str, str] = {"mbid": self.mbid, "#text": self.name}
        if self.url:
            data["url"] = self.url
        return data


@dataclass(slots=True)
class PaginationAttr:
    """Pagination metadata matching Last.fm's `@attr` block."""

    page: int
    per_page: int
    total_pages: int
    total: int
    user: str | None = None
    tag: str | None = None
    artist: str | None = None

    def to_dict(self) -> dict[str, str]:
        data: dict[str, str] = {
            "page": str(self.page),
            "perPage": str(self.per_page),
            "totalPages": str(self.total_pages),
            "total": str(self.total),
        }
        if self.user is not None:
            data["user"] = self.user
        if self.tag is not None:
            data["tag"] = self.tag
        if self.artist is not None:
            data["artist"] = self.artist
        return data


@dataclass(slots=True)
class TagInfo:
    """Tag entry with name, URL, and optional count."""

    name: str
    url: str = ""
    count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"name": self.name, "url": self.url}
        if self.count is not None:
            data["count"] = self.count
        return data


@dataclass(slots=True)
class WikiInfo:
    """Wiki / biography block."""

    summary: str = ""
    content: str = ""
    published: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "published": self.published,
            "summary": self.summary,
            "content": self.content,
        }


@dataclass(slots=True)
class StatsInfo:
    """Listeners and playcount statistics."""

    listeners: int = 0
    playcount: int = 0

    def to_dict(self) -> dict[str, str]:
        return {
            "listeners": str(self.listeners),
            "playcount": str(self.playcount),
        }


@dataclass(slots=True)
class RecentTrack:
    """A track entry returned by `user.get_recent_tracks`."""

    name: str
    artist: ArtistRef
    album: AlbumRef
    url: str
    images: list[Image] = field(default_factory=list)
    date: DateInfo | None = None
    loved: bool = False
    now_playing: bool = False
    mbid: str = ""

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "artist": self.artist.to_dict(),
            "mbid": self.mbid,
            "name": self.name,
            "album": self.album.to_dict(),
            "url": self.url,
            "image": [img.to_dict() for img in self.images],
            "loved": "1" if self.loved else "0",
        }
        if self.now_playing:
            data["@attr"] = {"nowplaying": "true"}
        elif self.date is not None:
            data["date"] = self.date.to_dict()
        return data


@dataclass(slots=True)
class RecentTracksPage:
    """Paginated result for `user.get_recent_tracks`."""

    tracks: list[RecentTrack]
    attr: PaginationAttr

    def to_dict(self) -> dict[str, Any]:
        return {
            "recenttracks": {
                "track": [t.to_dict() for t in self.tracks],
                "@attr": self.attr.to_dict(),
            }
        }


@dataclass(slots=True)
class ArtistEntry:
    """Compact artist item used in top artists, similar artists, search, and charts."""

    name: str
    url: str = ""
    images: list[Image] = field(default_factory=list)
    playcount: int | None = None
    listeners: int | None = None
    rank: int | None = None
    mbid: str = ""

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "mbid": self.mbid,
            "url": self.url,
            "image": [img.to_dict() for img in self.images],
        }
        if self.playcount is not None:
            data["playcount"] = str(self.playcount)
        if self.listeners is not None:
            data["listeners"] = str(self.listeners)
        if self.rank is not None:
            data["@attr"] = {"rank": str(self.rank)}
        return data


@dataclass(slots=True)
class ArtistInfo:
    """Detailed artist info returned by `artist.get_info`."""

    name: str
    url: str
    images: list[Image] = field(default_factory=list)
    stats: StatsInfo = field(default_factory=StatsInfo)
    similar: list[ArtistEntry] = field(default_factory=list)
    tags: list[TagInfo] = field(default_factory=list)
    bio: WikiInfo = field(default_factory=WikiInfo)
    mbid: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "artist": {
                "name": self.name,
                "mbid": self.mbid,
                "url": self.url,
                "image": [img.to_dict() for img in self.images],
                "stats": self.stats.to_dict(),
                "similar": {"artist": [s.to_dict() for s in self.similar]},
                "tags": {"tag": [t.to_dict() for t in self.tags]},
                "bio": self.bio.to_dict(),
            }
        }


@dataclass(slots=True)
class AlbumEntry:
    """Compact album item used in top albums, tag albums, and search."""

    name: str
    artist: ArtistRef
    url: str = ""
    images: list[Image] = field(default_factory=list)
    playcount: int | None = None
    listeners: int | None = None
    rank: int | None = None
    mbid: str = ""

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "mbid": self.mbid,
            "url": self.url,
            "artist": {"name": self.artist.name, "mbid": self.artist.mbid, "url": self.artist.url},
            "image": [img.to_dict() for img in self.images],
        }
        if self.playcount is not None:
            data["playcount"] = str(self.playcount)
        if self.listeners is not None:
            data["listeners"] = str(self.listeners)
        if self.rank is not None:
            data["@attr"] = {"rank": str(self.rank)}
        return data


@dataclass(slots=True)
class TrackEntry:
    """Compact track item used in top tracks, similar tracks, search, album tracklists, and charts."""

    name: str
    artist: ArtistRef
    url: str = ""
    images: list[Image] = field(default_factory=list)
    duration: int | None = None
    playcount: int | None = None
    listeners: int | None = None
    rank: int | None = None
    mbid: str = ""

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "mbid": self.mbid,
            "url": self.url,
            "artist": {"name": self.artist.name, "mbid": self.artist.mbid, "url": self.artist.url},
            "image": [img.to_dict() for img in self.images],
        }
        if self.duration is not None:
            data["duration"] = str(self.duration)
        if self.playcount is not None:
            data["playcount"] = str(self.playcount)
        if self.listeners is not None:
            data["listeners"] = str(self.listeners)
        if self.rank is not None:
            data["@attr"] = {"rank": str(self.rank)}
        return data


@dataclass(slots=True)
class AlbumInfo:
    """Detailed album info returned by `album.get_info`."""

    name: str
    artist: str
    url: str
    images: list[Image] = field(default_factory=list)
    listeners: int = 0
    playcount: int = 0
    tracks: list[TrackEntry] = field(default_factory=list)
    tags: list[TagInfo] = field(default_factory=list)
    wiki: WikiInfo = field(default_factory=WikiInfo)
    release_date: str = ""
    mbid: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "album": {
                "name": self.name,
                "artist": self.artist,
                "mbid": self.mbid,
                "url": self.url,
                "image": [img.to_dict() for img in self.images],
                "listeners": str(self.listeners),
                "playcount": str(self.playcount),
                "tracks": {"track": [t.to_dict() for t in self.tracks]},
                "tags": {"tag": [t.to_dict() for t in self.tags]},
                "wiki": self.wiki.to_dict(),
            }
        }


@dataclass(slots=True)
class TrackInfo:
    """Detailed track info returned by `track.get_info`."""

    name: str
    artist: ArtistRef
    url: str
    duration: int = 0
    listeners: int = 0
    playcount: int = 0
    album: AlbumRef | None = None
    toptags: list[TagInfo] = field(default_factory=list)
    wiki: WikiInfo = field(default_factory=WikiInfo)
    mbid: str = ""

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "mbid": self.mbid,
            "url": self.url,
            "duration": str(self.duration),
            "listeners": str(self.listeners),
            "playcount": str(self.playcount),
            "artist": {"name": self.artist.name, "mbid": self.artist.mbid, "url": self.artist.url},
            "toptags": {"tag": [t.to_dict() for t in self.toptags]},
            "wiki": self.wiki.to_dict(),
        }
        if self.album is not None:
            data["album"] = {
                "artist": self.artist.name,
                "title": self.album.name,
                "mbid": self.album.mbid,
                "url": self.album.url,
            }
        return {"track": data}


@dataclass(slots=True)
class UserEntry:
    """User entry returned by `user.get_friends`."""

    name: str
    url: str
    images: list[Image] = field(default_factory=list)
    realname: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "realname": self.realname,
            "url": self.url,
            "image": [img.to_dict() for img in self.images],
        }


@dataclass(slots=True)
class UserInfo:
    """Detailed user profile returned by `user.get_info`."""

    name: str
    url: str
    realname: str = ""
    images: list[Image] = field(default_factory=list)
    playcount: int = 0
    artist_count: int = 0
    registered: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "user": {
                "name": self.name,
                "realname": self.realname,
                "url": self.url,
                "image": [img.to_dict() for img in self.images],
                "playcount": str(self.playcount),
                "artist_count": str(self.artist_count),
                "registered": {"#text": self.registered},
            }
        }


@dataclass(slots=True)
class TagDetails:
    """Tag info returned by `tag.get_info`."""

    name: str
    url: str
    wiki: WikiInfo = field(default_factory=WikiInfo)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tag": {
                "name": self.name,
                "url": self.url,
                "wiki": self.wiki.to_dict(),
            }
        }


@dataclass(slots=True)
class CorrectionResult:
    """Canonical correction result for `artist.get_correction` or `track.get_correction`."""

    name: str
    url: str
    artist_name: str | None = None
    artist_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        if self.artist_name is not None:
            return {
                "corrections": {
                    "correction": {
                        "track": {
                            "name": self.name,
                            "url": self.url,
                            "artist": {
                                "name": self.artist_name,
                                "url": self.artist_url or "",
                            },
                        }
                    }
                }
            }
        return {
            "corrections": {
                "correction": {
                    "artist": {
                        "name": self.name,
                        "url": self.url,
                    }
                }
            }
        }


@dataclass(slots=True)
class ArtistListPage:
    """Paginated artist list (topartists / artists / similarartists)."""

    artists: list[ArtistEntry]
    attr: PaginationAttr
    root_key: str = "topartists"

    def to_dict(self) -> dict[str, Any]:
        return {
            self.root_key: {
                "artist": [a.to_dict() for a in self.artists],
                "@attr": self.attr.to_dict(),
            }
        }


@dataclass(slots=True)
class AlbumListPage:
    """Paginated album list (topalbums / albums)."""

    albums: list[AlbumEntry]
    attr: PaginationAttr
    root_key: str = "topalbums"

    def to_dict(self) -> dict[str, Any]:
        return {
            self.root_key: {
                "album": [a.to_dict() for a in self.albums],
                "@attr": self.attr.to_dict(),
            }
        }


@dataclass(slots=True)
class TrackListPage:
    """Paginated track list (toptracks / tracks / similartracks)."""

    tracks: list[TrackEntry]
    attr: PaginationAttr
    root_key: str = "toptracks"

    def to_dict(self) -> dict[str, Any]:
        return {
            self.root_key: {
                "track": [t.to_dict() for t in self.tracks],
                "@attr": self.attr.to_dict(),
            }
        }


@dataclass(slots=True)
class FriendsPage:
    """Paginated user friends list."""

    friends: list[UserEntry]
    attr: PaginationAttr

    def to_dict(self) -> dict[str, Any]:
        return {
            "friends": {
                "user": [u.to_dict() for u in self.friends],
                "@attr": self.attr.to_dict(),
            }
        }


@dataclass(slots=True)
class TagsListResult:
    """List of tags returned by `*.get_top_tags` or `tag.get_similar`."""

    tags: list[TagInfo]
    root_key: str = "toptags"

    def to_dict(self) -> dict[str, Any]:
        return {self.root_key: {"tag": [t.to_dict() for t in self.tags]}}


@dataclass(slots=True)
class LibraryPlays:
    """User library playcount for a specific artist, album, or track."""

    user: str
    artist: str
    playcount: int
    url: str
    album: str | None = None
    track: str | None = None
    tracks: list[TrackEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "user": self.user,
            "artist": self.artist,
            "playcount": str(self.playcount),
            "url": self.url,
        }
        if self.album is not None:
            data["album"] = self.album
        if self.track is not None:
            data["track"] = self.track
        if self.tracks:
            data["tracks"] = {"track": [t.to_dict() for t in self.tracks]}
        return {"library": data}


@dataclass(slots=True)
class SearchResultsPage:
    """Search results wrapper matching Last.fm's `results` structure."""

    items: list[ArtistEntry] | list[AlbumEntry] | list[TrackEntry]
    attr: PaginationAttr
    match_key: str  # "artistmatches" | "albummatches" | "trackmatches"
    item_key: str   # "artist" | "album" | "track"

    def to_dict(self) -> dict[str, Any]:
        return {
            "results": {
                "opensearch:totalResults": str(self.attr.total),
                "opensearch:startIndex": str((self.attr.page - 1) * self.attr.per_page),
                "opensearch:itemsPerPage": str(self.attr.per_page),
                self.match_key: {
                    self.item_key: [item.to_dict() for item in self.items],
                },
            }
        }
