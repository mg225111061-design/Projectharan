# PILLAR 3 — The Whole-Program Verified Speedup Engine (v48 → v53)

> Make ordinary, unstructured code faster by finding and eliminating accidental waste — and **prove** every
> fix preserves behaviour. The product is *faster code you can trust*, measured at the **whole-program** level
> and graded by a verifier, never by a label.

You slept; it drove. Stages 0–5 were built one at a time, each measured honestly, verified, graded, and
pushed. **118 tests pass, 0 regression.**

---

## The Constitution (six rules, non-negotiable) — and where each is enforced in code

1. **MEASURED-ONLY, whole-program.** Every ratio comes from `pillar3/measure.py`, a warmup-aware median
   wall-clock ratio of the *whole program* (Clock C). `SpeedupReport` **refuses to exist** without `n` and
   `hotspot_fraction`. A 700× kernel that yields 1.9× end-to-end is reported as **1.9×**.
2. **AMDAHL HONESTY.** Every report carries the hotspot fraction `f` and the ceiling `1/(1−f)`. The offload
   gate (`pillar3/offload.py`) computes and states the ceiling **before** acting and DECLINEs when it is too
   low. The panel renders a gauge that fills toward the ceiling and is forbidden to cross it.
3. **GRADES ENFORCED BY THE VERIFIER.** `kernel_verdict.Verdict.__post_init__` raises unless a non-DECLINE
   carries a *passed* certificate whose grade matches; PROBABILISTIC must state δ; EXACT may not carry a δ. A
   fix with no whole-program win is **DECLINE**, never "EXACT 1.0×".
4. **VERIFY EVERY STEP.** Differential testing (`pillar3/record.py`) runs *first* on every candidate; a
   divergence is DECLINEd and never chained. Algorithm swaps add Z3 bounded translation validation
   (`pillar3/equiv.py`).
5. **THE PROPOSER IS A CLASSIFIER, NOT THE ARBITER.** Detectors (`pillar3/fixers/detectors.py`,
   `pillar3/recognize.py`) only *propose*; the profiler is ground truth and the verifier decides. (No live LLM
   in the sandbox ⇒ the proposer is realized as deterministic structural detectors — which is exactly Rule 5.)
6. **HONEST UNVERIFIED TAGGING.** What can't be verified here (GPU, orjson/msgpack, the React+CI design build)
   is tagged UNVERIFIED and **excluded from auto-apply** — never faked into a pass.

### Three clocks, never mixed
- **Clock A** — proposer latency (a deterministic detector here).
- **Clock B** — verification throughput (differential + Z3; measured; must be ≪ the kernel it certifies).
- **Clock C** — emitted-code runtime — *the product*. Every speedup ratio in this campaign is Clock C.

---

## What was built, stage by stage

| Stage | Commit | What it is | The verified claim |
|------:|--------|------------|--------------------|
| 0 (v48) | `90661cb` | profiler · neutral-baseline measure · complexity fitter (trend-prof) · I/O recorder | foundation: measure refuses a ratio without n+ceiling; fitter recovers O(n)…O(n³); profiler ranks the real hotspot |
| 1 (v49) | `6b600da` | the four highest-leverage fixers: list-as-set, uncached recompute, accidental-quadratic, N+1 | each verify→measure→graded; **a wrong fix is caught → DECLINE** (Rule 4 safety net) |
| 2 (v50) | `72a5de3` | iterative compounding loop + diminishing-returns controller | cumulative = a **fresh** end-to-end measure ≈ independent re-measure; **≠ the product of local multipliers** (Whatnot check) |
| 3 (v51) | `4267f6c` | cross-cutting global transforms: async/batch I/O, serialization swap, compile-numeric | the **flat-profile killer**: a global transform beats local fixing where no hotspot dominates |
| 4 (v52) | `6523034` | algorithm recognition + the **Z3 equivalence certificate (the moat)** | Horner ≡ naive **Z3-proven → EXACT**; ★ a wrong Horner *and* a wrong matmul swap are **refuted → DECLINE** ★ |
| 5 (v53) | *(this)* | GPU/SIMD offload, **Amdahl-gated**, whole-program-honest + the Pillar-3 verification panel | dominant SIMD → PROBABILISTIC whole-program win; **a 700× kernel @40% → DECLINE** (ceiling 1.67×); GPU → UNVERIFIED |

