"""E0: generate small instances of every gate set and validate them independently."""
import subprocess, sys, json, itertools
import instance
D = "results/instances/e0"
names = []
for gset, n, tfrac, seed in itertools.product(["A", "Aw", "B", "Bw"], [12, 16], [0.0, 0.5, 2.0], [0, 1]):
    beta = 2.5 if gset.endswith("w") else None
    inst, geo = instance.generate(gset=gset, n=n, d=2, k_nb=6.0, m_per_n=4.0, tfrac=tfrac, seed=seed, beta=beta)
    nm = instance.save(inst, D)
    names.append(nm)
    print(nm, "t_done=%d/%d" % (inst["params"]["t_done"], inst["params"]["t"]), flush=True)
fails = 0
for nm in names:
    p = subprocess.run([sys.executable, "check.py", "%s/%s.json" % (D, nm), "--solver"], capture_output=True, text=True)
    out = (p.stdout + p.stderr).strip()
    if p.returncode != 0 or "UNSAT=True" not in out:
        fails += 1
    print(out.splitlines()[-1], flush=True)
print("E0 FAILURES:", fails, "of", len(names))
