"""Shared BeautifulSoup parsing helpers to avoid duplication across page parsers."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from fmscrape.models import Image, StatsInfo, TagInfo, WikiInfo
from fmscrape.normalize import absolute_url, expand_images, parse_int

PAGINATION_PAGE_SELECTOR = ".pagination-page"
INTABBR_SELECTOR = "abbr.intabbr"
TAG_LINK_SELECTOR = ".tags-list .tag a"
BIG_TAG_SELECTOR = ".big-tags-item"
WIKI_SELECTOR = ".wiki-content, .wiki-block-inner"
WIKI_AUTHOR_SELECTOR = ".wiki-author"

_DURATION_RE = re.compile(r"(\d+):(\d{2})")
_READ_MORE_RE = re.compile(r"\s*…?\s*read more\s*$", re.IGNORECASE)
_WIKI_DATE_RE = re.compile(r"\bon\s+(.+?)(?:\s*·|$)")


def images_from_element(el: Tag | None, *, img_selector: str = "img") -> list[Image]:
    """Extract and expand Last.fm images from a container element."""
    if el is None:
        raw_src = None
    else:
        img = el if el.name == "img" else el.select_one(img_selector)
        src = img.get("src") if img is not None else None
        raw_src = src if isinstance(src, str) else None
    return [Image(url=item["#text"], size=item["size"]) for item in expand_images(raw_src)]


def parse_pagination_total(soup: BeautifulSoup, current_page: int) -> int:
    """Return the highest page number visible in pagination controls."""
    max_page = current_page
    for el in soup.select(PAGINATION_PAGE_SELECTOR):
        val = parse_int(el.get_text(strip=True))
        if val is not None and val > max_page:
            max_page = val
    return max_page


def parse_stats_intabbr(soup: BeautifulSoup) -> StatsInfo:
    """Extract listeners and playcount from `<abbr class='intabbr' title='...'>`."""
    abbrs = soup.select(INTABBR_SELECTOR)
    listeners = 0
    playcount = 0
    if len(abbrs) >= 1:
        val = parse_int(str(abbrs[0].get("title") or abbrs[0].get_text(strip=True)))
        if val is not None:
            listeners = val
    if len(abbrs) >= 2:
        val = parse_int(str(abbrs[1].get("title") or abbrs[1].get_text(strip=True)))
        if val is not None:
            playcount = val
    return StatsInfo(listeners=listeners, playcount=playcount)


def parse_tags(soup: BeautifulSoup) -> list[TagInfo]:
    """Extract tags from `.big-tags-item` or `.tags-list .tag a`, deduplicated."""
    seen: set[str] = set()
    tags: list[TagInfo] = []

    big_items = soup.select(BIG_TAG_SELECTOR)
    if big_items:
        for item in big_items:
            link = item.select_one("h3 a, a.link-block-target")
            if link is None:
                continue
            name = link.get_text(strip=True)
            if not name or name.lower() in seen:
                continue
            seen.add(name.lower())
            href = link.get("href")
            tags.append(TagInfo(name=name, url=absolute_url(href if isinstance(href, str) else "")))
        if tags:
            return tags

    for link in soup.select(TAG_LINK_SELECTOR):
        name = link.get_text(strip=True)
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        href = link.get("href")
        tags.append(TagInfo(name=name, url=absolute_url(href if isinstance(href, str) else "")))
    return tags


def parse_wiki(soup: BeautifulSoup, *, is_full_page: bool = False) -> WikiInfo:
    """Extract summary/content/published text from wiki block."""
    el = soup.select_one(WIKI_SELECTOR)
    if el is None:
        return WikiInfo()
    if is_full_page:
        paragraphs = [p.get_text(" ", strip=True) for p in el.select("p") if p.get_text(strip=True)]
        content = "\n\n".join(paragraphs) if paragraphs else el.get_text(" ", strip=True)
        published = ""
        author_el = soup.select_one(WIKI_AUTHOR_SELECTOR)
        if author_el is not None:
            m = _WIKI_DATE_RE.search(author_el.get_text(" ", strip=True))
            if m:
                published = m.group(1).strip()
        return WikiInfo(summary="", content=content, published=published)

    raw_summary = _READ_MORE_RE.sub("", el.get_text(" ", strip=True)).strip()
    return WikiInfo(summary=raw_summary, content=raw_summary)


def parse_duration_ms(text: str | None) -> int:
    """Convert `mm:ss` duration text into milliseconds (Last.fm API format)."""
    if not text:
        return 0
    m = _DURATION_RE.search(text)
    if not m:
        return 0
    minutes, seconds = int(m.group(1)), int(m.group(2))
    return (minutes * 60 + seconds) * 1000

