#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Validate the per-year aggregation against the original Pola Retradio dump.

Checks performed:
  - Total article count parity (original vs. sum of yearly files)
  - Per-year counts parity (expected from original vs. each yearly file)
  - Set equality of unique article keys (date+URL or date+title)
  - Duplicates within yearly outputs
  - Yearly file frontmatter 'article_count' matches parsed count
  - Basic ordering check: non-decreasing Published dates within each year

Usage:
  python scripts/validate_yearly_aggregation.py \
      --input pola_retradio_2011-02-15_2025-10-15.md \
      --yeardir "年ごとの記事"
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple, Set


ENTRY_SEP = re.compile(r"^---\s*$")
PUBLISHED_RE = re.compile(r"^\*\*Published:\*\*\s*(\d{4})-(\d{2})-(\d{2})\s*$")
URL_RE = re.compile(r"^\*\*URL:\*\*\s*(\S+)\s*$")
TITLE_RE = re.compile(r"^#\s+(.+?)\s*$")
YEAR_FILE_RE = re.compile(r"^(\d{4})\.md$")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate yearly aggregation")
    p.add_argument("--input", required=True, help="Path to original markdown dump")
    p.add_argument("--yeardir", required=True, help="Directory containing yearly files e.g., 年ごとの記事")
    return p.parse_args()


class Article:
    def __init__(self, lines: List[str]):
        self.lines = lines
        self.year: Optional[int] = None
        self.month: Optional[int] = None
        self.day: Optional[int] = None
        self.url: Optional[str] = None
        self.title: Optional[str] = None
        self._parse()

    def _parse(self) -> None:
        for ln in self.lines:
            if self.title is None:
                mtitle = TITLE_RE.match(ln)
                if mtitle:
                    self.title = mtitle.group(1).strip()
            mp = PUBLISHED_RE.match(ln)
            if mp:
                self.year = int(mp.group(1))
                self.month = int(mp.group(2))
                self.day = int(mp.group(3))
            mu = URL_RE.match(ln)
            if mu:
                self.url = mu.group(1)

    def has_published(self) -> bool:
        return self.year is not None and self.month is not None and self.day is not None

    def date_tuple(self) -> Tuple[int, int, int]:
        y = self.year if self.year is not None else 0
        m = self.month if self.month is not None else 0
        d = self.day if self.day is not None else 0
        return (y, m, d)

    def key(self) -> Tuple[str, str]:
        date = f"{self.date_tuple()[0]:04d}-{self.date_tuple()[1]:02d}-{self.date_tuple()[2]:02d}"
        if self.url:
            return (date, self.url)
        # Fallback to title if URL missing
        title = (self.title or "").strip()
        return (date, title)


def read_blocks_skip_frontmatter(path: str) -> List[List[str]]:
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    i = 0
    # Skip YAML frontmatter if present
    if i < len(lines) and ENTRY_SEP.match(lines[i]):
        i += 1
        while i < len(lines) and not ENTRY_SEP.match(lines[i]):
            i += 1
        if i < len(lines) and ENTRY_SEP.match(lines[i]):
            i += 1

    blocks: List[List[str]] = []
    buf: List[str] = []
    while i < len(lines):
        ln = lines[i]
        if ENTRY_SEP.match(ln):
            if buf:
                blocks.append(buf)
                buf = []
        else:
            buf.append(ln)
        i += 1
    if buf:
        blocks.append(buf)
    return blocks


def parse_articles_from_file(path: str) -> List[Article]:
    blocks = read_blocks_skip_frontmatter(path)
    arts: List[Article] = []
    for b in blocks:
        a = Article(b)
        if a.has_published():
            arts.append(a)
    return arts


def read_yearly_files(yeardir: str) -> Dict[int, str]:
    mapping: Dict[int, str] = {}
    for name in os.listdir(yeardir):
        m = YEAR_FILE_RE.match(name)
        if not m:
            continue
        y = int(m.group(1))
        mapping[y] = os.path.join(yeardir, name)
    return mapping


