"""
webapi/coder_models.py — coder-model TIER catalog + hardware-aware recommendation (코더-티어 지시서).
=================================================================================================================
The download path already runs JEFF's tool/fold/verify pipeline for ANY provider-selected model (parity is
established + regression-locked). This module adds only the model-SELECTION layer the directive asks for:
a 4-tier (+API-only) catalog of coder-capable local models, and a hardware-fit recommendation.

★ HONEST HYBRID (프라임 2 — "don't hardcode the catalog from memory; live-query, seed is fallback,
timestamp it") ★: the ONE thing reliably machine-extractable from `ollama.com/library` is the set of model
NAMES (the `/library/<name>` links). So `live_library_names()` fetches exactly that and no more. Everything
NOT reliably extractable — VRAM need, recommended quant, license, and the coder-vs-general EVIDENCE — stays
in a CURATED seed (`SEED_TIERS`), each entry citing its basis (프라임 3: coder classification is
evidence-based, never an arbitrary whitelist). `tier_catalog()` merges the two: a seed model is flagged
`live_confirmed` iff its name is in the live set; a live `*-coder`/`*coder*` name absent from the seed is
surfaced as a `discovered` entry, labelled "general" unless it carries evidence. On a live-fetch failure the
catalog degrades to seed-only with `source="seed-fallback"` — never a fabricated "this is current" claim.

★ RECOMMENDATION (프라임 4 — the corrected rule) ★: recommend the LARGEST coder model that FITS the user's
VRAM, NOT the smallest (a big model at Q4 beats a small model, and sub-7B loses the most under Q4). 3-bit is
demoted to a "only when VRAM is really tight" option, never the default.

★ TIER LABELS (프라임 5) ★: tier names are LOCAL-execution-capability tiers — "local frontier" never means
"beyond Mythos". The top local coder still trails a cloud frontier; the UI must say so. `:cloud`-only models
are NOT in the local tiers (프라임: they can't be pulled locally) — they live in the separate API-only list.

Stdlib-only (urllib + re), matching local_models.py's zero-dependency discipline.
"""
from __future__ import annotations

import re as _re
import time as _time
import urllib.request as _urlreq
from typing import Dict, List, Optional, Tuple

LIBRARY_URL = "https://ollama.com/library"

# Local-capability tiers. VRAM figures are the directive's own §티어 seed table (Q4_K_M default unless noted)
# — SEED ESTIMATES, not scraped: labelled as such and shown with the fetch timestamp so the UI never implies
# they are live-measured. `coder_evidence` cites WHY each is classified coder-capable (프라임 3).
TIERS = ("local_frontier", "upper", "mid", "entry", "cpu_offline")

SEED_TIERS: Dict[str, List[Dict]] = {
    "local_frontier": [
        {"name": "gpt-oss:120b", "pull": "gpt-oss:120b", "vram_gb": 80, "quant": "MXFP4",
         "license": "Apache-2.0", "coder_evidence": "gpt-oss model card: strong coding; Apache-2.0 (2026-06)"},
        {"name": "qwen3-coder:large", "pull": "qwen3-coder", "vram_gb": 48, "quant": "q8_0",
         "license": "Apache-2.0", "coder_evidence": "Qwen3-Coder card: agentic coding, 256K ctx; Apache-2.0"},
    ],
    "upper": [
        {"name": "qwen3-coder:30b", "pull": "qwen3-coder:30b", "vram_gb": 20, "quant": "Q4_K_M",
         "license": "Apache-2.0", "coder_evidence": "Qwen3-Coder 30B-A3B MoE, 256K, coding-optimized card",
         "recommended_default": True},
        {"name": "qwen3.6:27b", "pull": "qwen3.6:27b", "vram_gb": 24, "quant": "Q4_K_M",
         "license": "Apache-2.0", "coder_evidence": "qwen3.6:27b card: 77.2% SWE-bench (self-reported), 24GB Q4"},
        {"name": "devstral-2", "pull": "devstral", "vram_gb": 22, "quant": "Q4_K_M",
         "license": "Apache-2.0", "coder_evidence": "Devstral (Mistral) agentic SWE-specialized; 72.2% SWE-bench Verified (self-reported)"},
    ],
    "mid": [
        {"name": "gpt-oss:20b", "pull": "gpt-oss:20b", "vram_gb": 16, "quant": "Q4_K_M",
         "license": "Apache-2.0", "coder_evidence": "gpt-oss:20b card: coding-capable; 16GB class; Apache-2.0",
         "recommended_default": True},
        {"name": "devstral-small-2:24b", "pull": "devstral-small", "vram_gb": 14, "quant": "Q4_K_M",
         "license": "Apache-2.0", "coder_evidence": "Devstral Small 2 (24B) agentic SWE card"},
    ],
    "entry": [
        {"name": "qwen2.5-coder:7b", "pull": "qwen2.5-coder:7b", "vram_gb": 6, "quant": "Q4_K_M",
         "license": "Apache-2.0", "coder_evidence": "Qwen2.5-Coder 7B: code-specialized card",
         "recommended_default": True},
        {"name": "qwen2.5-coder:7b-3bit", "pull": "qwen2.5-coder:7b", "vram_gb": 4, "quant": "Q3_K_M",
         "license": "Apache-2.0", "coder_evidence": "same model, tighter quant",
         "tight_only": True},   # 프라임 4: 3-bit only when VRAM is really tight, never the default
    ],
    "cpu_offline": [
        {"name": "qwen2.5-coder:3b", "pull": "qwen2.5-coder:3b", "vram_gb": 0, "quant": "Q4_K_M",
         "license": "Apache-2.0", "coder_evidence": "Qwen2.5-Coder 3B: code-specialized card",
         "cpu_ok": True, "slow_warning": True},
    ],
}

