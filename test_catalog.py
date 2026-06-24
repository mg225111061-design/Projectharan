"""
CATALOG ENGINE — test suite (Constitution §7.6). Standalone runner (deterministic). Each kernel/mechanism gets
(a) a positive case, (b) a negative control that DECLINEs, (c) grade-consistency. PHASE A covers the skeleton +
honesty invariants; later phases add gated-kernel tests.

Run:  OMP_NUM_THREADS=1 python3 test_catalog.py
"""
from __future__ import annotations

import traceback


def test_mechanisms_closed():
    """The 14 mechanisms are exactly 1..14 + 2 primitives; the framework is CLOSED (no 15th — §D-1·D-2)."""
    import mechanisms as M
    assert sorted(M.MECHANISMS) == list(range(1, 15)), sorted(M.MECHANISMS)
    assert set(M.PRIMITIVES) == {"legendre_dual", "symmetry_reduce"}
    rep = M.closure_report()
    assert rep["framework_closed"] and rep["fifteenth_candidate"] is None, rep
    # every mechanism carries a HARAN contract (requires/ensures/grade) and a probe + apply
    for i, mech in M.MECHANISMS.items():
        c = mech.contract
        assert "requires" in c and "ensures" in c and "grade" in c, (i, c)
        assert callable(mech.probe) and callable(mech.apply)
    print("PASS test_mechanisms_closed (14 mechanisms 1..14 + 2 primitives; framework closed; every mechanism has a "
          "HARAN contract + probe + apply)")


def test_probe_vector_routes():
    """The cheap probe vector routes sample inputs to the right mechanism (heuristic first pass)."""
    import mechanisms as M
    assert M.top_mechanisms([[1, 2], [3, 4]])[0][0] == 1                      # matrix → diagonalize
    assert M.top_mechanisms("x**2-2x+1 >= 0 sum of squares")[0][0] == 4       # poly inequality → SOS
    assert M.top_mechanisms("classify curvature invariant")[0][0] == 9        # classification → complete invariant
    assert M.top_mechanisms("does this program halt (rice)")[0][0] == 14      # undecidable → obstruction
    pv = M.probe_vector("def f(n):\n s=0\n for k in range(n): s+=k\n return s")
    assert len(pv) == 14 and all(0.0 <= s <= 1.0 for s in pv)                 # valid [0,1]^14
    print("PASS test_probe_vector_routes (matrix→M1, poly-ineq→M4, classify→M9, halt→M14; probe vector ∈ [0,1]^14)")


def test_catalog_coverage_honest():
    """100% REGISTERED (§1.4): every §4 transform has an honest entry; all 14 mechanisms + all 9 passes present.
    'verified' is reported honestly (0 at PHASE A — applies gated later), NEVER faked to 100%."""
    import catalog
    cov = catalog.coverage()
    assert cov["registered"] == 94, cov                       # the §4 named transforms
    assert cov["all_14_mechanisms_have_a_transform"], cov
    assert set(cov["per_pass"]) == {"1-6", "A-1", "A-2", "B-1", "B-2", "C-1", "C-2", "D-1", "D-2"}, cov["per_pass"]
    assert cov["registered"] == cov["verified"] + cov["deferred"], cov       # honest accounting
    assert cov["composed"] >= 30, cov                          # deep results are compositions (§3.4)
    # every transform is an honest entry: VERIFIED or UNVERIFIED(reason); mechanisms in 1..14 (+0/-1)
    for t in catalog.TRANSFORMS:
        assert t.verified or t.status.startswith("UNVERIFIED"), (t.tid, t.status)
        assert t.mechanisms, t.tid
    print(f"PASS test_catalog_coverage_honest ({cov['registered']} transforms registered across all 9 passes + 14 "
          f"mechanisms; {cov['verified']} VERIFIED / {cov['deferred']} honest-deferred [honest 100% REGISTERED, not "
          f"faked 100% pass]; {cov['composed']} compositions)")


