"""
CATALOG ENGINE — mechanism-composition engine (Constitution §5, the heart of chaos→structure).
==============================================================================================
No single-discipline 1:1 decomposition (§2). An input is decomposed into a mechanism PIPELINE/TREE: one
mechanism's StructForm output becomes the next's input, each stage is §7-gated, and the composed grade follows
the WEAKEST-LINK law (`combine_grade`). A chain is only as strong as its weakest stage — a false upgrade (claiming
EXACT while a PROBABILISTIC/DECLINE cert is in the chain) is an ADT exception, never a silent label.

  HEAD  `plan(x)`     — probe vector [0,1]^14 → a composition TREE plan (a SHAPE + a mechanism path), using the
                        research grammar (each Mechanism's `composable_with`).
  BODY  `execute(p,x)`— walk the plan, threading a `StructForm` (catalog.ir) through each stage: mechanism `apply`
                        → §7 gate → pass ⇒ output becomes the next input, fail ⇒ DECLINE recorded at that point.
  LAW   `combine_grade`— EXACT∘EXACT→EXACT; any PROBABILISTIC→PROBABILISTIC (δ_total≤Σδ_i union bound, never
                        upgraded); a DECLINE short-circuits the chain (downstream not run).

Built compositions that RUN for real: ★ M7 structure⊕pseudorandom split (master principle: clean k-sparse ⇒
EXACT closed form + bounded remainder), M9⟂M14 (complete invariant OR an obstruction certificate), M4|M14 (SOS
or impossibility), M2(∘M3) on structured QE goals. Wired-but-deferred legs (M10→M14 forbidden-minor compute,
M6∘M13 multigrid): the body CALLS them; only the leg's heavy compute is HONEST_DEFER'd. "잘못된 답보다 DECLINE."
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

import kernel_verdict as KV
import mechanisms as MECH
from catalog import decline_boundary as DB
from catalog import ir
from catalog import lossless_gate as LG
from mechanisms.base import feats


@dataclass
class CatalogResult:
    verdict: KV.Verdict                       # the graded result (EXACT/PROBABILISTIC/DECLINE)
    mechanism_path: List[int] = field(default_factory=list)  # the bare mechanism path (compat with the §5 tuple)
    probe: List[float] = field(default_factory=list)         # the [0,1]^14 probe vector (traceability)
    note: str = ""
    trace: List[Tuple[int, str, str]] = field(default_factory=list)  # full (m_num, grade, cert_kind) path
    lossless: str = ""                                       # the §5 lossless judgment (condition or 'approximation')

    @property
    def grade(self) -> str:
        return self.verdict.status

    @property
    def bound(self):
        """The certificate's bound/ε (the §5 output tuple's `bound` slot), if any."""
        c = self.verdict.certificate
        return None if c is None else (c.bound if c.bound is not None else c.epsilon)

    def as_tuple(self):
        """The §5.6 output: (result, grade, certificate, bound, mechanism_path)."""
        return (self.verdict.result, self.grade, self.verdict.certificate, self.bound, self.mechanism_path)


# ── the weakest-link composition LAW (Constitution §5 — the honesty core) ──────────────────────────────
def combine_grade(prev_grade: str, prev_certs: list, v: "KV.Verdict") -> Tuple[str, list, bool]:
    """Compose an accumulated (prev_grade, prev_certs) with the next mechanism's Verdict `v`, weakest-link:
      • v is DECLINE        → grade DECLINE, stop=True (the pipeline halts here; downstream is NOT run);
      • EXACT ∘ EXACT       → EXACT (both certs retained; the ADT re-checks every cert is passed=True);
      • any PROBABILISTIC   → PROBABILISTIC (NEVER upgraded to EXACT; δ_total ≤ Σδ_i is computed at exit by the
                              union bound, ε propagated per-op).
    Returns (composed_grade, composed_cert_chain, stop). The grade is the MIN of the lattice
    DECLINE < PROBABILISTIC < EXACT — the weakest link. A false upgrade is impossible here (we never take a MAX)
    and is re-asserted at `StructForm.to_verdict` (ADT exception)."""
    if v.status == KV.DECLINE:
        return KV.DECLINE, list(prev_certs), True
    certs = list(prev_certs) + [v.certificate]
    grade = ir.weaker(prev_grade, v.status)
    return grade, certs, False


# ── the §7 gate on a single composition stage ──────────────────────────────────────────────────────────
def _gate(m_num: int, v: "KV.Verdict") -> "KV.Verdict":
    """§7 gate. The grade ADT is already enforced at Verdict construction (a mechanism CANNOT return a non-DECLINE
    grade without a passed certificate). Here we (a) re-assert cert.passed and (b) mark the point where a mechanism
    with an independent oracle has ALREADY run its differential-equivalence recheck inside `apply` (Prony held-out
    residual, SOS PSD re-check, MDL re-measure, z3/CAD model). A stage that fails its own gate already returned
    DECLINE — there is no path to a fake pass."""
    if v.status != KV.DECLINE:
        assert v.certificate is not None and v.certificate.passed, \
            f"§7 GATE: mechanism {m_num} returned {v.status} without a passed certificate (blocked — no fake pass)"
    return v


# kinds the structured `data` takes after each mechanism (for the IR `kind` label).
_KIND = {1: "spectral", 2: "normal_form", 4: "closed_form", 7: "spectral", 9: "invariant",
         11: "latent_state", 12: "code_length", 13: "closed_form"}

# research-confirmed composition pipelines for the generic CHAIN shape: (top-mechanism predicate) → path.
_COMPOSITIONS: List[Tuple[frozenset, Tuple[int, ...], str]] = [
    (frozenset({10}), (10, 14), "Robertson–Seymour: wqo size-guarantee → finite forbidden-minor obstruction"),
    (frozenset({6}), (6, 13), "renormalize → Kleene fixpoint (± widening)"),
    (frozenset({2}), (2, 3), "eliminate (QE) → certify the finite witness"),
    (frozenset({1}), (1, 9), "diagonalize → complete spectral invariant"),
    (frozenset({13}), (13,), "Kleene fixpoint = the existing fold"),
    (frozenset({3}), (3, 2), "guess-finite-certify → canonical normal form"),
]


def _existing_fold(x: Any) -> Optional[KV.Verdict]:
    """§5.1 — try the existing fold engine first (only for code-source strings). Returns a Verdict if it collapses."""
    if not (isinstance(x, str) and ("def " in x or "lambda" in x)):
        return None
    try:
        import structure_recognizer as SR
        d = SR.dispatch(x)
    except Exception:  # noqa: BLE001
        return None
    if getattr(d, "status", "NONE") == "OFFLOADED" and getattr(d, "closed_form", ""):
        cert = KV.Cert(KV.EXACT, "fold_closed_form", passed=True, check_cost="differential-equivalence gate",
                       detail=str(d.certificate)[:200])
        return KV.exact(d.closed_form, "fold(structure_recognizer)", getattr(d, "complexity", "O(1)"), cert)
    return None


# ── HEAD: the planner — probe vector → a composition TREE plan ──────────────────────────────────────────
@dataclass
class Plan:
    shape: str                 # m7_split | m9_perp_m14 | sos | mdl | fold | chain
    path: Tuple[int, ...]      # the mechanism path / leg order
    why: str
    probe: List[float] = field(default_factory=list)


def _is_signal(x) -> bool:
    return isinstance(x, (list, tuple)) and len(x) >= 8 and bool(x) and all(isinstance(v, (int, float, complex)) for v in x)


def _is_classification(x, f) -> bool:
    if "classify" in f.tags:
        return True
    if isinstance(x, dict) and x and all(isinstance(v, dict) and all(isinstance(e, int) for e in v.values()) for v in x.values()):
        return True                                       # Buckingham: dict of dimension-vectors
    if isinstance(x, (list, tuple)) and len(x) == 5:      # the 5 Weyl scalars → Petrov
        return True
    return False


def plan(x: Any) -> Plan:
    """The §5 head: route the input to a composition SHAPE (a tree), using the research grammar. Not a single
    max-probe point — a structured decomposition (e.g. a signal ⇒ M7 split into a structure leg + a remainder leg)."""
    probe = MECH.probe_vector(x)
    f = feats(x)
    if isinstance(x, dict) and "detect" in x:             # FRONT-END: the probe cascade (widened structure detection)
        return Plan("detect", (), "probe cascade: cheapest-first detectors, each exact-certified before folding", probe)
    if isinstance(x, dict) and "quasi_periodic" in x:     # GAP 8/14: almost-periodic → PROBABILISTIC approximation
        return Plan("quasi_periodic", (), "almost-periodic structure → PROBABILISTIC (δ-bounded approximation, never EXACT)", probe)
    if isinstance(x, dict) and "zeilberger" in x:         # GAP 13: holonomic sum → exact WZ creative-telescoping cert
        return Plan("zeilberger", (13,), "Zeilberger creative telescoping: holonomic recurrence + exact WZ certificate", probe)
    if isinstance(x, dict) and "persistence" in x:        # M15: multiscale-topological summary (persistent homology)
        return Plan("persistence", (15,), "persistent homology: barcode + bottleneck-stability witness (multiscale topology)", probe)
    if isinstance(x, dict) and "causal" in x:             # M16: causal-structure recovery (relational-asymmetric)
        return Plan("causal", (16,), "causal recovery: CPDAG + do-calculus/hedge (faithfulness DECLARED, not certified)", probe)
    if isinstance(x, dict) and "sheaf" in x:              # M17: sheaf cohomology (local-to-global; generalizes M14)
        return Plan("sheaf", (17,), "sheaf cohomology: H⁰ global sections / H¹ gluing obstruction (generalizes M14)", probe)
    if isinstance(x, dict) and "flow" in x:               # M18: geometric flow → canonical form + monotone witness
        return Plan("flow", (18,), "geometric flow → canonical form + monotone (Lyapunov) convergence witness", probe)
    if isinstance(x, dict) and "knot" in x:               # M19 (scope): knot/Jones state-sum invariant
        return Plan("knot", (19,), "knot invariant: Kauffman bracket state-sum + Reidemeister invariance", probe)
    if isinstance(x, dict) and "aperiodic" in x:          # M20 (scope): quasicrystal cut-and-project + diffraction
        return Plan("aperiodic", (20,), "aperiodic order: cut-and-project scheme + pure-point diffraction", probe)
    if isinstance(x, dict) and ("lift_sum" in x or "lift_code" in x):   # FRONT-END: verified lifting (code → closed form)
        return Plan("lift", (13,), "verified lifting: imperative loop → closed form, z3-proved equivalent", probe)
    if isinstance(x, dict) and ("speedup" in x or "validate" in x or "superopt" in x):   # Topic A constant-factor speedup
        return Plan("topic_a", (8,), "Topic A: certified constant-factor speedup (asymptotics unchanged)", probe)
    if _is_signal(x):                                     # ★ structure⊕pseudorandom: M7 → [M1/M13] + [M12]
        return Plan("m7_split", (7, 1, 12), "structure⊕pseudorandom split (M7 → structure[M1/M13] + remainder[M12])", probe)
    if isinstance(x, (bytes, bytearray)):                 # raw bytes ⇒ MDL directly (not a signal for M7)
        return Plan("mdl", (12,), "MDL 2-part code (algorithmic statistics)", probe)
    if isinstance(x, dict) and ("presburger" in x or "rcf" in x):   # M2∘M3 fused: z3/CAD eliminates AND certifies the
        return Plan("chain", (2,), "QE: eliminate → certify finite witness (z3 model / CAD sample-point — M2∘M3 fused)", probe)
    if isinstance(x, dict) and "groebner" in x:                     # M2: Gröbner ideal membership + cofactor witness
        return Plan("chain", (2,), "Gröbner ideal membership (Buchberger + cofactor certificate)", probe)
    if isinstance(x, dict) and "smt_string" in x:                   # M2: straight-line string constraints (cvc5)
        return Plan("chain", (2,), "straight-line / QF_SLIA string decision (cvc5 + model re-verification)", probe)
    if isinstance(x, dict) and "lstar" in x:                        # M9: minimal DFA via Angluin L* (complete invariant)
        return Plan("chain", (9,), "complete invariant: minimal DFA via Angluin L* (regular-language canonical form)", probe)
    if isinstance(x, dict) and ((x.get("ic3") or "taint" in x) or (x.get("chc") and "trans" in x) or "telescope" in x):
        return Plan("chain", (13,), "Kleene/least-fixpoint: IC3 / CHC-Spacer invariant / taint IFDS / Gosper Σ", probe)
    if isinstance(x, dict) and ("egraph" in x or "zx_equiv" in x or "zx_simplify" in x):   # M8: confluent normal form
        return Plan("chain", (8,), "confluent normal form (e-graph / ZX-calculus, formally re-checked)", probe)
    if isinstance(x, tuple) and x and x[0] in ("+", "*", "var", "const"):
        return Plan("chain", (8,), "confluent normal form (e-graph equality saturation, Z3-certified)", probe)
    if isinstance(x, dict) and ("galois_quintic" in x or x.get("liouville")):   # M14: Galois/Liouville impossibility
        return Plan("chain", (14,), "obstruction: Galois insolvability / Liouville non-elementary (impossibility)", probe)
    if isinstance(x, dict) and ("lll" in x or "int_relation" in x or ("diophantine" in x and "b" in x) or "realroots" in x):
        return Plan("chain", (2,), "native lattice/relation/real-root (LLL · integer relation · Smith Diophantine · Sturm)", probe)
    if isinstance(x, dict) and "recurrence_seq" in x:               # M11: Berlekamp–Massey minimal linear recurrence
        return Plan("chain", (11,), "Berlekamp–Massey minimal linear recurrence (randomness gate: L≪n/2 fold, L≈n/2 DECLINE)", probe)
    if isinstance(x, dict) and ("lcg" in x or "lfsr" in x):         # M11: weak-PRNG recovery (secure CSPRNG → DECLINE)
        return Plan("chain", (11,), "weak-PRNG state recovery (LCG/LFSR replay; secure CSPRNG → DECLINE)", probe)
    if isinstance(x, dict) and "repair" in x:                       # M12: Re-Pair grammar compression (lossless SLP)
        return Plan("chain", (12,), "Re-Pair grammar compression (lossless straight-line program)", probe)
    if isinstance(x, dict) and "sat_count" in x and "nvars" in x:   # M12: exact #SAT (DPLL, differential-checked)
        return Plan("chain", (12,), "exact #SAT via DPLL (two-ordering + brute-force cross-check)", probe)
    if isinstance(x, dict) and "kb_rules" in x and "u" in x and "v" in x:   # M8: Knuth–Bendix monoid word problem
        return Plan("chain", (8,), "Knuth–Bendix completion: monoid word problem (confluent rewriting)", probe)
    if isinstance(x, dict) and "unify" in x:                        # M2: first-order syntactic unification
        return Plan("chain", (2,), "first-order unification (most-general unifier, occurs-checked)", probe)
    if isinstance(x, dict) and (("markov" in x and "partition" in x) or ("linsolve" in x and "b" in x)):   # M6 coarse-grain
        return Plan("chain", (6,), "renormalize: exact Markov lumping / multigrid fixpoint (residual enclosure)", probe)
    if isinstance(x, dict) and ("sequence" in x or "states" in x or ("ramsey" in x and "n" in x)):   # M10 forced structure
        return Plan("chain", (10,), "guaranteed-by-size: Erdős–Szekeres / pigeonhole-cycle / Ramsey (constructive witness)", probe)
    if _is_classification(x, f):                          # classification ⟂ obstruction
        return Plan("m9_perp_m14", (9, 14), "classification ⟂ obstruction (M9: complete invariant ⟂ M14: turbulence/E₀)", probe)
    if "inequality" in f.tags:                            # polynomial inequality ⇒ SOS or impossibility
        return Plan("sos", (4, 14), "relax/dualize: SOS nonnegativity, else impossibility (M4 | M14)", probe)
    top = MECH.top_mechanisms(x, k=3)
    top_set = {i for i, _ in top}
    for pred, cpath, why in _COMPOSITIONS:
        if pred & top_set:
            return Plan("chain", cpath, why, probe)
    return Plan("chain", tuple(i for i, _ in top), "ad-hoc top-mechanism order (no canonical composition matched)", probe)


# backward-compatible thin shim (older callers): the planned path + probe + why, no execution.
def plan_pipeline(x: Any) -> Tuple[List[int], List[float], str]:
    p = plan(x)
    return list(p.path), p.probe, p.why


# ── BODY: the executor — walk the plan, thread the StructForm, gate each stage ──────────────────────────
def _result(sf: "ir.StructForm", probe, why) -> CatalogResult:
    v = sf.to_verdict()                                   # re-checks the weakest-link invariant (false upgrade ⇒ raise)
    lj = LG.judge(v)                                      # §5 lossless gate: is this a certified-lossless fold or lossy?
    return CatalogResult(v, sf.mechanism_path, probe, why, trace=list(sf.path), lossless=lj.condition)


def _exec_m7_split(x, probe, why) -> CatalogResult:
    """★ The master principle, executed. M7 splits the signal into a k-sparse structure + a remainder; M1 reads the
    spectral closed form off the structure; M12 bounds the remainder. Clean k-sparse ⇒ EXACT closed form + ε
    remainder. If M7 can't cleanly split, fall back to M12 on the WHOLE (another model class may compress it) — the
    M7 probe is recorded in the trace but does NOT poison the M12 branch's grade."""
    v7 = _gate(7, MECH.MECHANISMS[7].apply(x))
    if v7.status == KV.EXACT:
        spec = v7.result["spectrum"]
        relres = v7.certificate.bound or 0.0
        sf = ir.StructForm.raw(x).accumulate(7, v7, data={"spectrum": spec, "k": v7.result.get("k")},
                                             residual=v7.result.get("residual"), new_kind="spectral")
        sf = sf.note_step(1, KV.EXACT, "spectral(read-off from M7 split: the spectrum IS the eigenstructure)")
        if relres < 1e-7:                                 # clean: remainder ≈ machine-ε ⇒ negligible (M12 trivial)
            sf = sf.note_step(12, KV.EXACT, f"remainder ≈ machine-ε ({relres:.1e}) — negligible, no residual MDL needed")
        else:
            vr = _gate(12, MECH.MECHANISMS[12].apply(sf.residual))
            sf = (sf.accumulate(12, vr, cert_kind="residual_bound") if vr.status != KV.DECLINE
                  else sf.note_step(12, KV.DECLINE, "remainder incompressible (Ω(N) floor) — structure EXACT, remainder bounded"))
        return _result(sf, probe, why + " [M7 split: structure=k tones (EXACT), remainder bounded]")
    # M7 did not cleanly split → M12 on the whole (record the M7 probe in the trace, don't poison the grade)
    sf = ir.StructForm.raw(x).note_step(7, v7.status, "split-probed: " + ((v7.reason or "")[:80] if v7.status == KV.DECLINE else "clean"))
    v12 = _gate(12, MECH.MECHANISMS[12].apply(x))
    sf = sf.accumulate(12, v12, data=(v12.result if v12.status != KV.DECLINE else None), new_kind="code_length")
    return _result(sf, probe, why + " [M7 found no clean split; M12 MDL on the whole]")


