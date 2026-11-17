# sat-miter-explore

Experiments for the proposal *Random geometric miters: explanations that are
easy to record and hard to recover*.

- [REPORT.md](REPORT.md): round 1. The model as proposed, the gauge-only
  finding, solver and sweeping results, and the first weighted variant.
- [REPORT_ROUND2.md](REPORT_ROUND2.md): round 2. Richer rewriting
  (knead, inflate, deflate), the correspondence width and its plateau, and the
  corrected weighted variant.
- [REPORT_ROUND3.md](REPORT_ROUND3.md): round 3, after an external review.
  - It corrects the round-2 plateau claim and calibrates a layer-cut width
    estimator.
  - It measures width scaling up to n = 256 (≈ log n, about half of it
    removable with spatially varying cuts).
  - It reports the planted R·R⁻¹, large-inflation and geometry-noise tests,
    and ends with a stop/continue decision.
- [THEORY.md](THEORY.md): what is proved, sketched or only measured:
  - gauge rigidity;
  - constant-width refutations under gauge-only rewriting;
  - the spatial-separator cap;
  - the open width question.
