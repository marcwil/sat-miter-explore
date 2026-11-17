"""Round 3 / C2 arm (iii), gate-first check: weighted gate arity.

Circuits mix 2-control XOR gates (gate set B) with heavy gates
    x_a ^= AND(l_b, l_c, l_e)       (multi-controlled Toffoli with literal polarities)
where {a, b, c} is a local triple and the extra control e comes from the
long-range kernel. Fraction of heavy gates q3 (default 0.25).

For 300 knead windows (4 gates, <= 7 wires) that contain at least one heavy gate
we compute all equivalent 4-gate sequences over the gate set on the window's wires:
  B gates on local triples (10 phi) + Toffoli gates (a; b, c local triple, e any
  other wire of the window; 8 polarities).
Kill criteria (plan): fraction with a new-skeleton alternative not above 52%
(gate set B knead), < 5% of heavy windows fit the wire cap, or > 1 s per step.
"""
import sys, json, time, collections, itertools
import numpy as np
import model, mix
from r2_richness import classify


def toffoli_gate(a, ctrls, pol):
    """x_a ^= AND_i (x_{ctrls[i]} == pol[i]); controls stored sorted"""
    order = sorted(range(len(ctrls)), key=lambda i: ctrls[i])
    cs = tuple(ctrls[i] for i in order)
    ps = tuple(pol[i] for i in order)
    k = len(cs)
    table = []
    for idx in range(1 << (1 + k)):
        xa = idx & 1
        bits = [(idx >> (1 + i)) & 1 for i in range(k)]
        table.append(xa ^ int(all(b == p for b, p in zip(bits, ps))))
    return ((a,), cs, tuple(table))


def random_mixed_gate(geo, rng, q3):
    g = model.random_gate(geo, "B", rng)
    if rng.random() >= q3:
        return g
    a, (b, c) = g[0][0], g[1]
    e = geo.sample_long(rng, a, [a, b, c])
    return toffoli_gate(a, (b, c, e), tuple(int(x) for x in rng.integers(0, 2, 3)))


def gate_set(geo, Sw):
    gates = list(model.xor_gates_on(geo, "B", Sw))
    for a in Sw:
        for b, c in itertools.combinations([x for x in Sw if x != a], 2):
            if not geo.is_local([a, b, c]):
                continue
            for e in Sw:
                if e in (a, b, c):
                    continue
                for pol in itertools.product((0, 1), repeat=3):
                    gates.append(toffoli_gate(a, (b, c, e), pol))
    return list(dict.fromkeys(gates))


if __name__ == "__main__":
    nwin = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    q3 = float(sys.argv[2]) if len(sys.argv) > 2 else 0.25
    rng = np.random.default_rng(5)
    recs, heavy_windows_total, heavy_windows_fit, tsum, ksum = [], 0, 0, 0.0, 0
    rep = 0
    while len(recs) < nwin:
        geo = model.Geometry(64, 2, 8.0, seed=900 + rep); rep += 1
        C = [random_mixed_gate(geo, rng, q3) for _ in range(512)]
        for _ in range(400):
            if len(recs) >= nwin:
                break
            W = model.pick_window(C, 4, rng)
            if W is None:
                continue
            win = [C[k] for k in W]
            if not any(len(g[1]) == 3 for g in win):
                continue
            heavy_windows_total += 1
            Sw = model.window_wires(win)
            if len(Sw) > 7:
                continue
            heavy_windows_fit += 1
            t0 = time.time()
            F = model.window_function(win, Sw)
            gates = gate_set(geo, Sw)
            P = np.stack([model.window_function([g], Sw) for g in gates])
            sol = mix.Solutions(F, gates, P, 4)
            tsum += time.time() - t0; ksum += len(gates)
            alt = sol.total - 1
            cls = collections.Counter()
            if alt > 0:
                for _ in range(20):
                    s = sol.sample(rng)
                    if s != win:
                        cls[classify(win, s)] += 1
            recs.append(dict(alt=alt, newskel=cls.get("newskel", 0) > 0, s=len(Sw), k=len(gates)))
    n = len(recs)
    out = dict(windows=n, frac_alt=sum(r["alt"] > 0 for r in recs) / n,
               frac_windows_newskel=sum(r["newskel"] for r in recs) / n,
               frac_heavy_windows_fit_cap=heavy_windows_fit / heavy_windows_total,
               sec_per_window=tsum / n, mean_gate_set_size=ksum / n, q3=q3,
               baseline_B_knead_newskel=0.52)
    print(json.dumps(out, indent=1))
    json.dump(out, open("results/r3_toffoli_check.json", "w"), indent=1)
