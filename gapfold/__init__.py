"""
§AD — EIGHT STRUCTURE-EXISTS-BUT-UNFOLDED GAPS: finish the machine (real structure the detector missed, not new theory).
================================================================================================================
Not new structures to recognize or new ways to count — eight EXACT HOLES where the structure genuinely exists and is
established mathematics, but our detector/closed-form machinery wasn't built yet. These are CURRENTLY-unfoldable (a
missing detector), NOT principled-impossible (genuine I/O / randomness / data-dependent control — those stay unfoldable
forever). Each is well-established math, so the risk is low and the certificate is EXACT (precision 1.0) where it applies.

  • GAP 1 — multi-way mutual recursion (k≥3 entangled linear recurrences) → one k×k companion matrix → matrix power.
  • GAP 2 — divide-and-conquer recurrences T(n)=a·T(n/b)+f(n) → Master / Akra-Bazzi closed-form asymptotic cost.
  • GAP 3 — deep nested sums ΣᵢΣⱼ i·j → multivariate Faulhaber closed form.
  • GAP 4 — structured-data conditions (sortedness/cumulative) → fold under PROVABLE structure (the grey zone, conservative).
  • GAP 5 — deep algebraic cancellation → simplify-before-fold exposes the post-cancellation structure.
  • GAP 6 — the float-exact subset (x·2.0, power-of-two scaling) → EXACT (z3 IEEE-754-proved bit-exact), not APPROX-ε.
  • GAP 7 — large-but-bounded state with provable structure → fold the structure (matrix/QF_BV), never enumerate.
  • GAP 8 — consecutive-loop fusion (the 2nd consumes the 1st's output) → fuse, then fold the closed form.

★ THE NO-FORCING INVARIANT (GAP 4/6/7): never force structure where there is none — a data-dependent condition stays
DECLINE (GAP 4), a non-bit-exact float stays APPROX-ε/DECLINE (GAP 6), an unstructured large state stays DECLINE (GAP 7).
The proposer may try; the z3 certifier disposes. Fold rate = APPLIED not issued; LLM-free; zero-dep (`forbidden_present
== []`; sympy grandfathered for GAP 5 only); the pigeonhole/physics wall stands. Never imported by test_build.
Modules: mutual_recursion · divide_conquer · nested_sums · structured_data · simplify_fold · float_exact · large_state ·
loop_fusion · gapfold_report.
"""
