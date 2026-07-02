"""
§R PHASE 4 — CONDITIONAL HARDENING: fix a flagged vuln in SENSITIVE code, PROVED-equivalent, with MEASURED cost.
================================================================================================================
When SENSITIVE code has a flagged vuln, apply a fix that is z3/differential-PROVED to (a) eliminate the vuln and (b)
compute the IDENTICAL result. The hardening may slow the code (constant-time removes fast-path branches; masking adds
ops) — that cost is MEASURED (Clock C) and reported honestly: "hardened against <vuln>, +X% latency". The user sees
the trade and chooses.

★ NEVER harden NOT-SENSITIVE code — the Phase-1 gate is BINDING here. A non-sensitive hot loop is left untouched and
fast even if it carries a "vulnerability" that never reaches a sensitive sink; hardening it would be the overhead
defect. A result-changing hardening (breaks equivalence) or a hardening applied to non-sensitive code is REJECTED.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Set

from security.sidechannel import constant_time, CT_PROVEN


@dataclass
class HardenResult:
    applied: bool
    vuln_closed: bool
    equivalent: bool
    cost_ratio: Optional[float] = None      # hardened/original runtime (Clock C); >1 = slower (the honest cost)
    reason: str = ""

    def __str__(self):
        if self.applied:
            pct = f"+{round((self.cost_ratio - 1) * 100, 1)}%" if self.cost_ratio else "cost n/a"
            return f"HARDENED — vuln closed + result-equivalent; latency {pct} (Clock C, measured)"
        return f"NOT HARDENED — {self.reason}"


def _compile(src: str, name: str) -> Optional[Callable]:
    ns: dict = {}
    try:
        exec(compile(src.strip(), "<harden>", "exec"), ns, ns)
    except Exception:  # noqa: BLE001
        return None
    fn = ns.get(name)
    return fn if callable(fn) else None


def harden_constant_time(security_on: bool, original_src: str, hardened_src: str, fn_name: str,
                         secret: Set[str], battery: Sequence[tuple], k: int = 7) -> HardenResult:
    """Replace a secret-dependent-branch function with a branchless constant-time version. Applies ONLY if
    `security_on` (the gate said SENSITIVE) AND the hardened source is CT_PROVEN (vuln closed) AND it is
    result-equivalent to the original over `battery` (differential, exact). Measures the Clock-C cost honestly."""
    if not security_on:
        return HardenResult(False, False, False, reason="gate says NOT-SENSITIVE — hardening non-sensitive code would "
                            "be the overhead defect (gate binding); left untouched and fast")
    # (a) vuln closed: the hardened source must be constant-time PROVEN
    ct = constant_time(hardened_src, secret)
    vuln_closed = ct.status == CT_PROVEN
    if not vuln_closed:
        return HardenResult(False, False, False, reason=f"hardened version still leaks ({ct.status}) — not applied")
    fo, fh = _compile(original_src, fn_name), _compile(hardened_src, fn_name)
    if fo is None or fh is None:
        return HardenResult(False, vuln_closed, False, reason="could not compile original/hardened")
    # (b) functional equivalence — IDENTICAL result on every battery input (a result-changing fix is rejected)
    try:
        equivalent = all(fo(*args) == fh(*args) for args in battery)
    except Exception as e:  # noqa: BLE001
        return HardenResult(False, vuln_closed, False, reason=f"evaluation raised {type(e).__name__}")
    if not equivalent:
        return HardenResult(False, vuln_closed, False, reason="hardened version CHANGES the result — REJECTED "
                            "(result-changing hardening is never applied)")
    # measure the honest Clock-C cost (median-of-k)
    import clocks
    big = battery[len(battery) // 2]
    ba = clocks.before_after("harden:ct_select", "C", lambda: fo(*big), lambda: fh(*big), k=k)
    cost_ratio = round(ba.after_ms / ba.before_ms, 3) if ba.before_ms > 0 else None
    return HardenResult(True, True, True, cost_ratio,
                        reason=f"constant-time select proved: no secret branch + identical result on all "
                               f"{len(list(battery))} inputs; cost measured")


def refuse_nonsensitive_hardening(security_on: bool) -> bool:
    """The binding gate, as a checkable predicate: hardening is permitted ONLY when security_on (SENSITIVE)."""
    return security_on
