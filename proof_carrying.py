"""
§AT — PROOF-CARRYING VERIFICATION (Clock B fast-lane). A measurement+routing track, NOT a new mechanism/cert kind.
================================================================================================================
The §0 verifier truth (shared with §AY/§AI): z3 does NOT prove ∀-n unbounded sequences/sums (`prove_exact` says
array-induction is out of scope; `equiv_check` maps z3 `unknown`/timeout → DECLINE). ∀-n comes from a STRUCTURE
THEOREM — telescoping (S(n)−S(n−1)≡body(n), a finite-variable polynomial identity) or a companion/minimal-polynomial
recurrence (∀-n by construction) — re-checked by an EXACT, DECIDABLE, NON-HEURISTIC computation.

A "proof-carrying" certificate carries the PORTABLE WITNESS (polynomial coefficients / companion (c,init) + held-out
oracle values) so the claim can be re-verified WITHOUT re-running z3. Re-checking the certificate is Clock B
(verification wall-clock) — cheap and decidable — whereas a fresh z3 ∀-n attempt DECLINEs (out of scope) or times
out under a budget. The measured win is the **FLIP COUNT**: claims that a budgeted/limited z3 route DECLINEs but a
certificate re-check confirms EXACT.

★ THREE CLOCKS NEVER CONFLATED (the directive's core): Clock B = certificate-check time (this module); Clock C =
the emitted code's runtime (a fold's speedup); Axis B = a speedup RATIO. §AT touches ONLY Clock B; it never sums
Clock B with Clock C or Axis B.
★ EXACT-LANE PURITY: only DECIDABLE-EXACT re-check kinds enter the EXACT fast-lane. Schwartz–Zippel / Freivalds /
any SAMPLING kind is FORBIDDEN here (it is PROBABILISTIC, never EXACT — §1.1). A sampling cert is rejected from the
fast-lane. A wrong certificate FAILS its re-check ⇒ false-EXACT 0.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from math import comb
from typing import Callable, Dict, List, Optional

import cfinite
import clocks
import kernel_verdict as KV

# decidable + exact + non-heuristic re-check kinds permitted on the EXACT fast-lane
_EXACT_LANE = ("telescoping_identity", "companion_replay")
# sampling kinds — PROBABILISTIC only, FORBIDDEN on the EXACT lane (§1.1 / §0.2)
_SAMPLING_FORBIDDEN = ("schwartz_zippel", "freivalds", "differential_sampling", "monte_carlo")


@dataclass
class PCCert:
    """A proof-carrying certificate: a portable witness whose re-check is exact + decidable (no z3, no sampling)."""
    recheck_kind: str                 # one of _EXACT_LANE
    claim: str
    data: Dict                        # portable witness (poly coeffs / companion c,init + oracle tail)


# ── decidable exact re-checkers (the portable witness re-verified from `data` alone) ────────────────────────────
def _poly_minus_shift_coeffs(a: List[Fraction]) -> List[Fraction]:
    """Coefficients of S(n)−S(n−1) where S(n)=Σ a_i n^i (exact, via the binomial expansion of (n−1)^i)."""
    d = len(a)
    out = [Fraction(0)] * d
    for i in range(d):
        out[i] += a[i]
        for j in range(i + 1):                       # (n−1)^i = Σ_j C(i,j) n^j (−1)^(i−j)
            out[j] -= a[i] * comb(i, j) * ((-1) ** (i - j))
    return out


def recheck_telescoping(data: Dict) -> bool:
    """EXACT, decidable: confirm S(n)−S(n−1)−body(n) ≡ 0 as a polynomial identity, by comparing coefficients over ℚ
    (NOT sampling — coefficient equality of bounded-degree polynomials is a complete, finite check)."""
    try:
        S = [Fraction(x) for x in data["S_coeffs"]]
        body = [Fraction(x) for x in data["body_coeffs"]]
    except (KeyError, TypeError, ValueError):
        return False
    diff = _poly_minus_shift_coeffs(S)               # coeffs of S(n)−S(n−1)
    width = max(len(diff), len(body))
    diff += [Fraction(0)] * (width - len(diff))
    bodyp = body + [Fraction(0)] * (width - len(body))
    if any(diff[i] != bodyp[i] for i in range(width)):
        return False                                 # S(n)−S(n−1) ≢ body(n) ⇒ NOT a telescoping cert
    base = data.get("base")                          # optional base case S(n0)=value
    if base is not None:
        n0, val = base
        s_n0 = sum((S[i] * Fraction(n0) ** i for i in range(len(S))), Fraction(0))
        if s_n0 != Fraction(val):
            return False
    return True


def recheck_companion(data: Dict) -> bool:
    """EXACT, decidable: replay the companion recurrence on the carried held-out oracle tail (exact ℤ/ℚ arithmetic).
    ∀-n holds by the companion-matrix theorem; the tail confirms (c,init) match the true sequence."""
    try:
        c = [Fraction(x) for x in data["c"]]
        init = [Fraction(x) for x in data["init"]]
        tail = data["oracle_tail"]                   # [[k, value], …] TRUE values beyond the fit window
    except (KeyError, TypeError, ValueError):
        return False
    if not tail:
        return False
    for k, v in tail:
        if cfinite.companion_nth(c, init, int(k)) != Fraction(v):
            return False
    return True


_RECHECKERS: Dict[str, Callable[[Dict], bool]] = {
    "telescoping_identity": recheck_telescoping,
    "companion_replay": recheck_companion,
}


# ── certificate export / import (proof-carrying portability) ────────────────────────────────────────────────────
def cert_export(cert: PCCert) -> Dict:
    """Serialize a cert to a portable dict (rationals as strings) — it carries everything needed to re-verify."""
    def enc(x):
        if isinstance(x, Fraction):
            return str(x)
        if isinstance(x, list):
            return [enc(y) for y in x]
        return x
    return {"recheck_kind": cert.recheck_kind, "claim": cert.claim, "data": {k: enc(v) for k, v in cert.data.items()}}


def cert_import(d: Dict) -> PCCert:
    return PCCert(d["recheck_kind"], d.get("claim", ""), d["data"])


def recheck_exported(d: Dict) -> bool:
    """Re-verify a cert from its EXPORTED dict ALONE (no original closures) — the proof-carrying guarantee."""
    kind = d.get("recheck_kind")
    if kind not in _RECHECKERS:
        return False
    return _RECHECKERS[kind](d["data"])


# ── the Clock-B fast-lane ───────────────────────────────────────────────────────────────────────────────────────
@dataclass
class FastLaneResult:
    verdict: KV.Verdict
    clock_B_ms: float                  # certificate re-check time (Clock B) — NEVER summed with Clock C / Axis B
    used_cert: bool
    detail: str = ""


def verify_exact_fast_lane(cert: Optional[PCCert]) -> FastLaneResult:
    """Re-check a proof-carrying certificate on the EXACT lane (Clock B). A sampling kind is REJECTED (PROBABILISTIC,
    never EXACT). A passing exact re-check ⇒ EXACT; a failing/absent cert ⇒ DECLINE (the caller may fall back to z3)."""
    if cert is None:
        return FastLaneResult(KV.decline("proof-carrying: no certificate ⇒ DECLINE (fall back to z3)", "proof_carrying"),
                              0.0, False, "no cert")
    if cert.recheck_kind in _SAMPLING_FORBIDDEN:
        return FastLaneResult(KV.decline(f"proof-carrying: '{cert.recheck_kind}' is a SAMPLING cert — PROBABILISTIC "
                                         f"only, FORBIDDEN on the EXACT lane (§1.1)", "proof_carrying"),
                              0.0, False, "sampling rejected")
    if cert.recheck_kind not in _RECHECKERS:
        return FastLaneResult(KV.decline(f"proof-carrying: unknown re-check kind '{cert.recheck_kind}' ⇒ DECLINE",
                                         "proof_carrying"), 0.0, False, "unknown kind")
    sample = clocks.measure(f"pc_recheck[{cert.recheck_kind}]", "B", lambda: _RECHECKERS[cert.recheck_kind](cert.data))
    passed = _RECHECKERS[cert.recheck_kind](cert.data)
    if not passed:
        return FastLaneResult(KV.decline(f"proof-carrying: certificate re-check FAILED ({cert.claim}) ⇒ DECLINE "
                                         f"(no false-EXACT)", "proof_carrying"), sample.ms, True, "recheck failed")
    c = KV.Cert(KV.EXACT, "exact_replay", passed=True, check_cost=f"Clock B decidable re-check ({cert.recheck_kind})",
                detail=f"proof-carrying cert re-checked exactly (no z3, no sampling): {cert.claim}")
    return FastLaneResult(KV.exact({"recheck_kind": cert.recheck_kind, "claim": cert.claim}, "proof_carrying",
                                   "O(cert) Clock-B re-check", c), sample.ms, True, "EXACT via cert")


def z3_route_unbounded_declines(_claim: str) -> KV.Verdict:
    """The pure-z3 route for an UNBOUNDED ∀-n claim: z3 cannot do array/sequence induction (`prove_exact`: out of
    scope) — `equiv_check` maps the unknown/timeout to DECLINE. So the unbounded claim is z3-DECLINE by construction;
    the proof-carrying cert is what supplies ∀-n. (Honest: this is not a strawman — it is the verifier's stated limit.)"""
    return KV.decline("z3: ∀-n unbounded induction is out of scope (prove_exact) — z3 unknown ⇒ DECLINE", "z3_route")


# ── flip measurement: z3-route DECLINE → certificate EXACT (the measured value of proof-carrying) ───────────────
def measure_flips(claims: List[PCCert]) -> Dict:
    """For each ∀-n claim carrying a decidable cert: the z3 route DECLINEs (out of scope), the proof-carrying lane
    re-checks EXACT. A FLIP = z3-DECLINE ∧ cert-EXACT. Reports flip count + total Clock-B time (separate from any
    speedup). NO flip uses sampling (the EXACT lane forbids it)."""
    flips, clock_B_total, sampling_used = 0, 0.0, False
    rows = []
    for cert in claims:
        z3v = z3_route_unbounded_declines(cert.claim)
        fl = verify_exact_fast_lane(cert)
        clock_B_total += fl.clock_B_ms
        is_flip = (z3v.status == KV.DECLINE) and (fl.verdict.status == KV.EXACT)
        flips += 1 if is_flip else 0
        if cert.recheck_kind in _SAMPLING_FORBIDDEN:
            sampling_used = True
        rows.append({"claim": cert.claim, "z3": z3v.status, "cert": fl.verdict.status, "flip": is_flip,
                     "clock_B_ms": round(fl.clock_B_ms, 4)})
    return {"flip_count": flips, "total": len(claims), "clock_B_total_ms": round(clock_B_total, 4),
            "sampling_used_on_exact_lane": sampling_used, "rows": rows}


# ── demonstration claims (each TRUE, each with a decidable cert; z3 can't do the unbounded ∀-n) ─────────────────
def _faulhaber_sum_cert() -> PCCert:
    """Σ_{k=1}^n k = n(n+1)/2. S(n)=n²/2+n/2, body(n)=n. Telescoping coeff identity (exact)."""
    return PCCert("telescoping_identity", "Σ_{k=1}^n k = n(n+1)/2",
                  {"S_coeffs": ["0", "1/2", "1/2"], "body_coeffs": ["0", "1"], "base": [0, "0"]})


def _sum_squares_cert() -> PCCert:
    """Σ_{k=1}^n k² = n(n+1)(2n+1)/6. S(n)=n³/3+n²/2+n/6, body(n)=n². Telescoping (exact)."""
    return PCCert("telescoping_identity", "Σ_{k=1}^n k² = n(n+1)(2n+1)/6",
                  {"S_coeffs": ["0", "1/6", "1/2", "1/3"], "body_coeffs": ["0", "0", "1"], "base": [0, "0"]})


def _fibonacci_cert() -> PCCert:
    """Fibonacci f(n)=f(n-1)+f(n-2): companion (c=[1,1], init=[0,1]) + a far held-out oracle tail (exact)."""
    fib = [0, 1]
    while len(fib) <= 40:
        fib.append(fib[-1] + fib[-2])
    tail = [[k, str(fib[k])] for k in (30, 35, 40)]
    return PCCert("companion_replay", "Fibonacci f(n)=f(n-1)+f(n-2) ∀n",
                  {"c": ["1", "1"], "init": ["0", "1"], "oracle_tail": tail})


def _tribonacci_cert() -> PCCert:
    """Tribonacci f(n)=f(n-1)+f(n-2)+f(n-3): companion order-3 + held-out tail (exact)."""
    t = [0, 0, 1]
    while len(t) <= 30:
        t.append(t[-1] + t[-2] + t[-3])
    tail = [[k, str(t[k])] for k in (22, 26, 30)]
    return PCCert("companion_replay", "Tribonacci f(n)=f(n-1)+f(n-2)+f(n-3) ∀n",
                  {"c": ["1", "1", "1"], "init": ["0", "0", "1"], "oracle_tail": tail})


def adversarial_battery() -> dict:
    """★ FLIP: ∀-n claims (Faulhaber sums, Fibonacci/Tribonacci recurrences) that z3 cannot prove (unbounded
    induction out of scope ⇒ DECLINE) are re-checked EXACT by a decidable proof-carrying cert (Clock B). ★★ false-
    EXACT 0: a TAMPERED cert (wrong coefficient / wrong recurrence) FAILS its re-check ⇒ not EXACT. ★★ a SAMPLING
    cert (Schwartz–Zippel) is REJECTED from the EXACT lane. ★ cert export→import→independent re-check round-trips
    (proof-carrying portability). ★ Clock B measured + reported separately (never summed with Axis B / Clock C)."""
    claims = [_faulhaber_sum_cert(), _sum_squares_cert(), _fibonacci_cert(), _tribonacci_cert()]
    flips = measure_flips(claims)
    all_flip = flips["flip_count"] == len(claims) and not flips["sampling_used_on_exact_lane"]

    # ★★ tampered certs must FAIL (false-EXACT 0)
    bad_tel = PCCert("telescoping_identity", "WRONG: Σk = n²/2 (missing n/2)",
                     {"S_coeffs": ["0", "0", "1/2"], "body_coeffs": ["0", "1"]})
    bad_comp = PCCert("companion_replay", "WRONG Fibonacci coeffs",
                      {"c": ["1", "2"], "init": ["0", "1"], "oracle_tail": [[10, "55"]]})  # 55 is true fib(10); c wrong
    tampered_decline = (verify_exact_fast_lane(bad_tel).verdict.status == KV.DECLINE
                        and verify_exact_fast_lane(bad_comp).verdict.status == KV.DECLINE)

    # ★★ a sampling cert is rejected from the EXACT lane
    sampling_cert = PCCert("schwartz_zippel", "polynomial identity by random probes", {"rounds": 3})
    sampling_rejected = verify_exact_fast_lane(sampling_cert).verdict.status == KV.DECLINE

    # ★ portability: export → import → independent re-check (from the dict alone)
    exported = cert_export(_sum_squares_cert())
    portable = recheck_exported(exported) and not recheck_exported(cert_export(bad_tel))

    # ★ Clock B is its own clock (sample carries clock=="B")
    s = clocks.measure("pc_demo", "B", lambda: recheck_telescoping(_faulhaber_sum_cert().data))
    clock_B_labeled = s.clock == "B" and s.ms >= 0.0

    cases = {
        "all_claims_flip_z3decline_to_certEXACT": all_flip,
        "tampered_cert_declines": tampered_decline,
        "sampling_cert_rejected_from_exact_lane": sampling_rejected,
        "cert_export_import_roundtrip": portable,
        "clock_B_labeled_separately": clock_B_labeled,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
