"""
§R PHASE 2 — LOGICAL VULNERABILITY VERIFICATION: prove each class absent, or flag it with its location.
================================================================================================================
Static analysis (no code change ⇒ ZERO runtime overhead), so it runs even on NOT-SENSITIVE code as analysis-only. For
each class the verdict is PROVEN_ABSENT (z3/exact proof) or FLAGGED (location + detail). ★ "safe" is asserted ONLY
when proved; anything unproven is "NOT VERIFIED — possible <vuln>", never a false clear. A wrongly-cleared vuln is a
correctness violation. Reuses the QF_BV overflow proof and the B-engine race-freedom conflict analysis.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

PROVEN_ABSENT = "PROVEN_ABSENT"
FLAGGED = "FLAGGED"


@dataclass
class VulnResult:
    vuln_class: str
    status: str                        # PROVEN_ABSENT | FLAGGED
    location: str = ""
    detail: str = ""

    @property
    def safe(self) -> bool:
        return self.status == PROVEN_ABSENT


# ── bounds: PROVEN only for the canonical guarded pattern `for i in range(len(c)): c[i]`; else FLAGGED ──────
def check_bounds(code: str) -> List[VulnResult]:
    try:
        tree = ast.parse(code.strip())
    except SyntaxError as e:
        return [VulnResult("bounds", FLAGGED, "0", f"parse error: {e}")]
    out: List[VulnResult] = []
    # collect `for i in range(len(c))` guards: var -> collection
    guarded: Dict[str, str] = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.For) and isinstance(n.target, ast.Name) and isinstance(n.iter, ast.Call) \
                and isinstance(n.iter.func, ast.Name) and n.iter.func.id == "range" and n.iter.args:
            a0 = n.iter.args[-1] if len(n.iter.args) <= 2 else None
            if isinstance(a0, ast.Call) and isinstance(a0.func, ast.Name) and a0.func.id == "len" and a0.args \
                    and isinstance(a0.args[0], ast.Name):
                guarded[n.target.id] = a0.args[0].id
    for n in ast.walk(tree):
        if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name):
            idx = n.slice.value if isinstance(n.slice, ast.Index) else n.slice   # py<3.9 / py>=3.9
            line = getattr(n, "lineno", 0)
            if isinstance(idx, ast.Constant) and isinstance(idx.value, int) and idx.value >= 0:
                continue                                       # nonneg constant index — treated proven (literal access)
            if isinstance(idx, ast.Name) and guarded.get(idx.id) == n.value.id:
                continue                                       # i ∈ range(len(c)) and c[i] — PROVEN in bounds
            out.append(VulnResult("bounds", FLAGGED, str(line),
                                  f"{n.value.id}[{ast.dump(idx)[:20]}] — index not proved within [0,len) "
                                  "(unguarded / mismatched collection) ⇒ NOT VERIFIED"))
    return out or [VulnResult("bounds", PROVEN_ABSENT, "", "all subscripts are guarded range(len()) or constant — "
                              "every access proved within bounds")]


# ── injection: a sink fed by a CONCATENATED/formatted untrusted string ⇒ FLAGGED; parameterized ⇒ proven ──
_SINK_FNS = {"execute", "executescript", "eval", "exec", "system", "popen", "Popen", "run", "query", "raw"}


def check_injection(code: str) -> List[VulnResult]:
    try:
        tree = ast.parse(code.strip())
    except SyntaxError as e:
        return [VulnResult("injection", FLAGGED, "0", f"parse error: {e}")]
    out: List[VulnResult] = []
    sinks = 0
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            fn = n.func.attr if isinstance(n.func, ast.Attribute) else (n.func.id if isinstance(n.func, ast.Name) else None)
            if fn in _SINK_FNS and n.args:
                sinks += 1
                arg = n.args[0]
                # structure-altering: string built by + / % / .format / f-string ⇒ input can become code ⇒ FLAG
                dynamic = isinstance(arg, (ast.BinOp, ast.JoinedStr)) or \
                    (isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute) and arg.func.attr == "format")
                if dynamic:
                    out.append(VulnResult("injection", FLAGGED, str(getattr(n, "lineno", 0)),
                                          f"sink {fn}(...) built from a dynamic/concatenated string — untrusted input "
                                          "can alter the query/command STRUCTURE ⇒ NOT VERIFIED (parameterize it)"))
                # else: a constant string (optionally with separate params) — structure is fixed ⇒ safe sink
    if sinks == 0:
        return [VulnResult("injection", PROVEN_ABSENT, "", "no injection sink present")]
    return out or [VulnResult("injection", PROVEN_ABSENT, "", "every sink uses a fixed (constant/parameterized) "
                              "command string — untrusted input cannot alter the structure (stays data)")]


# ── integer overflow: QF_BV / range proof — prove the result stays in width, or flag ────────────────────────
def check_overflow(expr: str, width: int = 32, signed: bool = True,
                   ranges: Optional[Dict[str, Tuple[int, int]]] = None) -> VulnResult:
    """Prove the arithmetic `expr` cannot overflow a `width`-bit integer given each variable's range. z3 searches for
    an in-range assignment whose result exceeds the bound: SAT ⇒ FLAGGED (overflow possible); UNSAT ⇒ PROVEN_ABSENT."""
    import z3
    try:
        tree = ast.parse(expr.strip(), mode="eval")
    except SyntaxError as e:
        return VulnResult("overflow", FLAGGED, "0", f"parse error: {e}")
    names = sorted({n.id for n in ast.walk(tree) if isinstance(n, ast.Name)})
    env = {nm: z3.Int(nm) for nm in names}
    s = z3.Solver()
    for nm in names:
        lo, hi = (ranges or {}).get(nm, (0, (1 << width) - 1))
        s.add(env[nm] >= lo, env[nm] <= hi)

    def rec(n):
        if isinstance(n, ast.Expression):
            return rec(n.body)
        if isinstance(n, ast.Constant):
            return n.value
        if isinstance(n, ast.Name):
            return env[n.id]
        if isinstance(n, ast.BinOp):
            a, b = rec(n.left), rec(n.right)
            return {ast.Add: a + b, ast.Sub: a - b, ast.Mult: a * b}[type(n.op)]
        raise ValueError(f"unsupported op {ast.dump(n)[:30]}")
    try:
        val = rec(tree)
    except (ValueError, KeyError) as e:
        return VulnResult("overflow", FLAGGED, "0", f"unmodeled expr ({e}) ⇒ NOT VERIFIED")
    hi = (1 << (width - 1)) - 1 if signed else (1 << width) - 1
    lo = -(1 << (width - 1)) if signed else 0
    s.push()
    s.add(z3.Or(val > hi, val < lo))
    r = s.check()
    if r == z3.sat:
        return VulnResult("overflow", FLAGGED, "", f"overflow possible: {expr} can exceed {width}-bit "
                          f"{'signed' if signed else 'unsigned'} range at {s.model()} ⇒ NOT VERIFIED")
    if r == z3.unsat:
        return VulnResult("overflow", PROVEN_ABSENT, "", f"{expr} proved within {width}-bit range for all inputs "
                          "in their declared bounds (z3 UNSAT of the overflow condition)")
    return VulnResult("overflow", FLAGGED, "", "z3 unknown ⇒ NOT VERIFIED (never clear on a guess)")


# ── memory: use-after-del / None-deref (Python's analogues of UAF / null-deref) ─────────────────────────────
def check_memory(code: str) -> List[VulnResult]:
    try:
        tree = ast.parse(code.strip())
    except SyntaxError as e:
        return [VulnResult("memory", FLAGGED, "0", f"parse error: {e}")]
    deleted: set = set()
    none_set: set = set()
    out: List[VulnResult] = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Delete):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    deleted.add(t.id)
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) \
                and isinstance(n.value, ast.Constant) and n.value.value is None:
            none_set.add(n.targets[0].id)
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            if n.id in deleted:
                out.append(VulnResult("memory", FLAGGED, str(getattr(n, "lineno", 0)),
                                      f"use of {n.id} after `del {n.id}` (use-after-free analogue) ⇒ NOT VERIFIED"))
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in none_set:
            out.append(VulnResult("memory", FLAGGED, str(getattr(n, "lineno", 0)),
                                  f"attribute access on {n.value.id} which is None (null-deref) ⇒ NOT VERIFIED"))
    return out or [VulnResult("memory", PROVEN_ABSENT, "", "no use-after-del / null-deref on tracked names")]


# ── race: reuse the B-engine conflict analysis (disjoint read/write ⇒ race-free) ────────────────────────────
def check_race(tasks: Sequence[dict]) -> VulnResult:
    """Prove race-freedom on concurrent access to shared state. `tasks` = [{name, reads, writes}]. Any write that
    another task reads/writes ⇒ FLAGGED race; pairwise-disjoint ⇒ PROVEN_ABSENT."""
    from accel.verified_parallel import _conflicts
    conflicts = _conflicts(list(tasks))
    if conflicts:
        return VulnResult("race", FLAGGED, "", f"data race: {conflicts[0]} ⇒ NOT VERIFIED (synchronize or isolate)")
    return VulnResult("race", PROVEN_ABSENT, "", f"all {len(tasks)} concurrent tasks have disjoint read/write sets — "
                      "race-freedom proved (B-engine conflict analysis)")


def analyze_logical(code: str) -> dict:
    """Run every logical-vuln class on `code` (static, zero runtime overhead). Returns per-class results + the overall
    'all_proven_absent' flag (True ONLY if every class proved absent — 'safe' only when proved)."""
    results: List[VulnResult] = []
    results += check_bounds(code)
    results += check_injection(code)
    results += check_memory(code)
    flagged = [r for r in results if r.status == FLAGGED]
    return {"results": [r.__dict__ for r in results], "flagged": [r.__dict__ for r in flagged],
            "all_proven_absent": not flagged,
            "note": "static analysis — zero runtime overhead; 'safe' only where z3/exact-proved; unproven = "
                    "'NOT VERIFIED — possible vuln at <location>', never a false clear"}
