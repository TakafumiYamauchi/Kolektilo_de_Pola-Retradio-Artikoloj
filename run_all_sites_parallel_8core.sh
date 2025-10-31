#!/bin/sh
set -u

# 8-core parallel collection for all Esperanto sites (sequential per site).
# Date range and throttle are tuned for careful, thorough fetching.

START="2010-01-01"
END="2025-10-31"
WORKERS=8

mkdir -p logs output || true

echo "[ALL] Start: $START End: $END Workers: $WORKERS"
export OMP_NUM_THREADS=$WORKERS

# 1) El Popola Ĉinio
OUT_DIR="output/elpopola_20100101_20251031_parallel_8w"
LOG_PREFIX="logs/elpopola_parallel_20100101_20251031_8w"
mkdir -p "$OUT_DIR" "$(dirname "$LOG_PREFIX")"
echo "[El Popola Ĉinio] Parallel run..."
python3 "El Popola Ĉinio/parallel_scraper.py" \
  --start "$START" \
  --end "$END" \
  --workers "$WORKERS" \
  --throttle 1.0 \
  --split-by year \
  --out "$OUT_DIR" \
  > "${LOG_PREFIX}.out" 2> "${LOG_PREFIX}.err"

# 2) Global Voices en Esperanto
OUT_DIR="output/global_voices_eo_20100101_20251031_parallel_8w"
LOG_PREFIX="logs/global_voices_eo_parallel_20100101_20251031_8w"
mkdir -p "$OUT_DIR"
echo "[Global Voices en Esperanto] Parallel run..."
python3 "Global Voices en Esperanto/parallel_scraper.py" \
  --start "$START" \
  --end "$END" \
  --workers "$WORKERS" \
  --method rest \
  --throttle 0.5 \
  --split-by year \
  --out "$OUT_DIR" \
  > "${LOG_PREFIX}.out" 2> "${LOG_PREFIX}.err"

# 3) Monato
OUT_DIR="output/monato_20100101_20251031_parallel_8w"
LOG_PREFIX="logs/monato_parallel_20100101_20251031_8w"
mkdir -p "$OUT_DIR"
echo "[Monato] Parallel run..."
python3 "Monato/parallel_scraper.py" \
  --start "$START" \
  --end "$END" \
  --workers "$WORKERS" \
  --method feed \
  --throttle 1.0 \
  --split-by year \
  --out "$OUT_DIR" \
  > "${LOG_PREFIX}.out" 2> "${LOG_PREFIX}.err"

# 4) Scivolemo
OUT_DIR="output/scivolemo_20100101_20251031_parallel_8w"
LOG_PREFIX="logs/scivolemo_parallel_20100101_20251031_8w"
mkdir -p "$OUT_DIR"
echo "[Scivolemo] Parallel run..."
python3 "Scivolemo/parallel_scraper.py" \
  --start "$START" \
  --end "$END" \
  --workers "$WORKERS" \
  --method feed \
  --throttle 0.5 \
  --split-by year \
  --out "$OUT_DIR" \
  > "${LOG_PREFIX}.out" 2> "${LOG_PREFIX}.err"

# 5) Pola Retradio
OUT_DIR="output/pola_retradio_20100101_20251031_parallel_8w"
LOG_PREFIX="logs/pola_retradio_parallel_20100101_20251031_8w"
mkdir -p "$OUT_DIR"
echo "[Pola Retradio] Parallel run..."
python3 "Pola Retradio/parallel_scraper.py" \
  --start "$START" \
  --end "$END" \
  --workers "$WORKERS" \
  --method auto \
  --include-audio \
  --throttle 1.0 \
  --split-by year \
  --out "$OUT_DIR" \
  > "${LOG_PREFIX}.out" 2> "${LOG_PREFIX}.err"

# 6) UEA Facila (parallel)
OUT_DIR="output/uea_facila_20100101_20251031_parallel_8w"
LOG_PREFIX="logs/uea_facila_parallel_20100101_20251031_8w"
mkdir -p "$OUT_DIR"
echo "[UEA Facila] Parallel run..."
python3 "Uea_Facila/parallel_scraper.py" \
  --start "$START" \
  --end "$END" \
  --workers "$WORKERS" \
  --throttle 0.5 \
  --split-by year \
  --out "$OUT_DIR" \
  > "${LOG_PREFIX}.out" 2> "${LOG_PREFIX}.err"

echo "[ALL] Done. Check 'output/' and 'logs/' directories."
