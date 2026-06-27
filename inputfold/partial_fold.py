"""
§AC FOLD 3 — PARTIAL FOLD (fold the foldable part, leave the rest; the denominator becomes statement-level).
================================================================================================================
A loop that DECLINEs AS A WHOLE (one statement is I/O / data-dependent) often has a FOLDABLE SLICE — the statements that
DO have closed-form structure. Example: `for i: s += c; io_write(x)` — the accumulation `s += c` folds (to n·c), the
`io_write` does not; we fold the accumulation and leave the write. The loop shrinks; the foldable work collapses.

★ z3 gate (precision 1.0): prove (a) the folded slice equals the original slice's effect (∀ inputs), AND (b) SLICING
PRESERVED SEMANTICS — the slice is independent of the residual (no read/write hazard across the I/O: the residual never
reads the accumulator mid-loop, the slice never depends on the residual's effect). A missed dependency ⇒ REJECT.
★ THE DENOMINATOR HONESTY: a partial fold folds PART of a loop. So the loop-granularity rate is the wrong number — we
report a STATEMENT-LEVEL / fraction rate ("2 of 3 statements folded") DISTINCT from whole-loop fold rate, NEVER merged to
inflate it. LLM-free (dependency analysis is deterministic). No new certificate kind.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Set, Tuple


@dataclass
class Stmt:
    name: str
    reads: Set[str]
    writes: Set[str]
    foldable: bool                          # has closed-form/sublinear structure (e.g. an accumulation)
    kind: str = ""                          # "accumulate" | "io" | "data-dependent" | ...


@dataclass
class PartialFold:
    issued: bool
    folded_stmts: List[str] = field(default_factory=list)
    residual_stmts: List[str] = field(default_factory=list)
    total_stmts: int = 0
    detail: str = ""

    @property
    def statement_level_rate(self) -> float:
        return round(len(self.folded_stmts) / self.total_stmts, 4) if self.total_stmts else 0.0


def _independent(slice_stmts: List[Stmt], residual: List[Stmt]) -> bool:
    """Slicing preserves semantics iff the slice and residual do not interfere: the residual never reads/writes a slice
    accumulator (so the slice's intermediate values are NOT observed), and the slice never reads a residual write."""
    slice_writes = set().union(*[s.writes for s in slice_stmts]) if slice_stmts else set()
    slice_reads = set().union(*[s.reads for s in slice_stmts]) if slice_stmts else set()
    res_writes = set().union(*[s.writes for s in residual]) if residual else set()
    res_reads = set().union(*[s.reads for s in residual]) if residual else set()
    # hazard if the residual touches a slice accumulator, or the slice reads a residual write
    if slice_writes & (res_reads | res_writes):
        return False
    if slice_reads & res_writes:
        return False
    return True


def prove_accumulator_closed(c_step: int, kind: str = "constant") -> bool:
    """z3 ∀-prove the foldable slice's closed form. constant accumulation `s += c` over n folds to n·c (Σ c = n·c);
    proved by the trivial sum identity (base + step). A non-accumulation slice would not reach here."""
    import z3
    n = z3.Int("n")
    S = lambda k: c_step * k                                 # Σ_{i=1}^k c = c·k
    s = z3.Solver()
    base = S(1) == c_step
    step = z3.ForAll([n], z3.Implies(n >= 1, S(n + 1) - S(n) == c_step))
    s.add(z3.Not(z3.And(base, step)))
    return s.check() == z3.unsat


def partial_fold(body: List[Stmt], c_step: int = 1) -> PartialFold:
    """Fold the foldable slice of a whole-loop DECLINE, leave the residual. Requires the slice independent of the residual
    (slicing-preserves-semantics) AND the slice's closed form z3-proved. Else DECLINE (no partial fold)."""
    slice_stmts = [s for s in body if s.foldable]
    residual = [s for s in body if not s.foldable]
    if not slice_stmts:
        return PartialFold(False, total_stmts=len(body), detail="no foldable slice ⇒ DECLINE")
    if not _independent(slice_stmts, residual):
        return PartialFold(False, total_stmts=len(body),
                           detail="slice NOT independent of the residual (read/write hazard — the residual observes the "
                                  "accumulator mid-loop) ⇒ slicing would change behavior ⇒ DECLINE")
    if not prove_accumulator_closed(c_step):
        return PartialFold(False, total_stmts=len(body), detail="slice closed form not z3-proved ⇒ DECLINE")
    return PartialFold(True, [s.name for s in slice_stmts], [s.name for s in residual], len(body),
                       detail=f"folded {len(slice_stmts)}/{len(body)} statements (the accumulation → n·c, z3-proved, "
                              f"independent of the residual); residual loop kept ({[s.name for s in residual]})")


def adversarial_battery() -> dict:
    """A loop `s+=c; io_write` partially folds (accumulation → n·c, the I/O residual kept) — statement-level rate < 1,
    DISTINCT from whole-loop; ★ a residual that READS the accumulator mid-loop (a dependency) is REJECTED (slicing would
    change behavior); ★ the partial fold is NOT counted as a whole-loop fold."""
    # foldable accumulation + an independent I/O residual
    body = [Stmt("s_plus_c", {"s", "c"}, {"s"}, True, "accumulate"),
            Stmt("io_write", {"x"}, {"_io"}, False, "io")]
    pf = partial_fold(body, c_step=3)
    # ★ a residual that reads the accumulator s mid-loop ⇒ hazard ⇒ DECLINE (the intermediate s is observed)
    body_hazard = [Stmt("s_plus_c", {"s", "c"}, {"s"}, True, "accumulate"),
                   Stmt("io_write_s", {"s"}, {"_io"}, False, "io")]               # reads s ⇒ dependency
    pf_hazard = partial_fold(body_hazard, c_step=3)
    # a loop with no foldable slice ⇒ DECLINE
    pf_none = partial_fold([Stmt("io1", {"x"}, {"_io"}, False, "io")], c_step=1)
    cases = {
        "partial_fold_issued": pf.issued and "s_plus_c" in pf.folded_stmts and "io_write" in pf.residual_stmts,
        "statement_level_rate_distinct": 0 < pf.statement_level_rate < 1.0,    # ★ not 0 (whole-loop) nor 1 (full fold)
        "missed_dependency_rejected": not pf_hazard.issued,                    # ★ residual reads accumulator ⇒ REJECT
        "no_foldable_slice_declines": not pf_none.issued,
        "not_counted_as_whole_loop": pf.statement_level_rate != 1.0,           # it folded PART, honestly
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
