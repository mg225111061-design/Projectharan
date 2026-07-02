"""
§X — THIRD-PATH FOLD PARADIGMS: raise the fold rate WITHOUT a 23rd mechanism (widen WHERE the 22 apply).
================================================================================================================
The mechanism set is converged at 22 (14 certificate kinds). These five paradigms do NOT add a 23rd — they widen the
*opportunity to apply* the existing folds to code that currently DECLINEs (a loop blocked by one dynamic parameter, an
unused output, a linear functional, an array write, a stride). Each is z3-gated; precision stays exactly 1.0; every
paradigm feeds an EXISTING mechanism — opportunity widened, universe unchanged.

★ THE HONESTY SPINE (binding, read first — the two honesties that are this directive's life):
  • Certificate-issued ≠ fold-applied. Several paradigms issue a CONDITIONAL fold (valid under a guard / for a
    projection / for a dual / for an array transition). It counts toward the fold rate ONLY when its condition is
    actually met at a real callsite. Counting issued-but-unused certificates is a false inflation — the corpus-swap
    trick by another name. We MEASURE issued-vs-applied separately; the fold rate is the APPLIED count.
  • Fold rate ≠ speedup. A fold on a tiny / rarely-called loop raises the rate but accelerates nothing. We report the
    fold rate AND the actual measured speedup SEPARATELY; a fold-but-no-speedup is shown for exactly what it is.
  • Precision = 1.0 is inviolable — every conditional fold is z3-proved sound under its condition; unproven ⇒ DECLINE
    and fall back to the original. A false fold fails the build.
  • Still the 22 mechanisms / 14 certificate kinds — NO new kind. A 23rd mechanism is sealed; this is not that.

Modules: axiomatic_fold (P1, guard synthesis) · projection_fold (P2) · dual_fold (P3) · array_fold (P4) ·
stride_fold (P5) · fold_paradigms_report. Reuses catalog/equiv_check (z3 ∀ equivalence + assumptions = the guard).
Engine zero-dep; never imported by test_build.
"""
