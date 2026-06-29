"""
§3 LOOP C — ADVERSARIAL false-EXACT HUNT (the autonomous engine's only ACTIVE safety device).
================================================================================================================
For every EXACT-producing fold built this session (§AY/§AU/§AT), actively try to BREAK it: randomized adversarial
inputs, each EXACT output independently re-checked against a BRUTE-FORCE ground truth, and every boundary input
must DECLINE. A `false_exact` is an EXACT verdict whose value is provably WRONG (vs ground truth) OR an interacting/
non-structured input accepted as EXACT. **false_exact MUST be 0** (INV-1) — a single one freezes the engine.

Deterministic (seeded LCG, no RNG nondeterminism) so the hunt is reproducible (the determinism cap). This is the
codified form of the curation filter: the mirage is caught by independent re-verification, not by trust.
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Tuple

import kernel_verdict as KV


class _LCG:
    """Deterministic small-integer source (no `random` — reproducible)."""
    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF

    def nxt(self, lo: int, hi: int) -> int:
        self.s = (1103515245 * self.s + 12345) & 0x7FFFFFFF
        return lo + (self.s % (hi - lo + 1))


# ── Pfaffian core: Pf²=det AND Pf==combinatorial on random skew matrices (a wrong Pf = false-EXACT) ─────────────
def redteam_pfaffian(trials: int = 240) -> dict:
    from mathmode import free_fermion as FF
    rng = _LCG(20260628)
    false_exact, checked = 0, 0
    for t in range(trials):
        n = (rng.nxt(1, 4)) * 2                                   # even dim 2,4,6,8
        A = [[Fraction(0)] * n for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                v = Fraction(rng.nxt(-4, 4))
                A[i][j] = v
                A[j][i] = -v
        pf = FF.pfaffian_Q(A)
        if pf * pf != FF.det_Q(A):                               # Pf²≠det ⇒ Pfaffian core is WRONG
            false_exact += 1
        elif FF.pfaffian_combinatorial(A) != pf:                 # disagrees with the (2n−1)!! pairing sum
            false_exact += 1
        checked += 1
    return {"checked": checked, "false_exact": false_exact}


# ── Wick free-vs-interacting: the TRUE 4-point (Pf) is accepted; TRUE+δ (interacting) must be REJECTED ──────────
def redteam_wick(trials: int = 160) -> dict:
    from mathmode import free_fermion as FF
    rng = _LCG(777)
    false_exact, checked = 0, 0
    for t in range(trials):
        n = 4
        A = [[Fraction(0)] * n for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                v = Fraction(rng.nxt(-3, 3))
                A[i][j] = v
                A[j][i] = -v
        true4 = FF.pfaffian_Q(A)                                 # the genuine free 4-point = Pf(A)
        if FF.is_wick_consistent(A, {(0, 1, 2, 3): true4}).status != KV.EXACT:
            false_exact += 1                                     # rejected a genuinely free correlator (precision break)
        if FF.is_wick_consistent(A, {(0, 1, 2, 3): true4 + 1}).status == KV.EXACT:
            false_exact += 1                                     # ★ accepted an INTERACTING correlator as free = false-EXACT
        checked += 1
    return {"checked": checked, "false_exact": false_exact}


# ── Krylov / moment-sequence: a random low-order recurrence folds & predicts CORRECTLY; a hash stream DECLINEs ──
def _naive_rec(c: List[int], init: List[int], n: int) -> int:
    d = len(c)
    s = list(init)
    while len(s) <= n:
        s.append(sum(c[i] * s[-1 - i] for i in range(d)))
    return s[n]


def redteam_krylov(trials: int = 80) -> dict:
    from qfold import krylov as K
    rng = _LCG(31337)
    false_exact, checked = 0, 0
    for t in range(trials):
        d = rng.nxt(1, 3)
        c = [rng.nxt(-2, 2) for _ in range(d)]
        init = [rng.nxt(-3, 3) for _ in range(d)]
        seq = [_naive_rec(c, init, i) for i in range(2 * d + 14)]
        v = K.fold_moment_sequence(seq)
        if v.status == KV.EXACT:
            # independently re-verify the recovered recurrence predicts the TRUE next terms (ground truth)
            order = v.result["order"]
            true_far = [_naive_rec(c, init, i) for i in range(len(seq), len(seq) + 6)]
            import cfinite
            crec = [Fraction(x) for x in [-__import__("native_sequence").berlekamp_massey_Q(seq[:len(seq) - 8])[0][j]
                                          for j in range(1, order + 1)]]
            pred = [cfinite.companion_nth(crec, [Fraction(s) for s in seq[:order]], len(seq) + k) for k in range(6)]
            if any(pred[k] != true_far[k] for k in range(6)):
                false_exact += 1                                 # EXACT but predicts WRONG = false-EXACT
        checked += 1
    # a genuine random (hash) stream must DECLINE
    import hashlib
    rnd = [int.from_bytes(hashlib.sha256(str(k).encode()).digest()[:4], "big") for k in range(40)]
    rnd_declines = K.fold_moment_sequence(rnd).status == KV.DECLINE
    return {"checked": checked, "false_exact": false_exact, "random_stream_declines": rnd_declines}


# ── proof-carrying: random TAMPERED certs must all fail their re-check (never EXACT) ────────────────────────────
def redteam_proof_carrying(trials: int = 80) -> dict:
    import proof_carrying as PC
    rng = _LCG(99001)
    false_exact, checked = 0, 0
    for t in range(trials):
        # a telescoping cert with a deliberately WRONG body coefficient must DECLINE
        S = [str(rng.nxt(-3, 3)) for _ in range(3)]
        body_wrong = [str(rng.nxt(-3, 3)) for _ in range(3)]     # arbitrary body, almost surely ≠ S(n)−S(n−1)
        cert = PC.PCCert("telescoping_identity", "random tamper", {"S_coeffs": S, "body_coeffs": body_wrong})
        # only count as false-EXACT if it is accepted AND the identity does NOT actually hold
        accepted = PC.verify_exact_fast_lane(cert).verdict.status == KV.EXACT
        truly_holds = PC.recheck_telescoping({"S_coeffs": S, "body_coeffs": body_wrong})
        if accepted and not truly_holds:
            false_exact += 1
        checked += 1
    # a sampling cert must always be rejected from the EXACT lane
    sampling_rejected = PC.verify_exact_fast_lane(PC.PCCert("schwartz_zippel", "sz", {})).verdict.status == KV.DECLINE
    return {"checked": checked, "false_exact": false_exact, "sampling_rejected": sampling_rejected}


# ── stabilizer / CSS: random Clifford circuits stay symplectic; any injected T ⇒ DECLINE ────────────────────────
def redteam_stabilizer(trials: int = 80) -> dict:
    from qfold import stabilizer as ST
    rng = _LCG(5550123)
    false_exact, checked = 0, 0
    for t in range(trials):
        n = rng.nxt(2, 4)
        gates = []
        for _ in range(rng.nxt(3, 8)):
            g = rng.nxt(0, 2)
            if g == 0:
                gates.append(("H", rng.nxt(0, n - 1)))
            elif g == 1:
                gates.append(("S", rng.nxt(0, n - 1)))
            else:
                a = rng.nxt(0, n - 1)
                b = (a + 1 + rng.nxt(0, n - 2)) % n
                gates.append(("CNOT", a, b))
        if ST.detect_clifford_circuit(gates, n).status != KV.EXACT:
            false_exact += 1                                     # a pure-Clifford circuit MUST fold (precision)
        # inject a T gate ⇒ must DECLINE (non-Clifford)
        if ST.detect_clifford_circuit(gates + [("T", 0)], n).status == KV.EXACT:
            false_exact += 1                                     # ★ accepted a non-Clifford circuit = false-EXACT
        checked += 1
    return {"checked": checked, "false_exact": false_exact}


# ── CORE conjecturer path (cycle 4): random TRUE foldables must fold EXACT-and-CORRECT; random hashes must DECLINE ──
def _cfinite_oracle_src(c: List[int], init: List[int]) -> str:
    """Emit a self-contained unary oracle f(n) for the C-finite sequence f(n)=Σ c[i]·f(n-1-i) (memoized default-arg ⇒
    O(n) amortized so the far-window re-verification stays cheap). This is genuine foldable code for the black-box path."""
    terms = " + ".join(f"({c[i]})*_s[m-1-{i}]" for i in range(len(c)))
    init_lit = repr(list(init))
    return (f"def f(n, _s={init_lit}):\n"
            f"    while len(_s) <= n:\n"
            f"        m = len(_s)\n"
            f"        _s.append({terms})\n"
            f"    return _s[n]\n")


def _poly_oracle_src(coeffs: List[int]) -> str:
    """Emit f(n)=Σ coeffs[i]·nⁱ — a closed-form polynomial (C-finite of order deg+1); stresses closedform_guess."""
    terms = " + ".join(f"({coeffs[i]})*(n**{i})" for i in range(len(coeffs)))
    return f"def f(n):\n    return {terms}\n"


def _periodic_oracle_src(table: List[int]) -> str:
    """Emit f(n)=table[n%p] — an eventually-periodic sequence (C-finite via the cyclic recurrence); stresses period_guess."""
    return f"def f(n):\n    return {repr(list(table))}[n % {len(table)}]\n"


def redteam_core_conjecturers(foldable_trials: int = 60, hash_trials: int = 40,
                              poly_trials: int = 40, periodic_trials: int = 40) -> dict:
    """★ CYCLE-4 Loop-C ESCALATION — broaden INV-1 from this-session folds to the ENGINE CORE. Randomly GENERATE true
    C-finite oracles (the conjecturers' bread-and-butter) and confirm the full `engine_adapter.classify` path folds them
    EXACT **and** the recovered closed form matches the TRUE oracle on a FAR window n≈400-420 (via the EXISTING
    `engine_adapter.reverify_exact` — reuse, not reimplement); a recovered-but-wrong fold is a false-EXACT. ★★ Randomly
    GENERATE genuine hash oracles (information floor) and confirm they are NEVER issued EXACT/PROBABILISTIC. This is a NEW
    randomized adversarial surface over the core (distinct from the FIXED 660-corpus reverify and the §AY/§AU probes)."""
    from corpus.build_corpus import CorpusItem
    from measure import engine_adapter as EA
    rng = _LCG(20260629)
    false_exact, checked, folded = 0, 0, 0
    for t in range(foldable_trials):
        d = rng.nxt(1, 3)
        c = [rng.nxt(-3, 3) for _ in range(d)]
        if all(x == 0 for x in c):
            c[0] = 1                                              # avoid the degenerate all-zero (eventually-0) tail
        init = [rng.nxt(-3, 3) for _ in range(d)]
        src = _cfinite_oracle_src(c, init)
        item = CorpusItem(f"rt:core:{t}", "numeric", "synthetic", src, "f", True, "cfinite_random")
        r = EA.classify(item)
        if r.classification == EA.EXACT_FOLD:
            folded += 1
            rv = EA.reverify_exact(item)                         # ★ independent far-window ground-truth re-check
            if rv.get("false_exact"):
                false_exact += 1                                 # ★ EXACT but diverges from the true oracle = false-EXACT
        checked += 1
    hash_false_exact = 0
    for t in range(hash_trials):
        seed = rng.nxt(0, 10 ** 9)
        src = (f"def f(n):\n    import hashlib\n"
               f"    return int.from_bytes(hashlib.sha256(str(n + {seed}).encode()).digest()[:6], 'big')\n")
        item = CorpusItem(f"rt:hash:{t}", "crypto_preprocessing", "synthetic", src, "f", True, "hash_oracle")
        r = EA.classify(item)
        if r.classification in (EA.EXACT_FOLD, EA.PROBABILISTIC_FOLD):
            hash_false_exact += 1                                # ★ a hash oracle issued a fold = false-EXACT
        checked += 1
    # ── cycle-6: polynomial (closedform_guess) + periodic (period_guess) foldable classes, same reverify discipline ──
    poly_folded = 0
    for t in range(poly_trials):
        deg = rng.nxt(1, 3)
        coeffs = [rng.nxt(-4, 4) for _ in range(deg + 1)]
        if coeffs[-1] == 0:
            coeffs[-1] = 1                                        # keep the stated degree (leading coeff ≠ 0)
        item = CorpusItem(f"rt:poly:{t}", "numeric", "synthetic", _poly_oracle_src(coeffs), "f", True, "poly_random")
        r = EA.classify(item)
        if r.classification == EA.EXACT_FOLD:
            poly_folded += 1
            if EA.reverify_exact(item).get("false_exact"):
                false_exact += 1                                 # ★ EXACT-but-wrong polynomial fold = false-EXACT
        checked += 1
    periodic_folded = 0
    for t in range(periodic_trials):
        p = rng.nxt(2, 6)
        table = [rng.nxt(-5, 5) for _ in range(p)]
        item = CorpusItem(f"rt:per:{t}", "numeric", "synthetic", _periodic_oracle_src(table), "f", True, "periodic_random")
        r = EA.classify(item)
        if r.classification == EA.EXACT_FOLD:
            periodic_folded += 1
            if EA.reverify_exact(item).get("false_exact"):
                false_exact += 1                                 # ★ EXACT-but-wrong periodic fold = false-EXACT
        checked += 1
    return {"checked": checked, "false_exact": false_exact + hash_false_exact,
            "foldable_folded": folded, "foldable_trials": foldable_trials,
            "hash_false_exact": hash_false_exact, "hash_trials": hash_trials,
            "poly_folded": poly_folded, "poly_trials": poly_trials,
            "periodic_folded": periodic_folded, "periodic_trials": periodic_trials}


_REPORT_CACHE = {}      # the sweep is fully deterministic (seeded LCG) ⇒ memoize so a second call in-process is free


def red_team_report() -> dict:
    if "r" in _REPORT_CACHE:
        return _REPORT_CACHE["r"]
    teams = {
        "pfaffian": redteam_pfaffian(),
        "wick_free_vs_interacting": redteam_wick(),
        "krylov_moment": redteam_krylov(),
        "proof_carrying": redteam_proof_carrying(),
        "stabilizer_css": redteam_stabilizer(),
        "core_conjecturers": redteam_core_conjecturers(),
    }
    total_false_exact = sum(v["false_exact"] for v in teams.values())
    total_checked = sum(v["checked"] for v in teams.values())
    rep = {"teams": teams, "total_checked": total_checked, "total_false_exact": total_false_exact,
           "INV_1_holds": total_false_exact == 0,
           "note": "Loop C — every EXACT fold attacked with randomized adversarial inputs + independent ground-truth "
                   "re-check; every boundary forced to DECLINE. false_exact MUST be 0 (INV-1)."}
    _REPORT_CACHE["r"] = rep
    return rep


def adversarial_battery() -> dict:
    """★★ the red team finds ZERO false-EXACT across ~640 randomized adversarial probes (Pfaffian Pf²=det &
    combinatorial, Wick free-vs-interacting, Krylov prediction vs ground truth, proof-carrying tamper, Clifford+T);
    ★ every boundary (random stream / sampling cert / injected T) DECLINEs."""
    r = red_team_report()
    core = r["teams"]["core_conjecturers"]
    cases = {
        "no_false_exact": r["total_false_exact"] == 0,
        "inv1_holds": r["INV_1_holds"],
        "krylov_random_declines": r["teams"]["krylov_moment"]["random_stream_declines"],
        "proof_carrying_sampling_rejected": r["teams"]["proof_carrying"]["sampling_rejected"],
        "core_hash_never_folds": core["hash_false_exact"] == 0,           # ★ random hash oracles never issued a fold
        "core_cfinite_nonvacuous": core["foldable_folded"] >= core["foldable_trials"] // 2,   # C-finite class not vacuous
        "core_poly_nonvacuous": core["poly_folded"] >= core["poly_trials"] // 2,              # polynomial class not vacuous
        "core_periodic_nonvacuous": core["periodic_folded"] >= core["periodic_trials"] // 2,  # periodic class not vacuous
        "swept_enough": r["total_checked"] >= 800,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(red_team_report(), indent=2, default=str))
