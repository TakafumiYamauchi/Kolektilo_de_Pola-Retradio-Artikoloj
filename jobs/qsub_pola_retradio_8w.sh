#!/bin/sh
#$ -S /bin/sh
#$ -cwd
#$ -V
#$ -q all.q
#$ -pe openmpi8 8
#$ -N retradio_8w
#$ -o logs/pola_retradio_qsub_20100101_20251031_8w.out
#$ -e logs/pola_retradio_qsub_20100101_20251031_8w.err

ulimit -s unlimited
export OMP_NUM_THREADS=8
cd "$SGE_O_WORKDIR" || exit 1
START="2010-01-01"
END="2025-10-31"

OUT_DIR="output/pola_retradio_20100101_20251031_parallel_8w"
LOG_PREFIX="logs/pola_retradio_parallel_20100101_20251031_8w"
mkdir -p "$OUT_DIR" "$(dirname "$LOG_PREFIX")"

python3 "Pola Retradio/parallel_scraper.py" \
  --start "$START" \
  --end "$END" \
  --workers 8 \
  --method auto \
  --include-audio \
  --throttle 1.0 \
  --split-by year \
  --out "$OUT_DIR" \
  > "${LOG_PREFIX}.out" 2> "${LOG_PREFIX}.err"

