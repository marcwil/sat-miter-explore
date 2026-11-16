"""E4: transcript-free 'relational sweeping'.

Generalises SAT sweeping from equivalences between single signals to bijective
relations between gate groups (all wires of a gate right after it):
  1. simulate C_0 and C_t on P random inputs; canonical signature of each group;
  2. for each C_t gate (in order) take C_0 groups with the same canonical
     signature as candidates; the induced value map H is the candidate relation;
  3. verify the relation with an incremental SAT solver on the gate clauses of both
     circuits plus the relations verified so far (no output-difference clause, so
     the formula is satisfiable and verification is sound); keep it if valid;
  4. solve the miter plus all verified relations with CaDiCaL.
Everything is derived from C_0 and C_t only; the transcript is never read.

  python sweep.py inst.json [timeout]
"""
import sys, os, time, json, subprocess, tempfile
import numpy as np
from pysat.solvers import Solver
import instance, encode, stats

HERE = os.path.dirname(os.path.abspath(__file__))
CADICAL = os.path.join(HERE, "tools/cadical/build/cadical")


def group_vars(circ, recs):
    out = []
    for g, (ins, outs) in zip(circ, recs):
        out.append(list(outs) + list(ins[len(g[0]):]))
    return out


def relation_clauses(v0, vt, H):
    cls = []
    k0 = len(v0)
    for a, b in H.items():
        neg = [(-v0[i] if (a >> i) & 1 else v0[i]) for i in range(k0)]
        for j in range(len(vt)):
            cls.append(neg + [vt[j] if (b >> j) & 1 else -vt[j]])
    return cls


def sweep(inst, P=1024, timeout=300, check_budget=None):
    t_start = time.time()
    n = inst["params"]["n"]
    cnf, meta = encode.miter(n, inst["C0"], inst["Ct"])
    gv0 = group_vars(inst["C0"], meta["rec0"])
    gvt = group_vars(inst["Ct"], meta["rect"])
    rng = np.random.default_rng(1)
    X = (rng.random((n, P)) < 0.5).astype(np.uint8)
    _, g0 = stats.trace(inst["C0"], n, X)
    _, gt = stats.trace(inst["Ct"], n, X)
    index = {}
    for i, v in enumerate(g0):
        index.setdefault(stats.canon_group(v), []).append(i)
    s = Solver(name="cadical195", bootstrap_with=cnf.clauses[:-1])  # drop output OR clause
    act = cnf.nv
    lemmas, tried, failed = [], 0, 0
    for j, vt in enumerate(gt):
        cands = index.get(stats.canon_group(vt), [])
        for i in cands[:3]:
            v0 = g0[i]
            H = {}
            ok = True
            for a, b in zip(v0.tolist(), vt.tolist()):
                if H.setdefault(a, b) != b:
                    ok = False; break
            if not ok:
                continue
            tried += 1
            # verify: for every value a of the C_0 group, C_t group must be H(a)
            valid = True
            for a, b in H.items():
                act += 1
                k0 = len(gv0[i])
                assum = [(gv0[i][q] if (a >> q) & 1 else -gv0[i][q]) for q in range(k0)]
                diff = [(-gvt[j][q] if (b >> q) & 1 else gvt[j][q]) for q in range(len(gvt[j]))]
                s.add_clause([-act] + diff)
                res = s.solve(assumptions=assum + [act])
                s.add_clause([-act])
                if res:
                    valid = False; break
            if valid and len(H) == (1 << len(gv0[i])):
                cl = relation_clauses(gv0[i], gvt[j], H)
                for c in cl:
                    s.add_clause(c)
                lemmas += cl
                break
            failed += 1
    s.delete()
    t_sweep = time.time() - t_start
    # final solve
    with tempfile.NamedTemporaryFile("w", suffix=".cnf", delete=False) as f:
        f.write("p cnf %d %d\n" % (cnf.nv, len(cnf.clauses) + len(lemmas)))
        for c in cnf.clauses + lemmas:
            f.write(" ".join(map(str, c)) + " 0\n")
        path = f.name
    t1 = time.time()
    try:
        p = subprocess.run([CADICAL, "-q", path], capture_output=True, timeout=timeout)
        status = {20: "UNSAT", 10: "SAT"}.get(p.returncode, "UNKNOWN")
    except subprocess.TimeoutExpired:
        status = "TIMEOUT"
    t_final = time.time() - t1
    os.unlink(path)
    return dict(status=status, t_sweep=round(t_sweep, 2), t_final=round(t_final, 2),
                t_total=round(t_sweep + t_final, 2),
                groups_t=len(gt), verified=tried - failed, tried=tried, n_lemma_clauses=len(lemmas))


if __name__ == "__main__":
    inst = instance.load(sys.argv[1])
    to = float(sys.argv[2]) if len(sys.argv) > 2 else 300
    print(os.path.basename(sys.argv[1]), json.dumps(sweep(inst, timeout=to)))
