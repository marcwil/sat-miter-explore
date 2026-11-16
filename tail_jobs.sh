#!/bin/bash
# Remaining round-1 jobs, run sequentially after the big-grid solve so timings are not disturbed.
set -x
cd "$(dirname "$0")"
until grep -q "big solve done" "$1" 2>/dev/null; do sleep 20; done
python3 -u e4_sweep.py results/instances/big results/e4_sweep_big.csv 300 > results/e4_sweep_big.log 2>&1
N=results/instances/n64
python3 -u e5_backdoor.py results/e5_backdoor.csv 300 $N/Aw_n64_d2_m8_w2_t0_s0_b2.5.cnf $N/Aw_n64_d2_m8_w2_t1_s0_b2.5.cnf \
    $N/A_n64_d2_m8_w2_t0_s0.cnf $N/A_n64_d2_m8_w2_t1_s0.cnf > results/e5_backdoor.log 2>&1
# clean re-timing (machine otherwise idle)
python3 -u run.py solve $N results/e3_n64_clean.csv 300 cadical,kissat,abc_cec,abc_gcec "_t(0|1|10)_s[012](_b2.5)?$" > results/e3_n64_clean.log 2>&1
echo TAIL_DONE