def parse_year_file_article_count(path: str) -> Optional[int]:
    # Read frontmatter only
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    if not lines or not ENTRY_SEP.match(lines[0]):
        return None
    for i in range(1, len(lines)):
        if ENTRY_SEP.match(lines[i]):
            break
        if lines[i].startswith('article_count:'):
            try:
                return int(lines[i].split(':', 1)[1].strip())
            except Exception:
                return None
    return None


def main() -> None:
    args = parse_args()

    original_articles = parse_articles_from_file(args.input)
    orig_total = len(original_articles)

    # Expected per-year counts from original
    expected_by_year: Counter[int] = Counter()
    for a in original_articles:
        if a.year is not None:
            expected_by_year[a.year] += 1

    # Read yearly files
    year_files = read_yearly_files(args.yeardir)
    parsed_by_year: Dict[int, List[Article]] = {}
    for y, p in sorted(year_files.items()):
        parsed_by_year[y] = parse_articles_from_file(p)

    # Counts
    actual_by_year: Dict[int, int] = {y: len(v) for y, v in parsed_by_year.items()}
    actual_total = sum(actual_by_year.values())

    # Check frontmatter counts
    fm_mismatches: List[Tuple[int, int, Optional[int]]] = []
    for y, p in year_files.items():
        fm_count = parse_year_file_article_count(p)
        actual = actual_by_year.get(y, 0)
        if fm_count is None or fm_count != actual:
            fm_mismatches.append((y, actual, fm_count))

    # Build sets of keys
    orig_keys: Set[Tuple[str, str]] = {a.key() for a in original_articles}
    yearly_keys: Set[Tuple[str, str]] = set()
    dup_keys: Counter[Tuple[str, str]] = Counter()
    for y, arts in parsed_by_year.items():
        for a in arts:
            k = a.key()
            if k in yearly_keys:
                dup_keys[k] += 1
            yearly_keys.add(k)

    missing_in_years = orig_keys - yearly_keys
    extra_in_years = yearly_keys - orig_keys

    # Order check
    ordering_issues: List[int] = []
    for y, arts in parsed_by_year.items():
        dates = [a.date_tuple() for a in arts]
        if any(dates[i] > dates[i+1] for i in range(len(dates)-1)):
            ordering_issues.append(y)

    # Per-year parity issues
    per_year_issues: List[Tuple[int, int, int]] = []
    for y in sorted(set(expected_by_year.keys()) | set(actual_by_year.keys())):
        exp = expected_by_year.get(y, 0)
        act = actual_by_year.get(y, 0)
        if exp != act:
            per_year_issues.append((y, exp, act))

    # Report
    print("Validation Summary")
    print("===================")
    print(f"Original total articles: {orig_total}")
    print(f"Yearly sum of articles: {actual_total}")
    print(f"Total parity: {'OK' if orig_total == actual_total else 'MISMATCH'}")
    print()

    if per_year_issues:
        print("Per-year count mismatches:")
        for y, exp, act in per_year_issues:
            print(f"  {y}: expected {exp}, actual {act}")
        print()
    else:
        print("Per-year counts: OK")
        print()

    if fm_mismatches:
        print("Frontmatter article_count mismatches:")
        for y, act, fm in sorted(fm_mismatches):
            print(f"  {y}: actual {act}, frontmatter {fm}")
        print()
    else:
        print("Frontmatter article_count fields: OK")
        print()

    if dup_keys:
        print(f"Duplicates in yearly outputs: {sum(dup_keys.values())}")
        for k, c in dup_keys.most_common(10):
            print(f"  {k} x{c+1}")
        print()
    else:
        print("Duplicates: none")
        print()

    print(f"Missing in yearly (should be 0): {len(missing_in_years)}")
    if missing_in_years:
        for k in list(sorted(missing_in_years))[:10]:
            print(f"  {k}")
        print("  ...")
    print()

    print(f"Extras in yearly (should be 0): {len(extra_in_years)}")
    if extra_in_years:
        for k in list(sorted(extra_in_years))[:10]:
            print(f"  {k}")
        print("  ...")
    print()

    if ordering_issues:
        print("Ordering issues in years:")
        print("  ", ", ".join(str(y) for y in sorted(ordering_issues)))
    else:
        print("Within-year chronological order: OK")


if __name__ == "__main__":
    main()

