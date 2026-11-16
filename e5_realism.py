"""E5 realism: variable degree distribution of the miter CNF and how geometric the
formula looks before / after removing high-degree variables.

For each instance: variable degree = number of clauses containing the variable.
Variable incidence graph: two variables adjacent if they share a clause. Each
circuit variable belongs to a wire (and so to a point on the torus). We sample
pairs of variables and correlate graph hop distance with torus distance of their
wires, (a) on the whole graph, (b) after deleting variables of degree above the
99th percentile of the unweighted model's degree (the 'hubs').
"""
import sys, json, glob, os, collections
import numpy as np
import instance, encode

OUT = "results/e5_realism.json"


def var_wires(n, C0, Ct, cnf, meta):
    vw = {}
    for i, v in enumerate(meta["xs"]):
        vw[v] = i
    for circ, recs in ((C0, meta["rec0"]), (Ct, meta["rect"])):
        for g, (ins, outs) in zip(circ, recs):
            for w, v in zip(g[0], outs):
                vw[v] = w
    return vw


def bfs_dist(adj, src, allowed):
    dist = {src: 0}
    frontier = [src]
    while frontier:
        nxt = []
        for v in frontier:
            for u in adj[v]:
                if u in allowed and u not in dist:
                    dist[u] = dist[v] + 1
                    nxt.append(u)
        frontier = nxt
    return dist


def analyse(path, cutoff=None, nsrc=30, seed=0):
    inst = instance.load(path)
    n = inst["params"]["n"]
    cnf, meta = encode.miter(n, inst["C0"], inst["Ct"])
    deg = collections.Counter(abs(l) for c in cnf.clauses for l in c)
    vw = var_wires(n, inst["C0"], inst["Ct"], cnf, meta)
    pts = np.array(inst["geo"]["pts"])
    adj = collections.defaultdict(set)
    for c in cnf.clauses[:-1]:  # skip the big output OR clause
        vs = [abs(l) for l in c]
        for a in vs:
            adj[a].update(vs)
    for a in adj:
        adj[a].discard(a)
    rng = np.random.default_rng(seed)
    circ_vars = [v for v in vw]

    def corr(allowed):
        src = rng.choice([v for v in circ_vars if v in allowed], size=nsrc, replace=False)
        gd, td = [], []
        for s in src:
            dist = bfs_dist(adj, int(s), allowed)
            for u, dd in dist.items():
                if u in vw and u != s:
                    diff = np.abs(pts[vw[int(s)]] - pts[vw[u]]); diff = np.minimum(diff, 1 - diff)
                    gd.append(dd); td.append(float(np.sqrt((diff ** 2).sum())))
        gd, td = np.array(gd), np.array(td)
        reach = len(gd) / (nsrc * (len(allowed) - 1))
        return dict(spearman=float(_spearman(gd, td)), mean_hops=float(gd.mean()), reach=float(reach))

    allv = set(adj)
    res = dict(instance=os.path.basename(path), degs=sorted(deg.values()),
               max_deg=max(deg.values()), whole=corr(allv))
    if cutoff is not None:
        kept = {v for v in allv if deg[v] <= cutoff}
        res["removed"] = len(allv) - len(kept)
        res["hubs_removed"] = corr(kept)
    return res


def _spearman(a, b):
    ra = np.argsort(np.argsort(a)); rb = np.argsort(np.argsort(b))
    return np.corrcoef(ra, rb)[0, 1]


if __name__ == "__main__":
    d = sys.argv[1]
    out = {}
    # cutoff from the unweighted model: 99th percentile of A degrees
    base = analyse(os.path.join(d, "A_n64_d2_m8_w2_t1_s0.json"))
    cutoff = float(np.percentile(base["degs"], 99))
    names = ["A_n64_d2_m8_w2_t1_s0", "B_n64_d2_m8_w3_t1_s0"] + \
        ["%s_n64_d2_m8_w%d_t1_s0_b%s" % (g, w, b) for g, w in (("Aw", 2), ("Bw", 3)) for b in ("2.2", "2.5", "3")]
    for nm in names:
        p = os.path.join(d, nm + ".json")
        if not os.path.exists(p):
            continue
        r = analyse(p, cutoff=cutoff)
        degs = np.array(r.pop("degs"))
        r["deg_quantiles"] = {q: float(np.percentile(degs, q)) for q in (50, 90, 99, 99.9, 100)}
        r["deg_hist"] = {int(k): int(v) for k, v in zip(*np.unique(degs, return_counts=True))}
        out[nm] = r
        print(json.dumps({k: v for k, v in r.items() if k != "deg_hist"}), flush=True)
    out["cutoff"] = cutoff
    json.dump(out, open(OUT, "w"), indent=1)
