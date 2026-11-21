# Last.fm Public HTML vs API v2 Mapping

## General Findings

1. **`robots.txt` (`https://www.last.fm/robots.txt`)**:
   - `Disallow: /search*`
   - `Disallow: /tag/*`
   - `Disallow: /music/*?` (affects `?page=N` pagination on `/music/{artist}/+albums`, `+tracks`, `+similar`)
   - `Disallow: /music/*/+tags*`
   - `Disallow: /login?next=/*`
   - Blocked locally when `respect_robots=True` (default); pass `respect_robots=False` to allow.
2. **Login Gate for Library Filters**:
   - `/user/{user}/library/artists` and `/user/{user}/library/albums` without parameters (`overall`) return `200 OK`.
   - `?date_preset=...` and `?from=...&to=...` redirect (`302`) to `/login?next=...` unless user cookies are provided.
3. **Anti-Bot Gate (Fastly Client Challenge / HTTP `600`)**:
   - Without session cookies, `/user/{user}`, `/user/{user}/library/tracks`, `/user/{user}/loved`, `/user/{user}/tags`, and `/user/{user}/followers` return HTTP `600` / JS `Client Challenge`.
   - With user-supplied cookies (`sessionid`, `csrftoken`, `fsuid`, `lfmanon=0`), all of these routes and date filters return `200 OK`.

## Endpoint Mapping

| Group | Method | Public URL | Pagination | Availability |
| :--- | :--- | :--- | :--- | :--- |
| `user` | `get_info` | `/user/{user}` | — | Requires cookies |
| `user` | `get_recent_tracks` | `/user/{user}/library` | `?page=N` | Public (`from_ts`/`to_ts` require cookies) |
| `user` | `get_top_artists` | `/user/{user}/library/artists` | `?page=N` | Public for `overall`; periods/ranges require cookies |
| `user` | `get_top_albums` | `/user/{user}/library/albums` | `?page=N` | Public for `overall`; periods/ranges require cookies |
| `user` | `get_top_tracks` | `/user/{user}/library/tracks` | `?page=N` | Requires cookies |
| `user` | `get_loved_tracks` | `/user/{user}/loved` | `?page=N` | Requires cookies |
| `user` | `get_top_tags` | `/user/{user}/tags` | — | Requires cookies |
| `user` | `get_friends` | `/user/{user}/following` | `?page=N` | Public |
| `user` | `get_weekly_artist_chart` | `/user/{user}/library/artists?from=...&to=...` | `?page=N` | Requires cookies |
| `user` | `get_weekly_album_chart` | `/user/{user}/library/albums?from=...&to=...` | `?page=N` | Requires cookies |
| `user` | `get_weekly_track_chart` | `/user/{user}/library/tracks?from=...&to=...` | `?page=N` | Requires cookies |
| `user` | `get_weekly_chart_list` | — | — | Unsupported |
| `user` | `get_personal_tags` | `/user/{user}/tags/{tag}` | `?page=N` | Public |
| `artist` | `get_info` | `/music/{artist}` + `/+wiki` | — | Public |
| `artist` | `get_similar` | `/music/{artist}/+similar` | `?page=N` | Public (`respect_robots=False` for `page>1`) |
| `artist` | `get_top_albums` | `/music/{artist}/+albums` | `?page=N` | Public (`respect_robots=False` for `page>1`) |
| `artist` | `get_top_tracks` | `/music/{artist}/+tracks` | `?page=N` | Public (`respect_robots=False` for `page>1`) |
| `artist` | `get_top_tags` | `/music/{artist}/+tags` | — | Requires `respect_robots=False` |
| `artist` | `get_correction` | `/music/{artist}` (HTTP redirect) | — | Public |
| `artist` | `search` | `/search/artists?q={query}` | `?page=N` | Requires `respect_robots=False` |
| `album` | `get_info` | `/music/{artist}/{album}` | — | Public |
| `album` | `get_top_tags` | `/music/{artist}/{album}/+tags` | — | Requires `respect_robots=False` |
| `album` | `search` | `/search/albums?q={query}` | `?page=N` | Requires `respect_robots=False` |
| `track` | `get_info` | `/music/{artist}/_/{track}` | — | Public |
| `track` | `get_similar` | `/music/{artist}/_/{track}` | — | Public |
| `track` | `get_top_tags` | `/music/{artist}/_/{track}/+tags` | — | Requires `respect_robots=False` |
| `track` | `get_correction` | `/music/{artist}/_/{track}` (HTTP redirect) | — | Public |
| `track` | `search` | `/search/tracks?q={query}` | `?page=N` | Requires `respect_robots=False` |
| `tag` | `get_info` | `/tag/{tag}` + `/wiki` | — | Requires `respect_robots=False` |
| `tag` | `get_similar` | `/tag/{tag}` | — | Requires `respect_robots=False` |
| `tag` | `get_top_artists` | `/tag/{tag}/artists` | `?page=N` | Requires `respect_robots=False` |
| `tag` | `get_top_albums` | `/tag/{tag}/albums` | `?page=N` | Requires `respect_robots=False` |
| `tag` | `get_top_tracks` | `/tag/{tag}/tracks` | `?page=N` | Requires `respect_robots=False` |
| `tag` | `get_top_tags` | `/music/+tags` (404) | — | Unsupported |
| `tag` | `get_weekly_chart_list` | — | — | Unsupported |
| `chart` | `get_top_artists` | `/charts/weekly` | `?page=N` | Public |
| `chart` | `get_top_tracks` | `/charts` | — | Public |
| `chart` | `get_top_tags` | — | — | Unsupported |
| `geo` | `get_top_artists` / `get_top_tracks` | `/place/{country}/...` (404) | — | Unsupported |
| `library` | `get_artists` | `/user/{user}/library/artists` | `?page=N` | Public (`overall`); filters require cookies |
| `library` | `get_artist_plays` / `get_album_plays` / `get_track_plays` | `/user/{user}/library/music/...` | — | Public (`overall`); filters require cookies |