# `:cloud`-only — cannot be pulled locally, so NOT in the local tiers. Exposed only on the API path (프라임).
API_ONLY_SEED: List[Dict] = [
    {"name": "kimi-k2.6", "license": "modified-MIT",
     "coder_evidence": "Kimi K2.6: SWE-Bench Pro 58.6 (self-reported); :cloud tag — no local pull"},
    {"name": "glm-5.x", "license": "MIT", "coder_evidence": "GLM-5.x coding-strong; :cloud tag — no local pull"},
    {"name": "deepseek-v4:pro", "license": "MIT",
     "coder_evidence": "DeepSeek V4 Pro; :cloud tag — no local pull"},
]

_TIER_LABEL = {
    "local_frontier": "로컬 최상위 (클라우드 프론티어 아님)",
    "upper": "상위 (24–32GB)",
    "mid": "중급 (16GB)",
    "entry": "보급형 (8–12GB)",
    "cpu_offline": "CPU/오프라인 (느림)",
}

_LINK_RE = _re.compile(r'href="/library/([a-z0-9._-]+)"')
_CODER_HINT = _re.compile(r"cod(?:e|er)|devstral|codestral", _re.IGNORECASE)


def _extract_library_names(html: str) -> List[str]:
    """The ONLY reliably-parseable thing from the library page: the model-name link set (프라임 2)."""
    seen, out = set(), []
    for m in _LINK_RE.finditer(html):
        n = m.group(1)
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def live_library_names(timeout: float = 8.0) -> Tuple[List[str], str]:
    """Fetch ollama.com/library and return (names, "OK") or ([], "BLOCKED"). Never raises — a blocked/slow
    egress is the SWE-bench honest-BLOCKED pattern, not a crash, and drops us to the seed fallback."""
    try:
        req = _urlreq.Request(LIBRARY_URL, method="GET", headers={"User-Agent": "mrjeffrey-catalog"})
        with _urlreq.urlopen(req, timeout=timeout) as r:  # noqa: S310 — fixed public URL
            if r.status != 200:
                return [], "BLOCKED"
            names = _extract_library_names(r.read().decode("utf-8", "replace"))
            return (names, "OK") if names else ([], "BLOCKED")
    except Exception:  # noqa: BLE001
        return [], "BLOCKED"


def _base_name(pull: str) -> str:
    return pull.split(":", 1)[0]