def test_decline_backbone():
    """§6 DECLINE guards fire on explicit boundary markers and the proven-boundary list is present. A DECLINE is a
    POSITIVE absence-proof (a win) — and is always safe (never a §7.5 false positive, which is claiming structure)."""
    import catalog.decline_boundary as DB
    import kernel_verdict as KV
    assert DB.rice_guard("does this program halt on all inputs?").status == KV.DECLINE
    assert DB.incompressibility_guard("this is a kolmogorov-random string").status == KV.DECLINE
    assert DB.turbulence_guard("classification with no complete invariant (E0/turbulence)").status == KV.DECLINE
    # conservative: ordinary structured input does NOT trip a guard (no over-decline of foldable code)
    assert DB.check("def f(n):\n return sum(k for k in range(n))") is None
    assert len(DB.boundary_names()) >= 15                      # the proven-boundary list
    print(f"PASS test_decline_backbone (Rice/incompressibility/turbulence guards fire on boundary markers; ordinary "
          f"structured code passes through; {len(DB.boundary_names())} proven boundaries listed)")


def test_compose_router():
    """§5 router: existing fold first (EXACT), DECLINE boundary short-circuits, catalog composition returns an
    HONEST DECLINE with the planned mechanism_path (no fake result at PHASE A — applies gated in PHASE E)."""
    import catalog.compose as C
    import kernel_verdict as KV
    # existing fold → EXACT, mechanism 13
    r = C.route("def f(n):\n s=0\n for k in range(1,n+1):\n  s+=k*k\n return s")
    assert r.grade == KV.EXACT and r.mechanism_path == [13] and "n*(n + 1)*(2*n + 1)/6" in str(r.verdict.result), r
    # Rice boundary → DECLINE, mechanism 14
    r = C.route("is this arbitrary program semantically equivalent to that one?")
    assert r.grade == KV.DECLINE and r.mechanism_path == [14], r
    # an UNBUILT composition (classification 9→2) → honest DEFER naming the path (not a fake pass)
    r = C.route("classify the curvature complete invariant")
    assert r.grade == KV.DECLINE and r.mechanism_path == [9, 2] and "HONEST_DEFER" in r.verdict.reason, r
    assert len(r.probe) == 14
    print("PASS test_compose_router (fold→EXACT[13]; Rice→DECLINE[14]; unbuilt composition [9→2]→honest-DEFER with "
          "probe vector + mechanism_path — no fake pass)")


def test_no_unverified_autoselect():
    """§2/§7: the kernel_router never auto-selects an UNVERIFIED kernel; catalog transforms with kernel=None are
    not yet wired (honest). This guards the 'no unverified auto-select' rule across the build."""
    import kernel_router as KR
    import catalog
    vc = KR.verify_contracts()
    assert vc["all_well_formed"], vc                           # every registered kernel has a well-formed contract
    # the invariant (§2/§7): a VERIFIED transform is backed by a kernel that is a VERIFIED router kernel; an
    # UNVERIFIED transform carries kernel=None (never auto-selected). And the router auto-select list is all VERIFIED.
    verified_kernels = set(KR.registered(verified_only=True))
    for t in catalog.TRANSFORMS:
        if t.verified:
            assert t.kernel is not None and t.kernel in verified_kernels, (t.tid, t.kernel)
        else:
            assert t.kernel is None, (t.tid, t.kernel)
    assert all(KR.REGISTRY[n].status == "VERIFIED" for n in verified_kernels)
    print(f"PASS test_no_unverified_autoselect ({vc['n_kernels']} router kernels, contracts well-formed; every "
          f"VERIFIED transform backed by a VERIFIED kernel, every UNVERIFIED transform kernel=None — no UNVERIFIED "
          f"auto-select)")


