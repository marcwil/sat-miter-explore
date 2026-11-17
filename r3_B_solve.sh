#!/bin/sh
# Round 3 / B follow-up: t=0 baselines, then solvers + sweeping on the scaling instances (n = 32..256)
cd "$(dirname "$0")"
python3 -u r2_gen.py grids/r3_B_t0.json results/instances/r3B 4 > results/r3_B_solve.log 2>&1
python3 -u r2_gen.py grids/r3_B256_t0.json results/instances/r3B256 2 >> results/r3_B_solve.log 2>&1
for f in results/instances/r3B/*.json results/instances/r3B256/*.json; do b=${f%.json}; for c in c0 ct; do [ -f $b.$c.aig ] || tools/abc/abc -c "read $b.$c.blif; strash; write_aiger $b.$c.aig" >/dev/null 2>&1; done; done
for d in r3B r3B256; do python3 -u run.py solve results/instances/$d results/r3_B_e3.csv 300 cadical,kissat,abc_cec,abc_gcec >> results/r3_B_solve.log 2>&1; done
for d in r3B r3B256; do python3 -u e4_sweep.py results/instances/$d results/r3_B_sweep.csv 300 >> results/r3_B_solve.log 2>&1; done
echo R3BSOLVE_DONE >> results/r3_B_solve.log
