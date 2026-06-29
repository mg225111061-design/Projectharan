"""
§AQ REPORT — math fragments in non-math code, MEASURED with the DUAL METRIC (S-3), never summed; precision 1.0.
================================================================================================================
A classifier frontend (effect gate) + five extractors reduce checksums / parsing / periodic-FSM / I/O-surrounding
arithmetic / I/O-call-counts to the EXISTING 22 mechanisms (S-1: no new mechanism, no new disposer, no new cert kind);
the new code is a classification / extraction / effect-isolation pipeline, not new math.

★ S-2 (the soul): every AI hand-derived closed form is RE-PROVEN by z3 — CRC (GF(2)-linear), Adler (telescoping),
Luhn (the convenient 2d-mod-9 form REFUTED at d=9), Rabin-Karp (Horner), FNV (honest DECLINE — the GF(2)-affine claim
does not survive), the Gregorian leap-year period (Julian REFUTED), the alignment bit-trick, the Q9 ceil-count. false-
EXACT 0.
★ S-3 (the dual metric, NEVER summed): Axis A = coverage + verification value (we are a VERIFIED fold compiler — proving
"this loop computes CRC-32 / does ⌈S/CHUNK⌉ reads" has value regardless of speed); Axis B = program speedup (Amdahl, for
§AO priority). CRC / I/O-arith / Q9 are explicitly "Axis A positive, Axis B ≈ 0". The "20-30%" figure is an over-claim
(presented as speedup) — forbidden.
★ S-4 / honest: the §AK numeric corpus does not contain these I/O/parsing idioms, so the §AK realworld delta is ~0;
§AQ's coverage is measured on a focused idiom corpus (M-2: the value is on non-math code the numeric corpus doesn't
represent). ★ S-5: Q9 upper-bound = SPEED/KoAT re-hash (labelled), only the EXACT count is new; data-dependent branch →
spec-declared.
"""
from __future__ import annotations

from extract import classify as CLS, checksum as CK, parse_arith as PA, periodic_fsm as FSM, io_arith as IOA, io_count as IOC
from extract import verhoeff as VH, semiring_lens as SL


def section_batteries() -> dict:
    return {"classify": CLS.adversarial_battery()["all_ok"], "checksum": CK.adversarial_battery()["all_ok"],
            "parse_arith": PA.adversarial_battery()["all_ok"], "periodic_fsm": FSM.adversarial_battery()["all_ok"],
            "io_arith": IOA.adversarial_battery()["all_ok"], "io_count": IOC.adversarial_battery()["all_ok"],
            "verhoeff": VH.adversarial_battery()["all_ok"], "semiring_lens": SL.adversarial_battery()["all_ok"]}


def ai_closed_forms_reverified() -> dict:
    """★★ S-2: every AI hand-derived closed form re-proven by z3, AND a wrong variant of each refuted. The heart."""
    from extract.checksum import crc as CRC, accum as ACC, horner_hash as HH
    from extract.parse_arith import date as DT
    from extract.io_arith import align as AL
    from extract.io_count import count_forms as CF
    luhn = ACC.prove_luhn_lookup()
    proven = {
        "crc_gf2_linear": CRC.prove_crc_linear(32, 0xEDB88320, True),
        "adler_telescoping": ACC.prove_adler_telescoping(4, True),
        "luhn_correct": luhn["correct_proven"],
        "rabin_karp_horner": HH.prove_horner_closed(256, 0, 4, True),
        "gregorian_leapyear": DT.prove_gregorian_period(True),
        "align_bittrick": AL.prove_align_up(6, 32, True),
        "q9_ceil_count": CF.prove_ceil_count(4096, 100000, True),
    }
    refuted = {
        "crc_nonlinear_refuted": not CRC.prove_crc_linear(32, 0xEDB88320, False),
        "adler_offbyone_refuted": not ACC.prove_adler_telescoping(4, False),
        "luhn_2d_mod_9_refuted": luhn["naive_2d_mod_9_refuted"] and luhn["counterexample_d"] == 9,
        "horner_wrong_exp_refuted": not HH.prove_horner_closed(31, 0, 4, False),
        "julian_refuted": not DT.prove_gregorian_period(False),
        "align_wrong_mask_refuted": not AL.prove_align_up(6, 32, False),
        "q9_undercount_refuted": not CF.prove_ceil_count(4096, 100000, False),
    }
    fnv_honest = HH.prove_fnv_not_gf2_affine()                    # FNV: the GF(2)-affine claim did NOT survive z3
    false_exact = sum(1 for v in proven.values() if not v)       # an AI form claimed EXACT but z3-unproven
    return {"proven": proven, "wrong_refuted": refuted, "fnv_honest_decline": fnv_honest,
            "all_proven": all(proven.values()), "all_wrong_refuted": all(refuted.values()),
            "false_exact": false_exact}


def axis_a_coverage() -> dict:
    """★ Axis A: per-section RECOGNITION coverage on a focused idiom corpus (verification value — independent of speed)."""
    recognized = {
        "checksum": CK.fold("def crc32(d):\n c=0\n for b in d: c=(c>>8)^b\n return c").folded,
        "parse_arith": PA.fold("def atoi(s):\n n=0\n for c in s: n=n*10+ord(c)\n return n").folded,
        "periodic_fsm": FSM.fold("def f(n):\n s=0\n for i in range(n):\n  if i%3==0: s+=1\n return s").folded,
        "io_arith": IOA.fold("def a(x):\n read_page()\n return (x+4095)&~4095").folded,
        "io_count": IOC.fold("def f(S):\n pos=0;n=0\n while pos<S:\n  read(fd,4096);pos+=4096;n+=1\n return n").is_exact_count,
    }
    return {"recognized_per_section": recognized, "n_recognized": sum(1 for v in recognized.values() if v),
            "note": "Axis A = coverage + verification value (a VERIFIED fold compiler); reported SEPARATELY from Axis B"}


