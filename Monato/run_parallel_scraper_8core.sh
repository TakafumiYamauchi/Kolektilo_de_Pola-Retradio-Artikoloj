#!/bin/sh
# Wrapper for Monato parallel scraper (8 workers assumed).

python3 "$(dirname "$0")/parallel_scraper.py" "$@"
