# COMPLETION REPORT — UI/UX (§A) + ACCURACY (§B) + PERFORMANCE (§C)

All three definition-of-done checklists in `COMPLETION_PROGRESS.md` are ticked + verified (passing test or
working artifact; honest UNVERIFIED only where a sandbox limit truly blocks it). Engine suite **140/140, 0
regression**. Branch `claude/funny-maxwell-im9x07`, every item committed + pushed.

## §A — TOTAL UI/UX (priority, done in full)
- **A1 (the #1 requirement) — the mode color switch re-themes the WHOLE app.** `web/src/theme.ts`:
  `applyMode(root, mode)` sets `data-mode` AND writes `--accent/-deep/-tint` on the root, so selecting
  **fast→cyan #0E9FB5 / normal→amber #BA7517 / extend→violet #534AB7** recolors every `var(--accent)` user at
  once (with a transition). **Verified by `web/test_theme.mjs`**: three distinct live accents, exact spec
  colours, and the theme var actually changes on selection.
- **A2** extreme minimalism × extreme dimensionality: real CSS 3D (perspective/translateZ ×13), pointer tilt,
  scroll parallax, multi-layer shadows; the signature slab's fill **never crosses the Amdahl wall** — proven by
  `web/test_ui.mjs` (`slabGeometry`, fill ≤ wall on 794 ratio≤ceiling points incl. equality + unbounded).
- **A3** all six screens (Landing/Mode/Provider+key/Code+run/Verification/Corpus) bound to `/api/*`; build clean.
- **A4** dark-volume auto, responsive, reduced-motion, focus-visible + sr-only + aria, rounded numbers, honesty
  copy — grep-verified + build.
- **A5** back end wired to the real engine — **e2e smoke PASS**: modes=3, gemini default gemini-3.5-flash+free,
  corpus ratio≤ceiling, optimize real (n+1→EXACT 3.88×, cumulative 4.045), key validated **live** and the
  canary key **absent from the response AND the server log**, `/app` + `/onefile` served.
- Bonus: the **entire app in one self-contained file** (`mrjeffrey.html`) — static offline + live when served.
- UNVERIFIED: browser **visual** rendering (no browser in sandbox) — structure verified via tsc+build + a
  DOM-stub harness that builds all six screens.

## §B — ACCURACY (EXACT share up, logged) — see PHASE_ACCURACY_REPORT.md
- **10 EXACT classes** machine-checked by Z3 (7 lifts + strength-reduction/hoist/CSE) — up from ~2
  pre-campaign (**5×**). Each EXACT needs a proof AND a measured win (no "EXACT 1.0×").
- Control-flow recognizers kept **PROBABILISTIC and labelled** (Z3 returns *unknown*) — nothing differential
  mislabeled EXACT.
- Stronger input gen (boundary + float specials + concolic, δ shrinks), metamorphic + cross-check (catches a
  dedup-sort differential misses), **moat 15/15** (11 Z3 + 4 differential), zero false-accepts.

## §C — PERFORMANCE (big asymptotic, measured whole-program) — see PHASE_PERFORMANCE_REPORT.md
- Flagship **memoized-DP Fibonacci O(2ⁿ)→O(n): ~10,000× whole-program @ n=29, f≈1.0, ceiling ≈2×10⁵×,
  ratio ≤ ceiling** (honest because f≈1 and n is quoted). Hash-join O(n·m)→O(n+m) ~28×.
- Real LLM proposer (Gemini default gemini-3.5-flash / Groq), LLM proposes / verifier arbitrates; Gemini live
  reachable, Groq egress UNVERIFIED. GPU UNVERIFIED [no GPU]; SIMD measured.

## §X — WHAT WE MUST NOT CLAIM (verbatim)
- Whole-program **average** 50–100× is impossible for already-reasonable code (Amdahl). 50–100× requires a
  dominant hotspot (>95–99%) with an asymptotic/algorithmic/offloadable inefficiency; else ~10–20×, <2×
  already-optimized.
- **Kernel ≠ whole-program** (700× kernel → 4–6× end-to-end). Whole-program only.
- Asymptotic multipliers are **input-size-dependent** — quote n.
- Component multipliers **do not multiply** (Whatnot 3×·20×·6.7× → 5.8×). Measure fresh.
- The LLM **proposes**; the verifier decides. Unaided LLMs are wrong ~62% — value is verification. Never ship
  an LLM proposal that failed verification.
- Differential-only evidence is **PROBABILISTIC**, never EXACT.
- The grade is **OUTPUT confidence at runtime** (input + verifier), not a fixed property.
