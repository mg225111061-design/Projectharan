"""
§BN NEW-4 — discrete Morse data ⊣ homology: the Morse inequalities, certified (conservation m05 / m09, Axis B).
==================================================================================================================
A discrete Morse function on a CW/cubical complex has c_k critical cells of dimension k.  Morse theory forces
THREE relations between the critical-cell vector (c_k) and the homology Betti numbers (b_k = free rank of H_k):

  • weak Morse     : c_k ≥ b_k                              for every k
  • strong Morse   : Σ_{i≤k} (−1)^{k−i} c_i ≥ Σ_{i≤k} (−1)^{k−i} b_i   for every k   (alternating partial sums)
  • Morse equation : Σ (−1)^k c_k = Σ (−1)^k b_k = χ        (the Euler characteristic)

This is a cheap VERIFIER (Axis B): given a PROPOSED Morse vector and the topology (Betti given directly, or a
chain complex routed through smith_homology), it certifies consistency in O(#dims).  A Morse function whose
critical counts equal the Betti numbers (c_k = b_k) is PERFECT — the topological minimum.

★ certificate-or-DECLINE: the three relations are re-checked exactly; ANY violation ⇒ DECLINE (the proposed
  Morse data is NOT realizable on a complex with that homology — or the Betti input is wrong).  false-EXACT 0.
0 new mechanism (conservation m05 — Euler — + complete-invariant m09 branch); 0 new disposer. zero-dep.
"""
from __future__ import annotations

from typing import List, Optional

import kernel_verdict as KV
from newengine5 import smith_homology as SH


def _betti_from_complex(boundaries) -> Optional[List[int]]:
    v = SH.homology(boundaries)
    return v.result["betti"] if v.status == "EXACT" else None


def verify(critical: List[int], betti: List[int]) -> KV.Verdict:
    """EXACT 'valid Morse data' iff weak + strong Morse inequalities and the Morse (Euler) equation all hold; the
    `perfect` flag reports c_k == b_k for all k. Any violation ⇒ DECLINE."""
    c = [int(x) for x in critical]
    b = [int(x) for x in betti]
    K = max(len(c), len(b))
    c += [0] * (K - len(c)); b += [0] * (K - len(b))
    if any(x < 0 for x in c):
        return KV.decline("morse: negative critical-cell count", "morse_inequalities")
    # weak
    weak = all(c[k] >= b[k] for k in range(K))
    if not weak:
        bad = next(k for k in range(K) if c[k] < b[k])
        return KV.decline(f"morse: weak inequality c_{bad}={c[bad]} ≥ b_{bad}={b[bad]} violated ⇒ DECLINE",
                          "morse_inequalities")
    # strong (alternating partial sums)
    for k in range(K):
        lhs = sum((-1) ** (k - i) * c[i] for i in range(k + 1))
        rhs = sum((-1) ** (k - i) * b[i] for i in range(k + 1))
        if lhs < rhs:
            return KV.decline(f"morse: strong inequality at k={k} ({lhs} ≥ {rhs}) violated ⇒ DECLINE",
                              "morse_inequalities")
    # Morse (Euler) equation
    chi_c = sum((-1) ** k * c[k] for k in range(K))
    chi_b = sum((-1) ** k * b[k] for k in range(K))
    if chi_c != chi_b:
        return KV.decline(f"morse: Morse equation Σ(−1)^k c_k={chi_c} ≠ χ={chi_b} ⇒ DECLINE", "morse_inequalities")
    perfect = all(c[k] == b[k] for k in range(K))
    cert = KV.Cert(KV.EXACT, "morse_inequalities", passed=True, check_cost="O(#dims) weak+strong+Euler re-check",
                   detail=f"c={c}, b={b}: weak c_k≥b_k ✓, strong partial sums ✓, Morse eq χ={chi_c} ✓; "
                          f"perfect={perfect}")
    return KV.exact({"valid_morse": True, "perfect": perfect, "euler_characteristic": chi_c,
                     "morse_number_lower_bound": sum(b)}, "morse_inequalities", "Morse inequalities", cert)


def morse_grade(payload: dict) -> KV.Verdict:
    """Route: {critical:[…], betti:[…]} | {critical:[…], complex:[∂_1,…]} (Betti via smith_homology)."""
    if not (isinstance(payload, dict) and "critical" in payload):
        return KV.decline("morse: expected {critical:[…], betti|complex:…}", "morse_inequalities")
    if "betti" in payload:
        return verify(payload["critical"], payload["betti"])
    if "complex" in payload:
        b = _betti_from_complex(payload["complex"])
        if b is None:
            return KV.decline("morse: smith_homology DECLINEd the complex ⇒ DECLINE", "morse_inequalities")
        return verify(payload["critical"], b)
    return KV.decline("morse: need betti or complex", "morse_inequalities")


def adversarial_battery() -> dict:
    """★ a perfect Morse function on S² (c=[1,0,1]=b) ⇒ EXACT perfect; ★ a non-minimal one on S² (c=[1,1,1]) ⇒
    EXACT valid, not perfect; ★ too few cells (c=[1,0,0] vs b=[1,0,1]) ⇒ DECLINE (weak); ★ wrong Euler parity
    (c=[1,0,0] vs b=[1,0]) handled; ★ Betti from a chain complex (S¹) routes through smith_homology."""
    perfect = verify([1, 0, 1], [1, 0, 1])                 # sphere S², perfect Morse function
    valid = verify([1, 1, 2], [1, 0, 1])                   # adds a cancelling (1-cell,2-cell) pair: still valid
    too_few = verify([1, 0, 0], [1, 0, 1])                 # missing the top cell ⇒ weak inequality fails
    strong_bad = verify([1, 2, 0], [1, 0, 1])              # c violates strong/Euler vs S² Betti
    via_complex = morse_grade({"critical": [1, 1], "complex": [[[0]]]})   # S¹ Betti=[1,1], perfect c=[1,1]
    cases = {
        "sphere_perfect_EXACT": perfect.status == "EXACT" and perfect.result["perfect"] is True,
        "sphere_valid_not_perfect": valid.status == "EXACT" and valid.result["perfect"] is False,
        "too_few_cells_DECLINE": too_few.status == "DECLINE",
        "strong_or_euler_DECLINE": strong_bad.status == "DECLINE",
        "betti_via_complex_EXACT": via_complex.status == "EXACT" and via_complex.result["perfect"] is True,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