### §5 DONE criteria
- **The moat test passes** (Stage 4): a wrong fast swap is caught — differential FAILED **and** a Z3
  counterexample — and graded DECLINE. This is what makes a verified speedup engine more than a rewriter.
- **The compounding honesty test passes** (Stage 2): the cumulative whole-program number equals a fresh
  end-to-end measurement, not the (far larger, false) product of component multipliers.
- **Every stage: 0 regression.** 118 tests, all green.

---

## The headline, honestly stated
- The **kernel** speedups inside these fixes are large (the dedup goes O(n²)→O(n); memoize zeroes a recompute;
  numpy vectorizes sin/cos/sqrt by a big factor).
- The **whole-program** results are modest and **bounded by Amdahl** — typically **2×–7×** here, each sitting
  just under its measured ceiling — *because that is the truth*. The panel shows the gauge approaching, never
  crossing, the ceiling.
- The compounding loop reaches **~13× end-to-end** by fixing several stages — and we prove that number is a
  fresh measurement, **not** the ~3000× you would get by (wrongly) multiplying the local speedups.

---

## §6 — WHAT WE MUST NOT CLAIM

These are the claims a speedup engine is tempted to make and **must not**. They are enforced by the rules
above, asserted in tests, and printed on the panel.

1. **No "50–100× on average, whole-program."** Amdahl forbids it. A fix that touches fraction `f` of the
   runtime is capped at `1/(1−f)`; to *average* 50× you would need almost every program to be almost entirely
   one fixable hotspot, which is not how real programs look. Whole-program speedups are usually single-digit.
2. **A kernel speedup is NOT a whole-program speedup.** A 700× kernel inside 40% of the runtime is at best a
   1.67× program. We report the whole-program number and DECLINE the offload when the ceiling is too low —
   *even when the kernel number is spectacular*.
3. **Component multipliers do NOT multiply.** Speeding up three stages by 10×, 20×, 5× does **not** give
   1000×; it gives whatever a fresh end-to-end measurement says (here ~13×). Reporting the product is the
   "Whatnot fallacy"; we surface the product **only to refute it**.
4. **Instruction-level superoptimisation is near-useless at whole-program scale.** Shaving a few instructions
   off a basic block does not move Clock C; the leverage is in algorithms, data structures, I/O, and
   serialization — the global picture, not the peephole.
5. **A faster-but-different program is a regression, not a speedup.** A fix with no machine-checked
   equivalence (proof or differential) is never auto-applied. A wrong fix that happens to be faster is
   **DECLINE**, not a win.
6. **"EXACT" is not a synonym for "ran without error."** EXACT requires a proof or by-construction identity;
   sampling earns at most PROBABILISTIC(δ=3/n); no whole-program win earns DECLINE — never "EXACT 1.0×".
7. **We do not claim what we cannot verify here.** GPU offload, orjson/msgpack, and the full React+CI design
   build are `UNVERIFIED [BLOCKED]` and excluded from auto-apply — tagged honestly, not shipped as passes.

---

## Honest scope / what is simulated
No live LLM (no API key) ⇒ the proposer is deterministic structural detectors (Rule 5 — the LLM was never the
arbiter). No GPU and no orjson/msgpack ⇒ those offload/serialization targets are UNVERIFIED and excluded;
numpy (SIMD) and stdlib `marshal` are the verified demonstrations. No browser/CI toolchain ⇒ the verification
panel is a self-contained artifact whose **data binding is tested** and whose **visual design goes to human
review**. No Lean/Coq/Isabelle — equivalence is Z3 bounded translation validation only. Caches are local;
phone-home is 0.
