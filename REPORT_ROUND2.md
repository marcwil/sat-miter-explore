# Random geometric miters: round 2

Draft of 16 November 2026. Round 1 ([REPORT.md](REPORT.md)) found that
same-size rewriting of small windows barely changes the circuit's structure.
In this round:
- Gate set B: x_a ^= φ(x_b, x_c). Random 3-bit bijections (gate set A) were
  dropped, because their windows are rigid.
- New rewriting processes that can change the skeleton.
- A new primary statistic, the *correspondence width* between C_0 and C_t.
- A corrected weighted variant.

## Summary

SUMMARY_TEXT

## Processes

Each step picks a convex window of w gates, as in round 1. It replaces the
window by a uniformly random *different* sequence of L gates from the same
gate set, on the window's wires, that computes the same function.

| process | step types | size of C_t |
|---|---|---|
| `w3` (round 1) | 3 → 3 | m |
| `knead` | 4 → 4, windows on ≤ 7 wires | m |
| `ik` | 50% knead 4 → 4; otherwise inflate 2 → 4 while the size is < 1.25 m, else deflate 4 → 2 if possible | ≈ 1.25 m |

**The sampler is exact.**
- Length 2 and 3: exhaustive search, as in round 1.
- Length 4: meet in the middle over all 2-gate products on the window's wires
  (`csrc/prod4*.c`). Sample a first pair r with probability ∝ the number of
  second pairs r' whose product with r equals F, then r' uniformly among them.
  This is uniform over all solutions. The kernel's counts match an independent
  Python count on test windows.

**Validation.** `check.py` passes on 22 small instances:
- B, `knead` and `ik`, n ∈ {12, 16}, t up to 2m;
- the corrected weighted variant;
- snapshot runs.

**What a step can do** (n = 64, 300 windows each; 20 samples per window are
classified):

| step | windows with an alternative | median # alternatives | windows with a new-skeleton alternative | samples: reorder / same skeleton / inserted pair / new skeleton |
|---|---|---|---|---|
| w3 (3 → 3) | 59% | 1 | 21% | 54 / 18 / 0 / 28 % |
| knead (4 → 4) | 88% | 3 | 52% | 40 / 20 / 0 / 40 % |
| inflate (2 → 4) | 100% | 1354 | 100% | 0 / 0 / 35 / 65 % |
| deflate (4 → 2), random window | 0.7% | 0 | – | – |

Cost per step: knead about 0.15 s, inflate 0.01 s, w3 0.002 s.

## Correspondence width

**Definition.**
- Fix a cut j of C_t (its first j gates) and a cut i of C_0.
- Φ_{i,j} = (C_t prefix j) ∘ (C_0 prefix i)⁻¹ is a bijection of {0,1}ⁿ.
- D_{i,j}(w) is the set of input bits that output bit w of Φ depends on. It is
  found by sensitivity: 64 random base points, each with all n single-bit
  flips. This detects XOR dependencies, which an entropy-greedy search misses.
- The **wire width** of (j, w) is min_i |D_{i,j}(w)|, over C_0 prefixes near
  the relative position of j.
- Prefixes are only some of the cuts of C_0, so this is an upper bound
  (`width.py`).
- If the width stays ≤ k, the round-1 argument gives refutations of size
  m · 2^O(k). So hardness needs k = ω(log n).

**Validation** (n = 64, m = 512, 12 cuts):

| pair | mean wire width | wires with width ≤ 3 | mean cut width |
|---|---|---|---|
| t = 0 | 1.00 | 100% | 1.00 |
| round-1 A, t = 10m (gauge only) | 1.37 | 95% | 3.1 |
| round-1 B, t = 10m | 1.65 | 91% | 3.2 |
| C_0 vs an unrelated random circuit (null) | 28.0 | 18% | 28.3 (grows with depth, up to 49) |

## Width against t

![width](results/plots/r2_width.png)

WIDTH_TABLE

LONG_TEXT

## Solvers and sweeping

SOLVER_TEXT

## Weighted variant, corrected

WEIGHTED_TEXT

## Conclusions and next steps

CONCL_TEXT

## Reproduce

```bash
python3 r2_richness.py 300                                      # step richness
python3 r2_gen.py grids/r2_e0.json results/instances/r2e0       # validation instances
for f in results/instances/r2e0/*.json; do python3 check.py $f --solver; done
python3 r2_gen.py grids/r2_main.json results/instances/r2       # n = 64 grid (sampler "full")
python3 r2_gen.py grids/r2_long.json results/instances/r2long   # long runs with snapshots
python3 r2_gen.py grids/r2_weighted.json results/instances/r2w  # weighted variant
python3 r2_analyze.py results/instances/r2 results/r2_width.csv  # width + survival
python3 run.py solve results/instances/r2 results/r2_e3.csv 300 cadical,kissat,abc_cec,abc_gcec
python3 e4_sweep.py results/instances/r2 results/r2_sweep.csv
```
