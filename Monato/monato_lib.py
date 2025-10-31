# -*- coding: utf-8 -*-
"""
monato_lib.py

Utility helpers tailored to the MONATO website. The site predates WordPress, so
we cannot reuse the generic REST/feed/archive collectors. Instead we gather
article URLs from the public "Nova!" page plus historic yearly indexes, and
normalize the result into retradio_lib's data structures so that the existing
CLI flow keeps working.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, date
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

from retradio_lib import (  # type: ignore
    Article,
    ScrapeConfig,
    URLCollectionResult,
    _clean_text as base_clean_text,
    _session as shared_session,
    set_progress_callback,
)

USER_AGENT = "Mozilla/5.0 (compatible; MonatoScraper/1.0; +https://www.monato.be)"

MONATO_META: Dict[str, Dict[str, Optional[datetime]]] = {}


@dataclass
class _CollectedEntry:
    url: str
    title: str
    published: Optional[datetime]
    category: Optional[str]
    section: Optional[str]
    author_hint: Optional[str]


def _clean_space(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\b([A-Z])\s+([A-Z]{2,})\b", r"\1\2", text)
    return text.strip()


def _parse_issue_date(raw: str) -> Optional[datetime]:
    if not raw:
        return None
    m = re.search(r"(\d{4})/(\d{2})(?:-(\d{2}))?", raw)
    if not m:
        return None
    year = int(m.group(1))
    month = int(m.group(2))
    try:
        return datetime(year, month, 1)
    except ValueError:
        return None


def _iter_prefix_text(li: Tag) -> str:
    pieces: List[str] = []
    for child in li.children:
        if isinstance(child, Tag) and child.name == "a":
            break
        if isinstance(child, Tag):
            pieces.append(child.get_text(" ", strip=True))
        else:
            pieces.append(str(child))
    return _clean_space("".join(pieces))


def _collect_from_year(year: int, cfg: ScrapeConfig, session: requests.Session) -> List[_CollectedEntry]:
    base = cfg.base_url.rstrip("/")
    url = f"{base}/{year}/index.php?p"
    resp = session.get(url, timeout=cfg.timeout_sec)
    if resp.status_code != 200 or "Erarpaĝo" in resp.text:
        return []

    soup = BeautifulSoup(resp.content, "lxml")
    entries: List[_CollectedEntry] = []

    for header in soup.find_all("h3"):
        section = _clean_space(header.get_text(" ", strip=True))
        ul = header.find_next_sibling("ul")
        while ul and ul.name == "ul":
            for li in ul.find_all("li", recursive=False):
                anchors = li.find_all("a", href=True)
                if not anchors:
                    continue
                link = anchors[0]
                href = urljoin(f"{base}/{year}/", link["href"])
                title = _clean_space(link.get_text(" ", strip=True))
                prefix = _iter_prefix_text(li)
                author_hint = None
                category = None
                parts = [seg.strip() for seg in prefix.split(":") if seg.strip()]
                if parts:
                    author_hint = parts[0]
                if len(parts) > 1:
                    category = parts[1]
                issue_text = ""
                if len(anchors) > 1:
                    issue_text = anchors[-1].get_text(" ", strip=True)
                else:
                    tail = li.get_text(" ", strip=True)
                    match = re.search(r"\(\s*([^)]+)\)", tail)
                    if match:
                        issue_text = match.group(1)
                published = _parse_issue_date(issue_text)
                if published and (published.date() < cfg.start_date or published.date() > cfg.end_date):
                    continue
                entries.append(
                    _CollectedEntry(
                        url=href,
                        title=title,
                        published=published,
                        category=_clean_space(category) if category else None,
                        section=section or None,
                        author_hint=_clean_space(author_hint) if author_hint else None,
                    )
                )
            ul = ul.find_next_sibling("ul")
    return entries


def _collect_from_current(cfg: ScrapeConfig, session: requests.Session) -> List[_CollectedEntry]:
    base = cfg.base_url.rstrip("/")
    url = f"{base}/index.php"
    resp = session.get(url, timeout=cfg.timeout_sec)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "lxml")
    entries: List[_CollectedEntry] = []

    for header in soup.find_all("h3"):
        section = _clean_space(header.get_text(" ", strip=True))
        ul = header.find_next_sibling("ul")
        while ul and ul.name == "ul":
            for li in ul.find_all("li", recursive=False):
                anchor = li.find("a", href=True)
                if not anchor:
                    continue
                href = urljoin(base + "/", anchor["href"])
                if "/publika/" not in href:
                    continue
                title = _clean_space(anchor.get_text(" ", strip=True))
                prefix = _iter_prefix_text(li)
                author_hint = None
                category = None
                parts = [seg.strip() for seg in prefix.split(":") if seg.strip()]
                if parts:
                    author_hint = parts[0]
                if len(parts) > 1:
                    category = parts[1]
                entries.append(
                    _CollectedEntry(
                        url=href,
                        title=title,
                        published=None,
                        category=_clean_space(category) if category else None,
                        section=section or None,
                        author_hint=_clean_space(author_hint) if author_hint else None,
                    )
                )
            ul = ul.find_next_sibling("ul")
    return entries


def collect_urls(cfg: ScrapeConfig) -> URLCollectionResult:
    cfg.normalize()
    session = shared_session(cfg)
    session.headers.update({"User-Agent": USER_AGENT})

    year_start = cfg.start_date.year
    year_end = cfg.end_date.year

    aggregated: List[_CollectedEntry] = []
    fallback_needed = False

    for year in range(year_start, year_end + 1):
        batch = _collect_from_year(year, cfg, session)
        if batch:
            aggregated.extend(batch)
        else:
            if year >= date.today().year - 1:
                fallback_needed = True

    if fallback_needed:
        aggregated.extend(_collect_from_current(cfg, session))

    unique: Dict[str, _CollectedEntry] = {}
    for entry in aggregated:
        if entry.url not in unique:
            unique[entry.url] = entry

    urls: List[str] = []
    earliest: Optional[date] = None
    latest: Optional[date] = None

    MONATO_META.clear()

    def sort_key(item: _CollectedEntry) -> Tuple[datetime, str]:
        if item.published:
            return (item.published, item.url)
        far_future = datetime.max.replace(tzinfo=None)
        return (far_future, item.url)

    sorted_entries = sorted(unique.values(), key=sort_key)

    for entry in sorted_entries:
        urls.append(entry.url)
        MONATO_META[entry.url] = {
            "published": entry.published,
            "category": entry.category,
            "section": entry.section,
            "author_hint": entry.author_hint,
            "title_hint": entry.title,
        }
        if entry.published:
            pub_date = entry.published.date()
            if earliest is None or pub_date < earliest:
                earliest = pub_date
            if latest is None or pub_date > latest:
                latest = pub_date

    return URLCollectionResult(
        urls=urls,
        feed_initial=len(urls),
        archive_initial=0,
        rest_initial=0,
        feed_used=len(urls),
        archive_used=0,
        rest_used=0,
        duplicates_removed=0,
        out_of_range_skipped=0,
        earliest_date=earliest,
        latest_date=latest,
    )


def _extract_paragraphs(container: Tag) -> List[str]:
    paragraphs: List[str] = []
    for p in container.find_all("p"):
        text = _clean_space(p.get_text(" ", strip=True))
        if not text:
            continue
        if "sekcio por abonantoj" in text.lower():
            paragraphs.append(text)
            break
        paragraphs.append(text)
    if not paragraphs:
        text = _clean_space(container.get_text(" ", strip=True))
        if text:
            paragraphs.append(text)
    return [base_clean_text(p) for p in paragraphs if p]


def _find_article_container(soup: BeautifulSoup) -> Tag:
    h1 = soup.find("h1")
    node: Optional[Tag] = h1
    while node and node.name != "td":
        node = node.parent  # type: ignore[assignment]
    return node or soup.body or soup


def fetch_article(url: str, cfg: ScrapeConfig, session: Optional[requests.Session] = None) -> Article:
    cfg.normalize()
    s = session or shared_session(cfg)
    s.headers.update({"User-Agent": USER_AGENT})
    resp = s.get(url, timeout=cfg.timeout_sec)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "lxml")

    container = _find_article_container(soup)
    title_tag = container.find("h1") or soup.find("h1")
    title = base_clean_text(title_tag.get_text(" ", strip=True) if title_tag else url)

    meta = MONATO_META.get(url, {})
    published_dt = meta.get("published")
    author_hint = meta.get("author_hint")

    footer_divs = container.find_all("div", attrs={"style": re.compile(r"text-align:\\s*right")})
    author: Optional[str] = None
    if footer_divs:
        author = _clean_space(footer_divs[0].get_text(" ", strip=True))
    if not author and author_hint:
        author = author_hint

    h2 = container.find("h2")
    h3 = container.find("h3")
    categories: List[str] = []
    for candidate in [meta.get("section"), meta.get("category"), h3.get_text(" ", strip=True) if h3 else None, h2.get_text(" ", strip=True) if h2 else None]:
        if candidate:
            cleaned = _clean_space(str(candidate))
            if cleaned and cleaned not in categories:
                categories.append(cleaned)

    body_paragraphs = _extract_paragraphs(container)
    content_text = "\n\n".join(body_paragraphs)

    return Article(
        url=url,
        title=title,
        published=published_dt,
        content_text=content_text,
        author=author,
        categories=categories or None,
        audio_links=None,
    )


__all__ = [
    "collect_urls",
    "fetch_article",
    "shared_session",
    "set_progress_callback",
]
