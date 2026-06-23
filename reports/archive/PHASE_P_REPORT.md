# PHASE P (v56) — real LLM provider layer (Claude / ChatGPT / Gemini), proposer ≠ arbiter

The proposer becomes a real LLM — and is held to exactly the same verifier and the same ModePolicy as the
deterministic detectors. Rule 5 made executable: the LLM proposes *what*, the verifier decides *whether*.

## Delivered
- `provider.py` (extended) — **five providers**: `anthropic`, `anthropic_compat`, `openai_compat`, **`openai`**
  (native ChatGPT, `api.openai.com/v1/chat/completions`), **`gemini`** (native, `generativelanguage.google
  apis.com/.../:generateContent`). New: `transport_kind()` (anthropic_sdk / openai_chat / gemini_generate),
  `resolve_key_for()` (per-vendor key fallback), native base-URL defaults, ChatGPT + Gemini gateway presets.
  Existing behaviour unchanged (additive) — the `anthropic_compat`/`openai_compat` tests still pass.
- `pillar3/proposer.py` —
  - `Hotspot` (a profiler-located, detector-classified slow region) and `ProposedFix` (carries the proposed
    function + provenance + a verified/UNVERIFIED tag — **never the key**).
  - `build_request(cfg, prompt, key)` — selects the wire protocol per provider and builds the correct request
    body; the key goes **only into the send-headers** (Authorization: Bearer / x-goog-api-key / x-api-key),
    never into the JSON body, never logged.
  - `propose_fix(hotspot, mode, …)` — with provider+key+transport the LLM proposes (transport injectable; live
    network code is **not auto-executed** ⇒ UNVERIFIED, excluded). Without a key, the deterministic PHASE-M
    structural fix, tagged MEASURED.
  - `arbitrate(proposed, …)` — **the verifier arbitrates regardless of proposer**: differential FIRST, then a
    tier-gated certificate, then a measured whole-program win, then the mode grade floor.

## Measured / verified (the PHASE-P test)
- All five providers resolve and select the correct transport; `build_request` matches each vendor's API; the
  key appears only in headers, never in the body or the `ProposedFix`.
- No key → deterministic fallback, MEASURED, graded with a real whole-program win.
- ★ **a wrong LLM-proposed fix → DECLINE** — the arbiter holds regardless of who proposed (differential caught
  it). ★
- ★ **an LLM fix in extend with no certificate → DECLINE** — the EXACT-or-DECLINE floor holds over the LLM too;
  the *same* proposal is accepted (PROBABILISTIC) in normal. ★
- The live code-text path → UNVERIFIED, not auto-applied (Rule 6).

## §0 self-check
1. measured whole-program? yes — arbitration runs the Stage-1 measured pipeline. 2. fraction+ceiling? carried
through apply_and_grade. 3. graded + ADT? yes. 4. verified before accept? differential FIRST, every proposal.
5. blocked/unverifiable → UNVERIFIED + excluded? yes — live LLM code is not exec'd; tagged, not faked.

## Honest scope
No API key and no network in the sandbox ⇒ the LIVE LLM path is UNVERIFIED and the live proposal is not
auto-executed (arbitrary model code is not run); the proposer is exercised through an injectable transport
(mock in tests) and through the deterministic fallback. Keys are never logged, stored, committed, or phoned
home. 0 regression.
