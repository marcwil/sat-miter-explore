# Random geometric miters: first round of experiments

Draft of 16 November 2026. These are the first-round experiments for the
proposal *Random geometric miters: explanations that are easy to record and
hard to recover*. Code, data and plots are in this repository; how to
reproduce them is at the end.

## Summary

1. **As written, the model's rewriting is almost only "gauge".**
   - Take random 3-bit bijection gates and replace a window of w = 2 gates by
     2 gates with the same function. In 98.2% of windows, every equivalent
     sequence has the same wire triples as the original.
   - The only freedom is to insert h, h⁻¹ on the wires that the two gates
     share.
   - So C_t keeps the skeleton of C_0, and every cut of C_t is a product of
     local bijections, each on at most 3 wires, of the same cut of C_0.
   - This gives a resolution refutation of constant width and size O(m) for
     *every* t.
2. **Internal equivalences do not die out.**
   - 74% of windows share a single wire, and the only bijections of one bit
     are identity and NOT.
   - So at t = 10m, 93% of C_0's internal signals still have an equal or
     complementary signal in C_t, and 99% of gate groups have a bijective
     partner.
3. **No instance became hard.**
   - Grid: n ≤ 256 wires, m = 8n gates, t ≤ 10m (t ≤ 3m for B at n = 256),
     four model variants, 3 seeds.
   - In this grid, every miter was solved, mostly in seconds, by default
     CaDiCaL, Kissat or ABC.
   - Running time grows at most mildly with t, and saturates around t ≈ m.
4. **The structure can be recovered without the transcript.**
   - "Relational sweeping" finds bijective relations between gate groups of
     C_0 and C_t by simulation and verifies them with a SAT solver. It solves
     every instance in about 0.2–5 s, at every t.
   - This extends SAT sweeping from equal signals to bijectively related
     signal groups.
5. **The richer gate set does not change the outcome.**
   - With CCMR-style gates x_a ^= φ(x_b, x_c), w = 3 windows do allow skeleton
     changes (23% of windows).
   - But the process stalls: at t = 10m, 61% of the gates are still verbatim
     copies of gates in C_0. The instances stay easy.
6. **The weighted variant gives a heavy-tailed degree distribution but no
   hardness.**
   - It makes CDCL slower by a constant factor already at t = 0.
   - It does not make hardness grow with t.
   - With distance-independent controls, the formula stops looking geometric.
     A distance penalty on light wires (GIRG-like) and controls on only a
     fraction of gates restore it.
7. **Day-10 criterion: not met.**
   - No setting had instances solved within a minute at small t and by no
     tool within an hour at large t.
   - The obstacle is the rewriting process, not the instance size.
   - The rewrite process has to mix. Only then can Q2 hold, and internal
     equivalences are the wrong quantity to count: what matters is how wide the
     correspondences between cuts of C_0 and C_t are.

## Setup

- **Geometry.** n points uniform on the d-torus; d = 2 in this round. The
  radius r is set so that a wire has 8 neighbours on average, and point sets
  are resampled until the neighbour graph is connected. The *local* triples
  are the triples that are pairwise within r.
- **Gate sets.** A gate is (targets T, read-only controls K, table): for
  every value of the controls, a bijection on the target bits.
  - **A**: as in the proposal. A uniform local triple and a uniform
    permutation of {0,1}³.
  - **B**: CCMR-style. x_a ^= φ(x_b, x_c), with {a, b, c} local and φ one of
    the 10 two-input functions that depend on both inputs. This form is
    reconstructed from memory: eprint.iacr.org was not reachable from this
    machine.
  - **A_w**: weighted variant of A. Each wire has a Pareto weight
    (P(W > w) = w^−(β−1), default β = 2.5). A gate gets a control c ∉ T with
    P(c) ∝ W_c, and two permutations π₀, π₁ selected by c.
  - **B_w**: weighted variant of B. x_a ^= φ(x_b, x_c) with a, b local and c
    chosen by weight.
  - Optional knobs: α, a distance penalty (1 + dist/r)^−α; and p_ctrl, the
    fraction of controlled gates.
- **Windows.** Pick a uniform gate, then repeatedly add the first later gate
  that does not commute with the window. Gates commute if they act on
  disjoint wires, or share only control wires, or are XOR gates with the same
  target. The window is convex, and the gates between its members are moved in
  front of it.
- **Replacement.** Uniform among all *other* sequences with the same number of
  gates that compute the same function on the window's wires and use only
  gates of the same gate set.
  - A and A_w, w = 2: exact enumeration, via a 2-gate decomposition algorithm
    over all gate shapes on the window's wires. Each feasible shape is weighted
    by the size of its gauge orbit (`model.decompose2`).
  - B and B_w, w = 3: exhaustive meet-in-the-middle over the gate set on the
    window's wires (`model.equivalent_xor_fast`, with a C kernel).
- **Encoding.** Miter CNF with shared inputs. Each output bit is encoded by
  Tseitin from all prime implicants of the bit and of its negation. Each
  circuit is also written as BLIF for ABC.
- **Tools.**
  - CaDiCaL 3.0.1 and Kissat 4.0.4 (GitHub master), each with defaults and with
    `--congruence=false --sweep=false`.
  - ABC `cec`, and `&cec` on AIGs.
  - Timeouts: 300 s, and 120 s for the no-congruence runs. 4 parallel jobs on a
    4-core machine.

## E0 — validation

`check.py` is independent of the generator: it has its own gate evaluator and
its own commutation test. It checks:
1. Every reordering in the transcript only swaps gates that commute
   semantically, tested exhaustively on their wires.
