"""Uniform-wiring side study, stage 0: window availability, richness and cost,
uniform vs geometric wiring (gate set B, m = 8n).
  python r3u_stage0.py > results/r3u_stage0.json"""
import sys, json, collections
import numpy as np
import model, mix, r2_richness


def availability(n, wiring, w, nwin=3000, seed=0):
    rng = np.random.default_rng(seed)
    geo = model.Geometry(n, 2, 8.0, seed=800, wiring=wiring)
    C = model.random_circuit(geo, "B", 8 * n, rng)
    cnt = collections.Counter()
    for _ in range(nwin):
        W = model.pick_window(C, w, rng)
        if W:
            cnt[len(model.window_wires([C[k] for k in W]))] += 1
    tot = sum(cnt.values())
    return {s: cnt[s] / tot for s in sorted(cnt)}


if __name__ == "__main__":
    out = []
    for wiring in ("geo", "uniform"):
        for n in (64, 256):
            av4 = availability(n, wiring, 4); av3 = availability(n, wiring, 3)
            row = dict(wiring=wiring, n=n,
                       knead_fits7=sum(v for s, v in av4.items() if s <= 7),
                       knead_fits8=sum(v for s, v in av4.items() if s <= 8),
                       w3_mean_wires=sum(s * v for s, v in av3.items()))
            for kind, smax, nwin in (("w3", 99, 300), ("inflate", 99, 300), ("knead", 7, 300), ("knead", 8, 40)):
                if kind == "knead" and smax == 8 and wiring == "geo":
                    continue
                r = r2_richness.run("B", kind, nwin, smax=smax, n=n, wiring=wiring)
                row["%s_s%d" % (kind, smax) if kind == "knead" else kind] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}
                print(wiring, n, kind, smax, json.dumps(row.get("%s_s%d" % (kind, smax) if kind == "knead" else kind)), file=sys.stderr, flush=True)
            out.append(row)
    json.dump(out, sys.stdout, indent=1)
