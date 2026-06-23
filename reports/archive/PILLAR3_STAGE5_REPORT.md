# Pillar 3 · Stage 5 (v53) — GPU/SIMD offload, Amdahl-gated · + the Pillar-3 verification panel

The stage where Rules 1 & 2 are enforced hardest: a kernel speedup is **not** a whole-program speedup, and
the system must say so *before* it offloads anything.

## Delivered
- `pillar3/offload.py` —
  - `amdahl_gate(f, min_speedup)` → `(worth, ceiling=1/(1−f))`. The system states its own ceiling **before**
    attempting the offload (Rule 2).
  - `consider_offload(...)` — **Amdahl-gate FIRST**: if the kernel does not dominate, it DECLINES *without
    offloading* — no false big number — **even for a 700× kernel**. GPU device ⇒ UNVERIFIED DECLINE (absent in
    sandbox, excluded from auto-apply, Rule 6). Otherwise: differential-verify (Rule 4) → measure the
    **WHOLE-PROGRAM** ratio (never the kernel ratio, Rule 1) → grade PROBABILISTIC(δ=3/n).
- `pillar3_panel_gen.py` — the panel-data generator. Runs the **real** engine (fixers · compounding loop ·
  equivalence certificate · offload · global transforms) on demo programs and serialises genuine reports to
  `pillar3_panel_data.json`. No hand-edited numbers; the grade on every row is the grade the engine returned.
  Each measured demo carries a **timed residual** (non-hotspot section), so `f`, the ceiling, and the ratio are
  mutually consistent — **ratio ≤ ceiling by construction** (the residual is clamped to ≤ the fully-fixed time,
  which physically contains it). A generation-time self-check asserts Amdahl coherence on every row.
- `pillar3_panel.html` — the Pillar-3 verification panel. Reuses the "Certificate" design language; the central
  motif is the **Amdahl gauge**: each row's whole-program ratio fills toward a ceiling line it is forbidden to
  cross, so "kernel ≠ whole-program" is *visible*. Shows waste type, grade badge, whole-program ratio, hotspot
  `f`, ceiling, n, orig→cand ms, δ, certificate, the compounding curve, the three clocks, and a "what we must
  not claim" section. Binds to the real JSON (labelled real-run snapshot island as offline fallback).

## Measured / verified (the Stage-5 test + the panel test)
- Amdahl gate: ceiling **50.0×** @ f=0.98 → PASS; ceiling **1.67×** @ f=0.40 → FAIL.
- **dominant** SIMD offload (sin·cos+√ → numpy), n=60000: **~1.9× whole-program** (ceiling 50×, δ=3/30=0.10)
  → PROBABILISTIC. The number reported is whole-program, **not** the kernel's vectorization factor.
- ★ **a 700× kernel that is only 40% of runtime → DECLINE** — "offload not worth it: Amdahl ceiling 1.67× < 2×"
  (the whole point of the stage; not a big number, an honest refusal). ★
- GPU offload → **UNVERIFIED**, auto-apply-excluded (no GPU in sandbox).
- Panel: binds 12 real verdicts (all three grades); the **displayed grade == the engine's grade** (offload@40%,
  GPU, Horner-EXACT, wrong-Horner-DECLINE all re-run and compared); **every measured row is Amdahl-coherent**
  (ratio ≤ ceiling); HTML well-formed with the structural anchors and the three clocks.

## §0 self-check
1. whole-program measured ratio? yes — offload reports `measure_whole_program`, never the kernel factor.
2. carries hotspot + ceiling? yes — the gate computes and shows `1/(1−f)` before acting; the panel renders it.
3. graded + ADT raise? yes — PROBABILISTIC carries δ; DECLINE carries the Amdahl reason; grade ADT enforced.
4. differential at each step? yes — offload differential-verifies before measuring (and DECLINEs on divergence).
5. UNVERIFIED tagging? yes — GPU is UNVERIFIED/excluded; orjson is the UNVERIFIED production target.

## Honest scope
No GPU and no orjson/msgpack in the sandbox ⇒ those paths are tagged UNVERIFIED and excluded from auto-apply
(SIMD/numpy and stdlib marshal are the verified demonstrations). The panel is a self-contained artifact; the
full React+TS design-system build with CI visual/a11y/perf gates is `[BLOCKED: toolchain]` — visual quality
goes to human review, and what is *tested* is the real data binding. **118 tests pass, 0 regression.**