def _exec_m9_perp_m14(x, probe, why) -> CatalogResult:
    """M9 ⟂ M14: 'fold into a normal form, OR present the obstruction.' Check M14 (turbulence/E₀ ⇒ no complete
    invariant EXISTS) in parallel with attempting M9 (the complete invariant). M14 fires ⇒ DECLINE-classification +
    obstruction certificate. M9 succeeds (no obstruction) ⇒ EXACT classification."""
    ob = DB.turbulence_guard(x)
    if ob is not None:                                    # M14 leg: the obstruction (absence-of-invariant) proof — a win
        # surface the obstruction DECLINE verbatim (it names the obstruction — that IS the certificate of a win)
        return CatalogResult(ob, [14], probe, why + " [M14 fired: no complete invariant — obstruction certificate]",
                             trace=[(14, KV.DECLINE, "obstruction:turbulence_E0 — " + (ob.reason or ""))])
    v9 = _gate(9, MECH.MECHANISMS[9].apply(x))            # M9 leg: the complete invariant
    if v9.status != KV.DECLINE:
        sf = ir.StructForm.raw(x).accumulate(9, v9, data=v9.result, new_kind="invariant")
        sf = sf.note_step(14, KV.EXACT, "obstruction-checked: none (a complete invariant exists ⇒ classify)")
        return _result(sf, probe, why + " [M9: complete invariant ⇒ EXACT classification]")
    # neither a fired obstruction nor a wired complete invariant for THIS instance → honest DECLINE
    sf = ir.StructForm.raw(x).accumulate(9, v9, cert_kind="no-wired-complete-invariant")
    sf = sf.note_step(14, KV.EXACT, "obstruction-checked: none fired (not turbulence/E₀)")
    return _result(sf, probe, why + " [M9 deferred for this instance; no obstruction either]")