def test_phaseB_sos_exact_tier():
    """PHASE B (★) — SOS/Positivstellensatz EXACT tier: a global SOS gets an EXACT rational-PSD-Gram certificate
    (zᵀQz≡p exact + Q⪰0 Sturm-exact); non-nonneg polynomials DECLINE (no overclaim); the cert re-checks and a
    tampered cert is rejected. Backs catalog transforms B1.sos_positivstellensatz + D2.sos_refutation."""
    import sos_cert as S
    import sympy as sp
    import kernel_verdict as KV
    import catalog
    x, y = sp.symbols("x y")
    # positive: EXACT SOS + the certificate re-verifies exactly
    for e in (x**2 - 2*x + 1, x**2 + y**2 - 2*x*y, x**4 + 1, 2*x**2 + 2*y**2 + 2*x*y):
        v = S.sos_grade(e)
        assert v.status == KV.EXACT and v.certificate.passed, (e, v)
        assert S.verify_sos(e, v.result["gram"], v.result["basis"]), e          # cert re-checks
    # ★ negative controls: not globally nonneg ⇒ DECLINE (never a fake pass) ★
    for e in (x**2 - 1, x**3, x*y, x**4 - x**2, -x**2):
        assert S.sos_grade(e).status == KV.DECLINE, e
    # tamper: a wrong Gram is rejected by the exact re-check
    good = S.sos_grade(x**2 - 2*x + 1)
    assert not S.verify_sos(x**2 - 1, good.result["gram"], good.result["basis"])
    # transforms flipped to VERIFIED with the backing kernel
    tids = {t.tid: t for t in catalog.TRANSFORMS}
    assert tids["B1.sos_positivstellensatz"].verified and tids["B1.sos_positivstellensatz"].kernel == "sos_positivstellensatz"
    assert tids["D2.sos_refutation"].verified
    print("PASS test_phaseB_sos_exact_tier (global SOS → EXACT rational-PSD-Gram cert [re-checks; tamper rejected]; "
          "x²-1/x³/xy/x⁴-x²/-x² → DECLINE; B1.sos + D2.sos_refutation transforms VERIFIED)")


def test_phaseB_rcf_qe():
    """PHASE B — RCF/CAD quantifier elimination (reuse mathmode.real_qe) via a gated catalog kernel: ∀x.x²+1>0 is
    True, ∀x.x²-1>0 is False — EXACT decisions, routed through kernel_router with a structured RCF query."""
    import kernel_router as KR
    import kernel_verdict as KV
    import catalog
    import sympy as sp
    x = sp.Symbol("x")
    v = KR.dispatch({"rcf": True, "quantifier": "forall", "formula": x**2 + 1 > 0, "x": x})
    assert v.status == KV.EXACT and v.result is True, v          # routed to the RCF kernel (delegates to real_qe)
    v2 = KR.dispatch({"rcf": True, "quantifier": "forall", "formula": x**2 - 1 > 0, "x": x})
    assert v2.status == KV.EXACT and v2.result is False, v2
    assert {t.tid: t for t in catalog.TRANSFORMS}["D1.rcf_cad_qe"].verified
    print("PASS test_phaseB_rcf_qe (∀x.x²+1>0 → EXACT True; ∀x.x²-1>0 → EXACT False; via gated kernel_router; "
          "D1.rcf_cad_qe VERIFIED)")


