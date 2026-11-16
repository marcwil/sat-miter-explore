"""E5 backdoor test: split on the k highest-degree variables of the miter CNF
(in the weighted models these are heavy control signals) and solve all 2^k cubes
with CaDiCaL. Reports total and max cube time against the unsplit solve.

  python e5_backdoor.py out.csv timeout inst1.cnf inst2.cnf ...
"""
import sys, os, csv, time, subprocess, tempfile, collections
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
CADICAL = os.path.join(HERE, "tools/cadical/build/cadical")
KS = (0, 1, 2, 4, 6)


def read_cnf(path):
    cls = []
    nv = 0
    for line in open(path):
        if line.startswith(("c", "p")):
            if line.startswith("p"):
                nv = int(line.split()[2])
            continue
        lits = list(map(int, line.split()))[:-1]
        cls.append(lits)
    return nv, cls


def run_cube(args):
    nv, path, units, timeout = args
    with tempfile.NamedTemporaryFile("w", suffix=".cnf", delete=False) as f:
        body = open(path).read().split("\n", 1)
        # rewrite header with extra unit clauses
        lines = [l for l in open(path) if not l.startswith(("c", "p"))]
        f.write("p cnf %d %d\n" % (nv, len(lines) + len(units)))
        f.writelines(lines)
        for u in units:
            f.write("%d 0\n" % u)
        tmp = f.name
    t0 = time.perf_counter()
    try:
        p = subprocess.run([CADICAL, "-q", tmp], capture_output=True, timeout=timeout)
        st = {20: "UNSAT", 10: "SAT"}.get(p.returncode, "UNKNOWN")
        dt = time.perf_counter() - t0
    except subprocess.TimeoutExpired:
        st, dt = "TIMEOUT", timeout
    os.unlink(tmp)
    return st, dt


if __name__ == "__main__":
    outcsv, timeout = sys.argv[1], float(sys.argv[2])
    new = not os.path.exists(outcsv)
    with open(outcsv, "a", newline="") as fh, ProcessPoolExecutor(4) as ex:
        w = csv.DictWriter(fh, fieldnames=["instance", "k", "cubes", "solved", "total", "max", "top_degrees"])
        if new:
            w.writeheader()
        for path in sys.argv[3:]:
            nv, cls = read_cnf(path)
            deg = collections.Counter(abs(l) for c in cls[:-1] for l in c)
            top = [v for v, _ in deg.most_common(max(KS))]
            for k in KS:
                cubes = [[(top[j] if (c >> j) & 1 else -top[j]) for j in range(k)] for c in range(1 << k)]
                res = list(ex.map(run_cube, [(nv, path, cu, timeout) for cu in cubes]))
                row = dict(instance=os.path.basename(path)[:-4], k=k, cubes=len(cubes),
                           solved=sum(r[0] == "UNSAT" for r in res), total=round(sum(r[1] for r in res), 2),
                           max=round(max(r[1] for r in res), 2), top_degrees=[deg[v] for v in top[:max(k, 1)]])
                w.writerow(row); fh.flush()
                print(row, flush=True)