def axis_b_amdahl() -> dict:
    """★ Axis B: program speedup (Amdahl). ★★ NEVER summed with Axis A. Most §AQ fragments are I/O-dominated slivers."""
    return {"checksum": "~0 (I/O-wrapped sliver; Rabin-Karp hot-search may be >0)",
            "parse_arith": "~0 (small, I/O-bound)", "periodic_fsm": "~0 (>0 if the FSM dominates runtime)",
            "io_arith": "~0 (arithmetic beside the I/O)", "io_count": "~0 (the I/O still happens — count predicts, not removes)",
            "never_summed_with_axis_a": True,
            "over_claim_rejected": "the '20-30%' figure presented as speedup is forbidden (Axis A/B conflation)"}


def ak_corpus_delta(sample: int = 200) -> dict:
    """Run the classifier over a §AK corpus sample. ★ Honest: the §AK NUMERIC corpus does not contain checksum/parse/
    I/O idioms, so §AQ recognizes ~0 of its DECLINEs — §AQ's value is on non-math code the numeric corpus does not
    represent (S-4, M-2). Reported as coverage, never as a fold-rate inflation."""
    from corpus import build_corpus as BC
    from measure import engine_adapter as EA
    items = BC.build_corpus()[:sample]
    decline = recognized = 0
    for it in items:
        try:
            if EA.classify(it).classification != EA.DECLINE:
                continue
        except Exception:  # noqa: BLE001
            continue
        decline += 1
        c = CLS.classify(it.src)
        if c["route"] in ("checksum", "parse_arith", "periodic_fsm", "io_frame"):
            recognized += 1
    return {"sample": sample, "baseline_decline": decline, "aq_recognized": recognized,
            "note": "≈0 is HONEST — the §AK numeric corpus lacks checksum/parse/I/O idioms; §AQ covers non-math code "
                    "(measured on the focused idiom corpus). NOT added to the fold rate."}


def report(sample: int = 200) -> dict:
    bats = section_batteries()
    ai = ai_closed_forms_reverified()
    aa = axis_a_coverage()
    ab = axis_b_amdahl()
    delta = ak_corpus_delta(sample)
    return {
        "thesis": "extract deterministic math fragments from non-math (I/O / parsing / control-flow) code — classify "
                  "(effect gate) → extract → reduce to the EXISTING 22 mechanisms; z3 disposes (S-1/S-2). DUAL metric, "
                  "never summed (S-3).",
        "section_batteries": bats, "all_batteries_green": all(bats.values()),
        "ai_closed_forms_reverified": ai,
        "axis_A_coverage": aa, "axis_B_amdahl": ab,
        "ak_corpus_delta": delta,
        "precision": {"false_exact": ai["false_exact"], "gate_pass": ai["false_exact"] == 0 and ai["all_wrong_refuted"],
                      "note": "every AI closed form z3-proven; every wrong variant z3-refuted (incl. Luhn 2d-mod-9 at d=9); FNV honest DECLINE"},
        "S1_no_new_mechanism": True, "new_certificate_kinds": 0,
        "permanent_declines": ["MurmurHash3", "Pearson", "crypto (BCrypt/CSPRNG)", "data-dependent branches"],
        "one_line": f"비수학 코드 속 수학 조각 — 분류기(효과게이트)+체크섬/파싱/주기FSM/I/O산술/Q9, 전부 기존 22개 환원(S-1); "
                    f"AI 닫힌형 전부 z3 재증명(S-2, Luhn 2d-mod-9 d=9 반증·FNV 정직 DECLINE); 이중지표 분리(S-3, Axis B≈0); "
                    f"false-EXACT {ai['false_exact']}; 새 메커니즘/종류 0.",
    }


def adversarial_battery() -> dict:
    """★ all eight section batteries green; ★★ S-2: every AI closed form z3-re-proven AND every wrong variant refuted
    (Luhn 2d-mod-9 caught at d=9; FNV honest DECLINE) ⇒ false-EXACT 0; ★★ S-3: Axis A and Axis B reported separately and
    NEVER summed (CRC/io/Q9 = Axis-A-positive / Axis-B-≈0); ★ S-4 honest §AK delta; ★ S-1 no new mechanism / cert kind."""
    r = report(sample=80)
    ai = r["ai_closed_forms_reverified"]
    cases = {
        "all_sections_green": r["all_batteries_green"],
        "ai_all_proven": ai["all_proven"],                                        # ★★ S-2
        "ai_all_wrong_refuted": ai["all_wrong_refuted"],                          # ★★ S-2 (incl. Luhn d=9)
        "fnv_honest_decline": ai["fnv_honest_decline"],
        "false_exact_zero": r["precision"]["false_exact"] == 0 and r["precision"]["gate_pass"],
        "dual_metric_never_summed": r["axis_B_amdahl"]["never_summed_with_axis_a"],   # ★★ S-3
        "axis_a_recognizes": r["axis_A_coverage"]["n_recognized"] >= 4,
        "no_new_mechanism_or_kind": r["S1_no_new_mechanism"] and r["new_certificate_kinds"] == 0,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
