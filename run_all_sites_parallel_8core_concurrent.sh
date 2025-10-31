#!/bin/sh
set -u

# Launch all Esperanto sites concurrently, each with 8 workers.
# Total CPU usage ~ 48 cores.

START="2010-01-01"
END="2025-10-31"
WORKERS=8

mkdir -p logs output || true
export OMP_NUM_THREADS=$WORKERS

echo "[ALL-CONCURRENT] Start: $START End: $END Workers per site: $WORKERS"

launch() {
  name="$1"; shift
  log_prefix="logs/${name}"
  echo "[LAUNCH] $name"
  ( "$@" > "${log_prefix}.out" 2> "${log_prefix}.err" ) &
  pid=$!
  echo "  -> PID ${pid} for ${name}"
  echo "$pid $name" >> logs/pids_all_sites_parallel_8core.txt
}

# El Popola Ĉinio (parallel)
launch "elpopola_parallel_20100101_20251031_8w" \
  python3 "El Popola Ĉinio/parallel_scraper.py" \
    --start "$START" \
    --end "$END" \
    --workers "$WORKERS" \
    --throttle 1.0 \
    --split-by year \
    --out "output/elpopola_20100101_20251031_parallel_8w"

# Global Voices en Esperanto (parallel)
launch "global_voices_eo_parallel_20100101_20251031_8w" \
  python3 "Global Voices en Esperanto/parallel_scraper.py" \
    --start "$START" \
    --end "$END" \
    --workers "$WORKERS" \
    --method rest \
    --throttle 0.5 \
    --split-by year \
    --out "output/global_voices_eo_20100101_20251031_parallel_8w"

# Monato (parallel)
launch "monato_parallel_20100101_20251031_8w" \
  python3 "Monato/parallel_scraper.py" \
    --start "$START" \
    --end "$END" \
    --workers "$WORKERS" \
    --method feed \
    --throttle 1.0 \
    --split-by year \
    --out "output/monato_20100101_20251031_parallel_8w"

# Scivolemo (parallel)
launch "scivolemo_parallel_20100101_20251031_8w" \
  python3 "Scivolemo/parallel_scraper.py" \
    --start "$START" \
    --end "$END" \
    --workers "$WORKERS" \
    --method feed \
    --throttle 0.5 \
    --split-by year \
    --out "output/scivolemo_20100101_20251031_parallel_8w"

# Pola Retradio (parallel)
launch "pola_retradio_parallel_20100101_20251031_8w" \
  python3 "Pola Retradio/parallel_scraper.py" \
    --start "$START" \
    --end "$END" \
    --workers "$WORKERS" \
    --method auto \
    --include-audio \
    --throttle 1.0 \
    --split-by year \
    --out "output/pola_retradio_20100101_20251031_parallel_8w"

# UEA Facila (parallel)
launch "uea_facila_parallel_20100101_20251031_8w" \
  python3 "Uea_Facila/parallel_scraper.py" \
    --start "$START" \
    --end "$END" \
    --workers "$WORKERS" \
    --throttle 0.5 \
    --split-by year \
    --out "output/uea_facila_20100101_20251031_parallel_8w"

echo "[ALL-CONCURRENT] All jobs launched; waiting..."
wait
echo "[ALL-CONCURRENT] All jobs finished. See logs/ and output/."
