"""
§BI WORKSTREAM B — file attachment (300+ formats · compute-on-compressed · 100% extraction).
================================================================================================
Net-new here: `registry` (FL-1, 300+ formats with honest depth labels), `compute_on_compressed` (FL-3, query
without unpacking), `completeness` (FL-4, verifiable extraction vs uncertified understanding). REUSED, not rebuilt:

  • FL-2 compression-bomb guard + path-traversal defense → `mathmode/archive.py` (`extract`, `Limits`).
  • FL-5 extracted code/math → fold/checker route → `mathmode/ingest.py` (cfinite/Gosper, honest UNVERIFIED/DECLINE),
    riding `recall/core` (the single false-EXACT-0 disposer).

★ Two honesty corrections are the spine: decompression is standard (NOT fold; the fold-spirit gem is FL-3), and
100% EXTRACTION is verifiable/EXACT while understanding stays best-effort/uncertified (false-EXACT 0).
"""
from __future__ import annotations

from fileattach import completeness, compute_on_compressed, registry


def reuse_status() -> dict:
    """Confirm the FL-2 / FL-5 reuse targets import (the directive's 're-build 0' claim, checked)."""
    out = {}
    try:
        from mathmode import archive as _A
        out["FL2_bomb_guard"] = hasattr(_A, "extract") and hasattr(_A, "Limits")
    except Exception:  # noqa: BLE001
        out["FL2_bomb_guard"] = False
    try:
        from mathmode import ingest as _I
        out["FL5_fold_route"] = hasattr(_I, "ingest")
    except Exception:  # noqa: BLE001
        out["FL5_fold_route"] = False
    return out


def adversarial_battery() -> dict:
    subs = {
        "registry": registry.adversarial_battery(),
        "compute_on_compressed": compute_on_compressed.adversarial_battery(),
        "completeness": completeness.adversarial_battery(),
    }
    reuse = reuse_status()
    return {"sub": subs, "reuse": reuse, "all_ok": all(s["all_ok"] for s in subs.values()) and all(reuse.values()),
            "failed": {k: s["failed"] for k, s in subs.items() if not s["all_ok"]}}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