def test_phaseB_presburger_qe():
    """PHASE B — Presburger / linear integer arithmetic via direct z3 (trusted oracle): a valid ∀-formula → EXACT
    True (¬φ UNSAT), an invalid one → EXACT False with a counterexample model; garbage → DECLINE."""
    import kernel_router as KR
    import kernel_verdict as KV
    import catalog
    v = KR.dispatch({"presburger": True, "goal": "2*(x+y) == 2*x + 2*y", "int_vars": ["x", "y"]})
    assert v.status == KV.EXACT and v.result is True and v.kernel == "presburger_qe", v
    v2 = KR.dispatch({"presburger": True, "goal": "x + y == x", "int_vars": ["x", "y"]})
    assert v2.status == KV.EXACT and v2.result is False and "counterexample" in v2.certificate.detail.lower(), v2
    import presburger_qe as P
    assert P.presburger_decide("foo(bar", ["x"]).status == KV.DECLINE                  # negative control
    assert {t.tid: t for t in catalog.TRANSFORMS}["D1.presburger_qe"].verified
    print("PASS test_phaseB_presburger_qe (∀x,y. 2(x+y)=2x+2y → EXACT True; x+y=x → EXACT False+counterexample; "
          "garbage → DECLINE; D1.presburger_qe VERIFIED [z3 oracle])")


def test_phaseB_acf_honest_defer():
    """PHASE B — ACF (algebraically-closed-field QE / Chevalley) is HONESTLY DEFERRED (§1.6): no existing module,
    constructible-set projection beyond budget. Its transform stays UNVERIFIED with a precise reason — NOT faked."""
    import catalog
    t = {x.tid: x for x in catalog.TRANSFORMS}["D1.acf_qe"]
    assert not t.verified and t.status.startswith("UNVERIFIED") and t.kernel is None
    print("PASS test_phaseB_acf_honest_defer (D1.acf_qe HONEST_DEFER — UNVERIFIED, kernel=None, not faked)")


def test_phaseC_ordinal_termination():
    """PHASE C — ordinal-bounded termination (the fold decreases-clause): a lex measure mapping to a strictly
    DESCENDING ordinal sequence → EXACT termination (well-founded); a non-decreasing measure → DECLINE (no false
    termination claim). Backs D1.ordinal_termination + B2.ranking_termination, routed via kernel_router."""
    import kernel_router as KR
    import kernel_verdict as KV
    import catalog
    # strictly descending lex measures (e.g. Ackermann-like (m,n)): (3,0) > (2,5) > (2,4) > (1,9) → terminates
    v = KR.dispatch({"ordinal_termination": True, "measures": [(3, 0), (2, 5), (2, 4), (1, 9), (0, 0)]})
    assert v.status == KV.EXACT and v.result is True and v.kernel == "ordinal_termination", v
    # single step decrease (decreases-clause): (2,5) → (2,4) EXACT
    v2 = KR.dispatch({"ordinal_termination": True, "before": (2, 5), "after": (2, 4)})
    assert v2.status == KV.EXACT and v2.result is True, v2
    # ★ negative control: measure does NOT decrease (ascending / equal) → DECLINE (no false termination) ★
    import ordinal_cert as OC
    assert OC.descent_witness([(1, 0), (2, 0)]).status == KV.DECLINE      # ascending
    assert OC.descent_witness([(2, 2), (2, 2)]).status == KV.DECLINE      # equal
    tids = {t.tid: t for t in catalog.TRANSFORMS}
    assert tids["D1.ordinal_termination"].verified and tids["B2.ranking_termination"].verified
    print("PASS test_phaseC_ordinal_termination (strictly-descending lex measure → EXACT termination [well-founded]; "
          "ascending/equal → DECLINE [no false claim]; D1.ordinal_termination + B2.ranking_termination VERIFIED)")


def test_phaseC_arith_hierarchy_probe():
    """PHASE C — arithmetic-hierarchy routing probe (§5-first): a Σ⁰₁/Π⁰₁-complete semantic-program-property is
    placed undecidable → DECLINE; a bounded/decidable query → PROCEED; routed at the TOP of catalog.compose."""
    import arith_hierarchy as AH
    import catalog.compose as C
    import kernel_verdict as KV
    assert AH.classify("does f halt on all inputs?").route == "DECLINE"
    assert AH.classify("are these two programs semantically equivalent?").route == "DECLINE"
    assert AH.classify("decide this Presburger / linear arithmetic formula").route == "PROCEED"
    assert AH.classify("x**2 - 2*x + 1 sum of squares").route == "PROCEED"
    # compose places it FIRST: an undecidable query short-circuits to an obstruction DECLINE (mechanism 14)
    r = C.route("prove this arbitrary program always terminates on every input")
    assert r.grade == KV.DECLINE and r.mechanism_path == [14] and "hierarchy" in r.note, r
    print("PASS test_phaseC_arith_hierarchy_probe (Σ⁰₁/Π⁰₁ semantic-program-property → DECLINE; decidable → PROCEED; "
          "wired §5-first in compose — undecidable query short-circuits to obstruction [14])")


