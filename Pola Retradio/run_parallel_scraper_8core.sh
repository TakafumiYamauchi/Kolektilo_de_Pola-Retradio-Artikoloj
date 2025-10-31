#!/bin/sh
# Simple wrapper to mirror the original 8-core job script after relocating the scraper.

python3 "$(dirname "$0")/parallel_scraper.py" "$@"
