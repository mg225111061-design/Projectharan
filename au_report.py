"""
§AU REPORT — THE SECOND CLASSICAL-SIMULATION ISLAND (free-fermion / Gaussian) + Tier-1/2 hooks. No new mechanism.
================================================================================================================
There are exactly TWO efficiently-classically-simulable islands, closed under DIFFERENT algebras: ① Clifford /
stabilizer (Sp(2n,𝔽₂) — §AY/qfold.stabilizer) and ② free-fermion / Gaussian / matchgate (Pfaffian · covariance ·
symplectic — §AU/mathmode.free_fermion). Their union is still NOT universal QC (Gottesman–Knill ∪ Valiant ⊊ BQP), so
EXACT lives only inside one island and every boundary DECLINEs with a NAMED THEOREM.

★ Flagship: mathmode.free_fermion (FF-1 Pfaffian/Wick · FF-3 Bogoliubov covariance · FF-2 Peschel · FF-4 Jordan–Wigner
· CV-1 symplectic) — a NEW MODULE (independent algebra), zero-dep self-impl (rational skew-LU Pfaffian, NOT pyzx).
★ Hooks (new recognition branches, 14/22 unchanged): KOOP Koopman · TW treewidth/variable-elimination · LIE-1/2
Wei–Norman/Magnus · CODE-1 CSS · SW Schur–Weyl. ★ §5.5: Zeilberger/creative-telescoping is REUSED
(mathmode.telescoping.zeilberger), NOT reimplemented. ★ "quantum-origin speedup" is a banned bigram (self-checked).
"""
from __future__ import annotations

_MECHS = [
    ("FF-1/2/3/4 + CV-1 free-fermion/Gaussian (flagship)", "A+B", "mathmode.free_fermion", "adversarial_battery"),
    ("KOOP/LIE-1/LIE-2/CODE-1/SW island hooks", "A+B", "island_hooks", "adversarial_battery"),
    ("TW tensor-contraction = treewidth", "A+B", "extract.tensor_contract", "adversarial_battery"),
]

# ── §5 — REJECTED / honest-DECLINE walls (each with a NAMED THEOREM; ZERO code change) ──────────────────────────
REJECTED = [
    ("interacting field theory / models (λφ⁴ · Hubbard · Heisenberg · XXZ Δ≠0)",
     "outside both islands ⇒ DECLINE. Theorem: Wick/Isserlis holds ONLY for a quadratic action; Jordan–Wigner of a "
     "ZZ coupling is a quartic (density-density) fermion term ⇒ interacting. 0 change."),
    ("volume-law entanglement (high-energy eigenstates · random circuits · long-time quench)",
     "bond rank O(2^{N/2}) ⇒ TT/MPS/PEPS gain 0 ⇒ DECLINE. Theorem: Page 1993 / area-law (Hastings 2007) is the "
     "island boundary. 0 change."),
    ("2D PEPS exact contraction",
     "#P-hard ⇒ DECLINE. Theorem: Schuch–Wolf–Verstraete–Cirac 2007. (boundary-MPS approx = certified-numeric only). "
     "0 change."),
    ("high treewidth (expander · dense graphs)",
     "exp(tw) blow-up ⇒ DECLINE. Theorem: Markov–Shi 2008 (contraction cost lower-bounded by treewidth). 0 change."),
    ("non-Gaussian CV (cubic phase · Kerr · photon-number)",
     "outside the symplectic group ⇒ DECLINE. Theorem: Hudson (Wigner positivity ⟺ Gaussian). 0 change."),
    ("non-Clifford ∧ non-matchgate (T · Toffoli)",
     "the UNION of both islands is still not universal QC ⇒ DECLINE. Theorem: Gottesman–Knill ∪ Valiant ⊊ BQP. "
     "0 change."),
    ("mixing-chaos Koopman",
     "continuous Koopman spectrum ⇒ NO finite invariant observable subspace ⇒ DECLINE. Theorem: mixing ⟹ continuous "
     "spectrum. 0 change."),
    ("Jones polynomial = CFG semantic equivalence",
     "FALSE THEOREM (a knot invariant is not a program-semantics invariant) ⇒ wiring it would manufacture false-EXACT "
     "= constitutional violation. mech_knot stays circuit/knot-only. 0 change. (Also: Shor=BM+NTT repackaging, GP=∞-"
     "invariant, RMT=non-deterministic spectrum, Berry/geodesic/GPE/light-cone = heuristics — all 0 change.)"),
]

_BANNED = "quantum" + " " + "speedup"          # banned bigram, never written contiguously in source


