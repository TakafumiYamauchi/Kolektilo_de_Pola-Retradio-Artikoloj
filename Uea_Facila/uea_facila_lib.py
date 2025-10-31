# -*- coding: utf-8 -*-
"""
uea_facila_lib.py

Helper utilities to scrape articles from uea.facila.org.
The site runs on Invision Community, so we cannot rely on the WordPress
helpers provided in retradio_lib.  Instead we scrape the public "Ĉiu aktivado"
stream (https://uea.facila.org/malkovri/) and fetch individual article pages.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone, date
from typing import Dict, Iterable, List, Optional
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

from retradio_lib import (  # type: ignore
    Article,
    ScrapeConfig,
    URLCollectionResult,
    _clean_text as base_clean_text,
    _session as shared_session,
    set_progress_callback,
)

USER_AGENT = "Mozilla/5.0 (compatible; UEAFacilaScraper/1.0; +https://uea.facila.org)"
STREAM_PATH = "/malkovri/"
VALID_PATH_SEGMENTS = (
    "/artikoloj/",
    "/filmetoj/",
    "/niaj-legantoj/",
    "/loke/",
)

UEA_META: Dict[str, Dict[str, object]] = {}


def _session(cfg: ScrapeConfig) -> requests.Session:
    sess = shared_session(cfg)
    sess.headers.update({"User-Agent": USER_AGENT})
    return sess


def _canonicalize_url(base_url: str, href: str) -> Optional[str]:
    if not href:
        return None
    url = href.split("?", 1)[0]
    url = urljoin(base_url.rstrip("/") + "/", url)
    parts = urlsplit(url)
    # Ignore fragments and queries
    url = urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))
    if not any(segment in parts.path for segment in VALID_PATH_SEGMENTS):
        return None
    return url


def _parse_timestamp(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        if value.isdigit():
            return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except Exception:  # noqa: BLE001
        logging.getLogger(__name__).debug("failed to parse timestamp %s", value, exc_info=True)
    return None


def _parse_iso_datetime(value: str) -> Optional[datetime]:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except Exception:  # noqa: BLE001
        logging.getLogger(__name__).debug("iso parse failed for %s", value, exc_info=True)
        return None


def _stream_page_urls(
    cfg: ScrapeConfig,
    session: requests.Session,
) -> Iterable[BeautifulSoup]:
    base = cfg.base_url.rstrip("/")
    page = 1
    max_pages = cfg.max_pages or 50

    while page <= max_pages:
        url = f"{base}{STREAM_PATH}"
        if page > 1:
            url = f"{url}?page={page}"
        resp = session.get(url, timeout=cfg.timeout_sec)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "lxml")
        yield soup
        page += 1
        if cfg.throttle_sec:
            time.sleep(cfg.throttle_sec)


def collect_urls(cfg: ScrapeConfig) -> URLCollectionResult:
    cfg.normalize()
    session = _session(cfg)

    aggregated: Dict[str, datetime] = {}
    earliest: Optional[date] = None
    latest: Optional[date] = None

    reached_older_than_start = False
    for soup in _stream_page_urls(cfg, session):
        stream_items = soup.select(".ipsStreamItem")
        if not stream_items:
            break

        min_timestamp_on_page: Optional[datetime] = None
        for item in stream_items:
            title_el = item.select_one(".ipsStreamItem_title a")
            if not title_el or not title_el.get("href"):
                continue

            canonical = _canonicalize_url(cfg.base_url, title_el["href"])
            if not canonical:
                continue

            dt: Optional[datetime] = None
            time_el = item.find("time")
            if time_el and time_el.get("datetime"):
                dt = _parse_iso_datetime(time_el["datetime"])
            if not dt and item.has_attr("data-timestamp"):
                dt = _parse_timestamp(item["data-timestamp"])
            if not dt:
                continue

            dt = dt.astimezone(timezone.utc)
            item_date = dt.date()

            if item_date > cfg.end_date:
                continue

            if min_timestamp_on_page is None or dt < min_timestamp_on_page:
                min_timestamp_on_page = dt

            if item_date < cfg.start_date:
                reached_older_than_start = True
                continue

            if canonical in aggregated and aggregated[canonical] <= dt:
                continue
            aggregated[canonical] = dt
            if earliest is None or item_date < earliest:
                earliest = item_date
            if latest is None or item_date > latest:
                latest = item_date

        if reached_older_than_start and min_timestamp_on_page and min_timestamp_on_page.date() < cfg.start_date:
            break

    entries = sorted(aggregated.items(), key=lambda pair: (pair[1], pair[0]))

    urls = [url for url, _ in entries]
    UEA_META.clear()
    for url, dt in entries:
        UEA_META[url] = {"published": dt}

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


def _extract_article_paragraphs(article: BeautifulSoup) -> List[str]:
    paragraphs: List[str] = []
    for iframe in article.find_all("iframe"):
        src = iframe.get("src")
        if src:
            paragraphs.append(f"[Embed] {src}")
    for node in article.find_all(["p", "li", "blockquote", "h2", "h3"]):
        text = base_clean_text(node.get_text(" ", strip=True))
        if not text:
            continue
        paragraphs.append(text)
    return paragraphs


def _extract_categories(soup: BeautifulSoup) -> List[str]:
    crumbs = [base_clean_text(li.get_text(" ", strip=True)) for li in soup.select("nav.ipsBreadcrumb li")]
    filtered: List[str] = []
    skip_tokens = {"Hejmo", "Ĉiu aktivado", "Artikoloj", "Artikola fluo", ""}
    title_el = soup.find("h1", class_="ipsType_pageTitle")
    title_text = base_clean_text(title_el.get_text(" ", strip=True)) if title_el else None
    for crumb in crumbs:
        if crumb in skip_tokens:
            continue
        if title_text and crumb == title_text:
            continue
        if crumb not in filtered:
            filtered.append(crumb)
    return filtered


def _extract_author(soup: BeautifulSoup) -> Optional[str]:
    author_box = soup.select_one(".gastautoraj-detaloj")
    if author_box:
        primary = author_box.get_text("\n", strip=True).split("\n", 1)[0]
        return base_clean_text(primary)
    meta_author = soup.select_one(".ipsType_author")
    if meta_author:
        return base_clean_text(meta_author.get_text(" ", strip=True))
    return None


def _extract_audio_links(article: BeautifulSoup) -> List[str]:
    links = set()
    for el in article.find_all(["audio", "source", "a"]):
        href = el.get("src") or el.get("href")
        if not href:
            continue
        lower = href.lower()
        if "mp3" in lower or "audio" in lower:
            links.add(href)
    return sorted(links)


def fetch_article(url: str, cfg: ScrapeConfig, session: Optional[requests.Session] = None) -> Article:
    cfg.normalize()
    sess = session or _session(cfg)
    resp = sess.get(url, timeout=cfg.timeout_sec)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "lxml")

    title_el = soup.find("h1", class_="ipsType_pageTitle")
    title = base_clean_text(title_el.get_text(" ", strip=True) if title_el else url)

    article_el = soup.select_one("article.artikolo") or soup.select_one("article")
    if not article_el:
        raise ValueError(f"article content not found: {url}")

    paragraphs = _extract_article_paragraphs(article_el)
    content_text = "\n\n".join(paragraphs)
    if not content_text:
        fallback = base_clean_text(article_el.get_text(" ", strip=True))
        content_text = fallback

    published: Optional[datetime] = None
    meta_time = soup.find("time", attrs={"itemprop": "datePublished"}) or soup.find("time")
    if meta_time and meta_time.get("datetime"):
        published = _parse_iso_datetime(meta_time["datetime"])
    if not published:
        cached = UEA_META.get(url, {}).get("published")
        if isinstance(cached, datetime):
            published = cached

    author = _extract_author(soup)
    categories = _extract_categories(soup) or None
    audio_links = _extract_audio_links(article_el)

    return Article(
        url=url,
        title=title,
        published=published,
        content_text=content_text,
        author=author,
        categories=categories,
        audio_links=audio_links or None,
    )


__all__ = [
    "collect_urls",
    "fetch_article",
    "shared_session",
    "set_progress_callback",
]
