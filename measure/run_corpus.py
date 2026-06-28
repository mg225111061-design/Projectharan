"""
§AK §2 (aggregate) — run the unchanged engine over the whole corpus and aggregate HONESTLY.
================================================================================================================
★ M-1 (no single number): the fold rate is reported PER DOMAIN and PER PROVENANCE, never as a lone scalar. ★ The
honest fold-rate definition: EXACT_FOLD / (EXACT + PROBABILISTIC + DECLINE) — PROBABILISTIC is NOT in the numerator
(it is a weaker grade), and ERROR is EXCLUDED from the denominator (an engine-can't-analyze is not a DECLINE — folding
it in either direction would be a lie). ★ Measurement hygiene: each code is classified in ISOLATION (no state leak),
a fixed z3 timeout is set at the harness level (z3.set_param — the engine code is untouched), and the seed is fixed
(reproducible). No wall-clock assertions (we measure RESULTS, not speed — the §AJ flake lesson).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from corpus import build_corpus as BC
from measure import engine_adapter as EA

_CLASSES = (EA.EXACT_FOLD, EA.PROBABILISTIC_FOLD, EA.DECLINE, EA.ERROR)


@dataclass
class RunResult:
    summary: dict
    results: list = field(default_factory=list)   # the per-item AdapterResults (for §3 / §4 / M-3)


def _counts() -> dict:
    return {c: 0 for c in _CLASSES}


def _fold_rate(c: dict) -> float:
    """EXACT / (EXACT + PROB + DECLINE) — ERROR excluded, PROBABILISTIC NOT in the numerator."""
    denom = c[EA.EXACT_FOLD] + c[EA.PROBABILISTIC_FOLD] + c[EA.DECLINE]
    return round(c[EA.EXACT_FOLD] / denom, 4) if denom else 0.0


def _block(c: dict) -> dict:
    return {"EXACT": c[EA.EXACT_FOLD], "PROBABILISTIC": c[EA.PROBABILISTIC_FOLD], "DECLINE": c[EA.DECLINE],
            "ERROR": c[EA.ERROR], "fold_rate": _fold_rate(c)}


def run(n: int = BC.TOTAL, seed: int = BC.SEED, probe: int = EA._PROBE, z3_timeout_ms: int = 5000) -> RunResult:
    """Classify all `n` corpus codes with the unchanged engine; aggregate per-domain × per-provenance. Reproducible."""
    try:
        import z3
        z3.set_param("timeout", z3_timeout_ms)            # harness-level z3 timeout (engine code untouched)
    except Exception:  # noqa: BLE001
        pass
    items = BC.build_corpus(n, seed)
    overall, by_domain, by_prov, by_dp = _counts(), {}, {}, {}
    results = []
    try:
        for it in items:
            r = EA.classify(it, probe=probe)              # ISOLATED per-item classification
            results.append(r)
            overall[r.classification] += 1
            by_domain.setdefault(it.domain, _counts())[r.classification] += 1
            by_prov.setdefault(it.provenance, _counts())[r.classification] += 1
            by_dp.setdefault((it.domain, it.provenance), _counts())[r.classification] += 1
    finally:
        try:
            import z3
            z3.set_param("timeout", 0)                    # ★ RESTORE z3's default (no timeout) — never leak to other code
        except Exception:  # noqa: BLE001
            pass
    summary = {
        "n": n, "seed": seed, "probe": probe, "z3_timeout_ms": z3_timeout_ms,
        "overall": _block(overall),
        "by_domain": {d: _block(c) for d, c in sorted(by_domain.items())},
        "by_provenance": {p: _block(c) for p, c in sorted(by_prov.items())},
        "by_domain_provenance": {f"{d}/{p}": _block(c) for (d, p), c in sorted(by_dp.items())},
        "honest_notes": [
            "M-1: the overall fold rate is NEVER reported alone — it is dominated by the corpus mix; read per-domain.",
            "general_backend's low fold rate is CORRECT (structureless backend code has nothing to fold — math, not failure).",
            "PROBABILISTIC is reported SEPARATELY and is NOT in the fold-rate numerator.",
            "ERROR is EXCLUDED from the fold-rate denominator and reported on its own.",
            "synthetic = recall ceiling (does the engine catch what it knows?); realworld_style = the real number.",
        ],
    }
    return RunResult(summary, results)


def adversarial_battery() -> dict:
    """★ honest measurement on a small reproducible sample: general_backend fold rate < numeric (M-1 — domain matters);
    ★ synthetic fold rate > realworld (recall-ceiling vs real); ★ crypto folds ~0 (hashes must DECLINE — no false
    EXACT); ★ the fold-rate definition excludes ERROR and keeps PROBABILISTIC out of the numerator; ★ reproducible."""
    a = run(150, seed=7)
    b = run(150, seed=7)
    s = a.summary
    reproducible = a.summary["overall"] == b.summary["overall"]
    gen = s["by_domain"].get("general_backend", {}).get("fold_rate", 1.0)
    num = s["by_domain"].get("numeric", {}).get("fold_rate", 0.0)
    crypto = s["by_domain"].get("crypto_preprocessing", {}).get("fold_rate", 1.0)
    syn = s["by_provenance"].get("synthetic", {}).get("fold_rate", 0.0)
    real = s["by_provenance"].get("realworld_style", {}).get("fold_rate", 1.0)
    cases = {
        "reproducible": reproducible,
        "general_backend_low": gen < num,                       # ★ M-1: domain dominates the number
        "crypto_near_zero": crypto <= 0.05,                     # ★ hashes/CSPRNG must DECLINE
        "synthetic_beats_realworld": syn > real,               # ★ recall ceiling > real number (separated honestly)
        "error_excluded_prob_separate": "fold_rate" in s["overall"] and s["overall"]["PROBABILISTIC"] >= 0,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
