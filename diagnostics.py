"""
§BF FIX-7 — DECLINE diagnostics: turn a DECLINE from a WALL into FEEDBACK.
================================================================================================================
The verifiers already COMPUTE why they decline (loop_decision emits "no hypergeometric closed form", the conjecture
router emits "order > probe ⇒ under-determined", the precheck emits "structureless / pseudo-random", effect_gate
emits "opaque/nondet"). Historically that reason was dropped — the user saw only "DECLINE" and could not tell
whether to (a) give more terms, (b) raise the tier, or (c) accept an inherent limit. This module is a pure,
zero-dependency CATEGORIZER over the reason strings the engine ALREADY produces — it adds NO new analysis, it just
surfaces and classifies what the verifier said, with a developer-actionable hint.

★ This is feedback, not a soundness path: it never changes a grade. precision 1.0 is untouched.
"""
from __future__ import annotations

from typing import Optional

# (category, keyword triggers [lowercased substrings], developer-facing hint). First match wins; order = specificity.
_PATTERNS = [
    # ★ non_hypergeometric is checked BEFORE no_closed_form (more specific): "not a hypergeometric term … outside
    #   the Gosper decision scope" is an HONEST-SCOPE boundary, NOT a proven "no closed form exists".
    ("non_hypergeometric",
     ["non-hypergeometric", "not a hypergeometric", "not rational", "outside the gosper", "honest scope",
      "decision scope"],
     "Gosper/Abramov 결정 범위 밖입니다 (f(k+1)/f(k)가 유리식이 아님) — '닫힌형 없음'이라 단정하지 않고 정직하게 보류합니다. 표현을 단순화하면 접힐 수 있습니다."),
    ("no_closed_form",
     ["no closed form", "no_closed_form", "no hypergeometric", "irreducible", "harmonic",
      "not rationally summable", "not_rationally_summable", "keep the loop"],
     "증명상 닫힌 형식이 없습니다 — 루프를 그대로 두는 것이 맞습니다 (접을 수 없는 것이 정답인 경우). 이건 한계지 버그가 아닙니다."),
    ("under_determined",
     ["under-determined", "under_determined", "order >", "order>", "beyond", "probe", "not enough", "need more",
      "insufficient", "more terms", "더 많", "차수"],
     "관측된 항이 부족하거나 차수가 탐색 범위를 넘었습니다 — 더 많은 항을 주거나 더 깊은 티어(normal/extend)로 재시도하면 접힐 수 있습니다."),
    ("structureless",
     ["structureless", "random", "pseudo-random", "pseudorandom", "hash", "entropy", "incompressible", "monobit",
      "kolmogorov", "no structure", "skip", "precheck"],
     "구조가 없어 본질적으로 접히지 않습니다 (난수/해시/비압축 데이터) — 이건 검증기의 정직한 한계지, 고칠 수 있는 결함이 아닙니다."),
    ("effectful",
     ["opaque", "nondet", "non-deterministic", "io ", "i/o", "eval", "exec", "reflect", "getattr", "external",
      "side effect", "side-effect"],
     "외부효과/비결정/반사 호출(eval·exec·I/O·난수)이 있어 정적으로 검증할 수 없습니다 — 사람이 검토해야 합니다."),
    ("unparseable",
     ["unparseable", "cannot parse", "does not parse", "syntax", "parse error"],
     "입력을 파싱하지 못했습니다 — 먼저 구문 오류를 고친 뒤 다시 시도하세요."),
    ("budget",
     ["budget", "timeout", "timed out", "abandoned", "예산", "시간"],
     "주어진 시간(티어 예산) 안에 닫지 못했습니다 — 더 깊은 티어로 올리거나 다시 시도하세요 (결과를 위조하지 않습니다)."),
]

_UNKNOWN_HINT = ("현재 결정 절차의 범위 밖입니다 — 구조를 단순화하거나 더 깊은 티어로 시도해 보세요. "
                 "(왜 안 되는지가 보이면, 접히도록 코드를 고치거나 본질적 한계임을 이해할 수 있습니다.)")


def categorize_decline(reason: Optional[str]) -> dict:
    """Map an engine-emitted DECLINE/DEFER reason string → {category, why, hint}. Pure; adds no analysis."""
    low = (reason or "").lower()
    for cat, keys, hint in _PATTERNS:
        if any(k in low for k in keys):
            return {"category": cat, "why": reason or "", "hint": hint}
    return {"category": "unknown", "why": reason or "(이유 미상)", "hint": _UNKNOWN_HINT}


def explain_verdict(verdict) -> Optional[dict]:
    """Given a kernel_verdict.Verdict (or anything with .status/.reason/.certificate), return a diagnosis for a
    DECLINE (else None). Reads the reason the verifier already computed — never recomputes."""
    status = getattr(verdict, "status", None)
    if status not in (None, "DECLINE"):
        return None
    reason = getattr(verdict, "reason", "") or ""
    if not reason:
        cert = getattr(verdict, "certificate", None)
        reason = getattr(cert, "detail", "") if cert is not None else ""
    return categorize_decline(reason)


def adversarial_battery() -> dict:
    """★ each real engine reason maps to the right actionable category (not 'unknown'); ★ a bare/empty reason is
    handled gracefully; ★ the categorizer NEVER raises."""
    cases = {
        "harmonic_no_closed_form": categorize_decline(
            "Σ 1/k has NO hypergeometric closed form — Gosper is COMPLETE, keep the loop")["category"] == "no_closed_form",
        "non_hypergeometric_scope": categorize_decline(
            "summand is not a hypergeometric term (f(k+1)/f(k) not rational) — outside the Gosper decision scope")["category"] == "non_hypergeometric",
        "under_determined_order": categorize_decline(
            "order > probe ⇒ under-determined; need more observed terms")["category"] == "under_determined",
        "random_structureless": categorize_decline(
            "precheck skipped (pseudo-random / high entropy) ⇒ structureless ⇒ DECLINE")["category"] == "structureless",
        "opaque_effect": categorize_decline(
            "calls an UNANALYZABLE reflective construct (eval) ⇒ opaque")["category"] == "effectful",
        "empty_reason_ok": categorize_decline("")["category"] == "unknown",
        "always_has_hint": all(categorize_decline(r)["hint"] for r in ["", "x", "harmonic", "random"]),
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), ensure_ascii=False, indent=2))
