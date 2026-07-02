"""
§BD — debugging-zero checker layer. fold-based thorough CHECK + z3 PROVE + honest grading.
================================================================================================================
A new recognition/scan branch over the existing engines (NO new mechanism, NO new disposer): CHECK (exhaustive
bug-pattern scan, all code) and PROVE (bit-exact, verifiable code only) are kept SEPARATE, with separate grades:
  EXACT     — PROVE certified (guarantee; via the single recall/core / pillar3/equiv disposer).
  CHECKED   — every bug pattern passed (common bugs absent; strong trust, NOT a guarantee).
  FLAGGED   — a bug pattern matched ⇒ a fix instruction (line + what + hint) for the write→fix→recheck loop.
  DEFER     — the checker cannot meaningfully analyze this (dynamic eval/exec, structureless) ⇒ "review it".

★ Honest O(1): reading is O(N) (parse, fast); the SLOW semantic check (overflow/bound/termination) is what fold
collapses to O(1) by closing the loop into a formula. Not "know without looking".
"""
from checker.grade_and_fix import CheckResult, Finding, check  # noqa: F401
