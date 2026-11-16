"""Random geometric reversible circuits and function-preserving local rewrites.

Gate representation (all gate sets): a tuple (T, K, table)
  T     : tuple of target wires (rewritten by the gate)
  K     : tuple of control wires (read only)
  table : tuple of ints, index = tgt_bits + (ctrl_bits << len(T)),
          where bit j of tgt_bits is the value of T[j] and bit j of ctrl_bits
          the value of K[j]; entry = new tgt_bits.  For every fixed ctrl value the
          map on tgt_bits is a bijection.

Gate sets
  A   : T = local triple, K = (),        table = uniform permutation of 0..7
  Aw  : T = local triple, K = (c,),      c chosen by weight; two permutations
  B   : T = (a,), K = (b,c), {a,b,c} local;  x_a ^= phi(x_b, x_c), phi depends on both
  Bw  : T = (a,), K = (b,c), {a,b} local, c chosen by weight
"""
import itertools, math, random
import numpy as np

# two-input boolean functions phi(x_b, x_c) given as 4-bit truth tables
# (bit index x_b + 2*x_c) that depend on both inputs: 10 of the 16.
def _depends_on_both(tt):
    f = lambda b, c: (tt >> (b + 2 * c)) & 1
    dep_b = any(f(0, c) != f(1, c) for c in (0, 1))
    dep_c = any(f(b, 0) != f(b, 1) for b in (0, 1))
    return dep_b and dep_c
PHIS = [tt for tt in range(16) if _depends_on_both(tt)]
assert len(PHIS) == 10


def xor_gate(a, b, c, tt):
    """x_a ^= phi(x_b, x_c) with controls stored sorted (unique representation)."""
    if b > c:  # swap roles of the controls in the truth table
        tt = sum(((tt >> (bb + 2 * cc)) & 1) << (cc + 2 * bb) for bb in (0, 1) for cc in (0, 1))
        b, c = c, b
    table = tuple(xa ^ ((tt >> (kb + 2 * kc)) & 1)
                  for idx in range(8)
                  for xa, kb, kc in [(idx & 1, (idx >> 1) & 1, (idx >> 2) & 1)])
    return ((a,), (b, c), table)


def gate_wires(g):
    return set(g[0]) | set(g[1])


def is_xor_gate(g):
    return len(g[0]) == 1


def commute(g, h):
    """Syntactic commutation rule used for windows (verified semantically in check.py).
    Gates commute if no target of one is a wire of the other, except that two
    single-target XOR gates with the same target and disjoint controls-vs-targets commute."""
    Tg, Kg, Th, Kh = set(g[0]), set(g[1]), set(h[0]), set(h[1])
    if Tg & Kh or Th & Kg:
        return False
    if Tg & Th:
        return is_xor_gate(g) and is_xor_gate(h)
    return True


# ---------------------------------------------------------------- geometry
class Geometry:
    def __init__(self, n, d, k_nb=8.0, seed=0, beta=None, alpha=0.0):
        rng = np.random.default_rng(seed)
        vol = {1: 2.0, 2: math.pi, 3: 4.0 * math.pi / 3.0}[d]
        self.n, self.d = n, d
        self.r = (k_nb / (n * vol)) ** (1.0 / d)
        for _ in range(1000):
            pts = rng.random((n, d))
            diff = np.abs(pts[:, None, :] - pts[None, :, :])
            diff = np.minimum(diff, 1.0 - diff)
            dist = np.sqrt((diff ** 2).sum(-1))
            adj = (dist <= self.r) & ~np.eye(n, dtype=bool)
            if self._connected(adj):
                break
        else:
            raise RuntimeError("could not sample connected geometry")
        self.pts, self.dist, self.adj = pts, dist, adj
        self.nbrs = [list(np.nonzero(adj[i])[0]) for i in range(n)]
        self.pairs = [(i, j) for i in range(n) for j in self.nbrs[i] if i < j]
        self.triples = [(i, j, k) for (i, j) in self.pairs for k in self.nbrs[j]
                        if k > j and adj[i, k]]
        if not self.triples:
            raise RuntimeError("no local triples; increase k_nb")
        self.alpha = alpha
        if beta is not None:
            u = rng.random(n)
            self.weight = u ** (-1.0 / (beta - 1.0))  # Pareto, P(W>w)=w^-(beta-1)
        else:
            self.weight = np.ones(n)

    @staticmethod
    def _connected(adj):
        n = len(adj); seen = {0}; stack = [0]
        while stack:
            v = stack.pop()
            for u in np.nonzero(adj[v])[0]:
                if u not in seen:
                    seen.add(int(u)); stack.append(int(u))
        return len(seen) == n

    def is_local(self, wires):
        return all(self.adj[a, b] for a, b in itertools.combinations(wires, 2))

    def sample_control(self, rng, targets):
        w = self.weight.copy()
        if self.alpha > 0:
            dmin = self.dist[:, list(targets)].min(1)
            w = w * (1.0 + dmin / self.r) ** (-self.alpha)
        w[list(targets)] = 0.0
        w = w / w.sum()
        return int(rng.choice(self.n, p=w))


