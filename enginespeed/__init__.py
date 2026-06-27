"""
§V — FOLD THE ENGINE ITSELF: make MR.JEFFREY insanely fast by putting fold everywhere (sound caching).
================================================================================================================
The same weapon that pre-proved thousands of obligations offline and served them at O(1) is now turned INWARD on the
engine's own repeated work — detection, verification, folding, proof, AST analysis, and the LLM prompts. Every repeated
operation becomes a provably-sound lookup: compute each distinct piece of work ONCE, serve every re-encounter at O(1).

★THE HONESTY SPINE (binding, read first — the two speeds, never conflated):
  • The LLM's own latency is NOT reducible — only its call COUNT is. Opus is an external provider; we cannot make one
    call faster, only call it FEWER times (the verified response cache). When an LLM call is on the critical path no
    amount of engine-folding moves the total (Amdahl) — so cutting calls is the only honest attack on LLM latency.
  • The ENGINE's own work IS foldable — detection/verification/folding/proof/AST repeat on similar inputs. Fold them.
  • COLD vs WARM is the honest frame. A cold cache gives ZERO speedup (the first run computes everything). The wins are
    on WARM caches, on repeated work. Cold and warm are reported SEPARATELY — never a warm number as a first-run number.
  • Precision = 1.0 survives caching — a hit is served only when the key PROVABLY identifies the same computation
    (content hash, or a proved-canonical form). A wrong/stale hit is a correctness violation that FAILS the build.
  • Measured-only, three clocks never mixed (A=LLM call-count, B=verification, C=the fold/lookup speedup), zero deps.

Modules: profile · cache · folded_ops · brewing · speed_report. Engine zero-dep; never imported by test_build.
"""
