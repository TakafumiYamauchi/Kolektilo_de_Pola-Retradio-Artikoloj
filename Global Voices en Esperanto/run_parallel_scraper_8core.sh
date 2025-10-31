#!/bin/sh
# Wrapper for Global Voices en Esperanto parallel scraper (8 workers assumed).

python3 "$(dirname "$0")/parallel_scraper.py" "$@"