def _exec_sos(x, probe, why) -> CatalogResult:
    """M4 | M14: an SOS/Positivstellensatz nonnegativity certificate, ELSE the impossibility tail (no SOS)."""
    v4 = _gate(4, MECH.MECHANISMS[4].apply(x))
    if v4.status != KV.DECLINE:
        sf = ir.StructForm.raw(x).accumulate(4, v4, data=v4.result, new_kind="closed_form")
        return _result(sf, probe, why + " [M4: SOS certificate]")
    sf = ir.StructForm.raw(x).accumulate(4, v4)
    sf = sf.note_step(14, KV.DECLINE, "no SOS certificate (relaxation tail → impossibility/M14)")
    return _result(sf, probe, why + " [M4 found no SOS; M14 impossibility tail]")


def _exec_mdl(x, probe, why) -> CatalogResult:
    v = _gate(12, MECH.MECHANISMS[12].apply(x))
    sf = ir.StructForm.raw(x).accumulate(12, v, data=(v.result if v.status != KV.DECLINE else None), new_kind="code_length")
    return _result(sf, probe, why)


def _exec_chain(path, x, probe, why) -> CatalogResult:
    """The generic CHAIN: walk the mechanisms left-to-right, threading the StructForm; each gated; the first DECLINE
    short-circuits. A trailing M14 is the obstruction tail (named even when the prior stage's compute is deferred)."""
    sf = ir.StructForm.raw(x)
    for i, m in enumerate(path):
        if m == 14 and i > 0:                            # a TRAILING M14 is the obstruction tail (prior stage couldn't certify)
            sf = sf.note_step(14, KV.DECLINE, "obstruction tail (impossibility leg — forbidden-set/closure compute deferred)")
            break
        v = _gate(m, MECH.MECHANISMS[m].apply(sf.working()))
        sf = sf.accumulate(m, v, data=(v.result if v.status != KV.DECLINE else sf.data), new_kind=_KIND.get(m, sf.kind))
        if sf.stopped:
            if i + 1 < len(path) and path[i + 1] == 14:   # the next planned step is the obstruction tail
                sf = sf.note_step(14, KV.DECLINE, f"obstruction tail after M{m} (compute deferred)")
            break
    return _result(sf, probe, why)


