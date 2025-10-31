#!/bin/sh
#$ -S /bin/sh
#$ -cwd
#$ -V
#$ -q all.q
#$ -pe openmpi8 8

ulimit -s unlimited
export OMP_NUM_THREADS=8

cd "$SGE_O_WORKDIR" || exit 1

source ~/.bashrc

OUT_DIR="output/pola_retradio_20110101_20251019_parallel_8w"
LOG_PREFIX="logs/pola_retradio_parallel_20110101_20251019_8w"
mkdir -p "$OUT_DIR" "$(dirname "$LOG_PREFIX")"

python3 "Pola Retradio/parallel_scraper.py" \
  --start 2011-01-01 \
  --end 2025-10-19 \
  --workers 8 \
  --out "$OUT_DIR" \
  > "${LOG_PREFIX}.out" 2> "${LOG_PREFIX}.err"
