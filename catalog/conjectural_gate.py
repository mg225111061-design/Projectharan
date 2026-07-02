"""
CONSOLIDATION PHASE 4 — the conjectural-cluster HARD-GATE.
===========================================================
The third closure test found distinct-but-INADMISSIBLE candidates whose certificate depends on an OPEN CONJECTURE
or is UNCOMPUTABLE. This static gate REJECTS any fold path whose soundness rests on one of them — the engine can
never emit a conjectural certificate as if it were proven — while PERMITTING the constructive ISLANDS (the
computable sub-parts). A rejected claim DECLINEs with an explicit conjectural-dependency reason; it is NEVER EXACT.

  REJECT (certificate would depend on an open conjecture or an uncomputable core):
    Hodge conjecture · homological mirror symmetry · Grothendieck standard conjectures/motives · Iwasawa main
    conjecture (general) · BSD rank statements · general circuit lower bounds (natural-proofs barrier) · Wang-tile
    tiling (domino problem, undecidable) · general group word problem (Novikov–Boone) · higher K-theory (general).
  PERMIT (constructive islands — computable, certificate sound):
    Hodge DECOMPOSITION (harmonic forms) · étale/Betti cohomology of an EXPLICIT variety · low-degree K-theory ·
    p-adic L-function VALUES · hyperbolic/free word problem via Dehn / free reduction.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import kernel_verdict as KV

CONJECTURAL: Dict[str, str] = {
    "hodge_conjecture": "Hodge classes are algebraic — OPEN (only the Lefschetz (1,1) / p=1 case is known)",
    "homological_mirror_symmetry": "HMS is proven only case-by-case — OPEN in general",
    "standard_conjectures": "Grothendieck standard conjectures / unconditional mixed motives — OPEN",
    "iwasawa_main_general": "the Iwasawa main conjecture in general — OPEN (proven only in cases)",
    "bsd": "Birch–Swinnerton-Dyer: rank = analytic rank — CONJECTURAL (never emit 'rank = analytic rank')",
}
UNCOMPUTABLE: Dict[str, str] = {
    "circuit_lower_bound_general": "general circuit lower bounds — the natural-proofs barrier (Razborov–Rudich)",
    "wang_tile_tiling": "the domino problem (does this tile set tile the plane?) is UNDECIDABLE (Berger)",
    "group_word_problem_general": "the general group word problem is UNDECIDABLE (Novikov–Boone)",
    "higher_k_theory_general": "higher algebraic K-theory in general — Kummer–Vandiver-equivalent / not known computable",
}
CONSTRUCTIVE_ISLANDS: Dict[str, str] = {
    "hodge_decomposition": "the harmonic-form (p,q) Hodge DECOMPOSITION — constructive (Hodge theory ≠ the conjecture)",
    "etale_explicit_variety": "étale / Betti cohomology of an EXPLICIT variety — computable",
    "low_degree_k_theory": "K₀, K₁ of an explicit ring — computable",
    "padic_L_value": "a p-adic L-function VALUE at a point — computable (≠ the main conjecture)",
    "hyperbolic_word_problem": "the hyperbolic / free-group word problem via Dehn / free reduction — DECIDABLE",
}


def classify(dependency: str) -> str:
    if dependency in CONJECTURAL:
        return "conjectural"
    if dependency in UNCOMPUTABLE:
        return "uncomputable"
    if dependency in CONSTRUCTIVE_ISLANDS:
        return "constructive_island"
    return "unknown"


def gate(claim: dict) -> KV.Verdict:
    """The hard-gate. claim = {name, depends_on}. REJECT (DECLINE) iff the certificate depends on a conjecture or an
    uncomputable core — never emitted EXACT. PERMIT (the island is sound) iff it is a constructive island."""
    if not (isinstance(claim, dict) and "depends_on" in claim):
        return KV.decline("conjectural_gate: need {name, depends_on}", "conjectural_gate")
    dep = claim["depends_on"]
    kind = classify(dep)
    if kind == "conjectural":
        return KV.decline(f"conjectural-dependency: '{claim.get('name', dep)}' rests on {CONJECTURAL[dep]} ⇒ REJECT "
                          "(never emit a conjectural certificate as EXACT)", "conjectural_gate")
    if kind == "uncomputable":
        return KV.decline(f"uncomputable-core: '{claim.get('name', dep)}' — {UNCOMPUTABLE[dep]} ⇒ REJECT", "conjectural_gate")
    if kind == "constructive_island":
        cert = KV.Cert(KV.EXACT, "constructive_island", passed=True, check_cost="the island is computable",
                       detail=f"PERMIT: {CONSTRUCTIVE_ISLANDS[dep]} — only the constructive sub-part; the conjectural "
                              "extension remains REJECTED")
        return KV.exact({"permitted": True, "island": dep, "note": CONSTRUCTIVE_ISLANDS[dep]},
                        "conjectural_gate", "constructive island (permitted)", cert)
    return KV.decline(f"conjectural_gate: unknown dependency '{dep}' — not on the permitted-island list ⇒ REJECT "
                      "(fail-safe: only listed islands are admitted)", "conjectural_gate")


# ── a real constructive-island computation: the hyperbolic / free-group word problem (Dehn / free reduction) ──
def free_reduce(word: str) -> str:
    """Free reduction: cancel adjacent inverse pairs (lowercase x ↔ uppercase X). Solves the FREE-group word
    problem (the canonical hyperbolic decidable island; Dehn's algorithm generalizes it to small-cancellation groups)."""
    out: List[str] = []
    for c in word:
        if out and out[-1] == c.swapcase():
            out.pop()
        else:
            out.append(c)
    return "".join(out)


def dehn_reduce(word: str, relators: List[str]) -> str:
    """Dehn's algorithm (decidable island for C'(1/6) hyperbolic groups): free-reduce, then repeatedly replace any
    subword u that is MORE than half of a cyclic conjugate of a relator r=u·v with v⁻¹ (strictly shorter). Returns
    the reduced word; the empty string means the input represents the identity."""
    def inv(w):
        return w.swapcase()[::-1]
    pieces = []
    for r in relators:
        cyc = [r[i:] + r[:i] for i in range(len(r))] + [inv(r)[i:] + inv(r)[:i] for i in range(len(r))]
        for c in cyc:
            half = len(c) // 2
            for L in range(half + 1, len(c) + 1):              # u longer than half (incl. the whole relator r=1)
                pieces.append((c[:L], inv(c[L:])))
    w = free_reduce(word)
    changed = True
    while changed:
        changed = False
        w = free_reduce(w)
        for u, vrepl in pieces:
            idx = w.find(u)
            if idx >= 0 and len(vrepl) < len(u):
                w = w[:idx] + vrepl + w[idx + len(u):]
                changed = True
                break
    return free_reduce(w)


def word_problem_island(word: str, relators: Optional[List[str]] = None) -> KV.Verdict:
    """The PERMITTED island: decide whether `word` = identity via free reduction / Dehn's algorithm (hyperbolic /
    free groups). EXACT — a DECIDABLE island. (The GENERAL word problem is the rejected uncomputable core.)"""
    reduced = dehn_reduce(word, relators or [])
    is_identity = reduced == ""
    cert = KV.Cert(KV.EXACT, "word_problem_dehn", passed=True,
                   check_cost="Dehn's algorithm / free reduction (decidable for free / hyperbolic groups)",
                   detail=f"'{word}' reduces to '{reduced or 'ε'}' ⇒ {'= identity' if is_identity else '≠ identity'} "
                          "(the constructive island; the general word problem is the rejected uncomputable core)")
    return KV.exact({"word": word, "reduced": reduced, "is_identity": is_identity},
                    "conjectural_gate.word_problem", "word problem (hyperbolic island)", cert)


def betti_projective_space(n: int) -> List[int]:
    """A constructive étale/Betti island: the Betti numbers of ℂℙⁿ are 1,0,1,0,…,1 (computable — not a conjecture)."""
    return [1 if (k % 2 == 0 and k <= 2 * n) else 0 for k in range(2 * n + 1)]