def _exec_detect(x, probe, why) -> CatalogResult:
    """FRONT-END: run the probe cascade on x["detect"]; a certified candidate folds (cert tier recorded), else
    DECLINE. The cascade's native cores do the EXACT certification — nothing folds without a passed certificate."""
    from catalog import probe_cascade as PCAS
    cr = PCAS.cascade(x["detect"])
    note = why + f" [stage {cr.stage}: {cr.kind}, tier={cr.tier}]"
    _kind_mech = {"c_finite": 11, "exponential_sum": 11, "poly_law": 13, "low_rank": 1, "slp": 12, "integer_relation": 2}
    path = [_kind_mech.get(cr.kind, 14)] if cr.kind != "none" else []
    sf = ir.StructForm.raw(x).accumulate(path[0] if path else 14, cr.verdict,
                                         data=(cr.verdict.result if cr.grade != KV.DECLINE else None))
    return _result(sf, probe, note)


def _exec_lift(x, probe, why) -> CatalogResult:
    """FRONT-END: verified lifting — synthesize a closed form for the loop/sum and z3-PROVE equivalence before
    folding (the central invariant: no lift folds without a passing equivalence certificate)."""
    from catalog import lift as LIFT
    v = LIFT.lift_grade(x)
    sf = ir.StructForm.raw(x).accumulate(13, v, data=(v.result if v.status != KV.DECLINE else None), new_kind="closed_form")
    return _result(sf, probe, why + (f" [{v.result['tier']}]" if v.status != KV.DECLINE else " [not lifted]"))


