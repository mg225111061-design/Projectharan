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
### A2 — extreme minimalism × extreme dimensionality
- ☐ white volume, tiny palette, no chrome, mono numbers
- ☐ real CSS 3D (perspective/rotate/translateZ), multi-layer shadows, pointer tilt, scroll parallax
- ☐ signature slab: bar + Amdahl wall on raised planes, fill never crosses wall
- ☐ not a templated AI look; mode=temperature, grade=signal (separate)
### A3 — six screens, cohesive, real engine data
- ☐ Landing / Mode / Provider+key / Code+run / Verification / Corpus
### A4 — quality floor
- ☐ dark-volume / responsive / reduced-motion / focus rings+sr labels / rounded numbers / honesty copy
### A5 — back end wired to real engine
- ☐ /api/optimize /modes /providers /key/validate /corpus /demo; measured+f+ceiling+grade; e2e smoke

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