def test_phaseC_nbe_honest_defer():
    """PHASE C — NbE / cut-elimination as the evaluation core is HONESTLY DEFERRED (§1.6): haran_eval.Interp exists
    but a gated normalize() fold-core entry is beyond this PHASE's budget. The transforms stay UNVERIFIED, not faked."""
    import catalog
    tids = {t.tid: t for t in catalog.TRANSFORMS}
    for tid in ("D1.cut_elimination", "D2.nbe", "D2.hott_canonicity"):
        assert not tids[tid].verified and tids[tid].kernel is None, tid
    print("PASS test_phaseC_nbe_honest_defer (cut-elim/NbE/HoTT-canonicity eval-core HONEST_DEFER — UNVERIFIED, not faked)")


def test_phaseD_mdl_incompressibility():
    """PHASE D — MEASURED incompressibility (MDL 2-part code, mechanism 12/14): data with hidden structure
    COMPRESSES → EXACT code-length (proceed); incompressible data → DECLINE (per-instance, honest — NOT a
    Kolmogorov-randomness proof). This RECOVERS the 'fake Ω(N)' distinction: structured-looking data that
    compresses is kept, not declined. Backs D1.kolmogorov_incompressible."""
    import os
    import kernel_router as KR
    import kernel_verdict as KV
    import catalog
    import catalog.decline_boundary as DB
    # ★ negative control: genuinely-random bytes → incompressible → DECLINE ★
    rnd = os.urandom(1024)
    vr = KR.dispatch(rnd)
    assert vr.status == KV.DECLINE, vr
    assert DB.mdl_two_part(rnd)["compresses"] is False
    # structured data → EXACT code-length (a model beats the literal) — recovered, NOT declined
    vs = KR.dispatch(b"abcdabcd" * 200)
    assert vs.status == KV.EXACT and vs.result["compresses"] is True and vs.kernel == "mdl_incompressibility", vs
    # an arithmetic numeric sequence compresses (hidden structure) → EXACT
    assert KR.dispatch(list(range(1000))).status == KV.EXACT
    # the incompressibility GUARD: random declines, structured/code passes through (no over-decline)
    assert DB.incompressibility_guard(rnd).status == KV.DECLINE
    assert DB.incompressibility_guard(b"abcdabcd" * 200) is None
    assert DB.incompressibility_guard("def f(n):\n return sum(k*k for k in range(n))") is None
    assert {t.tid: t for t in catalog.TRANSFORMS}["D1.kolmogorov_incompressible"].verified
    print("PASS test_phaseD_mdl_incompressibility (random→DECLINE [ratio≥1]; repeated/range→EXACT code-length; "
          "guard: random declines, structured/code proceed — recovers 'fake Ω(N)'; D1.kolmogorov_incompressible VERIFIED)")


