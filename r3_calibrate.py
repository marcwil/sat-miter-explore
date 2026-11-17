"""Round 3 / A: calibration of the layer-cut width estimator.

Controls (expected value):
  t = 0                                      -> 1
  C_0 vs a random commuting reordering        -> 1   (random topological order of
                                                      the dependency DAG of model.commute)
  round-1 gate set A, gauge-only rewriting    -> <= 3 (<= 5 where one of the ~2% skeleton
                                                      changes sits at the cut), flat in n
  null: C_0 vs an unrelated random circuit    -> baseline, per n
  P sensitivity: P = 64 vs 256 vs 1024        -> same values
Writes results/r3_calibration.csv.
"""
import sys, os, csv, json, time
from concurrent.futures import ProcessPoolExecutor
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def random_topo(circ, rng):
    """random linear extension of the dependency DAG (non-commuting pairs keep their order)"""
    sys.path.insert(0, HERE)
    import model
    m = len(circ)
    preds = [set() for _ in range(m)]
    for j in range(m):
        for i in range(j):
            if not model.commute(circ[i], circ[j]):
                preds[j].add(i)
    succ = [[] for _ in range(m)]
    for j in range(m):
        for i in preds[j]:
            succ[i].append(j)
    indeg = [len(p) for p in preds]
    ready = [i for i in range(m) if indeg[i] == 0]
    out = []
    while ready:
        k = ready.pop(rng.integers(len(ready)))
        out.append(circ[k])
        for s in succ[k]:
            indeg[s] -= 1
            if indeg[s] == 0:
                ready.append(s)
    assert len(out) == m
    return out


def job(spec):
    sys.path.insert(0, HERE)
    import model, instance, width
    kind, arg, P = spec
    t0 = time.time()
    if kind == "inst":
        inst = instance.load(arg)
        n = inst["params"]["n"]
        C0, Ct = inst["C0"], inst["Ct"]
        label = os.path.basename(arg)[:-5]
    elif kind == "shuffle":
        inst = instance.load(arg)
        n = inst["params"]["n"]
        C0 = inst["C0"]
        Ct = random_topo(C0, np.random.default_rng(7))
        X = (np.random.default_rng(1).random((n, 2000)) < 0.5).astype(np.uint8)
        assert np.array_equal(model.simulate(C0, n, X), model.simulate(Ct, n, X))
        label = "shuffle:" + os.path.basename(arg)[:-5]
    elif kind in ("null", "nullU"):
        n, s = arg
        geo = model.Geometry(n, 2, 8.0, seed=1000 + s, wiring="uniform" if kind == "nullU" else "geo")
        C0 = model.random_circuit(geo, "B", 8 * n, np.random.default_rng(s))
        Ct = model.random_circuit(geo, "B", 8 * n, np.random.default_rng(100 + s))
        label = "%s:B_n%d_s%d" % (kind, n, s)
    rows = width.width_layers(C0, Ct, n, P=P)
    r = dict(label=label, kind=kind, n=n, P=P, seconds=round(time.time() - t0, 1))
    r.update(width.summary_layers(rows))
    return r


if __name__ == "__main__":
    D = "results/instances"
    specs = [("inst", D + "/n64/B_n64_d2_m8_w3_t0_s0.json", 256),
             ("shuffle", D + "/n64/B_n64_d2_m8_w3_t0_s0.json", 256),
             ("shuffle", D + "/big/B_n128_d2_m8_w3_t0_s0.json", 256)]
    for s in (0, 1):
        specs += [("inst", D + "/n64/A_n64_d2_m8_w2_t10_s%d.json" % s, 256),
                  ("inst", D + "/big/A_n128_d2_m8_w2_t10_s%d.json" % s, 256),
                  ("inst", D + "/big/A_n256_d2_m8_w2_t10_s%d.json" % s, 256)]
        specs += [("null", (n, s), 256) for n in (32, 64, 128)]
    specs += [("inst", D + "/r2long/B_n64_d2_m8_w4_t30_s0_Pknead.json", P) for P in (64, 1024)]
    specs += [("null", (64, 0), P) for P in (64, 1024)]
    out = "results/r3_calibration.csv"
    rows = []
    with ProcessPoolExecutor(4) as ex:
        for r in ex.map(job, specs):
            rows.append(r)
            print(json.dumps(r), flush=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
