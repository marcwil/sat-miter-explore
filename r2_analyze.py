"""Round 2 analysis: correspondence width + survival statistics per instance.
  python r2_analyze.py <instance dir> <out.csv> [jobs]"""
import sys, os, glob, csv, json
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))


def one(path):
    sys.path.insert(0, HERE)
    import instance, stats, width
    inst = instance.load(path)
    p = inst["params"]
    rows = width.width_profile(inst["C0"], inst["Ct"], p["n"])
    r = dict(instance=os.path.basename(path)[:-5], gset=p["gset"], n=p["n"], mode=p.get("mode", "w3"),
             tfrac=p["tfrac"], seed=p["seed"], beta=p.get("beta"), heavy_q=p.get("heavy_q"),
             m=p["m"], m_t=len(inst["Ct"]), t=p["t_done"])
    r.update(width.summary(rows))
    r.update(stats.instance_stats(inst))
    return r


if __name__ == "__main__":
    d, out = sys.argv[1], sys.argv[2]
    jobs = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    done = set()
    if os.path.exists(out):
        done = {r["instance"] for r in csv.DictReader(open(out))}
    paths = [p for p in sorted(glob.glob(os.path.join(d, "*.json"))) if os.path.basename(p)[:-5] not in done]
    rows = []
    with ProcessPoolExecutor(jobs) as ex:
        for f in as_completed([ex.submit(one, p) for p in paths]):
            r = f.result(); rows.append(r)
            print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}), flush=True)
    if rows:
        new = not os.path.exists(out)
        keys = list(rows[0])
        with open(out, "a", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            if new:
                w.writeheader()
            w.writerows(rows)
