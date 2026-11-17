# Theory note: what the experiments say about proof size

Draft of 17 November 2026. This note collects the statements behind rounds
1–3. It marks clearly what is proved, what is a proof sketch, and what is only
observed.

## Setting

- n wires on the d-torus, local radius r chosen for constant degree (about 8).
- C_0 is a sequence of m local gates.
- C_t is obtained from C_0 by t window rewrites.
- The miter M(C_0, C_t) has shared inputs, Tseitin clauses for both circuits
  (one fresh variable per target bit per gate), and the output clause
  OR_i d_i with d_i ↔ (y_i ⊕ z_i).
- A *gate* is (targets T, controls K, table). For every control value it is a
  bijection on the target bits.

## 1. Two-gate windows: the solution set of a shape is a gauge orbit (proved)

Let F = g_2 ∘ g_1 act on the wires S = U_1 ∪ U_2, where U_i = T_i ∪ K_i. A
*shape* is a pair of gate supports (T_1', K_1'), (T_2', K_2') inside S. Write
M = T_1' ∩ T_2' (the target wires both gates rewrite).

**Lemma 1 (exact characterisation).** Let F be decomposable for a shape. Every
decomposition (h_1, h_2) of F with this shape is described by the following.
1. A partition of the U_1'-assignments into *contexts* σ(u). A context is
   determined by
   - the bits of u on K_1' ∩ U_2', and
   - the bits of F(u) on T_1' ∩ K_2'.
2. Within each context, a bijection μ_σ from the *row classes* to {0,1}^M.
   Two assignments u are in the same row class if the map z ↦ F(u ∪ z)
   restricted to T_2' is the same function, where z ranges over U_2' ∖ U_1'.
3. The construction is
   - h_1(u) = (F(u) restricted to T_1' ∖ T_2', μ_σ(class(u))),
   - h_2 is defined by F = h_2 ∘ h_1.

Hence the number of solutions is ∏_σ (2^|M|)!.

*Proof.* Wires outside T_2' keep the value h_1 gives them. So the outputs on
T_1' ∖ T_2' are determined by F, and the only freedom is the value m(u) on M.
- h_2 must be well defined, and on each control value a bijection. So two u
  with the same visible context and the same middle value must have equal
  rows, and two different rows must get different middle values.
- h_1 is a bijection for each control value. So every fibre (control value,
  value on T_1' ∖ T_2') carries all 2^|M| middle values exactly once.
- Hence, within a context, μ is a bijection from row classes to {0,1}^M.

Conversely, every such μ defines valid gates. `model.decompose2` implements
exactly this construction, and every sampled decomposition is checked by
composing (`sample_decomposition`). ∎

**Corollary (gauge).** For gates without controls (gate set A) there is a
single context. So the solutions of the *original* shape are exactly the pairs
(h ∘ g_1, g_2 ∘ h⁻¹) with h ranging over the bijections of {0,1}^M: the
gauge orbit.

**Observation (rigidity; measured, not proved).** For uniformly random bijection
gates on local triples, a shape other than the original is feasible in 1.85%
of windows (n = 64, 2000 windows; `results/e1_richness.json`). The inspected
exceptions are windows where g_1's output on the shared wire depends on that
wire alone.
- Heuristic: a fixed shape realises at most about 8!² functions out of 32!
  on 5 wires.
- A proof would bound the probability that a random F satisfies the
  dependency conditions of another shape. The conditions in Lemma 1 make this
  a finite computation over the shapes inside S, but it is not done here.

## 2. Gauge-only rewriting has constant-width refutations (proved)

**Proposition 2.** Suppose C_t arises from C_0 by gauge moves only. Each move
replaces consecutive gates g_i, g_j on shared wires U by h ∘ g_i and g_j ∘ h⁻¹,
with no gate in between touching U, together with commuting reorders. Then the
miter has a resolution refutation of width O(1) and size O(m), with constants
independent of t.

*Proof.* Gauge moves do not change the dependency DAG. Group the moves by DAG
edge, an edge being the wires gate i passes directly to gate j. Then gate i of
C_t equals H_i^out ∘ g_i ∘ (H_i^in)⁻¹, where H^in and H^out are products of
bijections, one per incident edge, each on ≤ 3 wires.

Process the gates in topological order and derive, for each edge e from i,
the clauses expressing z_e = h_e(y_e), at most 8·3 clauses of width ≤ 4. Each
derivation uses:
- the relations of the edges entering gate i,
- the clauses of g_i and g'_i,
- at most 12 variables in total.