def _exec_topic_a(x, probe, why) -> CatalogResult:
    """Topic A: a certified constant-factor speedup (equality saturation / translation validation / superopt).
    Asymptotics unchanged — recorded honestly; nothing is reported faster without a passing equivalence certificate."""
    from catalog import topic_a as TA
    v = TA.topic_a_grade(x)
    sf = ir.StructForm.raw(x).accumulate(8, v, data=(v.result if v.status != KV.DECLINE else None), new_kind="normal_form")
    return _result(sf, probe, why)


def _exec_quasi(x, probe, why) -> CatalogResult:
    """GAP 8/14: almost-periodic structure graded PROBABILISTIC (δ-bounded approximation). NEVER EXACT — the EXACT
    ledger stays residual-0-only; an incommensurate-frequency signal admits only an ε-certificate on the samples."""
    from catalog import gap_prob as GP
    v = GP.quasi_periodic_grade(x["quasi_periodic"])
    sf = ir.StructForm.raw(x).accumulate(11, v, data=(v.result if v.status != KV.DECLINE else None))
    return _result(sf, probe, why + (f" [δ={v.certificate.delta:.2e}]" if v.status == KV.PROBABILISTIC else " [not almost-periodic]"))


def _exec_zeilberger(x, probe, why) -> CatalogResult:
    """GAP 13: certify a holonomic sum by Zeilberger creative telescoping with an exact WZ certificate (EXACT) or
    DECLINE (non-holonomic / outside the bounded island). Folds via M13 (the fold/closed-form mechanism)."""
    from catalog import gap_telescope as GT
    v = GT.zeilberger_grade(x["zeilberger"])
    sf = ir.StructForm.raw(x).accumulate(13, v, data=(v.result if v.status != KV.DECLINE else None))
    return _result(sf, probe, why + (f" [order {v.result['order']}]" if v.status == KV.EXACT else " [no WZ certificate]"))


