# COMPLETION_PROGRESS — definition-of-done tracker

Completion-driven (not time-boxed). Each box: ☐ pending / ☑ done — with the verifying commit + test/artifact.
Sandbox limits (no browser, no GPU, Groq host egress-blocked) → honest UNVERIFIED, never a fake pass.

RESUME POINTER: §A1 in progress (testable mode color switch). Then A3/A4/A5 verification, then §B report, §C recognizers.

## §A — TOTAL UI/UX (priority, in full)
### A1 — mode color switch re-themes the WHOLE app (the #1 requirement) ✅
- ☑ single `mode` drives a CSS-variable theme; fast/normal/extend re-theme the entire interface, smooth transition — `web/src/theme.ts` applyMode() sets data-mode + --accent/-deep/-tint on the root; App.tsx useEffect on activeMode [test_theme.mjs]
- ☑ fast→cyan #0E9FB5, normal→amber #BA7517, extend→violet #534AB7 [test_theme.mjs asserts exact hex]
- ☑ a test asserts 3 distinct live accent values + the theme variable changes on selection [web/test_theme.mjs PASS]
- ☑ each mode differs by icon + depth + real contract from /api/modes — ModeCard depth-{mode} + DEPTH tilt + dl of contract fields incl. risk_posture [build]
### A2 — extreme minimalism × extreme dimensionality ✅
- ☑ white volume, tiny palette, no chrome, mono numbers [styles.css tokens; tenets borderless]
- ☑ real CSS 3D (perspective/rotate/translateZ ×13), multi-layer shadows, pointer tilt (useTilt), scroll parallax (useParallax) [build]
- ☑ signature slab: bar + Amdahl wall on raised planes, fill never crosses wall [meter.ts slabGeometry; test_ui.mjs proves fill≤wall on 794 pts incl. equality+unbounded]
- ☑ mode=temperature (A1), grade=signal separate (exact green/prob slate/decline gray) [styles.css .grade]
### A3 — six screens, cohesive, real engine data ✅
- ☑ Landing/Mode/Provider+key/Code+run/Verification/Corpus — all in web/src/screens, bound to api.ts → /api/* [tsc+build; A5 e2e confirms the consumed data is real; same six-screen logic proven to build in the single-file DOM-stub harness]. Browser visual render: UNVERIFIED [no browser in sandbox]
### A4 — quality floor ✅
- ☑ dark-volume auto (prefers-color-scheme, App.tsx) / responsive (@media ×11) / reduced-motion (×5) / focus-visible + sr-only + aria / rounded (toFixed/r2/r3 ×30) / honesty copy ("never localStorage, never logged"; session-only) [grep-verified + build]
### A5 — back end wired to real engine ✅
- ☑ /api/optimize /modes /providers /key/validate /corpus /demo — e2e smoke PASS: modes=3, gemini default gemini-3.5-flash+free, corpus ratio≤ceiling, optimize real (n+1→EXACT 3.88×, cumulative 4.045), key validated LIVE + canary absent from response AND server log, /app+/onefile 200

## §B — ACCURACY (drive EXACT share up, log it)
- ☐ equiv covers more EXACT classes (reassoc/distributive/strength/hoist/CSE/prefix/diff-array/telescoping) + wrong→DECLINE
- ☐ recognizers promoted to EXACT where provable; Z3-unknown kept PROBABILISTIC + labeled
- ☐ stronger input gen (boundary+float specials+concolic; δ shrinks)
- ☐ metamorphic + cross-check; differential-pass-but-relation-violation → DECLINE
- ☐ moat battery refutes every adversarial wrong; count logged
- ☐ EXACT:PROB:DECLINE distribution reported, EXACT share up (PHASE_ACCURACY_REPORT.md)

## §C — PERFORMANCE (big asymptotic, measured whole-program)
- ☐ real LLM proposer wired (Gemini 3.5 Flash / Groq); mocked-LLM tests; live UNVERIFIED [no network to provider]
- ☐ big-multiplier recognizers (FFT, hash join, KMP, memoized DP, …) each verified, n quoted
- ☐ lifting widened beyond 7, Z3 two-step, wrong→DECLINE
- ☐ GPU/SIMD offload deeper; non-dominant→DECLINE; GPU UNVERIFIED [no GPU]
- ☐ flagship measured result documented (PHASE_PERFORMANCE_REPORT.md)

## Already landed before this directive (to verify/tick, not redo)
- lifting.py 7 lifts (EXACT, Z3 two-step); equiv_transforms 3 EXACT; algorithms 4 recognizers (PROBABILISTIC);
  inputgen (ints+floats+concolic); metamorphic; offload (SIMD+Amdahl); moat battery 15/15; proposer 5 providers;
  React app (6 screens, dimensional, dark/mobile/a11y) + webapi; single-file mrjeffrey.html. Suite 140/140.
