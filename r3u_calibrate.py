"""Uniform-wiring side study: width calibration (t = 0, commuting shuffle, null) for uniform wiring.
  python r3u_calibrate.py   -> results/r3u_calibration.csv"""
import sys, glob, csv, json
from concurrent.futures import ProcessPoolExecutor
from r3_calibrate import job

if __name__ == "__main__":
    D = "results/instances/r3U"
    specs = []
    for n in (32, 64, 128):
        t0 = sorted(glob.glob(D + "/B_n%d_*_t0_s40_Pw3_ws0_U.json" % n))[0]
        specs += [("inst", t0, 256), ("shuffle", t0, 256)]
        specs += [("nullU", (n, s), 256) for s in (0, 1)]
    rows = []
    with ProcessPoolExecutor(4) as ex:
        for r in ex.map(job, specs):
            rows.append(r); print(json.dumps(r), flush=True)
    with open("results/r3u_calibration.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