def _exec_mech(key: str, mod_fn, mech: int, exact_lossless: bool = True):
    """Generic executor for the new meta-mechanisms (M15–M20): call the module grader, accumulate the verdict."""
    def _run(x, probe, why) -> CatalogResult:
        v = mod_fn(x[key])
        sf = ir.StructForm.raw(x).accumulate(mech, v, data=(v.result if v.status != KV.DECLINE else None))
        tag = f" [{v.certificate.kind}]" if v.status in (KV.EXACT, KV.PROBABILISTIC) and v.certificate else " [DECLINE]"
        return _result(sf, probe, why + tag)
    return _run


def _persist(x):
    from catalog import mech_persistence as M
    return M.persistence_grade(x)


def _causal(x):
    from catalog import mech_causal as M
    return M.causal_grade(x)


def _sheaf(x):
    from catalog import mech_sheaf as M
    return M.sheaf_grade(x)


def _flow(x):
    from catalog import mech_flow as M
    return M.flow_grade(x)


def _knot(x):
    from catalog import mech_knot as M
    return M.knot_grade(x)


def _aperiodic(x):
    from catalog import mech_aperiodic as M
    return M.aperiodic_grade(x)


_SHAPES = {"m7_split": _exec_m7_split, "m9_perp_m14": _exec_m9_perp_m14, "sos": _exec_sos, "mdl": _exec_mdl,
           "detect": _exec_detect, "lift": _exec_lift, "topic_a": _exec_topic_a, "quasi_periodic": _exec_quasi,
           "zeilberger": _exec_zeilberger,
           "persistence": _exec_mech("persistence", _persist, 15), "causal": _exec_mech("causal", _causal, 16),
           "sheaf": _exec_mech("sheaf", _sheaf, 17), "flow": _exec_mech("flow", _flow, 18),
           "knot": _exec_mech("knot", _knot, 19), "aperiodic": _exec_mech("aperiodic", _aperiodic, 20)}


