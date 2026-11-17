#!/bin/sh
# queued after the scaling grid: generate C/C2 stage 1, widths, then solvers + sweep on an idle machine
cd "$(dirname "$0")"
until grep -q R3B_DONE results/r3_gen_B.log 2>/dev/null; do sleep 30; done
python3 -u r2_gen.py grids/r3_C_stage1.json results/instances/r3C 4 > results/r3_gen_C.log 2>&1
JOBS=4 python3 -u r3_analyze.py results/r3_C_width.csv results/instances/r3C > results/r3_C_analyze.log 2>&1
for f in results/instances/r3C/*.json; do b=${f%.json}; for c in c0 ct; do tools/abc/abc -c "read $b.$c.blif; strash; write_aiger $b.$c.aig" >/dev/null 2>&1; done; done
python3 -u run.py solve results/instances/r3C results/r3_C_e3.csv 300 cadical,kissat,abc_cec,abc_gcec > results/r3_C_e3.log 2>&1
python3 -u e4_sweep.py results/instances/r3C results/r3_C_sweep.csv 300 > results/r3_C_sweep.log 2>&1
echo R3C_DONE >> results/r3_gen_C.log