def test_phaseD_decline_backbone_complete():
    """PHASE D — the DECLINE backbone is complete: Rice + incompressibility + turbulence guards + the proven-
    boundary list. Negative controls: every guard DECLINEs on its boundary marker; ordinary structured code passes
    through every guard (no over-decline). A DECLINE is a POSITIVE absence-proof (a win, §6)."""
    import catalog.decline_boundary as DB
    import kernel_verdict as KV
    assert DB.rice_guard("does this program halt on every input?").status == KV.DECLINE
    assert DB.turbulence_guard("classify with no complete invariant — E0 / turbulence").status == KV.DECLINE
    assert len(DB.PROVEN_BOUNDARIES) >= 15 and len(DB.boundary_names()) == len(set(DB.boundary_names()))
    # ordinary foldable code trips NO guard (DB.check returns None)
    for ok in ("def f(n):\n s=0\n for k in range(n): s+=k\n return s",
               "sum(k*k for k in range(n))", "x**2 - 2*x + 1 sum of squares"):
        assert DB.check(ok) is None, ok
    # the boundary list names the un-recoverable proven boundaries (sanity of a few)
    names = set(DB.boundary_names())
    assert {"undecidable_halting_rice", "kolmogorov_random_string", "turbulence_closure",
            "mip_star_re", "ppad_hard_equilibrium"} <= names
    print(f"PASS test_phaseD_decline_backbone_complete (Rice/incompressibility/turbulence guards + "
          f"{len(DB.PROVEN_BOUNDARIES)} proven boundaries; every guard fires on its marker, ordinary code passes "
          f"all guards [no over-decline] — DECLINE = positive absence-proof)")


def test_phaseE_composition_router():
    """PHASE E — the §5 mechanism-composition router EXECUTES the built gated applies along the planned pipeline
    and returns (result, grade, certificate, bound, mechanism_path). Built: M4 (SOS), M12 (MDL), M13 (fold via the
    existing engine), M14 (DECLINE guards). Unbuilt mechanism paths return an HONEST DEFER naming the planned path
    — never a fake result. NO single-discipline 1:1 decomposition: routing is by mechanism composition."""
    import catalog.compose as C
    import os
    import kernel_verdict as KV
    # M13 existing fold
    r = C.route("def f(n):\n s=0\n for k in range(1,n+1): s+=k*k\n return s")
    assert r.grade == KV.EXACT and r.mechanism_path == [13]
    res, grade, cert, bound, path = r.as_tuple()                 # the §5.6 output tuple
    assert grade == KV.EXACT and cert is not None and path == [13]
    # M4 SOS (executed inline along [4,…])
    r = C.route("prove x**2 - 2*x + 1 >= 0 by sos")
    assert r.grade == KV.EXACT and r.mechanism_path == [4] and r.verdict.certificate.passed
    # M4 declines a non-SOS → composition [4,14] honest DECLINE (not a fake pass)
    r = C.route("is x**2 - 1 nonneg sos")
    assert r.grade == KV.DECLINE and r.mechanism_path == [4, 14]
    # M12 MDL: incompressible random → DECLINE[14]; structured data → EXACT[12]
    assert C.route(os.urandom(800)).grade == KV.DECLINE
    rs = C.route(b"abcd" * 200)
    assert rs.grade == KV.EXACT and rs.mechanism_path == [12]
    assert C.route(list(range(800))).grade == KV.EXACT
    # M14 obstruction (undecidable) and DECLINE backbone
    assert C.route("does this program halt on all inputs?").grade == KV.DECLINE
    # unbuilt composition → HONEST DEFER naming the planned path (e.g. classification 9→2, RS 10→14)
    r = C.route("classify the curvature complete invariant")
    assert r.grade == KV.DECLINE and r.mechanism_path == [9, 2] and "HONEST_DEFER" in r.verdict.reason
    r = C.route("is this graph minor-closed forbidden-minors")
    assert r.mechanism_path == [10, 14] and "HONEST_DEFER" in r.verdict.reason
    # every non-DECLINE result carries a passed certificate (no fake pass)
    for q in ("prove x**2+1 >= 0 sos", "def g(n):\n return sum(k for k in range(n))"):
        rr = C.route(q)
        if rr.grade != KV.DECLINE:
            assert rr.verdict.certificate and rr.verdict.certificate.passed
    print("PASS test_phaseE_composition_router (executes built applies along the pipeline: fold→EXACT[13], "
          "SOS→EXACT[4], SOS-fail→DECLINE[4,14], random→DECLINE[14], structured-data→EXACT[12], halt→DECLINE[14]; "
          "unbuilt paths [9→2], [10→14] → HONEST_DEFER naming the path; returns (result,grade,cert,bound,path) — no "
          "fake pass, no 1:1 discipline decomposition)")


