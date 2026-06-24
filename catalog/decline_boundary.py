"""
CATALOG ENGINE — the DECLINE backbone (Constitution §6, mechanism 14).
======================================================================
Proven refusal boundaries. An input hitting one gets an immediate HONEST DECLINE = a POSITIVE absence-proof (a
win, §2). Checked BEFORE the catalog engine (§5 cheapest probe). Three guards + a proven-boundary list.

PHASE A: conservative keyword guards (fire only on explicit boundary markers — a DECLINE is always safe, never a
false positive in the §7.5 sense, which is claiming STRUCTURE where there is none). PHASE D replaces the heuristics
with real tests (Kolmogorov 2-part code / index-set analysis / E₀ reduction).
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

import kernel_verdict as KV
from mechanisms.base import feats

# §6 proven boundaries (un-recoverable — NOT the "fake Ω(N)" subset the engine targets). (name, mechanism, why).
PROVEN_BOUNDARIES: List[Tuple[str, int, str]] = [
    ("kolmogorov_random_string", 14, "incompressible: no model beats the literal (Kolmogorov/ML-random)"),
    ("undecidable_halting_rice", 14, "non-trivial semantic property of programs is undecidable (Rice/Turing)"),
    ("statistical_computational_gap", 14, "OGP / planted-clique: info-theoretically present, computationally hard"),
    ("computational_irreversibility", 14, "one-way: forward easy, inverse hard (no per-instance witness)"),
    ("galois_liouville_impossibility", 14, "insolvable by radicals / non-elementary integral (impossibility proof)"),
    ("volume_law_entanglement", 14, "volume-law state is incompressible (area-law is the recoverable case)"),
    ("turbulence_closure", 14, "no finite closure for the moment hierarchy"),
    ("cryptographic_pseudorandom", 14, "indistinguishable from random under a hardness assumption"),
    ("mip_star_re", 14, "entangled-prover verification = halting-hard (MIP*=RE)"),
    ("natural_relativization_algebrization", 14, "lower-bound technique blocked by a meta-barrier"),
    ("mrdp_diophantine", 14, "Diophantine solvability is undecidable (MRDP / Hilbert's 10th)"),
    ("chaos_beyond_lyapunov", 14, "prediction impossible past the Lyapunov time"),
    ("ppad_hard_equilibrium", 14, "equilibrium exists (non-constructive) but is PPAD-hard to find"),
    ("ch_independence", 14, "independent of ZFC (Continuum Hypothesis class)"),
    ("ordinal_analysis_limit", 14, "consistency strength beyond current ordinal analysis (past Π¹₂-CA)"),
]

_RICE_RE = re.compile(
    r"\b(halt|halting problem|rice'?s? theorem|undecidable|for (all|every) (program|input)s?|"
    r"semantic(ally)? (equivalent|property)|index set|always (return|terminate|halt))\b", re.IGNORECASE)
_INCOMP_RE = re.compile(r"\b(kolmogorov[- ]?random|incompressible|maximally random|truly random|white noise)\b", re.IGNORECASE)
_TURB_RE = re.compile(r"\b(turbulence|turbulent closure|complete invariant.*(absent|none|impossible)|"
                      r"e0 reducib|glimm[- ]?effros|not (smoothly )?classifiable)\b", re.IGNORECASE)


def _decline(name: str, why: str) -> KV.Verdict:
    return KV.decline(f"OBSTRUCTION[{name}]: {why} (mechanism 14 — DECLINE-as-win, §6)", kernel="decline_boundary")


def rice_guard(x) -> Optional[KV.Verdict]:
    """A request for a non-trivial SEMANTIC property of programs is undecidable (Rice) → DECLINE."""
    if _RICE_RE.search(feats(x).text):
        return _decline("undecidable_halting_rice", "non-trivial semantic property of programs is undecidable")
    return None


def incompressibility_guard(x) -> Optional[KV.Verdict]:
    """Explicitly-random / incompressible input → DECLINE (PHASE D: real Kolmogorov 2-part code test)."""
    if _INCOMP_RE.search(feats(x).text):
        return _decline("kolmogorov_random_string", "declared incompressible/random — no model beats the literal")
    return None


def turbulence_guard(x) -> Optional[KV.Verdict]:
    """A classification problem with no complete invariant (E₀/turbulence) → classification DECLINE."""
    if _TURB_RE.search(feats(x).text):
        return _decline("turbulence_closure", "no complete invariant (E₀/turbulence) — classification impossible")
    return None


_GUARDS = (rice_guard, incompressibility_guard, turbulence_guard)


def check(x) -> Optional[KV.Verdict]:
    """Run the DECLINE guards (cheapest first). First hit → an honest obstruction DECLINE; else None (proceed)."""
    for g in _GUARDS:
        v = g(x)
        if v is not None:
            return v
    return None


def boundary_names() -> List[str]:
    return [b[0] for b in PROVEN_BOUNDARIES]
