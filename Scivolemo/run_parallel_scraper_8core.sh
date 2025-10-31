#!/bin/sh
# Wrapper for Scivolemo parallel scraper (8 workers assumed).

python3 "$(dirname "$0")/parallel_scraper.py" "$@"
