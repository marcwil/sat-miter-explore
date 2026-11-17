#!/bin/sh
# uniform-wiring side study, stage 1: generate, calibrate, width (flat + spatially varying), AIGs, solvers, sweeping
cd "$(dirname "$0")"
python3 -u r2_gen.py grids/r3_U_stage1.json results/instances/r3U 3 > results/r3u_gen.log 2>&1
python3 -u r3u_calibrate.py > results/r3u_calibration.log 2>&1
FILTER='_t(1|10)_' JOBS=4 python3 -u r3_analyze.py results/r3u_width.csv results/instances/r3U > results/r3u_analyze.log 2>&1
FILTER='_n(32|64|128)_' JOBS=4 python3 -u r3_nonflat.py results/r3u_nonflat.csv results/instances/r3U > results/r3u_nonflat.log 2>&1
for f in results/instances/r3U/*.json; do b=${f%.json}; for c in c0 ct; do [ -f $b.$c.aig ] || tools/abc/abc -c "read $b.$c.blif; strash; write_aiger $b.$c.aig" >/dev/null 2>&1; done; done
python3 -u run.py solve results/instances/r3U results/r3u_e3.csv 300 cadical,kissat,abc_cec,abc_gcec > results/r3u_e3.log 2>&1
python3 -u e4_sweep.py results/instances/r3U results/r3u_sweep.csv 300 > results/r3u_sweep.log 2>&1
echo R3U_DONE >> results/r3u_gen.log
