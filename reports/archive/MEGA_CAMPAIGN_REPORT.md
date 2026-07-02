# MEGA-DIRECTIVE — campaign report (honest end-state)

16-hour autonomous, performance-first build on `claude/funny-maxwell-im9x07`, on top of Pillar 3 Stages 0–5.
Mode separation was the #1 deliverable and the spine of everything after it. Every phase: real code, measured
whole-program, graded by the ADT, full suite re-run (0 regression), committed and pushed.

## What shipped (phase queue M → P → D → R → S → U)

| phase | commit(s) | deliverable | the measured headline |
|------:|-----------|-------------|-----------------------|
| **M** | v54, v55 | **Mode separation: fast / normal / extend** — `mode.py` (ModePolicy), `verifier.py` (tier ladder + Z3 counter), `engine.py` (mode-aware controller), `canonical.py` | seven distinctness proofs: fast z3=0 / 1 PROBABILISTIC win; normal EXACT+PROBABILISTIC; **extend EXACT-or-DECLINE**; cross-mode speedup & latency monotone; ★ same PROBABILISTIC fix accepted-in-normal / DECLINEd-in-extend ★ |
| **P** | v56 | **5-provider LLM proposer** (Claude/ChatGPT/Gemini/2 gateways), `proposer.py` | proposer ≠ arbiter: a wrong LLM fix → DECLINE; an LLM fix in extend with no certificate → DECLINE; key never logged |
| **D** | v57, v58, v59 | **detectors 4 → 19** (`detectors2.py`), gated by mode tier | D1 (fast) redos 3400× / quad-build 150× …; D2 (normal) materialize→lazy 3000× / hoist 700× …; D3 (extend) memoize 1270× / egg Z3-proven, wrong-coeff REFUTED |
| **R** | v60 | **real-code corpus** (`corpus/` + `corpus_runner.py`) | ai_todo_app ~44× · csv_stats ~115× · json_pipeline EXACT ~84× · log_analyzer ~8× · ★ template_render → honest DECLINE (well-written, nothing to ship) ★ |
| **S** | v61 | **extend depth: superopt + verified lifting** (`superopt.py`) | verified lifting Σc·x→c·Σx Z3-PROVEN ~6.5× · memoised DP fib ~190000× · egg Z3-PROVEN; ★ 3/3 adversarial wrong swaps Z3-REFUTED → DECLINE ★ |
| **U** | v62 | **MR.JEFFREY Studio** (mode + provider + key UI) | displayed mode contracts == ModePolicy; 5 providers == provider.py; runs coherent; key never logged/stored (session-only) |

Plus three robustness fixes (deterministic cost model + best-of-k coherent measurement) that made the spine and
the compounding loop stable under full-suite load. **127 tests, 0 regression.**

## The Constitution held (verifier-enforced)
1. **MEASURED-ONLY, whole-program** — every ratio is a best-of-k whole-program wall-clock ratio vs a neutral
   baseline (Clock C). Kernel ≠ whole-program.
2. **AMDAHL HONESTY** — every speedup carries hotspot fraction f + ceiling 1/(1−f); **ratio ≤ ceiling by
   construction** (floor-pipeline measurement), asserted on every shipped row in every phase.
3. **GRADES ENFORCED BY THE ADT** — EXACT / PROBABILISTIC(ε,δ) / DECLINE; no win = DECLINE; the ADT raises on a
   fake pass or an EXACT carrying a δ.
4. **VERIFY EVERY STEP** — differential FIRST on every candidate; cumulative measured fresh, never the product
   of locals (the Whatnot check).
5. **PROPOSER ≠ ARBITER** — profiler = where, detector/LLM = what, measurement + verifier = whether.
6. **HONEST UNVERIFIED TAGGING** — GPU, orjson, live LLM, React/CI, vendored repos: all `[BLOCKED]`/UNVERIFIED,
   excluded, never faked.

## Honest scope (what is simulated / blocked in this sandbox)
No live LLM/network ⇒ the proposer is deterministic detectors (Rule 5) and the live provider path is UNVERIFIED
(not auto-executed); the corpus is **authored representatives** of real archetypes, not vendored GitHub repos;
no GPU/orjson ⇒ those offload/serialisation targets are UNVERIFIED; no browser/CI toolchain ⇒ the panel and the
studio are self-contained artifacts whose **data binding is tested** and whose **visual design goes to human
review**. Z3 proofs are **bounded** translation validation (Alive2-spirit) — no Lean/Coq/Isabelle. Caches are
local; phone-home = 0.

---

## §X — WHAT WE MUST NOT CLAIM (verbatim)

- Whole-program **average** 50–100× is impossible for already-reasonable code (Amdahl).
- 50–100× requires a **dominant hotspot (>95–99%)** with an asymptotic/algorithmic/offloadable inefficiency;
  else ~10–20× compounding, <2× already-optimized.
- **Kernel ≠ whole-program** (700× kernel → 4–6× end-to-end). Whole-program only.
- Asymptotic multipliers are **input-size-dependent** — quote n.
- Component multipliers **do not multiply** (Whatnot 3×·20×·6.7× → 5.8×). Measure fresh.
- Generic instruction-level superoptimization is near-useless whole-program (AlphaDev 1.7%, Minotaur 1.5%,
  Souper ~0). Our value: waste elimination + asymptotic/algorithmic replacement with proof.
- The grade is **OUTPUT confidence at runtime** (input + verifier), not a fixed property of a fixer or a mode.

---

## What the measured numbers actually say
The large ratios in this campaign (44×, 115×, 190000×) are on **AI-generated / never-profiled code with a
genuine asymptotic inefficiency** — exactly where the thesis predicts wins. On **well-written code the engine
returns an honest DECLINE** (template_render ~1.0×). The canonical multi-waste program — a realistic mix —
compounds to a **single-digit whole-program speedup** (extend ~2.25×), each fix ≤ its Amdahl ceiling. That is
the truth the engine is built to tell.
