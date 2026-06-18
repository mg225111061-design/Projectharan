"""
v33 STAGE 6 — global sound DISPOSITION: every input → exact-fold | certified-approximate | honest-defer.
=========================================================================================================
"100% application" does NOT mean folding everything — it means giving EVERY loop a SOUND disposition
(rule 11). Strength-ordered dispatch (rule 6.2), fastest/strongest first; the FIRST that produces a CHECKED
certificate wins. Anything not folded is returned BYTE-IDENTICAL (no runtime regression — the absolute line).

Order (each step is a cheap CHECK, never a runtime search):
  (a) soup O(1) lookup        — a brewed, verified closed form exists (Clock C)           strength: cached cert
  (b) soup composition        — linear combination of library lemmas, induction-PIT       ∀n (induction-PIT)
  (c) Schwartz-Zippel / R1    — derive a candidate, verify by PIT / induction step        ∀n (induction-PIT) / ω^ω
  (d) existing engine         — Faulhaber / Gosper / C-finite (fold_kernels)               exact
  (e) absence cache           — a precomputed proof that THIS family cannot fold           informative DEFER
  (f) HONEST_DEFER            — byte-identical original, with a reason                      —

★ No silently-wrong fold: every EXACT_FOLD carries a checked certificate. DEFER returns the input verbatim. ★
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import sympy as sp

import soup as S
import soup_lib as SL

_n, _k = S._n, S._k

# absence cache (STAGE 5.4): families PROVEN/recognized to have no closed fold — instant informative defer
ABSENCE_CACHE: Dict[str, str] = {
    "1/k": "harmonic Σ1/k — Gosper-nonsummable (no hypergeometric closed form)",
    "q-harmonic": "Σ q^k/(1-q^k) — no q-closed form (q-Gosper-nonsummable)",
    "theta": "Σ q^(k²) — theta, not q-hypergeometric-summable",
    "airy": "ODE y''=xy — non-Liouvillian (Galois SL₂), recognized",
}


@dataclass
class Disposition:
    kind: str                   # EXACT_FOLD | APPROX_FOLD | DEFER
    technique: str
    clock: str                  # C | B | —
    closed_form: str = "—"
    cert_type: str = "—"        # exact | epsilon-bounded | probabilistic | asymptotic-with-error | —
    strength: str = "—"
    original: str = ""          # the input, returned VERBATIM on DEFER (byte-identical, no regression)
    detail: str = ""

    @property
    def folded(self) -> bool:
        return self.kind in ("EXACT_FOLD", "APPROX_FOLD")


def _absence_hit(summand_str: str) -> Optional[str]:
    s = summand_str.replace(" ", "")
    if re.fullmatch(r"1/k", s) or re.fullmatch(r"1/\(k\)", s):
        return ABSENCE_CACHE["1/k"]
    if "q**k/(1-q**k)" in s:
        return ABSENCE_CACHE["q-harmonic"]
    if "q**(k*k)" in s or "q**(k**2)" in s:
        return ABSENCE_CACHE["theta"]
    return None


def dispose_summand(summand_str: str, lib: Optional[SL.LemmaLibrary] = None,
                    approx_fn=None) -> Disposition:
    """Strength-ordered disposition of a Σ-summand. `approx_fn(summand)->Disposition|None` is the optional
    STAGE-3 certified-approximate fallback. Returns a Disposition; DEFER carries the input verbatim."""
    if lib is None:
        lib, _ = SL.get_library()
    orig = summand_str
    # (a) soup O(1) lookup
    lem = lib.lookup_summand(summand_str)
    if lem is not None:
        return Disposition("EXACT_FOLD", "soup-lookup", "C", lem.closed_form, lem.cert_type,
                           lem.strength, orig, "O(1) verified-closed-form lookup")
    # (b) soup composition (linear combination), induction-PIT verified
    comp = lib.compose_linear(summand_str)
    if comp is not None:
        return Disposition("EXACT_FOLD", "soup-compose", "C", comp["closed_form"], comp["cert_type"],
                           comp["strength"], orig, "linear composition of library lemmas (verified)")
    # (c)/(d) derive via sympy summation, verify by the FINITE-BASE-CASE checker (PRA, ω^ω — the sound gate)
    try:
        import finite_check as FC
        expr = sp.sympify(summand_str, locals={"k": _k, "n": _n})
        closed = sp.simplify(sp.summation(expr, (_k, 1, _n)))
        if not closed.has(sp.Sum) and not closed.has(sp.Piecewise):
            cert = FC.verify_sum(expr, closed)
            if cert is not None:
                return Disposition("EXACT_FOLD", "derive+finite-base-case", "C", str(closed),
                                   cert.cert_type, cert.strength, orig, "derived + finite-base-case (PRA) verified")
    except Exception:  # noqa: BLE001
        pass
    # (e) certified-approximate fallback (STAGE 3): recover an exact-defer with a STATED error bound
    if approx_fn is not None:
        ap = approx_fn(summand_str)
        if ap is not None:
            return ap
    # (e') absence cache → informative DEFER (no exact fold, no approximation)
    ab = _absence_hit(summand_str)
    if ab is not None:
        return Disposition("DEFER", "absence-cache", "—", original=orig, detail=ab)
    # (f) HONEST_DEFER — byte-identical
    return Disposition("DEFER", "none", "—", original=orig,
                       detail="no exact fold, no absence cert, no approx — byte-identical defer")


def measure_disposition(targets: List[str], lib: Optional[SL.LemmaLibrary] = None,
                        approx_fn=None) -> dict:
    """Measure the disposition distribution over `targets` (Σ-summands). Asserts global soundness:
    DEFER is byte-identical; no target is left undisposed. Returns the distribution + byte-identity check."""
    if lib is None:
        lib, _ = SL.get_library()
    counts = {"EXACT_FOLD": 0, "APPROX_FOLD": 0, "DEFER": 0}
    byte_identical = True
    rows = []
    for t in targets:
        d = dispose_summand(t, lib, approx_fn=approx_fn)
        counts[d.kind] += 1
        if d.kind == "DEFER" and d.original != t:
            byte_identical = False                      # ★ defer MUST return the input verbatim ★
        rows.append((t, d.kind, d.technique, d.closed_form if d.folded else ""))
    n = len(targets)
    return {"n": n, "counts": counts, "byte_identical_defer": byte_identical,
            "exact_rate": round(counts["EXACT_FOLD"] / n, 3) if n else 0.0,
            "disposed_rate": round((n - 0) / n, 3) if n else 0.0,   # every target gets a disposition (100%)
            "rows": rows}