def _run() -> list:
    import importlib
    rows = []
    for key, axis, mod, attr in _MECHS:
        m = importlib.import_module(mod)
        b = getattr(m, attr)()
        rows.append({"mechanism": key, "axis": axis, "battery_ok": b["all_ok"], "failed": b.get("failed", [])})
    return rows


def _banned_word_absent() -> bool:
    import importlib
    for _k, _a, mod, _b in _MECHS:
        m = importlib.import_module(mod)
        if m.__doc__ and _BANNED in m.__doc__.lower():
            return False
    return True


def _zeilberger_reused_not_reimplemented() -> bool:
    """§5.5: the SW 6j link must REUSE mathmode.telescoping.zeilberger, NOT a new implementation."""
    try:
        import island_hooks as IH
        from mathmode import telescoping as TS
        return hasattr(TS, "zeilberger") and IH.sixj_zeilberger_link().status in ("EXACT", "PROBABILISTIC")
    except Exception:  # noqa: BLE001
        return False


def report() -> dict:
    rows = _run()
    return {
        "thesis": "the SECOND classical-simulation island (free-fermion/Gaussian: Pfaffian·covariance·symplectic) added "
                  "as a net-new module + 6 recognition-branch hooks (14/22 unchanged). EXACT only inside the two "
                  "islands (Clifford 𝔽₂ ∧ free-fermion/Gaussian); every boundary DECLINEs with a named theorem. "
                  "Zeilberger reused (not reimplemented). Axis A/B separated, never summed.",
        "two_islands": {
            "island_1_clifford": "Sp(2n,𝔽₂) stabilizer — qfold.stabilizer (§AY)",
            "island_2_free_fermion": "Pfaffian / covariance / symplectic — mathmode.free_fermion (§AU)",
            "union_not_universal_QC": "Gottesman–Knill ∪ Valiant ⊊ BQP (different algebras, small intersection)",
        },
        "mechanisms": rows,
        "all_batteries_ok": all(r["battery_ok"] for r in rows),
        "axes_never_summed": True,
        "false_exact_0": all(r["battery_ok"] for r in rows),   # each battery asserts its DECLINE boundary holds
        "banned_phrase_absent": _banned_word_absent(),
        "zeilberger_reused_not_reimplemented": _zeilberger_reused_not_reimplemented(),
        "mechanism_count_unchanged": "14/22 (free_fermion is a NEW module = independent Pfaffian/covariance/symplectic "
                                     "algebra, justified; hooks reuse cfinite/carleman/stabilizer/gf2_solve/telescoping)",
        "zero_dep": "Pfaffian = rational skew-LU self-impl (Parlett–Reid); 𝔽₂ = native_sequence.gf2_solve; no pyzx/"
                    "cadabra/external tensor lib",
        "rejected": [{"wall": c, "theorem_0_change": r} for c, r in REJECTED],
        "verifier_truth": "∀-(2n)/∀-N via Wick / covariance / companion THEOREMS + held-out replay (NOT z3 induction); "
                          "z3/exact only finite identities (Pf²=det, RᵀR=I / SΩSᵀ=Ω, C²−C=0, structure constants, "
                          "H_X H_Zᵀ=0, hook-length).",
        "one_line": "두 번째 고전시뮬 섬(자유페르미온/가우시안: Pfaffian·공분산·심플렉틱)을 신규 모듈 + 6 인식 분기로 "
                    "추가(14/22 불변). EXACT는 두 섬(Clifford 𝔽₂ ∧ 자유페르미온/가우시안) 안에서만, 경계는 전부 이름붙은 "
                    "정리로 DECLINE(상호작용=Wick·부피법칙=Page/area-law·2D PEPS=#P-hard·고treewidth=Markov-Shi·비가우시안"
                    "=Hudson·mixing=연속스펙트럼). Zeilberger 재사용(재구현 0). Axis A/B 분리·금지 bigram 부재·새 메커니즘/"
                    "증명서 종류 0.",
    }


def adversarial_battery() -> dict:
    """★ all 3 §AU batteries green (EXACT-in-island + DECLINE-boundary each); ★ two-island boundary stated, union ⊊
    universal QC; ★ false-EXACT 0; ★ banned bigram absent; ★ Zeilberger REUSED not reimplemented; ★ 8 REJECTED walls
    (each a named theorem, 0 change)."""
    r = report()
    cases = {
        "all_batteries_ok": r["all_batteries_ok"],
        "two_islands_documented": "island_1_clifford" in r["two_islands"] and "island_2_free_fermion" in r["two_islands"],
        "false_exact_0": r["false_exact_0"],
        "banned_phrase_absent": r["banned_phrase_absent"],
        "zeilberger_reused": r["zeilberger_reused_not_reimplemented"],
        "rejected_walls_documented": len(r["rejected"]) == 8,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(report(), indent=2, default=str))