2. Every window replacement computes the same function, tested exhaustively on
   the window's wires.
3. Replaying the transcript reproduces C_t.
4. C_0 ≡ C_t by brute force (n ≤ 16), or on 10⁴ random inputs.
5. CaDiCaL returns UNSAT.

All 48 small instances pass (4 gate sets × n ∈ {12, 16} × t ∈ {0, m/2, 2m} × 2
seeds). In the negative control, one table entry of C_t is changed. Replay,
simulation, CaDiCaL (SAT) and ABC (counterexample) all catch it. Across all
runs below, no solver ever answered SAT on a miter.

## E1 — what rewrites exist?

1000–2000 random windows per setting (400 for w = 3), from random circuits
with n = 64, m = 512.

| gate set | w | windows with any alternative | … with a different skeleton | remark |
|---|---|---|---|---|
| A | 2 | 100% | **1.85%** | the gauge orbit has (2^k)! elements, k = number of shared wires |
| A_w | 2 | 66% | 0.15% | 41% of windows: gauge controlled by a shared control wire |
| B | 2 | 8.8% | 4.5% | XOR gates are almost rigid at w = 2 |
| B | 3 | 65% | 23% | half of the alternatives only reorder the gates |
| B_w | 2 | 2.4% | 1.3% | |
| B_w | 3 | 57% | 11% | |

Number of wires the two gates of an A window share: 1 wire in 74% of
windows, 2 in 24%, 3 in 2.5%.

Why A is almost gauge-only:
- A generic product of two random bijection gates determines its skeleton
  through its dependency structure.
- A count makes this plausible. A skeleton realises at most about 8!² ≈ 1.6·10⁹
  functions, out of 32! on 5 wires, so two different skeletons almost never
  realise the same function.
- The 1.85% exceptions arise when the first gate's output on a shared wire
  depends only on that wire's input. That wire then acts like a control, and
  the gates can be re-wired, e.g. (18,43,63),(43,52,63) → (18,43,52),(18,43,63).
- w = 3 was not checked exhaustively for A. The counting argument suggests the
  same behaviour.

**Consequence: a bounded-width proof.** For pure gauge rewriting, gate i of C_t
is H_i^out ∘ g_i ∘ (H_i^in)⁻¹. Here H^in and H^out are products of bijections,
one per edge of the dependency graph, and each acts on the wires the edge
carries (≤ 3).
1. Walk through the gates in order. From the relations on gate i's inputs and
   the clauses of g_i and g'_i, derive the relation z_out = H_i^out(y_out).
   This needs ≤ 24 clauses of width ≤ 4 over ≤ 12 variables.
2. Outputs have no outgoing edge, so the final relation is z = y.
3. Together with the miter clauses, this refutes the formula. The refutation
   has constant width and size O(m).

The rare skeleton changes widen individual relations to ≤ 5 wires. E4 shows
that this does not accumulate in practice.

## E2 — what survives? (n = 64, m = 512, 3 seeds)

![survival](results/plots/e2_survival.png)

| gate set | t/m = 0.1 | 1 | 10 |
|---|---|---|---|
| A: equal/complement signals | 0.99 | 0.96 | 0.93 |
| A: groups with bijective partner | 1.00 | 1.00 | 0.99 |
| A: gates verbatim | 0.82 | 0.29 | 0.12 |
| B: equal/complement signals | 0.95 | 0.81 | 0.78 |
| B: groups with bijective partner | 0.91 | 0.73 | 0.68 |
| B: gates verbatim | 0.94 | 0.73 | 0.61 |

All three curves saturate. In A, a signal keeps an equivalent unless its
outgoing edge carries ≥ 2 wires, and gauges never propagate. In B, about 35%
of windows have no alternative at all, and half of the alternatives are
reorderings. So the walk stays close to C_0 even at t = 10m.

*Measurement:* 1024 random input patterns. Two different balanced functions
that agree on all of them are possible in principle but unlikely; matches were
not confirmed by SAT.

## E3 — solver hardness against t

E3_TABLES

## E4 — relational sweeping (transcript-free)

`sweep.py`:
1. Simulate both circuits on 1024 inputs.
2. Hash each gate group (all wires of a gate, right after it) by its
   relabelled value sequence.
3. For each C_t group, take the C_0 groups with the same hash as candidates.
4. Verify each candidate relation with incremental CaDiCaL. The solver holds
   the gate clauses of both circuits (no output clause, so the formula is
   satisfiable and the check is sound) and the relations verified so far.
5. Add the verified relations as lemmas and solve the miter.

E4_TABLE

## E5 — weighted variant

E5_TEXT

## Day-10 criterion

DAY10_TEXT

## What this means for the proposal

RECO_TEXT

## Reproduce

```bash
python3 e0_validate.py                         # E0
python3 e1_richness.py 2000 400                # E1 -> results/e1_richness.json
python3 run.py gen grids/e2.json results/instances/n64 4
python3 run.py gen grids/big.json results/instances/big 4
python3 run.py gen grids/e5.json results/instances/n64 4
python3 e2_stats.py results/instances/n64 results/e2_stats.csv
python3 run.py solve results/instances/n64 results/e3_n64.csv 300 cadical,kissat,abc_cec,abc_gcec
python3 run.py solve results/instances/big results/e3_big.csv 300 cadical,kissat,abc_cec,abc_gcec
python3 e4_sweep.py results/instances/n64 results/e4_sweep_n64.csv
python3 e5_realism.py results/instances/n64 results/instances/e5geo
python3 plots.py e2 e3
```
Solvers are built from GitHub master (`tools/`, git-ignored). Instances are
deterministic given the grid entry, and are git-ignored because of their size.