def test_phaseF_domain_applies():
    """PHASE F — domain applies reusing mature [이미 있음] modules (reinforce+register, never reimplement):
    Buckingham-Π (M9, dimensionless-group normal form) and Noether energy conservation (M5, conserved Hamiltonian
    with dH/dt≡0). Both EXACT via gated kernels; backs 16.buckingham_pi + 16.noether."""
    import kernel_router as KR
    import kernel_verdict as KV
    import catalog
    import sympy as sp
    # Buckingham-Π: pendulum quantities → EXACT dimensionless group(s)
    q = {"period": {"T": 1}, "length": {"L": 1}, "gravity": {"L": 1, "T": -2}, "mass": {"M": 1}}
    v = KR.dispatch(q)
    assert v.status == KV.EXACT and v.certificate.passed, v        # routed to buckingham_pi (delegates to mathmode)
    # Noether energy conservation: L = ½m q̇² − ½q² → EXACT conserved H
    t = sp.Symbol("t"); qf = sp.Function("q"); m = sp.Symbol("m", positive=True)
    Lexpr = sp.Rational(1, 2) * m * qf(t).diff(t)**2 - qf(t)**2 / 2
    v2 = KR.dispatch({"noether": True, "L": Lexpr, "q": qf, "t": t})
    assert v2.status == KV.EXACT and v2.certificate.passed, v2
    tids = {tt.tid: tt for tt in catalog.TRANSFORMS}
    assert tids["16.buckingham_pi"].verified and tids["16.noether"].verified
    print("PASS test_phaseF_domain_applies (Buckingham-Π pendulum → EXACT Π-group; Noether L=½mq̇²−½q² → EXACT "
          "conserved H; 16.buckingham_pi + 16.noether VERIFIED [reuse mathmode.buckingham/lagrangian])")


def test_catalog_engine_report():
    """§C — the integrated catalog-engine report is HONEST: registered/verified/deferred accounting is consistent,
    every VERIFIED transform is backed by a VERIFIED router kernel, the framework is closed (14 mechanisms, no 15th),
    and false-positive = 0 (negative controls across the engine never produce a non-DECLINE)."""
    import catalog
    import mechanisms as M
    import kernel_router as KR
    import catalog.compose as C
    import kernel_verdict as KV
    import os
    cov = catalog.coverage()
    assert cov["registered"] == cov["verified"] + cov["deferred"] == 94
    assert cov["all_14_mechanisms_have_a_transform"] and M.closure_report()["framework_closed"]
    # every VERIFIED transform → a VERIFIED router kernel (no UNVERIFIED auto-select)
    vk = set(KR.registered(verified_only=True))
    assert all((t.kernel in vk) for t in catalog.TRANSFORMS if t.verified)
    # ★ FALSE-POSITIVE = 0: structureless / boundary inputs NEVER yield a non-DECLINE through the engine ★
    negatives = [os.urandom(600), "does f halt on every input?", "x**2 - 1 nonneg sos",
                 "is this program semantically equivalent", "totally unstructured glue text with no math"]
    for neg in negatives:
        assert C.route(neg).grade == KV.DECLINE, neg
    print(f"PASS test_catalog_engine_report (§C: {cov['registered']} registered / {cov['verified']} VERIFIED / "
          f"{cov['deferred']} deferred [consistent]; every VERIFIED transform backed by a VERIFIED kernel; framework "
          f"closed [14, no 15th]; false-positive = 0 on {len(negatives)} negative controls)")


