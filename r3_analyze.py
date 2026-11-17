"""Round 3: corrected (layer-cut) width for every instance in the given dirs.
  python r3_analyze.py out.csv dir1 [dir2 ...]   (skips instances already in out.csv)"""
import sys, os, glob, csv, json, re
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))


def one(path):
    sys.path.insert(0, HERE)
    import instance, width, stats
    inst = instance.load(path)
    p = inst["params"]
    rows = width.width_layers(inst["C0"], inst["Ct"], p["n"])
    nm = os.path.basename(path)[:-5]
    r = dict(instance=nm, gset=p["gset"], n=p["n"], mode=p.get("mode", "w%d" % p.get("w", 0)), tfrac=p["tfrac"],
             seed=p["seed"], walk_seed=p.get("walk_seed", p["seed"]), m=p["m"], m_t=len(inst["Ct"]),
             variant=re.sub(r"_t[\d.]+_s\d+", "", nm))
    r.update(width.summary_layers(rows))
    st = stats.instance_stats(inst)
    r.update(gate_frac=st["gate_frac"], eq_frac=st["eq_frac"])
    return r


if __name__ == "__main__":
    out, dirs = sys.argv[1], sys.argv[2:]
    jobs = int(os.environ.get("JOBS", 4))
    done = set()
    if os.path.exists(out):
        done = {r["instance"] for r in csv.DictReader(open(out))}
    paths = [p for d in dirs for p in sorted(glob.glob(os.path.join(d, "*.json")))
             if os.path.basename(p)[:-5] not in done]
    new = not os.path.exists(out)
    with open(out, "a", newline="") as fh, ProcessPoolExecutor(jobs) as ex:
        w = None
        for f in as_completed([ex.submit(one, p) for p in paths]):
            r = f.result()
            if w is None:
                w = csv.DictWriter(fh, fieldnames=list(r))
                if new:
                    w.writeheader()
            w.writerow(r); fh.flush()
            print(json.dumps({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()}), flush=True)
