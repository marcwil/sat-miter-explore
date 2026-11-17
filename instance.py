"""Generate, save and load miter instances."""
import json, os, time
import numpy as np
import model, encode

DEFAULTS = dict(gset="A", n=64, d=2, k_nb=8.0, m_per_n=8.0, w=2, tfrac=0.0,
                beta=None, alpha=0.0, pctrl=1.0, seed=0)


def name_of(p):
    s = "%s_n%d_d%d_m%g_w%d_t%g_s%d" % (p["gset"], p["n"], p["d"], p["m_per_n"], p["w"], p["tfrac"], p["seed"])
    if p.get("beta") is not None:
        s += "_b%g" % p["beta"]
    if p.get("alpha"):
        s += "_a%g" % p["alpha"]
    if p.get("pctrl", 1.0) != 1.0:
        s += "_p%g" % p["pctrl"]
    if p.get("mode"):
        s += "_P%s" % p["mode"]
    if p.get("heavy_q"):
        s += "_h%g" % p["heavy_q"]
    if p.get("size_mult", 1.25) != 1.25:
        s += "_x%g" % p["size_mult"]
    if p.get("walk_seed") is not None:
        s += "_ws%d" % p["walk_seed"]
    if p.get("c_long") is not None:
        s += "_c%g%s" % (p["c_long"], "A" if p.get("long_arm") == "allowed" else "L")
    if p.get("plant_mult"):
        s += "_R%g" % p["plant_mult"]
    return s


def generate(**kw):
    p = dict(DEFAULTS); p.update(kw)
    geo = model.Geometry(p["n"], p["d"], p["k_nb"], seed=1000 + p["seed"], beta=p["beta"], alpha=p["alpha"],
                         pctrl=p["pctrl"])
    rng = np.random.default_rng(p["seed"])
    m = int(round(p["m_per_n"] * p["n"]))
    C0 = model.random_circuit(geo, p["gset"], m, rng)
    t = int(round(p["tfrac"] * m))
    t0 = time.time()
    Ct, tr = model.rewrite(C0, geo, p["gset"], p["w"], t, rng)
    p.update(m=m, t=t, t_done=len(tr), gen_time=time.time() - t0)
    return dict(params=p, geo=dict(pts=geo.pts.tolist(), r=geo.r, weight=geo.weight.tolist()),
                C0=C0, Ct=Ct, transcript=tr), geo


def _g2j(g):
    return [list(g[0]), list(g[1]), list(g[2])]


def _j2g(g):
    return (tuple(g[0]), tuple(g[1]), tuple(g[2]))


def save(inst, d):
    os.makedirs(d, exist_ok=True)
    nm = name_of(inst["params"])
    js = dict(inst)
    js["C0"] = [_g2j(g) for g in inst["C0"]]
    js["Ct"] = [_g2j(g) for g in inst["Ct"]]
    js["transcript"] = [dict(r, new=[_g2j(g) for g in r["new"]]) for r in inst["transcript"]]
    with open(os.path.join(d, nm + ".json"), "w") as f:
        json.dump(js, f)
    n = inst["params"]["n"]
    cnf, meta = encode.miter(n, inst["C0"], inst["Ct"])
    cnf.write(os.path.join(d, nm + ".cnf"), comments=[nm])
    encode.write_blif(os.path.join(d, nm + ".c0.blif"), n, inst["C0"], "c0")
    encode.write_blif(os.path.join(d, nm + ".ct.blif"), n, inst["Ct"], "ct")
    return nm


def load(path):
    with open(path) as f:
        js = json.load(f)
    js["C0"] = [_j2g(g) for g in js["C0"]]
    js["Ct"] = [_j2g(g) for g in js["Ct"]]
    for r in js["transcript"]:
        r["new"] = [_j2g(g) for g in r["new"]]
    return js
