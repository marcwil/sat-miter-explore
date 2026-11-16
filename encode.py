"""Miter CNF (DIMACS) and BLIF encodings of circuits from model.py."""
import functools, itertools


@functools.lru_cache(maxsize=None)
def prime_implicants(nvars, onset):
    """Quine-McCluskey. onset: frozenset of minterms. Returns list of (value, dcmask)."""
    cur = {(mt, 0) for mt in onset}
    primes = set()
    while cur:
        nxt, used = set(), set()
        lst = sorted(cur)
        for (v1, m1), (v2, m2) in itertools.combinations(lst, 2):
            if m1 != m2:
                continue
            diff = v1 ^ v2
            if diff and diff & (diff - 1) == 0:
                nxt.add((v1 & ~diff, m1 | diff))
                used.add((v1, m1)); used.add((v2, m2))
        primes |= cur - used
        cur = nxt
    return sorted(primes)


def gate_bit_functions(g):
    """For gate g=(T,K,table): list over target bits j of the onset of bit j as a
    function of the local input index (T bits low, K bits high)."""
    T, K, table = g
    nin = len(T) + len(K)
    return nin, [frozenset(i for i in range(1 << nin) if (table[i] >> j) & 1) for j in range(len(T))]


class CNF:
    def __init__(self):
        self.nv = 0
        self.clauses = []

    def new(self):
        self.nv += 1
        return self.nv

    def gate(self, invars, outvar, nin, onset):
        """Prime-implicant Tseitin encoding of outvar <-> f(invars)."""
        offset = frozenset(range(1 << nin)) - onset
        for val, lit_out in ((onset, outvar), (offset, -outvar)):
            for v, dc in prime_implicants(nin, val):
                cl = []
                for i in range(nin):
                    if dc >> i & 1:
                        continue
                    cl.append(-invars[i] if (v >> i) & 1 else invars[i])
                cl.append(lit_out)
                self.clauses.append(cl)

    def write(self, path, comments=()):
        with open(path, "w") as f:
            for c in comments:
                f.write("c %s\n" % c)
            f.write("p cnf %d %d\n" % (self.nv, len(self.clauses)))
            for cl in self.clauses:
                f.write(" ".join(map(str, cl)) + " 0\n")


def encode_circuit(cnf, circ, invars):
    """Adds gate clauses; returns (final wire vars, per-gate records).
    record = (input vars (T then K), output vars of T)"""
    cur = list(invars)
    recs = []
    for g in circ:
        T, K, table = g
        nin, onsets = gate_bit_functions(g)
        ins = [cur[w] for w in T] + [cur[w] for w in K]
        outs = [cnf.new() for _ in T]
        for j, w in enumerate(T):
            cnf.gate(ins, outs[j], nin, onsets[j])
            cur[w] = outs[j]
        recs.append((ins, outs))
    return cur, recs


def miter(n, C0, Ct):
    cnf = CNF()
    xs = [cnf.new() for _ in range(n)]
    y, rec0 = encode_circuit(cnf, C0, xs)
    z, rect = encode_circuit(cnf, Ct, xs)
    ds = []
    for i in range(n):
        if y[i] == z[i]:
            continue
        d = cnf.new()
        a, b = y[i], z[i]
        cnf.clauses += [[-d, a, b], [-d, -a, -b], [d, -a, b], [d, a, -b]]
        ds.append(d)
    cnf.clauses.append(ds)
    meta = dict(xs=xs, y=y, z=z, rec0=rec0, rect=rect, ds=ds)
    return cnf, meta


def write_blif(path, n, circ, name="c"):
    """Circuit as BLIF with 3/4-input LUTs (.names). Inputs x*, outputs o*."""
    cur = ["x%d" % i for i in range(n)]
    lines = [".model %s" % name, ".inputs " + " ".join(cur), ".outputs " + " ".join("o%d" % i for i in range(n))]
    cnt = 0
    for g in circ:
        T, K, table = g
        nin, onsets = gate_bit_functions(g)
        ins = [cur[w] for w in T] + [cur[w] for w in K]
        outs = []
        for j, w in enumerate(T):
            s = "n%d" % cnt; cnt += 1
            lines.append(".names " + " ".join(ins) + " " + s)
            for v, dc in prime_implicants(nin, onsets[j]):
                lines.append("".join("-" if dc >> i & 1 else str((v >> i) & 1) for i in range(nin)) + " 1")
            outs.append(s)
        for j, w in enumerate(T):
            cur[w] = outs[j]
    for i in range(n):
        lines.append(".names %s o%d" % (cur[i], i))
        lines.append("1 1")
    lines.append(".end")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
