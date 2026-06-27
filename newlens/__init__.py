"""
§Z — THREE NEW FOLD LENSES: generating-function · sliding-window · projective(Möbius).
================================================================================================================
Three more sights the 22 mechanisms cannot see, each z3-gated, precision exactly 1.0, inheriting the §X/§Y honesties
(a fold counts only when APPLIED; fold rate reported SEPARATELY from speedup; the IEEE-754-vs-real caveat stated):
  • LENS A — GENERATING-FUNCTION / formal-power-series: a nonlinear self-convolution DP `dp[n]=Σ dp[i]·dp[n-1-i]`
    DECLINEs as nonlinear, but as a power series D(x)=Σ dp[n]xⁿ the convolution becomes a PRODUCT, yielding an
    algebraic equation (D=xD²+1 for Catalan) with an exact closed form (C(2n,n)/(n+1)). New (algebraic GF) — ⑬
    handles only LINEAR sums. ★ Exact over integer/rational (z3-proved); the general FFT product is float and is NOT a
    precision-1.0 fold unless proved under an exact integer/NTT model. Reuses the existing closed-form evaluator.
  • LENS B — SLIDING-WINDOW AGGREGATION: a loop that re-aggregates a whole window each step is O(N·W), but the
    invariant `acc==aggregate(window)` lets each step do `acc⊖oldest⊕newest` in O(1). The most PRACTICAL. ★ Exact for
    integer/exact sums and for monotone-deque min/max; float-sum is DECLINED (catastrophic cancellation breaks the
    invariant). New incremental-aggregation pattern; issues the existing EXACT verdict.
  • LENS C — PROJECTIVE / MÖBIUS: a fractional recurrence x←(a·x+b)/(c·x+d) DECLINEs as nonlinear, but it is a linear
    map on ℙ¹, so lifting x=u/v makes it the 2×2 matrix [[a,b],[c,d]] and N iterations fold to Mᴺ in O(log N).
    ★ HONEST OVERLAP: this is ALREADY built as `catalog/mobius_fold.py` (§P P5) — the identical PGL₂ construction. We
    REUSE it (no duplication), add only the §Z refinements (explicit orbit nonzero-denominator guard + float caveat),
    and count the projective fold as ZERO new contribution (already counted in §P). No double-count.

★ NO double-count: A/B are genuinely new to this repo; C is our own §P P5 (counted zero). None overlaps QF_BV / Galois /
stride (verified). NO gratuitous new certificate kind — A routes to closed-form/matrix-power, B issues EXACT, C reuses
matrix_recurrence. The pigeonhole wall is absolute; these lenses only notice that what looked like noise was a product,
a reused sum, or a matrix in disguise. Engine zero-dep; never imported by test_build.
Modules: genfunc_fold · window_fold · mobius_fold · newlens_report.
"""