def test_loop_cycle1_spectral_inertia():
    """§9 loop cycle 1 — mechanism 1 (diagonalize): Sylvester INERTIA (n₊,n₀,n₋), a complete congruence invariant of
    a symmetric rational matrix, EXACT via exact eigenvalue signs. Recovers 16.spectral_svd_pca (was deferred).
    Negative control: a non-symmetric matrix → DECLINE."""
    import sympy as sp
    import sos_cert as S
    import kernel_router as KR
    import kernel_verdict as KV
    import catalog
    # exact inertia incl. the zero-diagonal indefinite case [[0,1],[1,0]] → (1,0,1)
    assert S.inertia(sp.eye(3)) == (3, 0, 0)                          # PD
    assert S.inertia(sp.diag(1, 0, -2)) == (1, 1, 1)                  # indefinite, rank-deficient
    assert S.inertia(sp.Matrix([[0, 1], [1, 0]])) == (1, 0, 1)        # zero-diagonal indefinite
    assert S.inertia(sp.Matrix([[1, -1], [-1, 1]])) == (1, 1, 0)      # PSD rank-1
    # via the gated kernel: EXACT signature + definiteness
    v = KR.dispatch({"inertia": True, "matrix": sp.diag(2, 3)})
    assert v.status == KV.EXACT and v.result["inertia"] == (2, 0, 0) and v.result["definiteness"] == "positive-definite", v
    # ★ negative control: non-symmetric → DECLINE ★
    assert S.inertia_grade(sp.Matrix([[1, 2], [3, 4]])).status == KV.DECLINE
    assert {t.tid: t for t in catalog.TRANSFORMS}["16.spectral_svd_pca"].verified
    print("PASS test_loop_cycle1_spectral_inertia (§9: Sylvester inertia (n₊,n₀,n₋) EXACT — PD/indefinite/zero-"
          "diagonal/PSD; gated kernel gives signature+definiteness; non-symmetric → DECLINE; 16.spectral_svd_pca "
          "RECOVERED [deferred→VERIFIED])")


def test_loop_cycle2_petrov():
    """§9 loop cycle 2 — mechanism 9 (complete invariant): Petrov classification of the Weyl tensor (reuse
    mathmode.petrov). The 5 Weyl scalars → EXACT Petrov type (a complete invariant of the algebraic type). Recovers
    C1.petrov (deferred→VERIFIED)."""
    import kernel_router as KR
    import kernel_verdict as KV
    import catalog
    import mechanisms as M
    v = KR.dispatch({"petrov": True, "psi": [0, 0, 1, 0, 0]})         # only Ψ2 ≠ 0 → Type D
    assert v.status == KV.EXACT and v.result["type"] == "D", v
    vO = KR.dispatch({"petrov": True, "psi": [0, 0, 0, 0, 0]})        # vacuum-flat → Type O
    assert vO.status == KV.EXACT and vO.result["type"] == "O", vO
    # mechanism 9 apply routes the bare 5-scalar list too
    assert M.MECHANISMS[9].apply([0, 0, 1, 0, 0]).result["type"] == "D"
    assert {t.tid: t for t in catalog.TRANSFORMS}["C1.petrov"].verified
    print("PASS test_loop_cycle2_petrov (§9: Weyl scalars → EXACT Petrov type [D / O]; mechanism-9 apply routes the "
          "5-scalar list; C1.petrov RECOVERED [deferred→VERIFIED])")


ALL = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]


def main() -> int:
    passed = failed = 0
    for t in ALL:
        try:
            t()
            passed += 1
        except Exception:  # noqa: BLE001
            failed += 1
            print(f"FAIL {t.__name__}")
            traceback.print_exc()
    print(f"\n==== test_catalog: {passed} passed, {failed} failed (of {len(ALL)}) ====")
    return 1 if failed else 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
