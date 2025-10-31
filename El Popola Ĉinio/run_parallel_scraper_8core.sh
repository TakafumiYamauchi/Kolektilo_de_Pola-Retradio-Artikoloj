#!/bin/sh
# Wrapper for submitting El Popola Ĉinio parallel scraper with 8 workers.

python3 "$(dirname "$0")/parallel_scraper.py" "$@"
