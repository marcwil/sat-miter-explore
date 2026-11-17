# Random geometric miters: round 3

Draft of 17 November 2026. Round 3 acts on an external review of rounds 1–2.
The review is summarised in the plan; theory is in [THEORY.md](THEORY.md).

## 0. Correction to round 2

Round 2 claimed that the correspondence width "plateaus at O(1)". That claim
used `wire_mean`, a per-wire minimum over *different* C_0 cuts, which no single
cut realises. A proof needs the maximum over wires at one cut. The prefix-cut
version of that maximum (`cut_max_max` in `results/r2_long_width.csv`) grew
with n: 8–15, 18–20 and 29–32 at n = 32, 64, 128. The reviewer was right that
the round-2 statistic hid this.

Round 3 shows that most of that growth was an artifact of the estimator:
- Prefix cuts in sequence order drift out of alignment when commuting gates
  are reordered.
- With cuts at ASAP layers of the dependency DAG, the maximum is much smaller.
  The calibration controls pass (section A).
- What remains is a slow growth with n, roughly log₂ n (section B).

SUMMARY_TEXT

## A. Corrected width estimator and calibration

The new estimator is `width.width_layers`:
- Both circuits are layered as early as possible (ASAP), with the commutation
  rule used by the rewriting. Cuts are taken at layer boundaries, which are
  invariant under commuting reorders.
- For each of 12 C_t layer cuts, the C_0 layer cut within ±12% of the relative
  position (at least ±3 layers) that minimises the maximum over wires of |D(w)|
  is chosen.
- Reported: that maximum (`cut_max`), its mean and maximum over the 12 cuts,
  and the mean over wires.
- Sensitivity sampling uses P = 256 base points, each with all n single-bit
  flips.

Calibration (`r3_calibrate.py` → `results/r3_calibration.csv`):

| control | max width per cut: mean over 12 cuts / worst cut | expected |
|---|---|---|
| t = 0 (n = 64) | 1.00 / 1 | 1 |
| C_0 vs a random commuting reordering, n = 64 and n = 128 | 1.00 / 1 | 1 |
| round-1 A, gauge-only, t = 10m, n = 64 (2 seeds) | 2.25, 1.92 / 5, 3 | ≤ 3, up to about 5 at the 2% skeleton changes |
| same, n = 128 | 2.25, 2.83 / 3, 7 | flat in n |
| same, n = 256 | 2.83, 3.08 / 3, 6 | flat in n |
| null: C_0 vs an unrelated circuit, n = 32 / 64 / 128 (2 seeds) | 28.5 / 50.4 / 98.2; worst cut ≈ n | baseline |
| P = 64 vs 1024 (knead, n = 64, t = 30m) | 4.17 / 6 for both | equal |
| P = 64 vs 1024 (null, n = 64) | 46.5 vs 47.8 | equal |

The gauge-only control stays at about 2–3 for n = 64 to 256. The rare
skeleton changes give occasional cuts up to 5–7.

**Round-2 instances, re-analysed** (`results/r3_width.csv`; mean over the 12
cuts of the max width per cut; worst cut in parentheses; one or two seeds):

| n | w3 (t = 10m) | knead (t ≥ 3m) | ik (t ≥ 3m) | null |
|---|---|---|---|---|
| 32 | – | 3.7–4.1 (8) | 3.8–4.7 (7) | 28.5 |
| 64 | 4.2 (7) | 4.2–5.1 (11) | 4.8–5.7 (10) | 50.4 |
| 128 | – | 5.3–6.6 (10) | 5.8–7.8 (13) | 98.2 |

For comparison, the old prefix statistic gave 20 at n = 64 and 32 at n = 128.

## B. Width against n with seeds

B_TEXT

## C. Real inflation and planted R·R⁻¹

C_TEXT

## C2. Geometry noise and weighted gate arity

**Arm (iii), weighted gate arity: killed by the gate-first check.**
- Setup (`r3_toffoli_check.py` → `results/r3_toffoli_check.json`):
  - circuits with 25% heavy gates x_a ^= AND of 3 literals, where the third
    control comes from the long-range kernel;
  - 300 knead windows containing a heavy gate;
  - all equivalent 4-gate sequences over B gates plus 3-control Toffoli gates
    on the window's wires.
- Results:
  - 89% of windows have an alternative;
  - only **39%** have a new-skeleton alternative, against 52% for plain B;
  - only 18% of heavy windows fit the 7-wire cap;
  - 0.8 s per window.
- Heavy AND gates make windows *more* rigid, not less. An AND of 3 literals
  fires on 1/8 of inputs and has few equivalent rewritings. By the plan's rule
  this arm is dropped.

C2_TEXT

## Decisions and next steps

DECISION_TEXT
