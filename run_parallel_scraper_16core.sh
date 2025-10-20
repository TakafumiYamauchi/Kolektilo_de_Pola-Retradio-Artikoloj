#!/bin/sh
#$ -S /bin/sh
#$ -cwd
#$ -V
#$ -q all.q
#$ -pe openmpi16 16

ulimit -s unlimited
export OMP_NUM_THREADS=16

cd "$SGE_O_WORKDIR" || exit 1

source ~/.bashrc

OUT_DIR="output/pola_retradio_20110101_20251019_parallel_16w"
LOG_PREFIX="logs/pola_retradio_parallel_20110101_20251019"
mkdir -p "$OUT_DIR" "$(dirname "$LOG_PREFIX")"

python3 parallel_scraper.py \
  --start 2011-01-01 \
  --end 2025-10-19 \
  --workers 16 \
  --out "$OUT_DIR" \
  > "${LOG_PREFIX}.out" 2> "${LOG_PREFIX}.err"
