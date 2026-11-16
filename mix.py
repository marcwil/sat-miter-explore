"""Round 2: rewriting processes that can change the skeleton (XOR gate sets B, Bw).

Step types (all replacements are uniform over the equivalent sequences of the
given length, built from the same gate set on the window's wires, original
excluded):
  knead   : window of 4 gates  -> 4 gates
  inflate : window of 2 gates  -> 4 gates
  deflate : window of 4 gates  -> 2 gates (only if such a circuit exists)
  w3      : window of 3 gates  -> 3 gates (round-1 process, for comparison)

Transcript records use the round-1 format (start, end, order, w, new) so that
check.py validates them unchanged (window length w, replacement of any length).
"""
import ctypes, os, subprocess
import numpy as np
import model

HERE = os.path.dirname(os.path.abspath(__file__))


def _lib():
    so = os.path.join(HERE, "csrc", "libprod4.so")
    if not os.path.exists(so):
        subprocess.run(["gcc", "-O2", "-shared", "-fPIC", "-o", so, os.path.join(HERE, "csrc", "prod4.c")], check=True)
    lib = ctypes.CDLL(so)
    lib.prod4.restype = ctypes.c_int64
    lib.prod4.argtypes = [ctypes.c_int, ctypes.c_int] + [ctypes.c_void_p] * 8
    return lib


LIB = _lib()


def _libfp():
    so = os.path.join(HERE, "csrc", "libprod4fp.so")
    if not os.path.exists(so):
        subprocess.run(["gcc", "-O2", "-shared", "-fPIC", "-o", so, os.path.join(HERE, "csrc", "prod4fp.c")], check=True)
    lib = ctypes.CDLL(so)
    lib.prod4fp.restype = ctypes.c_int64
    lib.prod4fp.argtypes = [ctypes.c_int, ctypes.c_int] + [ctypes.c_void_p] * 4 + [ctypes.c_int] + [ctypes.c_void_p] * 6
    return lib


LIBFP = _libfp()
SAMPLER = "fp"   # "fp" (fingerprinted kernel) or "full" (kernel used for the first round-2 grid)
NS = 16
RNG_HASH = np.random.default_rng(12345).integers(1, 2**63 - 1, size=1 << 12, dtype=np.int64).astype(np.uint64)


# ---------------------------------------------------------------- gate tables
def xor_gates(geo, gset, Sw, heavy=frozenset()):
    gates = model.xor_gates_on(geo, gset, Sw)
    if heavy:
        gates = [g for g in gates if g[0][0] not in heavy]
    return gates


def perms_of(gates, Sw):
    """Vectorised permutation table (k, N) of single XOR gates on wires Sw."""
    pos = {w: i for i, w in enumerate(Sw)}
    N = 1 << len(Sw)
    X = np.arange(N, dtype=np.int64)[None, :]
    PA = np.array([pos[g[0][0]] for g in gates])[:, None]
    PB = np.array([pos[g[1][0]] for g in gates])[:, None]
    PC = np.array([pos[g[1][1]] for g in gates])[:, None]
    PHI = np.array([[g[2][2 * j] for j in range(4)] for g in gates], dtype=np.int64)
    idx = ((X >> PB) & 1) + 2 * ((X >> PC) & 1)
    f = np.take_along_axis(PHI, idx, axis=1)
    return X ^ (f << PA)


def invert(P):
    Pinv = np.empty_like(P)
    Pinv[np.arange(P.shape[0])[:, None], P] = np.arange(P.shape[1])[None, :]
    return Pinv