So it is a constant-size resolution derivation (completeness on 12
variables). A wire's final value has no outgoing edge, hence z_w = y_w. The
units ¬d_w then follow by constant-size steps, and resolving them with the
output clause completes the refutation. ∎

Relational sweeping (`sweep.py`) finds these relations without the transcript
by simulation, and verifies each of them by SAT. In every round-1 A instance,
99–100% of the C_t gate groups received a verified relation.

## 3. Geometry caps the hardness for any t (proved, standard)

**Proposition 3.** Let both circuits be geometric: every gate's wires are
pairwise within r, with nr^d = Θ(1). Then the miter has a resolution refutation
of size n · 2^O(n^(1−1/d) · m/n) for every t.

Suppose instead a set of p·m gates is long-range, with arbitrary wires, and
the rest are local. Then the bound becomes n · 2^O(n^(1−1/d) · m/n + p·m).

*Proof.* Split the miter into n formulas M_i: drop the output clause and add
the units d_i, y_i ≠ z_i. Refuting each M_i and resolving the resulting units
¬d_i with the output clause costs a factor n.

The primal graph of M_i embeds in space × time, each variable sitting at its
wire's position. Clauses only join variables of wires at distance ≤ r.
- A slab of width 2r around a hyperplane contains O(n · r) = O(n^(1−1/d))
  wires for d ≥ 2.
- Each wire has O(m/n) versions per circuit on average.
- So the slab is a balanced separator with O(n^(1−1/d) · m/n) variables.

Recursing on the halves gives a geometric series, so the treewidth is
O(n^(1−1/d) · m/n). Each long-range gate adds at most 4 variables to each
separator, giving + O(p·m). Davis–Putnam elimination along a tree
decomposition of width w produces only clauses of width ≤ w + 1, hence a
refutation of size n · 3^O(w). ∎

**Consequences.**
- For d = 1 with m = O(n), the bound is polynomial: no hardness at all.
- For d = 2 with m = Θ(n), the best possible hardness is 2^O(√n).
- Long-range gates remove this ceiling once p·m ≫ n^(1−1/d), i.e.
  p ≫ n^(−1/d) · n/m. This is the scale of the noise parameter c in round 3
  (p = c · n^(−1/d) · n/m).

## 4. Correspondence width and proof size (proof sketch only)

For a cut j of C_t and a cut i of C_0, let Φ_{i,j} = (C_t up to j) ∘ (C_0 up to i)⁻¹.
D_{i,j}(w) is the set of C_0 cut wires that bit w of Φ depends on.

**Sketch.** Suppose there are matched sequences of *layer* cuts with
- consecutive cuts one ASAP layer apart in both circuits, and
- max_w |D(w)| ≤ k at every matched pair.

Then the miter has a refutation of size m · 2^O(k).
- Derive, layer by layer, the clauses z_w = f_w(y_{D(w)}). That is ≤ 2^k
  clauses of width ≤ k + 1 per wire.
- A step involves the gates of one layer in each circuit. Their inputs depend
  on ≤ 3k C_0 wires of the previous cut, so the step is a resolution
  derivation on O(k) variables.

*Not proved:*
- that the optimal cuts can be chosen one layer apart;
- that each step's derivation stays within O(k) variables when the matched
  C_0 cut moves by more than one layer.

**What is measured** (`width.width_layers`, layer cuts, calibrated in
`results/r3_calibration.csv`): the maximum over wires at 12 sampled cuts.
- Gauge-only rewriting gives 2–3, flat in n.
- Kneading gives roughly log₂ n.
- Unrelated circuits give about 0.75 n.

If the width is O(log n), the sketch gives polynomial refutations.

## 5. Open question

**Question.** Does rewriting with windows of ≤ w gates, inside the gate set
and with the geometry fixed, keep the corrected correspondence width at
O_w(log n) for every t?

The data so far are consistent with "yes", with width ≈ log₂ n at w = 4.
- If true, Q2 and Q3 fail for every bounded-window local process: the
  recorded transcript is recoverable in polynomial time by relation search.
- If false, the counterexample process is the model the proposal wants.

The open ingredients are:
1. Is the move graph on equivalent circuits connected?
2. If it is, does its stationary distribution concentrate on circuits with
   narrow correspondence to C_0?
3. A per-wire tail bound on |D(w)| that would explain the log n maximum as an
   extreme value.