def random_gate(geo, gset, rng):
    if gset == "A":
        T = geo.triples[rng.integers(len(geo.triples))]
        return (tuple(int(x) for x in T), (), tuple(int(x) for x in rng.permutation(8)))
    if gset == "Aw":
        T = tuple(int(x) for x in geo.triples[rng.integers(len(geo.triples))])
        c = geo.sample_control(rng, T)
        table = tuple(int(x) for x in rng.permutation(8)) + tuple(int(x) for x in rng.permutation(8))
        return (T, (c,), table)
    if gset == "B":
        T = [int(x) for x in geo.triples[rng.integers(len(geo.triples))]]
        rng.shuffle(T)
        return xor_gate(T[0], T[1], T[2], PHIS[rng.integers(10)])
    if gset == "Bw":
        a, b = (int(x) for x in geo.pairs[rng.integers(len(geo.pairs))])
        if rng.random() < 0.5:
            a, b = b, a
        c = geo.sample_control(rng, (a, b))
        return xor_gate(a, b, c, PHIS[rng.integers(10)])
    raise ValueError(gset)


def random_circuit(geo, gset, m, rng):
    return [random_gate(geo, gset, rng) for _ in range(m)]


# ---------------------------------------------------------------- simulation
def simulate(circ, n, X):
    """X: uint8 array (n, P) of input bits. Returns final state (n, P)."""
    S = X.copy()
    for g in circ:
        apply_gate(g, S)
    return S


def apply_gate(g, S):
    T, K, table = g
    idx = np.zeros(S.shape[1], dtype=np.int64)
    for j, w in enumerate(T):
        idx |= S[w].astype(np.int64) << j
    for j, w in enumerate(K):
        idx |= S[w].astype(np.int64) << (len(T) + j)
    new = np.asarray(table, dtype=np.int64)[idx]
    for j, w in enumerate(T):
        S[w] = (new >> j) & 1


def window_function(gates, Swires):
    """Permutation F on 2^s states of the wires Swires (bit i <-> Swires[i])."""
    s = len(Swires)
    N = 1 << s
    pos = {w: i for i, w in enumerate(Swires)}
    states = np.arange(N, dtype=np.int64)
    for T, K, table in gates:
        idx = np.zeros(N, dtype=np.int64)
        for j, w in enumerate(T):
            idx |= ((states >> pos[w]) & 1) << j
        for j, w in enumerate(K):
            idx |= ((states >> pos[w]) & 1) << (len(T) + j)
        new = np.asarray(table, dtype=np.int64)[idx]
        for j, w in enumerate(T):
            p = pos[w]
            states = (states & ~(1 << p)) | (((new >> j) & 1) << p)
    return states


# ---------------------------------------------------------------- windows
def pick_window(circ, w, rng, i=None):
    """Convex window: gate i plus repeatedly the first later gate that does not
    commute with the window. Returns (i, last, window_positions) or None."""
    m = len(circ)
    if i is None:
        i = int(rng.integers(m))
    W = [i]
    j = i + 1
    while len(W) < w and j < m:
        if any(not commute(circ[k], circ[j]) for k in W):
            W.append(j)
        j += 1
    if len(W) < w:
        return None
    return W


def reorder_for_window(circ, W):
    """Move the non-window gates of the segment [W[0], W[-1]] in front of it.
    Returns (start, end, segment_order) with segment_order a list of absolute
    positions: non-window gates first, then window gates."""
    start, end = W[0], W[-1] + 1
    Wset = set(W)
    nonW = [k for k in range(start, end) if k not in Wset]
    return start, end, nonW + list(W)


