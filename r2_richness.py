"""R2-2: richness of knead (4->4), inflate (2->4), deflate (4->2) windows.

For random windows of random circuits (n = 64, m = 512) we record the number of
equivalent sequences and classify 20 uniform samples:
  perm      same multiset of gates, different order
  sameskel  same sequence of (target, controls), different phi
  pair      contains two identical adjacent gates (an inserted identity pair)
  newskel   anything else (a genuinely different skeleton)
"""
import sys, json, time, collections
import numpy as np
import model, mix
from e1_richness import windows_from


def classify(orig, seq):
    if sorted(seq) == sorted(orig):
        return "perm"
    if len(seq) == len(orig) and [(g[0], g[1]) for g in seq] == [(g[0], g[1]) for g in orig]:
        return "sameskel"
    if any(seq[i] == seq[i + 1] for i in range(len(seq) - 1)):
        return "pair"
    return "newskel"


def run(gset, kind, nwin, beta=None, smax=7, seed=3):
    w, L = {"knead": (4, 4), "inflate": (2, 4), "deflate": (4, 2), "w3": (3, 3)}[kind]
    rng = np.random.default_rng(seed)
    recs, t_sum = [], 0.0
    rep = 0
    while len(recs) < nwin:
        geo = model.Geometry(64, 2, 8.0, seed=700 + rep, beta=beta); rep += 1
        C = model.random_circuit(geo, gset, 512, rng)
        got = 0
        while got < 25 and len(recs) < nwin:
            W = mix._window(C, w, rng, smax if w == 4 else 99)
            if W is None:
                break
            orig = [C[k] for k in W]
            t0 = time.time()
            Sw, F, sol = mix.solutions(orig, geo, gset, L)
            t_sum += time.time() - t0
            alt = sol.total - (1 if w == L else 0)
            cls = collections.Counter()
            if alt > 0:
                for _ in range(20):
                    s = sol.sample(rng)
                    if s != orig:
                        cls[classify(orig, s)] += 1
            recs.append(dict(s=len(Sw), alt=alt, **cls))
            got += 1
    n = len(recs)
    out = dict(windows=n, frac_alt=sum(r["alt"] > 0 for r in recs) / n,
               median_alt=float(np.median([r["alt"] for r in recs])),
               mean_s=float(np.mean([r["s"] for r in recs])), sec_per_window=t_sum / n)
    tot = collections.Counter()
    for r in recs:
        for k in ("perm", "sameskel", "pair", "newskel"):
            tot[k] += r.get(k, 0)
    ssum = sum(tot.values()) or 1
    out.update({"sample_frac_" + k: tot[k] / ssum for k in ("perm", "sameskel", "pair", "newskel")})
    out["frac_windows_newskel"] = sum(r.get("newskel", 0) > 0 for r in recs) / n
    return out


if __name__ == "__main__":
    nwin = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    res = {}
    for gset, beta in (("B", None), ("Bw", 2.5)):
        for kind in ("w3", "knead", "inflate", "deflate"):
            key = "%s_%s" % (gset, kind)
            res[key] = run(gset, kind, nwin, beta=beta)
            print(key, json.dumps(res[key]), flush=True)
    json.dump(res, open("results/r2_richness.json", "w"), indent=1)
