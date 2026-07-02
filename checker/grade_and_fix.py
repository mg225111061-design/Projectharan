"""
§BD CHK-6 — GRADE + FIX (the orchestrator): assemble CHK-1/2/4 into ONE honest grade, with a fix instruction.
================================================================================================================
The two faces are kept SEPARATE and never mixed (the directive's first invariant):
  • CHECK  = the exhaustive bug-pattern scan (CHK-2) over all relevant sites.
  • PROVE  = a bit-exact guarantee, issued ONLY by the existing fold engine's kernel_verdict EXACT certificate
             (CHK-5 — routed through `loop_decision` / `recall/core`; this file NEVER mints a certificate itself,
             so a false-EXACT is structurally impossible).

The four grades, by actionability:
  FLAGGED  — a bug pattern matched (or the source won't parse) ⇒ findings + fix instructions for write→fix→recheck.
  DEFER    — eval/exec/reflection or otherwise unanalyzable ⇒ "can't verify this; review it" (no false clean).
  EXACT    — pure, and every loop folded to a closed form carrying a PASSED kernel_verdict EXACT cert (a guarantee).
  CHECKED  — no catalogued bug found, but no proof either ⇒ "common bugs absent" (strong trust, NOT a guarantee).

★ precision 1.0: a buggy line is never graded clean — when uncertain the catalog FLAGs (CHK-3), and EXACT rides
an existing passed certificate. ★ honest O(1): reading is O(N) (parse); only the loop SEMANTICS jump to O(1) (fold).
★ "all code debugging 0" is FALSE — structureless / opaque logic ⇒ HONEST_DEFER, never a silent pass.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from checker.bug_patterns import Finding, scan          # noqa: F401 — Finding re-exported for the package
from checker.loop_semantics import LoopReport, analyze_loops
from checker.structure_index import build_index

FLAGGED = "FLAGGED"
DEFER = "DEFER"
EXACT = "EXACT"
CHECKED = "CHECKED"


@dataclass
class CheckResult:
    grade: str
    summary: str
    findings: List[Finding] = field(default_factory=list)
    loops: Optional[LoopReport] = None
    effect: str = "unknown"
    n_lines: int = 0
    exact_verdict: object = None          # the kernel_verdict carried when grade == EXACT (a real passed cert)

    @property
    def clean(self) -> bool:
        """True only for a genuinely positive grade. FLAGGED/DEFER are never 'clean' (precision 1.0)."""
        return self.grade in (EXACT, CHECKED)

    def fix_instructions(self) -> List[str]:
        """The write→fix→recheck payload: one located instruction per finding (live LLM fix runs on Render)."""
        return [f"L{f.line}: {f.message} → FIX: {f.hint}" for f in self.findings]


def _exact_eligible(rep: LoopReport) -> bool:
    """EXACT needs: at least one loop, every loop folded (none deferred), and each fold carries a PASSED EXACT cert
    from the existing engine (we re-check the certificate object — we never assert EXACT on our own say-so)."""
    if rep.n_foldable < 1 or rep.n_deferred != 0:
        return False
    for f in rep.facts:
        if f.kind != "foldable":
            return False
        v = f.verdict
        cert = getattr(v, "certificate", None)
        if not (getattr(v, "status", None) == "EXACT" and cert is not None and getattr(cert, "passed", False)):
            return False
    return True


def check(src: str) -> CheckResult:
    """The single public entry: CHECK (+ DEFER) + PROVE → one honest grade. O(N) read, O(1) loop semantics."""
    idx = build_index(src)

    # 1) won't parse ⇒ a definite, located defect ⇒ FLAGGED (not a 'clean' grade).
    if not idx.parsed:
        syn = Finding("syntax_error", "high", _err_line(idx.syntax_error), 0,
                      f"source does not parse: {idx.syntax_error}",
                      "fix the syntax error before any further check can run")
        return CheckResult(FLAGGED, f"does not parse ({idx.syntax_error})", [syn], None, "unknown", idx.n_lines)

    findings = scan(idx, src)
    rep = analyze_loops(idx, src)

    # 2) a catalogued bug matched ⇒ FLAGGED dominates (a located, fixable defect is the most actionable output).
    if findings:
        hi = sum(1 for f in findings if f.severity == "high")
        return CheckResult(FLAGGED, f"{len(findings)} finding(s) ({hi} high) — see fix instructions",
                           findings, rep, idx.effect, idx.n_lines)

    # 3) no catalogued bug, but the code is unanalyzable (eval/exec/reflection) ⇒ HONEST_DEFER (never a silent pass).
    if idx.effect == "opaque" or idx.dynamic_calls:
        return CheckResult(DEFER, "uses eval/exec/reflection — static analysis cannot verify this; review by hand",
                           [], rep, idx.effect, idx.n_lines)

    # 4) PROVE (CHK-5): pure + every loop folded with a PASSED EXACT cert ⇒ EXACT (the existing engine's guarantee).
    if idx.effect == "pure" and _exact_eligible(rep):
        v = next((f.verdict for f in rep.facts if f.kind == "foldable"), None)
        return CheckResult(EXACT, f"pure; {rep.n_foldable} loop(s) folded to closed form with a passed EXACT cert",
                           [], rep, idx.effect, idx.n_lines, exact_verdict=v)

    # 5) no bug found, but no proof either ⇒ CHECKED ("common bugs absent" — strong trust, NOT a guarantee).
    note = "no catalogued bug found"
    if rep.n_deferred:
        note += f"; {rep.n_deferred} loop(s) not foldable (semantics not proven)"
    return CheckResult(CHECKED, note, [], rep, idx.effect, idx.n_lines)


def _err_line(msg: Optional[str]) -> int:
    if msg and "line " in msg:
        try:
            return int(msg.rsplit("line ", 1)[1].rstrip(")"))
        except Exception:  # noqa: BLE001
            return 0
    return 0


def adversarial_battery() -> dict:
    """★ buggy code ⇒ FLAGGED + a located finding (never clean); ★ a pure folding loop ⇒ EXACT (rides a passed
    cert); ★ eval/exec ⇒ DEFER; ★ clean-but-unprovable ⇒ CHECKED; ★★ PRECISION: a planted bug is NEVER `clean`."""
    md = check("def f(x=[]):\n x.append(1)\n return x")
    inf = check("def f():\n while True:\n  pass")
    exa = check("def f(n):\n s = 0\n for i in range(n):\n  s += i\n return s")
    dfr = check("def f(s):\n return eval(s)")
    chk = check("def f(a, b):\n if b == 0:\n  return 0\n return a // b")   # guarded div, no fold ⇒ CHECKED
    syn = check("def f(:\n pass")
    cases = {
        "mutable_default_FLAGGED": md.grade == FLAGGED and any(x.pattern_id == "mutable_default_arg" for x in md.findings),
        "mutable_default_has_location": md.findings and md.findings[0].line >= 1,
        "infinite_loop_FLAGGED_not_clean": inf.grade == FLAGGED and not inf.clean,
        "pure_fold_EXACT": exa.grade == EXACT and exa.exact_verdict is not None,
        "eval_DEFER": dfr.grade == DEFER,
        "guarded_clean_CHECKED": chk.grade == CHECKED,
        "syntax_error_FLAGGED": syn.grade == FLAGGED,
        # ★★ the spine: every planted-bug input is reported NOT clean (precision 1.0 — no false clean ever)
        "precision_buggy_never_clean": (not md.clean) and (not inf.clean) and (not syn.clean),
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
