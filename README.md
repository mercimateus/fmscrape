# fmscrape

Python library for reading public **Last.fm** data without an API key, with an interface compatible with the official Last.fm API v2. Returns JSON-ready `dict`s by default, or typed `dataclasses` when `raw_json=False`.

> **Disclaimer**: Use of this library is subject to Last.fm's Terms of Service. Data is parsed from public HTML pages on `last.fm`, so parsing may break if Last.fm changes its layout or access rules. This project is not affiliated with Last.fm.

## Installation

```bash
cd fmscrape
python -m venv --system-site-packages .venv
.\.venv\Scripts\activate
pip install -e .
```

> **Note**: Do not run scripts that `import fmscrape` from the parent directory containing the `fmscrape/` project folder, as Python will treat that folder as an empty namespace package. Run from inside `fmscrape/` or another directory.

## Usage

### Without Cookies

```python
import json
from fmscrape import LastFmClient

with LastFmClient(rate_limit=1.0, cache_ttl=60.0) as client:
    recent = client.user.get_recent_tracks("rj", limit=10)
    print(json.dumps(recent, indent=2, ensure_ascii=False))

    artist = client.artist.get_info("Radiohead")
    print(artist["artist"]["name"], artist["artist"]["stats"])

    for album in client.artist.iter_top_albums("Radiohead", max_pages=1):
        print(album["name"])

# Typed dataclasses instead of dicts
with LastFmClient(raw_json=False) as client:
    artist = client.artist.get_info("Radiohead")
    print(artist.name, artist.stats.listeners)
```

### With User Cookies

Some user endpoints (`/user/<user>`, `/library/tracks`, `/loved`, `/tags`, and `period` / `from_ts` / `to_ts` filters) require browser session cookies. Only these 4 cookies are required: `sessionid`, `csrftoken`, `fsuid`, and `lfmanon=0`.

```python
from fmscrape import LastFmClient

cookies = "sessionid=...; csrftoken=...; fsuid=...; lfmanon=0"
with LastFmClient(cookies=cookies) as client:
    profile = client.user.get_info("user")
    top_tracks = client.user.get_top_tracks("user", period="7day", page=2)

    # Unix GMT timestamp filters work across library endpoints
    artists_range = client.library.get_artists(
        "user", from_ts=1792324800, to_ts=1792929600
    )

    # Total plays for a specific album or track (with or without filters)
    album_plays = client.library.get_album_plays(
        "user", "Radiohead", "The Bends"
    )
    track_plays = client.library.get_track_plays(
        "user", "Radiohead", "High and Dry",
        from_ts=1792324800, to_ts=1792929600,
    )
    print(album_plays["library"]["playcount"], track_plays["library"]["playcount"])
```

### Async Client

```python
import asyncio
from fmscrape import AsyncLastFmClient

async def main() -> None:
    async with AsyncLastFmClient() as client:
        info = await client.album.get_info("Radiohead", "OK Computer")
        print(info["album"]["name"], len(info["album"]["tracks"]["track"]))

asyncio.run(main())
```

### `robots.txt`

By default, `respect_robots=True` enforces Last.fm's `robots.txt`, which disallows `/search*`, `/tag/*`, `/music/*/+tags*`, and `/music/*?`. Initialize with `LastFmClient(respect_robots=False)` if you need those routes.

## API Compatibility

See [docs/map.md](docs/map.md) for the full URL and field mapping.

| Group | Public | With User Cookies | Unsupported |
| :--- | :--- | :--- | :--- |
| `user` | `get_recent_tracks`, `get_top_artists` (`overall`), `get_top_albums` (`overall`), `get_friends`, `get_personal_tags` | `get_info`, `get_top_tracks`, `get_loved_tracks`, `get_top_tags`, `period` (`7day`–`12month`), `from_ts`/`to_ts`, `get_weekly_artist_chart`, `get_weekly_album_chart`, `get_weekly_track_chart` | `get_weekly_chart_list` |
| `artist` | `get_info`, `get_similar`, `get_top_albums`, `get_top_tracks`, `get_correction`, `get_top_tags`\*, `search`\* | Same | `add_tags`, `remove_tag` |
| `album` | `get_info`, `get_top_tags`\*, `search`\* | Same | `add_tags`, `remove_tag` |
| `track` | `get_info`, `get_similar`, `get_correction`, `get_top_tags`\*, `search`\* | Same | `scrobble`, `love`, `unlove`, `update_now_playing`, `add_tags`, `remove_tag` |
| `tag` | `get_info`\*, `get_similar`\*, `get_top_artists`\*, `get_top_albums`\*, `get_top_tracks`\* | Same | `get_top_tags`, `get_weekly_chart_list` |
| `chart` | `get_top_artists`, `get_top_tracks` | Same | `get_top_tags` |
| `geo` | — | — | `get_top_artists`, `get_top_tracks` |
| `library` | `get_artists` | Same | — |
| `auth` | — | — | `get_token`, `get_session`, `get_mobile_session` |

\* Disallowed in `robots.txt`; requires `respect_robots=False`.

## Tests

```bash
pytest -v
mypy fmscrape
pytest -m live
```
