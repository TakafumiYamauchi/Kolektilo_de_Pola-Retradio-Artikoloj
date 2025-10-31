#!/bin/sh
# Wrapper for UEA Facila scraper (no native parallel version; this calls the standard CLI).

python3 "$(dirname "$0")/scraper.py" "$@"
