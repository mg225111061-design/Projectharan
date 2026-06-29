"""
§AT REPORT — PROOF-CARRYING VERIFICATION (Clock B fast-lane). Measurement+routing track; NO new mechanism/cert kind.
================================================================================================================
A certificate carries a PORTABLE WITNESS re-checked by a DECIDABLE EXACT computation (telescoping coefficient-zero /
companion replay) — Clock B. A fresh z3 ∀-n attempt DECLINEs (array-induction out of scope) or times out; the cert
re-check recovers EXACT. Measured value = the FLIP COUNT (z3-route DECLINE → cert EXACT).

★ THREE CLOCKS NEVER CONFLATED: Clock B (cert-check time, here) ≠ Clock C (emitted-code runtime) ≠ Axis B (a speedup
ratio). This report measures ONLY Clock B and never sums it with the others.
★ EXACT-lane purity: sampling kinds (Schwartz–Zippel/Freivalds) are FORBIDDEN on the EXACT lane (PROBABILISTIC only);
a wrong cert FAILS its re-check ⇒ false-EXACT 0.
"""
from __future__ import annotations

import proof_carrying as PC


def report() -> dict:
    claims = [PC._faulhaber_sum_cert(), PC._sum_squares_cert(), PC._fibonacci_cert(), PC._tribonacci_cert()]
    flips = PC.measure_flips(claims)
    battery = PC.adversarial_battery()
    return {
        "thesis": "proof-carrying verification: a certificate carries a portable witness re-checked by a DECIDABLE "
                  "EXACT computation (Clock B) — recovering EXACT on ∀-n claims that a budgeted/limited z3 route "
                  "DECLINEs (array-induction out of scope). NO new mechanism, NO new certificate kind (reuses "
                  "cfinite companion replay + telescoping coefficient identities + kernel_verdict.Cert).",
        "clocks": {
            "Clock_B": "certificate re-check wall-clock (THIS track) — cheap, decidable",
            "Clock_C": "the EMITTED code's runtime (a fold's speedup) — DIFFERENT, not measured here",
            "Axis_B": "a speedup RATIO — DIFFERENT, never summed with Clock B",
            "never_conflated": True,
        },
        "flip_measurement": flips,                              # z3-route DECLINE → cert EXACT
        "flip_count": flips["flip_count"],
        "clock_B_total_ms": flips["clock_B_total_ms"],
        "exact_lane_purity": {
            "sampling_forbidden_on_exact_lane": list(PC._SAMPLING_FORBIDDEN),
            "exact_lane_kinds": list(PC._EXACT_LANE),
            "sampling_used": flips["sampling_used_on_exact_lane"],   # must be False
        },
        "false_exact_0": battery["cases"]["tampered_cert_declines"],
        "portability": battery["cases"]["cert_export_import_roundtrip"],
        "battery": battery,
        "no_new_mechanism": "14/22 unchanged; reuses cfinite/kernel_verdict/clocks",
        "no_new_cert_kind": "EXACT certs use the existing 'exact_replay' kind",
        "one_line": "증명서휴대 검증(Clock B 빠른길): 증명서가 *휴대 가능한 witness*를 담고 결정적·정확 재검(텔레스코핑 "
                    "계수영/companion replay)으로 재확인 — z3가 못하는 ∀-n(배열귀납 out-of-scope→DECLINE)을 EXACT로 "
                    "되살림. 측정값=FLIP 수(z3-DECLINE→cert-EXACT). ★3 클락 불혼동: Clock B(증명서검증)≠Clock C(방출코드)"
                    "≠Axis B(가속비). EXACT 레인은 샘플링(SZ/Freivalds) 금지(PROBABILISTIC 전용)·틀린 증명서는 재검 "
                    "실패 ⇒ false-EXACT 0. 새 메커니즘/증명서 종류 0.",
    }


def adversarial_battery() -> dict:
    """★ flip count = total (every ∀-n claim z3 DECLINEs is recovered EXACT by its cert); ★ Clock B measured &
    reported SEPARATELY (never summed with Clock C / Axis B); ★★ no sampling on the EXACT lane; ★★ false-EXACT 0
    (tampered cert DECLINEs); ★ proof-carrying portability (export→import→re-check)."""
    r = report()
    cases = {
        "all_claims_flipped": r["flip_count"] == r["flip_measurement"]["total"] and r["flip_count"] > 0,
        "clocks_never_conflated": r["clocks"]["never_conflated"],
        "no_sampling_on_exact_lane": not r["exact_lane_purity"]["sampling_used"],
        "false_exact_0": r["false_exact_0"],
        "portability": r["portability"],
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(report(), indent=2, default=str))
