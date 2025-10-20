#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Aggregate the Pola Retradio compiled Markdown into one file per year.

Output files are written as:
  <output_dir>/<YYYY>.md

Each yearly file contains a small YAML frontmatter with metadata,
followed by all articles of that year in chronological order, with
"---" separators between entries (purely as Markdown separators).

Usage:
  python scripts/aggregate_pola_markdown_by_year.py \
      --input pola_retradio_2011-02-15_2025-10-15.md \
      --output "年ごとの記事"
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
from typing import List, Dict, Optional, Tuple


ENTRY_SEP = re.compile(r"^---\s*$")
PUBLISHED_RE = re.compile(r"^\*\*Published:\*\*\s*(\d{4})-(\d{2})-(\d{2})\s*$")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Aggregate Pola Retradio markdown into one file per year")
    p.add_argument("--input", required=True, help="Input markdown file path")
    p.add_argument("--output", required=True, help="Output directory (e.g., 年ごとの記事)")
    return p.parse_args()


class Article:
    def __init__(self, content_lines: List[str]):
        self.content_lines = content_lines
        self.year: Optional[int] = None
        self.month: Optional[int] = None
        self.day: Optional[int] = None
        self._parse_metadata()

    def _parse_metadata(self) -> None:
        for line in self.content_lines:
            m = PUBLISHED_RE.match(line)
            if m:
                self.year = int(m.group(1))
                self.month = int(m.group(2))
                self.day = int(m.group(3))

    def date_key(self) -> Tuple[int, int, int]:
        y = self.year if self.year is not None else 0
        m = self.month if self.month is not None else 0
        d = self.day if self.day is not None else 0
        return (y, m, d)


def read_frontmatter(md_path: str) -> Dict[str, str]:
    meta: Dict[str, str] = {}
    with open(md_path, 'r', encoding='utf-8') as f:
        first = f.readline()
        if not ENTRY_SEP.match(first):
            return meta
        for line in f:
            if ENTRY_SEP.match(line):
                break
            # naive key: "value" parser
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"')
    return meta


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
            i += 1

    buf: List[str] = []
    while i < len(lines):
        line = lines[i]
        if ENTRY_SEP.match(line):
            if buf and any(PUBLISHED_RE.match(l) for l in buf):
                articles.append(Article(buf))
            buf = []
        else:
            buf.append(line)
        i += 1
    if buf and any(PUBLISHED_RE.match(l) for l in buf):
        articles.append(Article(buf))
    return articles


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_year_file(out_dir: str, year: int, articles: List[Article], front_meta: Dict[str, str], input_path: str) -> None:
    ensure_dir(out_dir)
    out_path = os.path.join(out_dir, f"{year:04d}.md")
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    time_range = front_meta.get("time_range", "")

    with open(out_path, 'w', encoding='utf-8') as w:
        # YAML frontmatter
        w.write("---\n")
        w.write("source: \"Pola Retradio (pola-retradio.org)\"\n")
        w.write(f"generated_at: \"{now}\"\n")
        w.write("generator: \"aggregate_pola_markdown_by_year.py\"\n")
        w.write(f"year: \"{year:04d}\"\n")
        w.write(f"article_count: {len(articles)}\n")
        if time_range:
            w.write(f"original_time_range: \"{time_range}\"\n")
        w.write(f"from_input: \"{os.path.basename(input_path)}\"\n")
        w.write("---\n\n")

        # Optional: Title
        w.write(f"# Pola Retradio {year:04d}\n\n")

        # Write all articles separated by horizontal rules
        for idx, a in enumerate(articles):
            if idx > 0:
                w.write("\n---\n\n")
            w.writelines(a.content_lines)


def main() -> None:
    args = parse_args()
    ensure_dir(args.output)

    # Read global metadata and articles
    front_meta = read_frontmatter(args.input)
    articles = read_articles(args.input)
    if not articles:
        raise SystemExit("No articles parsed. Check input format.")

    # Group by year and sort by date within year
    by_year: Dict[int, List[Article]] = {}
    for a in articles:
        if a.year is None:
            continue
        by_year.setdefault(a.year, []).append(a)
    for y in by_year:
        by_year[y].sort(key=lambda a: a.date_key())

    # Write out yearly files in ascending order
    for year in sorted(by_year):
        write_year_file(args.output, year, by_year[year], front_meta, args.input)

    print(f"Wrote {len(by_year)} yearly files to '{args.output}'. Total articles: {len(articles)}")


if __name__ == "__main__":
    main()

