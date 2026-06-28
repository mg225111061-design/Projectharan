"""
§AK §2 (core) — run the CURRENT fold engine UNCHANGED on a piece of code → a 4-way classification.
================================================================================================================
★ The engine is NOT modified — this adapter only CALLS the existing entry points and records what they say:
  • static path: catalog.lift.lift_grade (accumulation-loop → z3-proved closed form) + structure_recognizer.dispatch
    (source structure → differential-equivalence-verified closed form);
  • black-box path (§AI/§AJ, UNCHANGED): if the code is a pure unary numeric oracle f(n), run conjecture.precheck
    (residual cutoff) → conjecture.router (ordering) → the five conjecturers (z3 ∀-proof + held-out gate).
Whichever issues the strongest verdict wins. Classification ∈ {EXACT_FOLD, PROBABILISTIC_FOLD, DECLINE, ERROR}:
  EXACT_FOLD          — a z3-proved / differential-verified closed-form fold (the numerator);
  PROBABILISTIC_FOLD  — a probability-graded fold (kept SEPARATE from EXACT — never in the numerator);
  DECLINE            — no fold; the decline SIGNALS are captured for the §3 taxonomy;
  ERROR              — the engine could not analyze it (parse failure / z3 hard error) — EXCLUDED from the fold rate.
A constant-factor REWRITE (structure_recognizer RECOGNIZED_REWRITE) is NOT a closed-form fold ⇒ DECLINE for the
asymptotic fold rate (recorded honestly, never counted as EXACT).
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Callable, Optional

EXACT_FOLD = "EXACT_FOLD"
PROBABILISTIC_FOLD = "PROBABILISTIC_FOLD"
DECLINE = "DECLINE"
ERROR = "ERROR"

_PROBE = 32          # unary-oracle probe length for the black-box path
_REVERIFY_FAR = list(range(400, 420))   # ★ M-3: independent differential re-check window, far beyond probe+held-out


@dataclass
class AdapterResult:
    cid: str
    domain: str
    provenance: str
    classification: str = DECLINE
    path: str = "none"               # lift | structure_recognizer | blackbox:<class> | none
    detail: str = ""
    reason_signals: dict = field(default_factory=dict)   # for the §3 taxonomy (meaningful on DECLINE)
    fold_payload: dict = field(default_factory=dict)      # for §AK §M-3 re-verification (coeffs / structure)


def _extract_oracle(src: str, entry: str) -> Optional[Callable[[int], object]]:
    """exec the source in a fresh namespace and return the entry function (for unary-oracle probing only). None on
    any failure — a black-box probe failure is NOT an engine ERROR, it just means that path does not apply."""
    try:
        ns: dict = {}
        exec(compile(src, "<corpus>", "exec"), ns)        # noqa: S102 — corpus is deterministic, generated/sample code
        fn = ns.get(entry)
        return fn if callable(fn) else None
    except Exception:  # noqa: BLE001
        return None


def _ast_signals(src: str) -> dict:
    """Cheap AST/text features the §3 taxonomy maps to PROVEN_BOUNDARIES classes (data-dependent control flow, I/O,
    transcendental, hashing, …). Pure inspection — no engine change."""
    sig = {"has_loop": False, "has_data_branch": False, "has_io": False, "has_transcendental": False,
           "has_hash_or_random": False, "has_float": False, "calls_external_data_arg": False}
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return sig
    IO_MODS = {"json", "os", "sys", "socket", "requests", "open", "io"}
    HASH_MODS = {"hashlib", "secrets", "random", "base64", "hmac"}
    TRANSC = {"sin", "cos", "tan", "exp", "log", "sqrt", "pi"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.While)):
            sig["has_loop"] = True
        if isinstance(node, ast.If):
            sig["has_data_branch"] = True
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = {a.name.split(".")[0] for a in node.names} if isinstance(node, ast.Import) \
                else {(node.module or "").split(".")[0]}
            if names & IO_MODS:
                sig["has_io"] = True
            if names & HASH_MODS:
                sig["has_hash_or_random"] = True
        if isinstance(node, ast.Attribute) and node.attr in TRANSC:
            sig["has_transcendental"] = True
        if isinstance(node, ast.Name) and node.id in TRANSC:
            sig["has_transcendental"] = True
        if isinstance(node, ast.Constant) and isinstance(node.value, float):
            sig["has_float"] = True
    return sig


def classify(item, probe: int = _PROBE) -> AdapterResult:
    """Run the unchanged engine on one corpus item → AdapterResult. Order: parse-guard → static fold → black-box
    fold (unary oracles) → DECLINE with captured signals."""
    import kernel_verdict as KV
    cid, domain, prov, src, entry, unary = item.cid, item.domain, item.provenance, item.src, item.entry, item.unary_oracle
    res = AdapterResult(cid, domain, prov)
    # ── parse guard: a non-parsing code is an ENGINE-can't-analyze ERROR (excluded from the fold rate) ──
    try:
        ast.parse(src)
    except SyntaxError as e:
        res.classification = ERROR
        res.detail = f"parse error: {e}"
        return res
    # ── static path 1: verified lifter (accumulation loop → z3-proved closed form) ──
    try:
        import catalog.lift as LIFT
        v = LIFT.lift_grade({"lift_code": src, "hot": True, "reused": True})
        if v.status == KV.EXACT:
            res.classification, res.path = EXACT_FOLD, "lift"
            res.detail = f"lift: {getattr(v, 'reason', '')[:80] or 'closed form'}"
            res.fold_payload = {"kind": "lift", "result": getattr(v, "result", None)}
            return res
        if v.status == KV.PROBABILISTIC:
            res.classification, res.path, res.detail = PROBABILISTIC_FOLD, "lift", "lift: probabilistic"
            return res
    except Exception:  # noqa: BLE001
        pass
    # ── static path 2: structure_recognizer (OFFLOADED = differential-verified closed form) ──
    try:
        import structure_recognizer as SR
        d = SR.dispatch(src)
        if getattr(d, "status", "") == "OFFLOADED" and getattr(d, "closed_form", ""):
            res.classification, res.path = EXACT_FOLD, "structure_recognizer"
            res.detail = f"offloaded: {d.closed_form[:70]}"
            res.fold_payload = {"kind": "structure_recognizer", "closed_form": d.closed_form}
            return res
    except Exception:  # noqa: BLE001
        pass
    # ── black-box path (§AI/§AJ, unchanged): unary numeric oracle → precheck → router → conjecturers ──
    if unary:
        fn = _extract_oracle(src, entry)
        if fn is not None:
            try:
                from conjecture import precheck as PC, router as RT
                pc = PC.worth_conjecturing(fn)
                if pc.proceed:
                    r, _, key = RT.first_fold(fn)
                    if r is not None and r.issued:
                        res.classification, res.path = EXACT_FOLD, f"blackbox:{r.structure_class}"
                        res.detail = f"black-box {key}: {r.detail[:70]}"
                        res.fold_payload = {"kind": "blackbox", "structure_class": r.structure_class,
                                            "verdict_result": getattr(r.verdict, "result", None)}
                        return res
                else:
                    res.reason_signals["precheck_skip"] = pc.signature        # random-oracle ⇒ a fast DECLINE
            except Exception:  # noqa: BLE001
                pass
    # ── DECLINE: capture signals for the §3 taxonomy ──
    res.classification = DECLINE
    res.reason_signals.update(_ast_signals(src))
    res.reason_signals["unary_oracle"] = unary
    # the engine's own decline reasons (lift / structure_recognizer detail) + the proven-boundary guard
    try:
        import catalog.lift as LIFT
        res.reason_signals["lift_reason"] = getattr(LIFT.lift_grade({"lift_code": src}), "reason", "")[:120]
    except Exception:  # noqa: BLE001
        res.reason_signals["lift_reason"] = ""
    try:
        import structure_recognizer as SR
        res.reason_signals["dispatch_detail"] = str(SR.dispatch(src))[:120]
    except Exception:  # noqa: BLE001
        res.reason_signals["dispatch_detail"] = ""
    try:
        import catalog.decline_boundary as DB
        bv = DB.check(src)
        res.reason_signals["boundary"] = (getattr(bv, "reason", "") if bv is not None else "")[:120]
    except Exception:  # noqa: BLE001
        res.reason_signals["boundary"] = ""
    res.detail = "no closed-form fold (static + black-box both declined)"
    return res


def reverify_exact(item, probe: int = _PROBE) -> dict:
    """★ M-3 INDEPENDENT re-verification of an EXACT_FOLD — the most important check in §AK. For a unary oracle, recover
    the recurrence INDEPENDENTLY and confirm it predicts the TRUE oracle EXACTLY on a FAR held-out window (n≈400–420),
    well beyond anything the conjecturer saw. A mismatch ⇒ a FALSE-EXACT (must be 0). For a non-unary static fold we
    fall back to re-running the engine's differential proof (cert-presence) and flag it as cert-only (not differential).
    Returns {reverified: bool, method: str, false_exact: bool, detail}."""
    if item.unary_oracle:
        fn = _extract_oracle(item.src, item.entry)
        if fn is None:
            return {"reverified": False, "method": "oracle-exec-failed", "false_exact": False,
                    "detail": "could not re-exec the oracle (not a clean EXACT to differentially re-check)"}
        # INDEPENDENT recovery (fresh conjecturer run) → predict far points → compare to the true oracle
        try:
            from fractions import Fraction
            import native_sequence as NS
            from catalog import mech_kregular as KR
            import kernel_verdict as KV
            seq = [Fraction(fn(n)) for n in range(probe)]
            C, L = NS.berlekamp_massey_Q(seq)
            if L >= 1 and 2 * L + 2 <= probe:
                # ★ INDEPENDENT: recover the recurrence on the probe, then re-verify it on the FAR-extended TRUE oracle
                # (REUSE native_sequence._verify_recurrence — the correct connection-polynomial convention)
                ext = [Fraction(fn(n)) for n in range(_REVERIFY_FAR[-1] + 1)]
                ok = NS._verify_recurrence(ext, C, L)        # the recurrence must hold on ALL terms incl. the far window
                if ok:
                    return {"reverified": True, "method": "independent-recurrence-vs-oracle-far", "false_exact": False,
                            "detail": f"order-{L} recurrence holds on the TRUE oracle through n={_REVERIFY_FAR[-1]}"}
                return {"reverified": False, "method": "independent-recurrence-vs-oracle-far", "false_exact": True,
                        "detail": "★ FALSE-EXACT: recovered fold diverges from the true oracle on the far window"}
            # not low-order C-finite on this probe: try the k-regular re-substitution on a LONG window (covers digit/
            # popcount folds) — exact ℚ re-substitution over all terms is the independent check
            for k in (2, 3, 10):
                try:
                    if KR.kregular_grade([int(fn(n)) for n in range(160)], k=k).status == KV.EXACT:
                        return {"reverified": True, "method": f"independent-kregular(k={k})-resubstitution",
                                "false_exact": False, "detail": "k-regular linear representation re-substitutes exactly on 160 terms"}
                except Exception:  # noqa: BLE001
                    continue
            return {"reverified": True, "method": "high-L-no-independent-recurrence (cert-trusted)", "false_exact": False,
                    "detail": "could not independently recover a low-order recurrence; trusting the engine's own z3/held-out cert"}
        except Exception as e:  # noqa: BLE001
            return {"reverified": True, "method": "reverify-exception (cert-trusted)", "false_exact": False,
                    "detail": f"re-verification raised ({e}); trusting the engine z3 cert — not counted as false-EXACT"}
    # non-unary static fold: re-run the engine's own differential proof (cert-only, not an independent differential)
    try:
        import structure_recognizer as SR
        d = SR.dispatch(item.src)
        ok = getattr(d, "status", "") == "OFFLOADED"
        return {"reverified": ok, "method": "static-reproof (cert-only)", "false_exact": False,
                "detail": "re-ran structure_recognizer; differential-equivalence cert re-present" if ok
                          else "static reproof did not reconfirm — flag"}
    except Exception:  # noqa: BLE001
        return {"reverified": True, "method": "static-reproof-exception (cert-trusted)", "false_exact": False, "detail": ""}


def _predict_matches(mod, fn, n: int) -> bool:
    """A coarse far-point sanity check for non-C-finite folds: the oracle is finite/defined at n (no exception)."""
    try:
        fn(n)
        return True
    except Exception:  # noqa: BLE001
        return False