def tier_catalog(live: bool = True) -> Dict:
    """The merged catalog. Live layer confirms/discovers NAMES; the curated seed supplies the metadata.
    Returns per-model `live_confirmed` + a top-level `source`/`fetched_at`/`live_names_count` so the UI can
    show provenance honestly (프라임 2: 조회 시점 타임스탬프 표기, never a bare "this is current")."""
    names, status = (live_library_names() if live else ([], "SKIPPED"))
    live_set = set(names)
    tiers_out: Dict[str, Dict] = {}
    for tier, models in SEED_TIERS.items():
        rows = []
        for m in models:
            row = dict(m)
            row["tier"] = tier
            row["classification"] = "coder"          # every seed entry is evidence-backed coder (see field)
            row["live_confirmed"] = _base_name(m["pull"]) in live_set if status == "OK" else None
            row["pipeline"] = "JEFF 도구·fold·검증 적용됨"   # 프라임: every model rides the pipeline (§BG badge is the proof)
            rows.append(row)
        tiers_out[tier] = {"label": _TIER_LABEL[tier], "models": rows}

    # discovered: live `*coder*` names not already covered by a seed entry — surfaced, but labelled by evidence
    seed_bases = {_base_name(m["pull"]) for ms in SEED_TIERS.values() for m in ms}
    discovered = [{"name": n, "classification": "general_or_coder_unverified",
                   "note": "라이브 목록에서 발견 — coder 근거 미확인, 범용으로 분리", "live_confirmed": True}
                  for n in names if _CODER_HINT.search(n) and n not in seed_bases] if status == "OK" else []

    return {
        "source": "live+seed" if status == "OK" else "seed-fallback",
        "live_fetch_status": status,
        "fetched_at": _time.time(),
        "live_names_count": len(names),
        "tiers": tiers_out,
        "discovered_coder_names": discovered,
        "api_only": API_ONLY_SEED,          # :cloud models — API path only, never a local tier
        "quantization_note": ("코딩엔 VRAM 되면 q8_0 선호. ★큰 모델 Q4 > 작은 모델 (7B 미만이 Q4에서 "
                              "최다 손실). 3-bit는 VRAM이 정말 빠듯할 때만 — 디폴트 아님."),
        "tier_label_note": "티어 이름은 로컬 실행 가능성 기준 — '로컬 최상위'도 클라우드 프론티어엔 못 미침.",
    }


# hardware option buckets for the UI dropdown (프라임 6: don't guess VRAM — offer these when detection fails)
VRAM_OPTIONS = (48, 32, 24, 16, 12, 8, 0)   # 0 = CPU-only


# tier order high→low: this hierarchy is the directive's CURATED capability ordering. Recommending by "highest
# tier that fits" (not a raw VRAM-footprint sort) is the honest reading of 프라임 4's "largest that fits" —
# a raw VRAM sort is distorted by MoE models (e.g. qwen3-coder:30b MoE needs LESS VRAM than a dense 27b, yet is
# the directive's marked upper-tier default), so footprint ≠ capability. The tiers encode capability; use them.
_TIER_ORDER = ("local_frontier", "upper", "mid", "entry")


def recommend(vram_gb: Optional[int]) -> Dict:
    """★프라임 4★: the LARGEST coder class that FITS, not the smallest. Walks tiers high→low; the first tier
    with any non-tight model that fits wins, preferring that tier's curated `recommended_default`. `vram_gb`
    None/0 ⇒ CPU tier. 3-bit `tight_only` only when nothing standard fits. Never recommends a won't-run model."""
    if not vram_gb or vram_gb <= 0:
        cpu = SEED_TIERS["cpu_offline"][0]
        return {"recommended": dict(cpu, reason="GPU 없음 → CPU급 3B (느림 경고)"),
                "fits": [dict(cpu)], "vram_gb": 0}
    all_fits: List[Dict] = []
    chosen: Optional[Dict] = None
    for tier in _TIER_ORDER:
        tier_fits = [dict(m, tier=tier) for m in SEED_TIERS[tier]
                     if not m.get("tight_only") and m["vram_gb"] <= vram_gb]
        all_fits.extend(tier_fits)
        if tier_fits and chosen is None:
            # prefer this tier's curated default; else the largest-footprint model that fits within the tier
            default = next((m for m in tier_fits if m.get("recommended_default")), None)
            chosen = default or max(tier_fits, key=lambda m: m["vram_gb"])
    if chosen is not None:
        return {"recommended": dict(chosen, reason=f"{vram_gb}GB에 들어가는 가장 높은 티어의 coder 모델 "
                                    "(큰 모델 Q4 > 작은 모델; MoE 고려해 티어 순으로 선택)"),
                "fits": all_fits, "vram_gb": vram_gb}
    # nothing standard fits → the tight-only 3-bit option if it fits, else honestly say it's very tight
    tight = [dict(m, tier="entry") for m in SEED_TIERS["entry"]
             if m.get("tight_only") and m["vram_gb"] <= vram_gb]
    rec = tight[0] if tight else dict(SEED_TIERS["cpu_offline"][0], tier="cpu_offline")
    return {"recommended": dict(rec, reason=f"{vram_gb}GB로는 표준 quant가 빠듯 — 3-bit/최소 모델만 가능"),
            "fits": tight, "vram_gb": vram_gb, "tight": True}
