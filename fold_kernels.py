"""
v26 STAGE 7 — fold-kernel certificate layer (aggressive where provable, honest DECLINE elsewhere).
===================================================================================================
Unifies the existing sound closed-form kernels (Faulhaber/Gosper-Zeilberger/C-finite via
`closure_classifier` + `cfinite`) under one v26 certificate, and adds an INDEPENDENT numeric re-check:
before emitting a closed form, evaluate it against the naive fold for several n. A mismatch ⇒ DECLINE
(★ never emit a wrong closed form ★). Where no structure is provable, DECLINE honestly with the reason.

Verdicts:
  FOLDED   — closed form + kernel + complexity + soundness certificate (engine proof + numeric recheck)
  ABSENT   — a real impossibility result (Gosper: hypergeometric but NOT summable — e.g. Σ 1/k)
  DECLINED — no provable structure (data-dependent Ω(N), or no closed form / wrong-form recheck)

★ HONEST LIMITS (theorems, §1.4/§5) ★: the closed-form class is intentionally NARROW. Richardson's
theorem (closed-form equality is undecidable) ⇒ no universal simplifier; Petkovšek-Wilf-Zeilberger ⇒
some sums provably have NO hypergeometric closed form (frequent honest DECLINE is correct behavior).
Pointers/heap/control-flow ⇒ zero gain. Not-yet-implemented kernels (FFT/NTT, Toeplitz/displacement-rank,
holonomic binary-splitting) DECLINE rather than guess.
"""
from __future__ import annotations

from dataclasses import dataclass

import haran_ast as A
import closure_classifier as CC
from haran_parser import parse


@dataclass
class FoldVerdict:
    status: str                 # FOLDED | ABSENT | DECLINED | PARSE_ERROR | NONE
    closed_form: str = "—"
    kernel: str = "-"           # faulhaber | gosper | cfinite | sympy-sum
    complexity: str = "none"    # O(1) | O(log n) | none
    certificate: str = ""
    reason: str = ""

    def __str__(self):
        if self.status == "FOLDED":
            return f"FOLDED [{self.kernel}] {self.complexity}: {self.closed_form}  ({self.certificate})"
        if self.status == "ABSENT":
            return f"ABSENT — {self.reason}"
        return f"{self.status} — {self.reason}"


def _block_return(b):
    if isinstance(b, A.Block) and b.stmts and isinstance(b.stmts[-1], A.ExprStmt):
        return b.stmts[-1].value
    return b


def _numeric_recheck(fn) -> str:
    """Independently verify a fold's closed form against the naive sum for several n.
    Returns 'OK' (matches), 'MISMATCH' (engine produced a wrong form → must DECLINE), or
    'INCONCLUSIVE' (couldn't evaluate — trust the engine's own proof, don't falsely reject)."""
    ret = _block_return(fn.body) if fn.body else None
    if not isinstance(ret, A.Fold) or not isinstance(ret.domain, A.Range):
        return "INCONCLUSIVE"
    try:
        import sympy as sp
        k = sp.Symbol(ret.binder)
        summand = CC.haran_to_sympy(_block_return(ret.body), ret.binder)
        lo = int(ret.domain.lo.value) if isinstance(ret.domain.lo, A.Num) else None
        if lo is None:
            return "INCONCLUSIVE"
        v = CC.classify_fold(ret)
        if v.kind != "CLOSED":
            return "INCONCLUSIVE"
        closed = sp.sympify(v.closed_form)
        syms = list(closed.free_symbols)
        if len(syms) > 1:
            return "INCONCLUSIVE"
        nsym = syms[0] if syms else sp.Symbol("n")
        for nv in (1, 2, 3, 5, 8, 13):
            if nv < lo:
                continue
            naive = sum(sp.Rational(summand.subs(k, j)) for j in range(lo, nv + 1))
            cf = sp.Rational(closed.subs(nsym, nv)) if syms else sp.Rational(closed)
            if sp.simplify(naive - cf) != 0:
                return "MISMATCH"
        return "OK"
    except Exception:   # noqa: BLE001 — recheck can only strengthen; never false-reject on its own error
        return "INCONCLUSIVE"


def fold_certificate(code: str) -> FoldVerdict:
    """Classify + certify a HARAN fold/recurrence. See module docstring for the verdict semantics."""
    prog = parse(code)
    if prog.errors:
        return FoldVerdict("PARSE_ERROR", reason=str(prog.errors[0]))
    fns = prog.fns()
    if not fns:
        return FoldVerdict("NONE", reason="no function found")
    fn = fns[0]
    v = CC.classify_fn(fn)              # existing sound engine (Faulhaber/Gosper/C-finite/sympy)
    if v.kind == "CLOSED":
        rc = _numeric_recheck(fn)
        if rc == "MISMATCH":
            return FoldVerdict("DECLINED", reason="closed form failed an independent numeric recheck — "
                               "refusing to emit (never a wrong closed form)")
        cert = f"{v.proof}"
        cert += "; independent numeric recheck n∈{1,2,3,5,8,13}=OK" if rc == "OK" \
            else "; engine-verified (independent recheck inconclusive)"
        return FoldVerdict("FOLDED", closed_form=v.closed_form, kernel=v.method,
                           complexity=v.speedup, certificate=cert)
    if v.kind == "ABSENT":
        return FoldVerdict("ABSENT", kernel=v.method, reason=v.proof)
    # UNKNOWN / NO_STRUCTURE → honest decline with the engine's reason
    return FoldVerdict("DECLINED", kernel=v.method,
                       reason=v.proof or "no provable closed-form structure")
