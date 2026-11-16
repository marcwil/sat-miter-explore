"""E4 driver: run transcript-free relational sweeping on every instance in a dir.
  python e4_sweep.py <dir> <csv> [timeout] [name-regex]"""
import sys, os, glob, csv, json, re
import instance, sweep

d, outcsv = sys.argv[1], sys.argv[2]
timeout = float(sys.argv[3]) if len(sys.argv) > 3 else 300
filt = sys.argv[4] if len(sys.argv) > 4 else None
done = set()
if os.path.exists(outcsv):
    done = {r["instance"] for r in csv.DictReader(open(outcsv))}
new = not os.path.exists(outcsv)
fields = ["instance", "status", "t_sweep", "t_final", "t_total", "groups_t", "verified", "tried", "n_lemma_clauses"]
with open(outcsv, "a", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fields)
    if new:
        w.writeheader()
    for path in sorted(glob.glob(os.path.join(d, "*.json"))):
        nm = os.path.basename(path)[:-5]
        if nm in done or (filt and not re.search(filt, nm)):
            continue
        r = sweep.sweep(instance.load(path), timeout=timeout)
        r["instance"] = nm
        w.writerow(r); fh.flush()
        print(json.dumps(r), flush=True)