# ---------------------------------------------------------------- exact 2-gate decomposition
def _subsets(mask):
    """all sub-masks of mask (including 0), ascending enumeration order"""
    out = [0]
    bits = [1 << i for i in range(mask.bit_length()) if mask >> i & 1]
    for b in bits:
        out = out + [x | b for x in out]
    return out


def decompose2(F, s, sh1, sh2):
    """Find all (g1, g2) with g2 o g1 = F, g_i of shape sh_i = (Tpos, Kpos) given as
    position tuples into the window wires. Returns None if infeasible, else a dict
    with 'contexts': list of (classes, msize) and data to sample a solution."""
    T1, K1 = sh1; T2, K2 = sh2
    m = lambda ps: sum(1 << p for p in ps)
    Mt1, Mk1, Mt2, Mk2 = m(T1), m(K1), m(T2), m(K2)
    U1, U2 = Mt1 | Mk1, Mt2 | Mk2
    Mid = Mt1 & Mt2
    full = (1 << s) - 1
    X = np.arange(1 << s, dtype=np.int64)
    # 1. wires outside T1 u T2 unchanged
    if np.any((F ^ X) & (full & ~(Mt1 | Mt2))):
        return None
    # 2. outputs on T1\T2 depend only on U1
    A = Mt1 & ~Mt2
    if np.any((F & A) != (F[X & U1] & A)):
        return None
    # 3. outputs on T2 depend only on U1 | U2
    if np.any((F & Mt2) != (F[X & (U1 | U2)] & Mt2)):
        return None
    us = _subsets(U1)
    zs = _subsets(U2 & ~U1)
    msize = 1 << bin(Mid).count("1")
    ctx = {}
    fibers = {}
    for u in us:
        sigma = (u & Mk1 & U2, int(F[u]) & Mt1 & Mk2)
        row = tuple(int(F[u | z]) & Mt2 for z in zs)
        ctx.setdefault(sigma, {}).setdefault(row, []).append(u)
        fib = (u & Mk1, int(F[u]) & A)
        fibers.setdefault(fib, []).append(row)
    for fib, rows in fibers.items():
        if len(rows) != msize or len(set(rows)) != msize:
            return None
    contexts = []
    for sigma, classes in ctx.items():
        if len(classes) != msize:
            return None
        contexts.append(list(classes.values()))
    return dict(T1=T1, K1=K1, T2=T2, K2=K2, Mid=Mid, A=A, msize=msize, contexts=contexts,
                logcount=len(contexts) * math.lgamma(msize + 1))


def _gate_from_map(Tpos, Kpos, Swires, inmap):
    """Build a gate (T, K, table) from a dict local_index -> new_tgt_bits."""
    size = 1 << (len(Tpos) + len(Kpos))
    table = tuple(inmap[i] for i in range(size))
    return (tuple(Swires[p] for p in Tpos), tuple(Swires[p] for p in Kpos), table)


def sample_decomposition(F, s, Swires, dec, rng):
    """Sample a uniformly random (g1, g2) from a feasible decompose2 result."""
    T1, K1, T2, K2, Mid, A, msize = (dec[k] for k in ("T1", "K1", "T2", "K2", "Mid", "A", "msize"))
    midpos = [p for p in range(s) if Mid >> p & 1]
    mval = {}
    for classes in dec["contexts"]:
        perm = rng.permutation(msize)
        for ci, us in enumerate(classes):
            for u in us:
                mval[u] = int(perm[ci])
    # g1: for each u (bits on U1) -> new value of T1 bits
    def loc_index(state, Tpos, Kpos):
        idx = 0
        for j, p in enumerate(Tpos):
            idx |= ((state >> p) & 1) << j
        for j, p in enumerate(Kpos):
            idx |= ((state >> p) & 1) << (len(Tpos) + j)
        return idx
    g1map = {}
    for u, mv in mval.items():
        newstate = int(F[u]) & A  # T1\T2 part
        for j, p in enumerate(midpos):
            newstate |= ((mv >> j) & 1) << p
        tgt = 0
        for j, p in enumerate(T1):
            tgt |= ((newstate >> p) & 1) << j
        g1map[loc_index(u, T1, K1)] = tgt
    g1 = _gate_from_map(T1, K1, Swires, g1map)
    # g2 from y = g1(x) -> F(x)
    pos = {w: i for i, w in enumerate(Swires)}
    Y = window_function([g1], Swires)
    g2map = {}
    for x in range(1 << s):
        y = int(Y[x]); fx = int(F[x])
        li = loc_index(y, T2, K2)
        tgt = 0
        for j, p in enumerate(T2):
            tgt |= ((fx >> p) & 1) << j
        if g2map.get(li, tgt) != tgt:
            raise AssertionError("g2 not well defined")
        g2map[li] = tgt
    g2 = _gate_from_map(T2, K2, Swires, g2map)
    assert np.array_equal(window_function([g1, g2], Swires), F)
    return [g1, g2]


