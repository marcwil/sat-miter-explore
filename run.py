"""Generate instance grids and run solvers on them (4 parallel jobs).

  python run.py gen  <grid.json> <outdir>          # generate instances
  python run.py solve <outdir> <csv> <timeout> tool1,tool2,...  [name-filter]
"""
import csv, itertools, json, os, re, subprocess, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
T = os.path.join(HERE, "tools")
CADICAL = os.path.join(T, "cadical/build/cadical")
KISSAT = os.path.join(T, "kissat/build/kissat")
ABC = os.path.join(T, "abc/abc")

TOOLS = {
    "cadical": lambda b: [CADICAL, b + ".cnf"],
    "cadical_nocc": lambda b: [CADICAL, "--congruence=false", "--sweep=false", b + ".cnf"],
    "kissat": lambda b: [KISSAT, b + ".cnf"],
    "kissat_nocc": lambda b: [KISSAT, "--congruence=false", "--sweep=false", b + ".cnf"],
    "abc_cec": lambda b: [ABC, "-c", "cec %s.c0.blif %s.ct.blif" % (b, b)],
    "abc_gcec": lambda b: [ABC, "-c", "&r %s.c0.aig; &cec %s.ct.aig" % (b, b)],
}


def _gen_one(args):
    sys.path.insert(0, HERE)
    import instance
    params, outdir = args
    nm = instance.name_of(dict(instance.DEFAULTS, **params))
    if os.path.exists(os.path.join(outdir, nm + ".cnf")):
        return nm, "exists"
    inst, geo = instance.generate(**params)
    nm = instance.save(inst, outdir)
    b = os.path.join(outdir, nm)
    for c in ("c0", "ct"):  # AIGER for &cec
        subprocess.run([ABC, "-c", "read %s.%s.blif; strash; write_aiger %s.%s.aig" % (b, c, b, c)],
                       capture_output=True)
    p = inst["params"]
    return nm, "t=%d/%d gen=%.1fs" % (p["t_done"], p["t"], p["gen_time"])


def expand(grid):
    keys = list(grid)
    vals = [v if isinstance(v, list) else [v] for v in grid.values()]
    return [dict(zip(keys, c)) for c in itertools.product(*vals)]


def gen(gridfile, outdir, jobs=4):
    grids = json.load(open(gridfile))
    if isinstance(grids, dict):
        grids = [grids]
    plist = [p for g in grids for p in expand(g)]
    os.makedirs(outdir, exist_ok=True)
    with ProcessPoolExecutor(jobs) as ex:
        futs = [ex.submit(_gen_one, (p, outdir)) for p in plist]
        for f in as_completed(futs):
            print(*f.result(), flush=True)


def parse(tool, out, rc):
    status, conflicts = "UNKNOWN", None
    if tool.startswith(("cadical", "kissat")):
        if rc == 20 or "s UNSATISFIABLE" in out:
            status = "UNSAT"
        elif rc == 10:
            status = "SAT"
        m = re.search(r"^c conflicts:\s+(\d+)", out, re.M)
        if m:
            conflicts = int(m.group(1))
    else:
        if "Networks are equivalent" in out or "are equivalent" in out:
            status = "UNSAT"
        elif "NOT EQUIVALENT" in out.upper() or "are not equivalent" in out or "Output " in out and "Value in Network1" in out:
            status = "SAT"
    return status, conflicts


def _solve_one(args):
    base, tool, timeout = args
    cmd = TOOLS[tool](base)
    t0 = time.perf_counter()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        dt = time.perf_counter() - t0
        status, conf = parse(tool, p.stdout + p.stderr, p.returncode)
    except subprocess.TimeoutExpired:
        dt, status, conf = timeout, "TIMEOUT", None
    return dict(instance=os.path.basename(base), tool=tool, status=status, time=round(dt, 3),
                conflicts=conf, timeout=timeout)


def solve(outdir, csvfile, timeout, tools, filt=None, jobs=4):
    names = sorted(f[:-4] for f in os.listdir(outdir) if f.endswith(".cnf"))
    if filt:
        names = [n for n in names if re.search(filt, n)]
    done = set()
    if os.path.exists(csvfile):
        for r in csv.DictReader(open(csvfile)):
            done.add((r["instance"], r["tool"]))
    tasks = [(os.path.join(outdir, n), t, timeout) for n in names for t in tools if (n, t) not in done]
    new = not os.path.exists(csvfile)
    with open(csvfile, "a", newline="") as fh, ProcessPoolExecutor(jobs) as ex:
        w = csv.DictWriter(fh, fieldnames=["instance", "tool", "status", "time", "conflicts", "timeout"])
        if new:
            w.writeheader()
        for f in as_completed([ex.submit(_solve_one, t) for t in tasks]):
            r = f.result()
            w.writerow(r); fh.flush()
            print(r["instance"], r["tool"], r["status"], r["time"], r["conflicts"], flush=True)
            if r["status"] == "SAT":
                print("!!! SAT on a miter: generator bug?", r, flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "gen":
        gen(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 4)
    else:
        solve(sys.argv[2], sys.argv[3], float(sys.argv[4]), sys.argv[5].split(","),
              sys.argv[6] if len(sys.argv) > 6 else None)
