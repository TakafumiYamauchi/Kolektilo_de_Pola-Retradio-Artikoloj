#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Split a compiled Pola Retradio Markdown dump into per-year or biennial folders.

Usage:
  python scripts/split_pola_markdown.py \
      --input pola_retradio_2011-02-15_2025-10-15.md \
      --output "年ごとの記事" \
      --mode biennial

Modes:
  - per-year  => 2011/, 2012/, ...
  - biennial  => 2011-2012/, 2013-2014/, ... (last lone year kept as YYYY)

Notes:
  - Assumes entries are delimited by lines equal to '---' and that the file
    starts with YAML frontmatter enclosed by '---' lines.
  - Extracts Published date from a line starting with '**Published:** YYYY-MM-DD'.
  - File names are 'YYYY-MM-DD_<slug>.md' if URL is present, otherwise
    'YYYY-MM-DD_entry-<n>.md'.
"""

from __future__ import annotations

import argparse
import os
import re
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlsplit


ENTRY_SEP = re.compile(r"^---\s*$")
PUBLISHED_RE = re.compile(r"^\*\*Published:\*\*\s*(\d{4})-(\d{2})-(\d{2})\s*$")
URL_RE = re.compile(r"^\*\*URL:\*\*\s*(\S+)\s*$")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Split Pola Retradio markdown into year/biennial folders")
    p.add_argument("--input", required=True, help="Input markdown file path")
    p.add_argument("--output", required=True, help="Output base directory (e.g., 年ごとの記事)")
    p.add_argument("--mode", choices=["per-year", "biennial"], default="biennial",
                  help="Grouping mode (default: biennial)")
    return p.parse_args()


class Article:
    def __init__(self, content_lines: List[str]):
        self.content_lines = content_lines
        self.year: Optional[int] = None
        self.month: Optional[int] = None
        self.day: Optional[int] = None
        self.url: Optional[str] = None
        self.slug: Optional[str] = None
        self._parse_metadata()

    def _parse_metadata(self) -> None:
        for line in self.content_lines:
            m = PUBLISHED_RE.match(line)
            if m:
                self.year = int(m.group(1))
                self.month = int(m.group(2))
                self.day = int(m.group(3))
            u = URL_RE.match(line)
            if u:
                self.url = u.group(1)
        if self.url:
            try:
                path = urlsplit(self.url).path
                segments = [s for s in path.split('/') if s]
                if segments:
                    self.slug = segments[-1]
            except Exception:
                self.slug = None

    def date_str(self) -> str:
        if self.year and self.month and self.day:
            return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"
        return "unknown-date"

    def filename(self, fallback_index: int = 0) -> str:
        base = self.date_str()
        if self.slug:
            name = f"{base}_{self.slug}.md"
        else:
            suffix = f"_{fallback_index}" if fallback_index else ""
            name = f"{base}_entry{suffix}.md"
        # Sanitize minimal (keep ascii-ish; spaces not expected here)
        name = name.replace('/', '-').replace('\\', '-')
        return name


def read_articles(md_path: str) -> List[Article]:
    articles: List[Article] = []
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Skip YAML frontmatter between the first two '---' separators
    i = 0
    if i < len(lines) and ENTRY_SEP.match(lines[i]):
        i += 1
        while i < len(lines) and not ENTRY_SEP.match(lines[i]):
            i += 1
        if i < len(lines) and ENTRY_SEP.match(lines[i]):
            i += 1  # move past closing frontmatter '---'

    # Now parse articles delimited by '---' lines
    buf: List[str] = []
    while i < len(lines):
        line = lines[i]
        if ENTRY_SEP.match(line):
            # flush current article if non-empty (ignore stray separators)
            if buf and any(PUBLISHED_RE.match(l) for l in buf):
                articles.append(Article(buf))
            buf = []
        else:
            buf.append(line)
        i += 1

    # flush last
    if buf and any(PUBLISHED_RE.match(l) for l in buf):
        articles.append(Article(buf))

    return articles


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def compute_biennial_bucket(year: int, anchor: int) -> Tuple[int, int]:
    offset = year - anchor
    start = anchor + (offset // 2) * 2
    end = start + 1
    return start, end


def main() -> None:
    args = parse_args()
    articles = read_articles(args.input)
    if not articles:
        raise SystemExit("No articles parsed. Check input format.")

    # Determine year range
    years = [a.year for a in articles if a.year is not None]
    if not years:
        raise SystemExit("No Published years found in articles.")
    min_year, max_year = min(years), max(years)

    ensure_dir(args.output)

    # Prepare counters to avoid name collisions
    name_counters: Dict[str, Dict[str, int]] = {}

    # Group and write
    for idx, a in enumerate(articles):
        if a.year is None:
            # Skip entries lacking a valid year
            continue

        if args.mode == "per-year":
            group_dirname = f"{a.year:04d}"
        else:
            start, end = compute_biennial_bucket(a.year, anchor=min_year)
            # If 'end' goes beyond max_year, and there's no article in that year, keep single year dir
            if start == max_year:
                group_dirname = f"{start:04d}"
            elif end > max_year:
                # last lone year
                group_dirname = f"{start:04d}"
            else:
                group_dirname = f"{start:04d}-{end:04d}"

        out_dir = os.path.join(args.output, group_dirname)
        ensure_dir(out_dir)

        # Unique filename handling
        if group_dirname not in name_counters:
            name_counters[group_dirname] = {}
        # Tentative name
        base_name = a.filename()
        counter = name_counters[group_dirname].get(base_name, 0)
        filename = base_name
        if counter > 0:
            # add numeric suffix before extension
            root, ext = os.path.splitext(base_name)
            filename = f"{root}-{counter}{ext}"
        name_counters[group_dirname][base_name] = counter + 1

        out_path = os.path.join(out_dir, filename)
        with open(out_path, 'w', encoding='utf-8') as wf:
            wf.writelines(a.content_lines)

    print(f"Wrote articles to '{args.output}' grouped by {args.mode}.")
    print(f"Years covered: {min_year}–{max_year}. Total articles: {len(articles)}")


if __name__ == "__main__":
    main()

