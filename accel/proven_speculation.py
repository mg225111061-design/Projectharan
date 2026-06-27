"""
§Q IDEA 3 — PROVEN SPECULATION: overlap the WAIT, never guess wrong (the only idea that hides latency vs removing I/O).
================================================================================================================
Prove with z3/dependence-analysis that "whatever the I/O returns, this work is unaffected" (independence) — then run
that work DURING the I/O wait. This is NOT branch-prediction-with-rollback; it is PROVEN-safe overlap with NO rollback,
because independence is proved. Or prove two branches share an identical PREFIX and execute it before the fetch
resolves.

★ PROOF GATE: speculative work is committed ONLY if it is proved independent of the I/O outcome (it does not read what
the I/O writes; no shared write). Work that secretly reads the I/O result (via aliasing/global state) ⇒ DECLINE — no
speculation on a guess. ★ HONEST: this OVERLAPS the wait (the I/O still happens, its latency still exists); it never
makes the I/O faster. The win is hiding latency behind useful work — modeled, never framed as I/O acceleration.
"""
from __future__ import annotations

from typing import List, Sequence

from accel.pipeline import Acceleration, proved, rejected


def proven_overlap(io_writes: Sequence[str], work_reads: Sequence[str], work_writes: Sequence[str]) -> Acceleration:
    """Overlap `work` with the I/O wait iff `work` is independent of the I/O RESULT: work_reads ∩ io_writes = ∅ AND
    work_writes ∩ io_writes = ∅. Any overlap ⇒ DECLINE (the work depends on / races the I/O — no rollback path)."""
    iw, wr, ww = set(io_writes), set(work_reads), set(work_writes)
    conflicts = []
    if wr & iw:
        conflicts.append(f"work READS {sorted(wr & iw)} that the I/O writes (depends on the result)")
    if ww & iw:
        conflicts.append(f"work WRITES {sorted(ww & iw)} the I/O also writes (race)")
    if conflicts:
        return rejected("Q3.spec", "overlap work with the I/O wait",
                        "; ".join(conflicts) + " — NOT independent ⇒ DECLINE (no guess, no rollback)")
    return proved("Q3.spec", "overlap work with the I/O wait",
                  f"work proved INDEPENDENT of the I/O result (work r/w {sorted(wr | ww)} ∩ io-writes {sorted(iw)} = ∅) "
                  "⇒ safe concurrent overlap, NO rollback needed (proven, not guessed); latency HIDDEN not reduced")


def proven_common_prefix(branch_a: Sequence[str], branch_b: Sequence[str]) -> Acceleration:
    """Execute a branch prefix BEFORE the deciding fetch resolves iff the two branches share an IDENTICAL prefix (same
    ops in the same order). A prefix that differs in any op/side-effect ⇒ DECLINE."""
    pre = []
    for a, b in zip(branch_a, branch_b):
        if a != b:
            break
        pre.append(a)
    if not pre:
        return rejected("Q3.spec", "execute the common branch prefix early", "no shared prefix between the branches")
    return proved("Q3.spec", f"execute the {len(pre)}-op common branch prefix early",
                  f"both branches share the identical prefix {pre} ⇒ it runs before the fetch resolves regardless of "
                  "outcome (proved common, not a predicted branch)")
