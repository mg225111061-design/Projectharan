"""
§AO §2.3 — WINOGRAD convolution (fewer multiplies), z3-equivalence-gated. F(2,3) computes 2 outputs from a length-3
================================================================================================================
filter with 4 multiplies instead of 6, via the transform m1=(d0−d2)g0, m2=(d1+d2)(g0+g1+g2)/2, m3=(d2−d1)(g0−g1+g2)/2,
m4=(d1−d3)g2, y0=m1+m2+m3, y1=m2−m3−m4. We z3-prove (over ℚ — the /2 is rational, EXACT) that (y0,y1) ≡ the direct
convolution (d0g0+d1g1+d2g2, d1g0+d2g1+d3g2) ∀ inputs. ★ A wrong Winograd coefficient ⇒ z3 REJECTS. (For FLOAT operands
the /2 reassociation is not bit-exact ⇒ §AB APPROX-ε, named in the cert — not claimed EXACT.)
"""
from __future__ import annotations


def _verify_output(which: int, correct: bool = True):
    """Prove the Winograd y0 (which=0) or y1 (which=1) equals the direct convolution ∀ (ℚ). correct=False perturbs a
    coefficient to exhibit non-equivalence."""
    import catalog.topic_a as TA

    def m(e):
        m1 = (e["d0"] - e["d2"]) * e["g0"]
        m2 = (e["d1"] + e["d2"]) * (e["g0"] + e["g1"] + e["g2"]) / 2
        m3 = (e["d2"] - e["d1"]) * (e["g0"] - e["g1"] + e["g2"]) / 2
        m4 = (e["d1"] - e["d3"]) * e["g2"]
        if not correct:
            m1 = (e["d0"] - e["d2"]) * e["g0"] + 1          # injected coefficient error
        return (m1 + m2 + m3) if which == 0 else (m2 - m3 - m4)

    def direct(e):
        return (e["d0"] * e["g0"] + e["d1"] * e["g1"] + e["d2"] * e["g2"]) if which == 0 \
            else (e["d1"] * e["g0"] + e["d2"] * e["g1"] + e["d3"] * e["g2"])
    return TA.translation_validate(direct, m, ["d0", "d1", "d2", "d3", "g0", "g1", "g2"], sort="Real")


def adversarial_battery() -> dict:
    """★ both Winograd outputs are z3-proven ≡ the direct convolution over ℚ (the 4-mult kernel is accepted EXACT for
    integer/rational operands); ★★ a Winograd kernel with a coefficient error is z3-REJECTED (false EXACT 0)."""
    import kernel_verdict as KV
    y0 = _verify_output(0, correct=True)
    y1 = _verify_output(1, correct=True)
    bad = _verify_output(0, correct=False)
    cases = {
        "winograd_y0_equiv_direct": y0.status == KV.EXACT,
        "winograd_y1_equiv_direct": y1.status == KV.EXACT,
        "wrong_coefficient_rejected": bad.status == KV.DECLINE,     # ★★ A-2
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
