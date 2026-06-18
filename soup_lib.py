"""
v33 STAGE 2/5 — the brewed lemma library: orchestrate brewing, dedup, content-address, O(1) index, compose.
============================================================================================================
Brews all families (BUILD-TIME), DEDUPES by canonical signature, persists each verified lemma in the
content-addressed store, and builds an O(1) lookup index (dict — not a 3000-entry linear scan; rule 5.1).
At runtime: signature → O(1) index hit → verified closed form (no proof search). Composition (R2.2) folds
NEW targets as linear combinations of library lemmas, multiplying effective coverage.

★ Honest counting (rule 6): we report BOTH (a) META-FAMILIES = distinct procedures (a small number), and
(b) INSTANCE-LEMMAS = distinct individually-verified identities (large; C-finite instances dominate — each a
genuinely distinct sequence, not p-splitting). Deduped. Counts MEASURED. ★
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import sympy as sp

import soup as S
from artifact_store import STORE, ArtifactStore

_n, _k = S._n, S._k


@dataclass
class BrewReport:
    n_meta_families: int
    n_instances: int
    per_family: Dict[str, int]
    build_ms: float
    deduped: int
    usefulness: Dict[str, int] = field(default_factory=dict)   # per-family corpus hits (filled by measure)


class LemmaLibrary:
    """O(1) lookup over the brewed lemmas. `by_key` indexes sum-families by canonical summand signature;
    `by_recurrence` indexes C-finite by coefficient signature; `lemmas` is the full deduped list."""

    def __init__(self):
        self.lemmas: List[S.Lemma] = []
        self.by_key: Dict[str, S.Lemma] = {}
        self.by_recurrence: Dict[str, S.Lemma] = {}
        self.per_family: Dict[str, int] = {}

    def add(self, lem: S.Lemma) -> bool:
        if lem.key in self.by_key or lem.key in self.by_recurrence:
            return False                                    # dedup by canonical signature
        self.lemmas.append(lem)
        if lem.family == "c-finite":
            self.by_recurrence[lem.key] = lem
        else:
            # index by canonical summand signature for O(1) membership
            self.by_key[S.canonical_key(lem.summand) if lem.summand else lem.key] = lem
        self.per_family[lem.family] = self.per_family.get(lem.family, 0) + 1
        return True

    def lookup_summand(self, summand_str: str) -> Optional[S.Lemma]:
        """O(1): does a verified closed form exist for this summand? (dict lookup, not a scan.)"""
        return self.by_key.get(S.canonical_key(summand_str))

    def lookup_recurrence(self, coeffs: List[int]) -> Optional[S.Lemma]:
        return self.by_recurrence.get(f"cfin:{list(coeffs)}")

    # ── R2.2 composition: fold a target that is a linear combination of library summands ──
    def compose_linear(self, target_summand_str: str) -> Optional[dict]:
        """If target = Σ αᵢ·tᵢ(k) with each tᵢ a library summand, fold to Σ αᵢ·Cᵢ(n) (linearity).
        Returns {closed_form, parts} or None. The composed closed form is then induction-PIT verifiable."""
        try:
            expr = sp.expand(sp.sympify(target_summand_str, locals={"k": _k, "n": _n}))
        except Exception:  # noqa: BLE001
            return None
        terms = expr.as_ordered_terms()
        if len(terms) < 2:
            return None
        closed = sp.Integer(0)
        parts = []
        for term in terms:
            coeff, rest = term.as_coeff_Mul()
            lem = self.lookup_summand(str(rest))
            if lem is None:
                # try the whole term (coeff folded into a known summand)
                lem = self.lookup_summand(str(term))
                if lem is None:
                    return None
                closed += sp.sympify(lem.closed_form, locals={"n": _n})
                parts.append(lem.key)
                continue
            closed += coeff * sp.sympify(lem.closed_form, locals={"n": _n})
            parts.append(f"{coeff}·{lem.key}")
        closed = sp.simplify(closed)
        # ★ verify the COMPOSED closed form by induction-PIT (composition is sound only if it checks) ★
        cert = S.induction_pit_verify(expr, closed)
        if cert is None:
            return None
        return {"closed_form": str(closed), "parts": parts, "cert_type": cert["cert_type"],
                "strength": cert["strength"]}


def brew_all(*, cfinite_maxc: int = 18, cfinite_order3: bool = True, store: Optional[ArtifactStore] = None,
             include_slow: bool = True) -> Tuple[LemmaLibrary, BrewReport]:
    """BUILD-TIME: run every brewer, dedup, persist content-addressed, build the O(1) index. Returns the
    library + a measured report. (Parallelized in STAGE 5; here serial for the count.)"""
    store = store or STORE
    lib = LemmaLibrary()
    t0 = time.perf_counter()
    brewers: List[Tuple[str, Callable[[], List[S.Lemma]]]] = [
        ("faulhaber", lambda: S.brew_power_sums(8)),
        ("geometric-hypergeometric", lambda: S.brew_geometric_hypergeometric()),
        ("trig", lambda: S.brew_trig()),
        ("c-finite", lambda: S.brew_cfinite(maxc=cfinite_maxc, orders=(2, 3) if cfinite_order3 else (2,))),
    ]
    if include_slow:
        brewers.append(("telescoping", lambda: S.brew_telescoping(max_a=4, max_m=2)))
    deduped = 0
    for _, fn in brewers:
        for lem in fn():
            if lib.add(lem):
                store.put(lem.as_dict())
            else:
                deduped += 1
    build_ms = (time.perf_counter() - t0) * 1000
    return lib, BrewReport(n_meta_families=len(set(l.family for l in lib.lemmas)),
                           n_instances=len(lib.lemmas), per_family=dict(lib.per_family),
                           build_ms=round(build_ms, 1), deduped=deduped)


_SINGLETON: Optional[LemmaLibrary] = None
_SINGLETON_REPORT: Optional[BrewReport] = None


def get_library() -> Tuple[LemmaLibrary, BrewReport]:
    """Brew the library ONCE per process (build-time), then reuse — models 'brew the soup once at startup,
    then only look up at runtime' (first principle). Subsequent calls are free."""
    global _SINGLETON, _SINGLETON_REPORT
    if _SINGLETON is None:
        _SINGLETON, _SINGLETON_REPORT = brew_all(cfinite_maxc=20, cfinite_order3=True)
    return _SINGLETON, _SINGLETON_REPORT


def measure_usefulness(lib: LemmaLibrary) -> Dict[str, int]:
    """Rule 6: how many defer-corpus targets does each family actually fold? (usefulness, MEASURED).
    Marks families that fold nothing in the corpus (still valid lemmas, but flagged as unused here)."""
    import defer_corpus as DC
    hits = {f: 0 for f in lib.per_family}
    for c in DC.load():
        lem = None
        if c.haran:
            # extract the INNERMOST fold body from `fold k in lo..n { BODY }` (no nested braces), look it up
            import re
            m = re.search(r"fold\s+k\s+in\s+[^{]+\{([^{}]+)\}", c.haran)
            if m:
                lem = lib.lookup_summand(m.group(1).strip().replace("^", "**"))
        if lem:
            hits[lem.family] = hits.get(lem.family, 0) + 1
    return hits
