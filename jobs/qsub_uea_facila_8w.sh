#!/bin/sh
#$ -S /bin/sh
#$ -cwd
#$ -V
#$ -q all.q
#$ -pe openmpi8 8
#$ -N uea_facila_8w
#$ -o logs/uea_facila_qsub_20100101_20251031_8w.out
#$ -e logs/uea_facila_qsub_20100101_20251031_8w.err

ulimit -s unlimited
export OMP_NUM_THREADS=8
cd "$SGE_O_WORKDIR" || exit 1
START="2010-01-01"
END="2025-10-31"

OUT_DIR="output/uea_facila_20100101_20251031_parallel_8w"
LOG_PREFIX="logs/uea_facila_parallel_20100101_20251031_8w"
mkdir -p "$OUT_DIR" "$(dirname "$LOG_PREFIX")"

python3 "Uea_Facila/parallel_scraper.py" \
  --start "$START" \
  --end "$END" \
  --workers 8 \
  --throttle 0.5 \
  --split-by year \
  --out "$OUT_DIR" \
  > "${LOG_PREFIX}.out" 2> "${LOG_PREFIX}.err"