def shapes_for(geo, gset, Swires):
    """All gate shapes (Tpos, Kpos) available on the window wires for gate set gset."""
    s = len(Swires)
    out = []
    if gset in ("A", "Aw"):
        for T in itertools.combinations(range(s), 3):
            if not geo.is_local([Swires[p] for p in T]):
                continue
            if gset == "A":
                out.append((T, ()))
            else:
                for c in range(s):
                    if c not in T:
                        out.append((T, (c,)))
    return out


def dependency_matrix(F, s):
    """D[o, i] = True iff output bit o of F depends on input bit i."""
    X = np.arange(1 << s, dtype=np.int64)
    D = np.zeros((s, s), dtype=bool)
    for i in range(s):
        diff = F ^ F[X ^ (1 << i)]
        for o in range(s):
            D[o, i] = bool(np.any((diff >> o) & 1))
    return D


def equivalent_2gate(F, Swires, geo, gset):
    """All feasible 2-gate shapes for F (gate sets A, Aw). Returns list of decs."""
    s = len(Swires)
    D = dependency_matrix(F, s)
    changed = {o for o in range(s) if np.any(((F >> o) & 1) != ((np.arange(1 << s) >> o) & 1))}
    shapes = shapes_for(geo, gset, Swires)
    res = []
    for sh1 in shapes:
        U1 = set(sh1[0]) | set(sh1[1])
        for sh2 in shapes:
            T12 = set(sh1[0]) | set(sh2[0])
            if not changed <= T12:
                continue
            U12 = U1 | set(sh2[0]) | set(sh2[1])
            ok = True
            for o in range(s):
                deps = set(np.nonzero(D[o])[0])
                if o in sh2[0]:
                    if not deps <= U12: ok = False; break
                elif o in sh1[0]:
                    if not deps <= U1: ok = False; break
            if not ok:
                continue
            dec = decompose2(F, s, sh1, sh2)
            if dec is not None:
                res.append(dec)
    return res


# ---------------------------------------------------------------- gate sets B / Bw: meet in the middle
def xor_gates_on(geo, gset, Swires):
    s = len(Swires)
    gates = []
    for a in Swires:
        for b, c in itertools.combinations([x for x in Swires if x != a], 2):
            if gset == "B":
                if not geo.is_local([a, b, c]):
                    continue
                pairs = [(b, c)]
            else:  # Bw: one local control, the other arbitrary
                if not (geo.adj[a, b] or geo.adj[a, c]):
                    continue
                pairs = [(b, c)]
            for (bb, cc) in pairs:
                for tt in PHIS:
                    gates.append(xor_gate(a, bb, cc, tt))
    # dedupe
    return list(dict.fromkeys(gates))


def gate_perms(gates, Swires):
    return np.stack([window_function([g], Swires) for g in gates]) if gates else np.zeros((0, 1 << len(Swires)), dtype=np.int64)


def equivalent_xor(F, Swires, geo, gset, w, cap=None):
    """All sequences of exactly w gates from the gate set on Swires computing F (w = 2 or 3)."""
    gates = xor_gates_on(geo, gset, Swires)
    P = gate_perms(gates, Swires)
    N = P.shape[1]
    Pinv = np.empty_like(P)
    Pinv[np.arange(len(P))[:, None], P] = np.arange(N)[None, :]
    lookup = {P[i].tobytes(): i for i in range(len(P))}
    sols = []
    if w == 2:
        # F = g2 o g1  ->  g2 = F o g1^-1 : G[x] = F[g1inv[x]]
        G = F[Pinv]  # (k, N)
        for i1 in range(len(P)):
            j = lookup.get(G[i1].tobytes())
            if j is not None:
                sols.append((gates[i1], gates[j]))
    elif w == 3:
        # F = g3 o g2 o g1  ->  g2 = g3^-1 o F o g1^-1 : H[x] = g3inv[F[g1inv[x]]]
        G = F[Pinv]  # (k, N): F o g1^-1
        for i3 in range(len(P)):
            H = Pinv[i3][G]  # (k, N)
            for i1 in range(len(P)):
                j = lookup.get(H[i1].tobytes())
                if j is not None:
                    sols.append((gates[i1], gates[j], gates[i3]))
                    if cap and len(sols) >= cap:
                        return sols
    return sols


