"""Survival statistics of an instance (E2), computed by random simulation.

For both circuits we record every signal (gate output bit) and every gate *group*
(the values of all wires of a gate right after it: new targets + controls) on P
random input patterns.
  eq_frac   : fraction of C_0 internal signals equal or complementary to some C_t
              internal signal (internal = gate output, not the final value of a wire)
  rel_frac  : fraction of C_0 gate groups related by a bijection to some C_t gate
              group (canonical relabelled signature; includes equalities)
  gate_frac : fraction of C_0 gates (as exact tuples) that also occur in C_t
False positives are possible only if two different functions agree on all P
random patterns; P = 1024 makes this negligible for balanced functions.
"""
import sys, json, collections
import numpy as np
import model, instance


def trace(circ, n, X):
    """Returns (signals, groups, final): signals = list of (gate idx, bit vector)
    for internal gate outputs; groups = list of value-vectors (ints < 2^k) per gate."""
    S = X.copy()
    last_writer = {}
    sigs, groups = [], []
    for gi, g in enumerate(circ):
        model.apply_gate(g, S)
        ws = list(g[0]) + list(g[1])
        val = np.zeros(S.shape[1], dtype=np.int64)
        for j, w in enumerate(ws):
            val |= S[w].astype(np.int64) << j
        groups.append(val)
        for w in g[0]:
            sigs.append((gi, w, S[w].copy()))
            last_writer[w] = len(sigs) - 1
    final = set(last_writer.values())
    internal = [s[2] for k, s in enumerate(sigs) if k not in final]
    return internal, groups


def canon_bits(v):
    b = np.packbits(v)
    if v[0]:
        b = np.packbits(1 - v)
    return b.tobytes()


def canon_group(val):
    # relabel values by order of first occurrence
    _, first_idx, inv = np.unique(val, return_index=True, return_inverse=True)
    order = np.argsort(np.argsort(first_idx))
    return order[inv].astype(np.int16).tobytes()


def instance_stats(inst, P=1024, seed=0, cond=None):
    """cond: optional dict wire -> bit, fixes those input bits (conditional statistics)."""
    n = inst["params"]["n"]
    rng = np.random.default_rng(seed)
    X = (rng.random((n, P)) < 0.5).astype(np.uint8)
    if cond:
        for w, b in cond.items():
            X[w] = b
    s0, g0 = trace(inst["C0"], n, X)
    st, gt = trace(inst["Ct"], n, X)
    tset = {canon_bits(v) for v in st}
    eq = sum(canon_bits(v) in tset for v in s0)
    gset_t = {canon_group(v) for v in gt}
    rel = sum(canon_group(v) in gset_t for v in g0)
    c0 = collections.Counter(inst["C0"]); ct = collections.Counter(inst["Ct"])
    same = sum((c0 & ct).values())
    return dict(eq_frac=eq / max(1, len(s0)), rel_frac=rel / max(1, len(g0)),
                gate_frac=same / len(inst["C0"]), n_internal=len(s0))


if __name__ == "__main__":
    for path in sys.argv[1:]:
        inst = instance.load(path)
        print(path, json.dumps(instance_stats(inst)))
