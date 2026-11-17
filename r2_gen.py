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
    q["w"] = {"w3": 3, "knead": 4, "ik": 24, "ikfree": 25, "none": 0}[q["mode"]]
    if q.get("c_long") is not None:  # long-range fraction p = c * n^(-1/d) * (n/m)
        q["p_long"] = min(1.0, q["c_long"] / (q["m_per_n"] * q["n"] ** (1.0 / q["d"])))
    geo = model.Geometry(q["n"], q["d"], q["k_nb"], seed=1000 + q["seed"], beta=q["beta"],
                         alpha=q.get("alpha", 0.0), pctrl=q.get("pctrl", 1.0),
                         p_long=q.get("p_long", 0.0), alpha_long=q.get("alpha_long", 2.5))
    heavy = frozenset()
    if q.get("heavy_q"):
        cut = np.quantile(geo.weight, 1 - q["heavy_q"])
        heavy = frozenset(int(v) for v in np.nonzero(geo.weight >= cut)[0])
    rng = np.random.default_rng(q["seed"])
    m = int(round(q["m_per_n"] * q["n"]))
    C0 = []
    while len(C0) < m:
        g = model.random_gate(geo, q["gset"], rng)
        if not any(w in heavy for w in g[0]):
            C0.append(g)
    if q.get("long_arm") == "allowed":  # rewrites may reuse the long-range pairs of C_0
        geo.extra_pairs = {(min(u, v), max(u, v)) for g in C0 if not geo.is_local(list(g[0]) + list(g[1]))
                           for u, v in __import__("itertools").combinations(list(g[0]) + list(g[1]), 2)}
    q["n_long_gates"] = sum(1 for g in C0 if not all(geo.adj[u, v] for u, v in
                                                     __import__("itertools").combinations(list(g[0]) + list(g[1]), 2)))
    plant_tr = []
    if q.get("plant_mult"):  # insert R . R^-1 in the middle of C_0 (R random, same gate set)
        import width
        prng = np.random.default_rng(20_000 + q["seed"])
        R = [model.random_gate(geo, q["gset"], prng) for _ in range(int(q["plant_mult"] * q["n"]))]
        Rinv = [width.inverse_gate(g) for g in reversed(R)]
        h = m // 2
        plant_tr = [dict(start=h, end=h, order=[], w=0, new=R + Rinv, kind="plant")]
        C0_start = C0[:h] + R + Rinv + C0[h:]
    else:
        C0_start = C0
    mix.SAMPLER = q.get("sampler", "fp")
    if q.get("walk_seed") is not None:  # separate randomness for the rewriting walk
        rng = np.random.default_rng(10_000 + q["walk_seed"])
    snaps = sorted(q.get("snap", [q["tfrac"]]))
    out, Ct, tr, done, t0 = [], C0_start, list(plant_tr), 0, time.time()
    agg = {}
    for sf in snaps:
        t = int(round(sf * m))
        if q["mode"] == "none":
            tr_new, st = [], dict(attempts=0, final_m=len(Ct))
        else:
            Ct, tr_new, st = mix.process(Ct, geo, q["gset"], t - done, rng, q["mode"], heavy,
                                         target=int(q.get("size_mult", 1.25) * m))
        tr = tr + tr_new; done = len(tr) - len(plant_tr)
        for k2, v in st.items():
            agg[k2] = agg.get(k2, 0) + v if k2 != "final_m" else v
        qq = dict(q, tfrac=sf, m=m, t=t, t_done=len(tr), gen_time=time.time() - t0,
                  **{"stat_" + k2: v for k2, v in agg.items()}, heavy=sorted(heavy))
        qq.pop("snap", None)
        out.append(dict(params=qq, geo=dict(pts=geo.pts.tolist(), r=geo.r, weight=geo.weight.tolist()),
                        C0=C0, Ct=Ct, transcript=list(tr)))
    return out


def _job(args):
    p, outdir = args
    sys.path.insert(0, HERE)
    import instance
    last = dict(p, tfrac=max(p.get("snap", [p["tfrac"]])))
    last.pop("snap", None); last.pop("sampler", None)
    nm = instance.name_of(dict(instance.DEFAULTS, **last, w={"w3": 3, "knead": 4, "ik": 24, "ikfree": 25, "none": 0}[p["mode"]]))
    if os.path.exists(os.path.join(outdir, nm + ".json")):
        return nm, "exists"
    msgs = []
    for inst in generate(p):
        nm = instance.save(inst, outdir)
        q = inst["params"]
        msgs.append("%s t=%d/%d m_t=%d attempts=%d gen=%.0fs" % (nm, q["t_done"], q["t"], q["stat_final_m"], q["stat_attempts"], q["gen_time"]))
    return "\n".join(msgs), ""


def expand(grids):
    import itertools
    out = []
    for g in grids:
        keys = list(g); vals = [[v] if (k == "snap" or not isinstance(v, list)) else v for k, v in g.items()]
        out += [dict(zip(keys, c)) for c in itertools.product(*vals)]
    return out


if __name__ == "__main__":
    grids = json.load(open(sys.argv[1])); outdir = sys.argv[2]
    jobs = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    os.makedirs(outdir, exist_ok=True)
    plist = expand(grids if isinstance(grids, list) else [grids])
    # longest jobs first
    plist.sort(key=lambda p: -max(p.get("snap", [p["tfrac"]])) * p["n"] * (3 if p["mode"] == "knead" else 1))
    with ProcessPoolExecutor(jobs) as ex:
        for f in as_completed([ex.submit(_job, (p, outdir)) for p in plist]):
            print(*f.result(), flush=True)