class Solutions:
    """All sequences of exactly L gates from `gates` with composition F."""

    def __init__(self, F, gates, P, L):
        self.F, self.gates, self.P, self.L = F, gates, P, L
        k, N = P.shape
        self.k, self.N = k, N
        if L == 2:
            Pinv = invert(P)
            G = F[Pinv]  # row i: F o g_i^-1
            lookup = {P[i].tobytes(): i for i in range(k)}
            self.list = [(i, lookup[G[i].tobytes()]) for i in range(k) if G[i].tobytes() in lookup]
            self.total = len(self.list)
        elif L == 3:
            Pinv = np.ascontiguousarray(invert(P), dtype=np.int64)
            Fc = np.ascontiguousarray(F, dtype=np.int64)
            G = Fc[Pinv]  # row i1: F o g_i1^-1
            maxout = 1 << 20
            out = np.empty(2 * maxout, dtype=np.int64)
            cnt = model._LIB.search3(N, k, Pinv.ctypes.data, Fc.ctypes.data, out.ctypes.data, maxout)
            assert cnt <= maxout
            lookup = {P[i].tobytes(): i for i in range(k)}
            self.list = []
            for i1, i3 in out[:2 * cnt].reshape(-1, 2):
                H = Pinv[i3][G[i1]]
                j = lookup.get(H.astype(P.dtype).tobytes())
                if j is not None:
                    self.list.append((gates[i1], gates[j], gates[i3]))
            self.total = len(self.list)
        elif L == 4 and SAMPLER == "fp":
            Pinv = invert(P)
            P32 = np.ascontiguousarray(P, dtype=np.int32)
            Pi32 = np.ascontiguousarray(Pinv, dtype=np.int32)
            F32 = np.ascontiguousarray(F, dtype=np.int32)
            R = np.ascontiguousarray(RNG_HASH[:NS])
            xs = np.ascontiguousarray(np.random.default_rng(N).choice(N, size=min(NS, N), replace=False), dtype=np.int32)
            K = k * k
            self.rows = np.empty(K, dtype=np.int32)
            self.hs = np.empty(K, dtype=np.uint64)
            self.qstart = np.empty(K, dtype=np.int64)
            self.qlen = np.empty(K, dtype=np.int32)
            self.qcount = np.empty(K, dtype=np.int32)
            self.total = int(LIBFP.prod4fp(N, k, P32.ctypes.data, Pi32.ctypes.data, F32.ctypes.data, R.ctypes.data,
                                           len(xs), xs.ctypes.data, self.rows.ctypes.data, self.hs.ctypes.data,
                                           self.qstart.ctypes.data, self.qlen.ctypes.data, self.qcount.ctypes.data))
            self.fp = True
        elif L == 4:
            self.fp = False
            Pinv = invert(P)
            P32 = np.ascontiguousarray(P, dtype=np.int32)
            Pi32 = np.ascontiguousarray(Pinv, dtype=np.int32)
            F32 = np.ascontiguousarray(F, dtype=np.int32)
            R = np.ascontiguousarray(RNG_HASH[:N])
            K = k * k
            self.rows = np.empty(K, dtype=np.int32)
            self.hs = np.empty(K, dtype=np.uint64)
            self.qstart = np.empty(K, dtype=np.int64)
            self.qcount = np.empty(K, dtype=np.int32)
            self.total = int(LIB.prod4(N, k, P32.ctypes.data, Pi32.ctypes.data, F32.ctypes.data, R.ctypes.data,
                                       self.rows.ctypes.data, self.hs.ctypes.data, self.qstart.ctypes.data,
                                       self.qcount.ctypes.data))
        else:
            raise ValueError(L)

    def sample(self, rng):
        if self.total == 0:
            return None
        if self.L == 2:
            i, j = self.list[rng.integers(self.total)]
            return [self.gates[i], self.gates[j]]
        if self.L == 3:
            return list(self.list[rng.integers(self.total)])
        k = self.k
        for _ in range(10):
            c = self.qcount.astype(np.float64)
            r = int(rng.choice(len(c), p=c / c.sum()))
            if self.fp:
                i, j = divmod(r, k)
                q = self.F[invert(self.P[[i]])[0][invert(self.P[[j]])[0]]]  # q[x] = F[g_i^-1[g_j^-1[x]]]
                cand = self.rows[self.qstart[r]: self.qstart[r] + self.qlen[r]]
                ii, jj = np.divmod(cand, k)
                prods = self.P[jj[:, None], self.P[ii]]
                true = cand[np.all(prods == q[None, :], axis=1)]
                assert len(true) == self.qcount[r]
                r2 = int(true[rng.integers(len(true))])
            else:
                r2 = int(self.rows[self.qstart[r] + rng.integers(self.qcount[r])])
            i, j = divmod(r, k)
            i2, j2 = divmod(r2, k)
            seq = [self.gates[i], self.gates[j], self.gates[i2], self.gates[j2]]
            # exact verification (guards against hash collisions)
            idx = np.arange(self.N)
            for g in (i, j, i2, j2):
                idx = self.P[g][idx]
            if np.array_equal(idx, self.F):
                return seq
        raise AssertionError("hash collisions in prod4")


def solutions(window, geo, gset, L, heavy=frozenset()):
    Sw = model.window_wires(window)
    F = model.window_function(window, Sw)
    gates = xor_gates(geo, gset, Sw, heavy)
    P = perms_of(gates, Sw)
    return Sw, F, Solutions(F, gates, P, L)


# ---------------------------------------------------------------- steps
def _window(circ, w, rng, smax):
    for _ in range(50):
        W = model.pick_window(circ, w, rng)
        if W is None:
            continue
        if len(model.window_wires([circ[k] for k in W])) <= smax:
            return W
    return None


def try_step(circ, geo, gset, kind, rng, heavy=frozenset(), smax=7):
    """One attempted step. Returns (new_circ, record) or None if this window has no
    alternative of the requested kind."""
    w, L = {"knead": (4, 4), "inflate": (2, 4), "deflate": (4, 2), "w3": (3, 3)}[kind]
    W = _window(circ, w, rng, smax if w == 4 else 99)
    if W is None:
        return None
    orig = [circ[k] for k in W]
    Sw, F, sol = solutions(orig, geo, gset, L, heavy)
    if sol.total == 0 or (w == L and sol.total == 1):
        return None
    for _ in range(30):
        new = sol.sample(rng)
        if new != orig:
            break
    else:
        return None
    start, end, order = model.reorder_for_window(circ, W)
    nonW = [circ[k] for k in order[:len(order) - w]]
    new_circ = circ[:start] + nonW + list(new) + circ[end:]
    rec = dict(start=start, end=end, order=[k - start for k in order], w=w, new=list(new), kind=kind)
    return new_circ, rec


def process(circ, geo, gset, t, rng, mode, heavy=frozenset(), max_tries=200, target=None):
    """mode:
      'w3'        : round-1 process (3 -> 3)
      'knead'     : 4 -> 4 only (size fixed)
      'ik'        : inflate (2->4) and knead (4->4); size control: inflate while
                    len < 1.25 m, deflate (4->2) attempts while len > 1.25 m.
    Returns (circ, transcript, stats)."""
    m0 = len(circ)
    tr = []
    tries = 0
    stats = dict(attempts=0, inflate=0, deflate=0, knead=0, w3=0)
    if target is None:
        target = int(1.25 * m0)
    while len(tr) < t and tries < max_tries * max(1, t):
        if mode in ("w3", "knead"):
            kind = mode
        else:
            u = rng.random()
            if u < 0.5:
                kind = "knead"
            elif len(circ) < target:
                kind = "inflate"
            else:
                kind = "deflate"
        tries += 1
        stats["attempts"] += 1
        r = try_step(circ, geo, gset, kind, rng, heavy)
        if r is None:
            continue
        circ, rec = r
        tr.append(rec)
        stats[kind] += 1
    stats["final_m"] = len(circ)
    return circ, tr, stats