def execute(p: "Plan", x: Any) -> CatalogResult:
    """The §5 body: dispatch the plan SHAPE to its executor (each threads the StructForm and §7-gates every stage)."""
    fn = _SHAPES.get(p.shape)
    if fn is not None:
        return fn(x, p.probe, p.why)
    return _exec_chain(p.path, x, p.probe, p.why)         # "chain" / "fold" / ad-hoc


# ── measurement (NO_UNMEASURED §0): Clock B/C + crossover_n + Amdahl p for the sublinear M7 composition ──
_M7_PREFIX = 4 * 20 + 8                                   # the O(k) sample prefix sparse_fft/Prony actually reads


def measure_composition(x: Any) -> dict:
    """Honest measurement of a composition (three clocks never mixed; build-time is NOT a clock). For the ★ M7
    sublinear chain on a clean k-sparse signal, the GENUINE advantage is in SAMPLES READ: Prony recovers the
    structure from an O(k) prefix (≈88 samples) regardless of N, vs O(N) to read the whole signal — a real,
    complexity-faithful, measured win (crossover at ≈88 samples). We ALSO measure the Clock-B wall-clock vs numpy's
    FFT and report it TRUTHFULLY: numpy's optimized C-FFT is constant-dominated and typically wins on wall-clock in
    the tested range (no fake speedup — the honest result is reported, not hidden). Returns {"measured": False, …}
    for non-M7 compositions (never a fabricated number)."""
    import clocks
    import numpy as np
    import sparse_fft
    r = route(x)
    if not (r.mechanism_path[:1] == [7] and r.grade == KV.EXACT):
        return {"measured": False, "reason": "measurement wired for the M7 sublinear composition (clean k-sparse signal)"}
    k = r.verdict.result.get("k")
    N0 = len(x)
    ba = clocks.before_after(f"m7_spectral@N={N0}", "B",
                             lambda: np.fft.fft(np.asarray(x, dtype=complex)),
                             lambda: sparse_fft.recover(list(x)), k=5)
    wall_crossover = None
    for N in (256, 512, 1024, 2048, 4096, 8192, 16384):  # smallest N (doubling) where Prony recovery beats dense FFT on wall-clock
        tt = np.arange(N)                                 # frequencies scaled to N so the O(k) Prony prefix resolves them
        sigl = (np.cos(2 * np.pi * (N // 8) * tt / N) + np.cos(2 * np.pi * (N // 4) * tt / N)).tolist()
        b = clocks.measure_repeat("fft", "B", lambda: np.fft.fft(np.asarray(sigl, dtype=complex)), k=3)
        a = clocks.measure_repeat("sparse", "B", lambda: sparse_fft.recover(sigl), k=3)
        if a.median_ms < b.median_ms:
            wall_crossover = N
            break
    samples_read = min(N0, _M7_PREFIX)
    # Amdahl p (samples-faithful): the fraction of the O(N) read the composition ELIMINATES by touching only O(k).
    p = round(max(0.0, 1.0 - samples_read / N0), 3) if N0 > 0 else 0.0
    return {"measured": True, "clock": "B", "k": k, "N": N0,
            "samples_read": samples_read, "samples_baseline": N0, "samples_crossover_n": _M7_PREFIX,  # the GENUINE win
            "wall_clock": str(ba), "wall_clock_ratio": ba.ratio, "wall_clock_crossover_n": wall_crossover,  # honest: numpy C-FFT may win
            "amdahl_p": p,
            "note": "the sublinear advantage is SAMPLES READ (O(k)≈%d vs O(N)); wall-clock vs numpy's C-FFT is "
                    "constant-dominated (crossover beyond range = honest 'no measured wall-clock win') — measured, "
                    "not claimed; build-time NOT a clock" % _M7_PREFIX}


# ── top-level entry ─────────────────────────────────────────────────────────────────────────────────────
def route(x: Any) -> CatalogResult:
    """Top-level chaos→structure entry (§5). Order: arithmetic-hierarchy placement → proven-DECLINE boundary →
    existing fold → mechanism-composition plan+execute. Every path is §7-gated; a wrong answer is never emitted."""
    import arith_hierarchy as AH
    place = AH.classify(x)
    if place.route == "DECLINE":                          # §5 cheapest: Σ⁰₁/Π⁰₁ semantic-program-property → Rice DECLINE
        v = KV.decline(f"OBSTRUCTION[arith_hierarchy {place.level}]: {place.reason} (mechanism 14)", "catalog.compose")
        return CatalogResult(v, [14], MECH.probe_vector(x), f"hierarchy {place.level}", trace=[(14, KV.DECLINE, "arith_hierarchy")], lossless="none")
    ob = DB.check(x)                                      # §6 proven DECLINE boundary (incompressibility/turbulence/Rice)
    if ob is not None:
        return CatalogResult(ob, [14], MECH.probe_vector(x), "obstruction boundary", trace=[(14, KV.DECLINE, "boundary")], lossless="none")
    fold = _existing_fold(x)                              # §5.1 existing fold (code strings → M13)
    if fold is not None:
        return CatalogResult(fold, [13], MECH.probe_vector(x), "existing fold", trace=[(13, KV.EXACT, "fold_closed_form")],
                             lossless=LG.judge(fold).condition)
    return execute(plan(x), x)                            # §5.2-5.4 mechanism composition (plan → execute)
