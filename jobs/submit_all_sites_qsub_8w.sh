#!/bin/sh
set -eu

# Submit all Esperanto sites as separate qsub jobs.
# Each site runs the 8-core parallel scraper.

qsub jobs/qsub_elpopola_8w.sh
qsub jobs/qsub_global_voices_eo_8w.sh
qsub jobs/qsub_monato_8w.sh
qsub jobs/qsub_scivolemo_8w.sh
qsub jobs/qsub_pola_retradio_8w.sh
qsub jobs/qsub_uea_facila_8w.sh

echo "Submitted all jobs. Use 'qstat' to monitor. Logs in logs/*.qsub_*.out(err)."
