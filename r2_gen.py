"""Round 2 instance generation: processes 'w3', 'knead', 'ik' (see mix.py).

  python r2_gen.py <grid.json> <outdir> [jobs]
Grid entries: gset, n, m_per_n, mode, tfrac, seed, [beta, alpha, pctrl, heavy_q].
heavy_q: wires whose weight is in the top heavy_q fraction are never targets
(they stay inputs and act only as read-only controls).
"""
import sys, os, json, time, subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def generate(p):
    sys.path.insert(0, HERE)
    import model, mix, instance
    q = dict(instance.DEFAULTS); q.update(p)
    q["w"] = {"w3": 3, "knead": 4, "ik": 24}[q["mode"]]
    geo = model.Geometry(q["n"], q["d"], q["k_nb"], seed=1000 + q["seed"], beta=q["beta"],
                         alpha=q.get("alpha", 0.0), pctrl=q.get("pctrl", 1.0))
    heavy = frozenset()
    if q.get("heavy_q"):
        cut = np.quantile(geo.weight, 1 - q["heavy_q"])
        heavy = frozenset(int(v) for v in np.nonzero(geo.weight >= cut)[0])
    rng = np.random.default_rng(q["seed"])
    m = int(round(q["m_per_n"] * q["n"]))
    C0 = []
    while len(C0) < m:
        g = model.random_gate(geo, q["gset"], rng)
        if g[0][0] not in heavy:
            C0.append(g)
    t = int(round(q["tfrac"] * m))
    t0 = time.time()
    Ct, tr, st = mix.process(C0, geo, q["gset"], t, rng, q["mode"], heavy)
    q.update(m=m, t=t, t_done=len(tr), gen_time=time.time() - t0, **{"stat_" + k: v for k, v in st.items()},
             heavy=sorted(heavy))
    inst = dict(params=q, geo=dict(pts=geo.pts.tolist(), r=geo.r, weight=geo.weight.tolist()),
                C0=C0, Ct=Ct, transcript=[{k: v for k, v in r.items() if k != "kind"} | {"kind": r["kind"]} for r in tr])
    return inst


def _job(args):
    p, outdir = args
    sys.path.insert(0, HERE)
    import instance
    nm = instance.name_of(dict(instance.DEFAULTS, **p, w={"w3": 3, "knead": 4, "ik": 24}[p["mode"]]))
    if os.path.exists(os.path.join(outdir, nm + ".json")):
        return nm, "exists"
    inst = generate(p)
    nm = instance.save(inst, outdir)
    q = inst["params"]
    return nm, "t=%d/%d m_t=%d attempts=%d gen=%.0fs" % (q["t_done"], q["t"], q["stat_final_m"], q["stat_attempts"], q["gen_time"])


def expand(grids):
    import itertools
    out = []
    for g in grids:
        keys = list(g); vals = [v if isinstance(v, list) else [v] for v in g.values()]
        out += [dict(zip(keys, c)) for c in itertools.product(*vals)]
    return out


if __name__ == "__main__":
    grids = json.load(open(sys.argv[1])); outdir = sys.argv[2]
    jobs = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    os.makedirs(outdir, exist_ok=True)
    plist = expand(grids if isinstance(grids, list) else [grids])
    # longest jobs first
    plist.sort(key=lambda p: -p["tfrac"] * p["n"] * (3 if p["mode"] == "knead" else 1))
    with ProcessPoolExecutor(jobs) as ex:
        for f in as_completed([ex.submit(_job, (p, outdir)) for p in plist]):
            print(*f.result(), flush=True)