def equivalent_xor_fast(F, Sw, geo, gset, w):
    """Same as equivalent_xor but vectorised with 64-bit row hashes (verified exactly)."""
    gates = xor_gates_on(geo, gset, Sw)
    P = gate_perms(gates, Sw).astype(np.int64)
    k, N = P.shape
    Pinv = np.empty_like(P)
    Pinv[np.arange(k)[:, None], P] = np.arange(N)[None, :]
    R = np.random.default_rng(7).integers(1, 2**62, size=N, dtype=np.int64).astype(np.uint64)
    hP = (P.astype(np.uint64) * R).sum(1)
    order = np.argsort(hP); hs = hP[order]
    def lookup(rows):
        h = (rows.astype(np.uint64) * R).sum(1)
        idx = np.searchsorted(hs, h)
        idx[idx >= len(hs)] = 0
        hit = hs[idx] == h
        return hit, order[idx]
    sols = []
    G = F[Pinv]  # row i1: F o g1^-1
    if w == 2:
        hit, j = lookup(G)
        for i1 in np.nonzero(hit)[0]:
            if np.array_equal(P[j[i1]], G[i1]):
                sols.append((gates[i1], gates[j[i1]]))
    else:
        for i3 in range(k):
            H = Pinv[i3][G]
            hit, j = lookup(H)
            for i1 in np.nonzero(hit)[0]:
                if np.array_equal(P[j[i1]], H[i1]):
                    sols.append((gates[i1], gates[j[i1]], gates[i3]))
    return sols


# ---------------------------------------------------------------- rewriting process
def window_wires(gates):
    ws = set()
    for g in gates:
        ws |= gate_wires(g)
    return sorted(ws)


def candidates(circ_window, geo, gset):
    """Equivalent same-length replacements for a window. Returns (kind, payload)."""
    Swires = window_wires(circ_window)
    F = window_function(circ_window, Swires)
    w = len(circ_window)
    if gset in ("A", "Aw"):
        assert w == 2
        return Swires, F, equivalent_2gate(F, Swires, geo, gset)
    sols = equivalent_xor_fast(F, Swires, geo, gset, w)
    return Swires, F, sols


def rewrite_step(circ, geo, gset, w, rng, max_tries=200):
    """One rewrite: returns (new_circ, step_record) or None after max_tries windows
    without any alternative."""
    for _ in range(max_tries):
        W = pick_window(circ, w, rng)
        if W is None:
            continue
        orig = [circ[k] for k in W]
        Swires, F, cands = candidates(orig, geo, gset)
        if gset in ("A", "Aw"):
            if not cands:
                raise AssertionError("original decomposition not found")
            logw = np.array([d["logcount"] for d in cands])
            if len(cands) == 1 and logw[0] < 1e-9:
                continue  # unique decomposition = the original: no alternative
            pr = np.exp(logw - logw.max()); pr /= pr.sum()
            new = None
            for _t in range(20):
                dec = cands[int(rng.choice(len(cands), p=pr))]
                new = sample_decomposition(F, len(Swires), Swires, dec, rng)
                if new != orig:
                    break
            if new == orig:
                continue
        else:
            alts = [c for c in cands if list(c) != orig]
            if not alts:
                continue
            new = list(alts[int(rng.integers(len(alts)))])
        start, end, order = reorder_for_window(circ, W)
        nonW = [circ[k] for k in order[:len(order) - w]]
        new_circ = circ[:start] + nonW + new + circ[end:]
        rec = dict(start=start, end=end, order=[k - start for k in order], w=w, new=new)
        return new_circ, rec
    return None


def rewrite(circ, geo, gset, w, t, rng):
    transcript = []
    fails = 0
    for _ in range(t):
        r = rewrite_step(circ, geo, gset, w, rng)
        if r is None:
            fails += 1
            break
        circ, rec = r
        transcript.append(rec)
    return circ, transcript
