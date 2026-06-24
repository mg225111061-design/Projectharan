# CODE TOTAL UPGRADE — running log

CODE is the total focus: absorb the MATH engine as optimization+verification weaponry, enforce strict
fast/normal/extend roles with concrete TIME BUDGETS, stream every step to the UI, and upgrade CODE's substance
by orders of magnitude — measured, certificate-bearing, honest. This is a running log (not a stop signal); each
entry is a shipped, suite-green, pushed item on branch `claude/charming-brahmagupta-q4wwgh`.

Builds on the completed MATH work (G1–G4, P1–P9, transforms, decision procedures, in-house SMT, broth) — that
work is NOT deleted; it is the engine CODE now wields.

---

## §1 (CORE) — fast / normal / extend as ENFORCED TIME-BUDGET roles

The three tiers are DISTINCT roles with DISTINCT wall-clock budgets and DISTINCT guarantees — not speed presets.

| tier   | budget (TOTAL wall-clock) | role | solver | grade contract |
|--------|---------------------------|------|--------|----------------|
| fast   | **~1 s**                  | one safe win now; quick, may defer | NEVER calls the heavy solver (MICRO tier) | EXACT or honest fast PROBABILISTIC |
| normal | **~30 s**                 | standard verified within budget | differential + small-region Z3 (CHEAP_CERT) | EXACT-or-DECLINE within budget |
| extend | **~8 min (BOUNDED)**      | deepest work that fits in 8 min | full Z3/SMT + in-house SMT (FULL_CERT) | EXACT-or-DECLINE; best certified within budget |

**The headline change: extend is BOUNDED at ~8 minutes (480 s), NOT unlimited.** It was previously
`latency_budget_s=None` ("unbounded / overnight"). Now, when the 8-minute budget is spent, extend returns the
BEST CERTIFIED result it reached (or an honest partial — "couldn't close within the extend budget; here is what
is proven + what remains"). It NEVER runs past the budget, NEVER fakes a result to fill the time, and NEVER
weakens a grade to go faster.

**Contract vs runtime.** `pillar3/mode.py` (`ModePolicy`) is the executable contract — the source of truth for
each mode's `latency_budget_s`. `mode_budget.py` is the enforcement runtime:
- `TimeBudget` — a live deadline (elapsed / remaining / fraction) plus a `display()` line the UI renders
  (`extend · 3:12 / 8:00`).
- `run_under_mode_budget(mode, work)` — runs `work` under the mode's TOTAL budget with the existing
  `latency_budget.run_with_budget` daemon-thread watchdog as the HARD backstop (the pipeline can never hang past
  budget). Returns `WITHIN_BUDGET`, or `DEFERRED_PARTIAL` carrying the best CERTIFIED result `work` actually
  offered (a `Partial` holder) — an honest partial, never fabricated, never relabeled EXACT.

**Wired into the real engine path.** `webapi/engine_bridge.run_optimize` now runs `pillar3.engine.optimize`
UNDER the mode budget and surfaces a `budget` block (tier, budget_s, elapsed_s, status, `display`) in its
response — the data the live UI (§3) shows. Measured: the engine closes in ~44 ms (fast) / ~61 ms (normal) /
~122 ms (extend) on a representative wasteful input, all far within budget; the watchdog only fires on a
pathological hang.

**Enforced as per-commit tests** (`test_mode_budget_roles`, `test_phaseM1_mode_policy`):
- the three budgets are 1 / 30 / 480 s, strictly ordered, all bounded (extend is **not** `None`);
- fast (MICRO) provably never invokes the solver (`tier_allows_certificate(MICRO,·) is False`);
- a runaway task that would `sleep(5)` is abandoned at a 0.2 s budget in < 1.5 s (no hang) and returns its
  honest best-so-far partial WITHOUT being relabeled EXACT (grade not weakened to look complete);
- grades differ by tier on the REAL engine: the list-as-set fix (a differential/PROBABILISTIC win) is SHIPPED
  in fast but DECLINEd in extend (EXACT-or-DECLINE) — the same code, distinct roles;
- the live UI line renders `extend · 3:12 / 8:00`.

---

## §2 (ABSORB MATH) — decision-procedures-as-analysis: prove whether a loop has a closed form

The MATH decision procedures become CODE's loop-analysis weaponry. For an accumulation loop
`for k in range(lo, n): acc += f(k)`, `loop_decision.decide_sum_collapse(f, k, lo)` DECIDES — with a certificate
either way — whether `Σ_{k=lo}^{n} f(k)` collapses to a closed form:

- **GOSPER is a COMPLETE decision procedure on hypergeometric terms** (rational functions included). A closed
  form ⇒ the O(n) loop becomes an O(1) closed form, which we then DIFFERENTIAL-gate against the brute-force
  partial sums (OUR certificate — a Gosper answer is never emitted unless it reproduces the real sum). Measured:
  Σk² → `n(n+1)(2n+1)/6`, Σk³ → `n²(n+1)²/4`, Σk·2ᵏ → `2·2ⁿn − 2·2ⁿ + 2`, Σ1/(k(k+1)) → `n/(n+1)`, all
  re-verified vs ground truth.
- **A Gosper `None` on a hypergeometric term is a PROOF that no hypergeometric closed form exists** — so the loop
  is genuinely irreducible: a FIRST-CLASS PROVEN DECLINE ("this loop has no closed form"), not a give-up. The
  harmonic Σ1/k and Σ1/k! are decided irreducible (Σ1/k cross-checked by ABRAMOV — NOT_RATIONALLY_SUMMABLE —
  for defense in depth). The loop correctly stays as-is.
- **Outside the hypergeometric class** (e.g. Σ(2ᵏ+3ᵏ), not a single hypergeometric term) we return UNDECIDED and
  make NO "no closed form" claim — honest scope.

This is the moat: "this loop cannot be collapsed" is PROVEN by a complete decision procedure, not guessed; and a
collapse ships EXACT only behind our own differential certificate. A wrong closed form is never emitted (the gate
rejects it — tested with a deliberately-wrong `n³` vs Σk²); a wrong "irreducible" would be a correctness bug.
`loop_decision.py`, `test_loop_decision`.

**Wired into the live CODE source-analysis layer.** `structure_recognizer.decide_loop(source)` runs this decision
on a recognized Σ-accumulation loop in the user's actual code (it reuses the existing `_closed_form_loop`
extractor). It is ADDITIVE — it complements `dispatch`'s fold-offload without changing it (so the harmonic loop
`for k in range(1,n): acc += 1/k` is decided PROVEN-irreducible, and `acc += k*k` collapses to the verified
`n(n+1)(2n+1)/6`), and returns None outside the Σ-class (a product loop, glue code) — never a false verdict.
(Next: stream this verdict to the UI per §3.)

---

## §3 (STREAM EVERY STEP) — the live CODE process trace

The UI must show EVERY step of what CODE is doing, live — not just the final result. `code_stream.iter_code_trace`
is a GENERATOR that yields ordered phase records AS each real step completes, mirroring MATH mode's
ROUTE / RECOGNIZE / KERNEL / 증명서 transparency:

> `ANALYZE` 분석 중… → `RECOGNIZE` 구조 인식 중… → `APPLY` fold/결정 절차 적용 중… → `CERTIFY` 증명서 생성 중… →
> `VERIFY` 검증 중 (in-house SMT / 차분 등가성)… → `RESULT` grade + 증명서

Each record carries the **live tier + budget line** (`extend · 3:12 / 8:00` — the BOUNDED ~8 min, never
"unlimited"), and the §2 decision is surfaced live (a harmonic loop streams `결정 절차… 닫힌형 없음 증명 → PROVEN
DECLINE`). The SSE frames reuse the frontend's existing `data:` event channel, so the steps render progressively.

**Honesty invariant (tested).** The displayed grade EQUALS the engine's actual grade — `test_code_stream`
re-derives the real verdict and asserts the streamed RESULT grade/certificate match it verbatim (the harmonic
loop's PROVEN-DECLINE grade is the EXACT decision; the list-as-set win's grade is the engine's real PROBABILISTIC).
Never fabricated progress: an undecided step says so (`아직 닫히지 않음`) rather than inventing a result.
`code_stream.py`, `test_code_stream`.

**Wired end-to-end.** `server.py` exposes `POST /api/optimize/stream` — an SSE endpoint that yields each phase
frame as `iter_code_trace` produces it (the route is registered and the frame stream verified). `mrjeffrey.html`
opens it over `fetch`+`ReadableStream` (`runOptimizeStream`) and renders a **live process panel** that fills in
step-by-step as the engine works — phase · message, the tier·예산 pill (`extend · 0:03 / 8:00`), and the
grade+증명서 — mirroring MATH mode's reasoning display. The frontend JS passes `node --check`; the visual is HUMAN
review per §X. So the user now watches the real CODE process unfold live, not just the final number.

---

## §4 (generated-code speed) — a DECIDED closed form → a MEASURED, Amdahl-honest speedup

`loop_decision.measure_collapse_speedup` turns a §2 closed-form decision into a MEASURED whole-program speedup,
honestly framed. The accumulation loop IS the function, so it times the naive O(n) loop vs the O(1) closed form at
a stated n — a whole-program speedup FOR THIS FUNCTION (f = 1). Measured: `Σk²` collapses ~**5000×** at n = 30 000
(naive ~2 ms → closed ~0.4 µs), grade EXACT. The honest limits are stated in the certificate, verbatim, every
time: the ratio is MEASURED at n and **GROWS as O(n)** (never an average, never a guarantee); if the loop were
only 50 % of a larger program the whole-program speedup would be ≤ the **Amdahl** ceiling; and it is
**DOMAIN-CONDITIONAL** — closed-form-able loops only, near-zero on general/control-flow code, never a
general-purpose accelerator. SOUND: the speedup is reported only after the closed form is re-verified == the loop
AT the measured n (a mismatch DECLINEs — never a wrong "speedup"); the harmonic Σ1/k has no closed form, so it
honestly DECLINEs (nothing to measure). Per C6 the magnitude is `perf_obs` (informational), not a hard gate — the
gate is soundness + the honest-limit certificate. `test_loop_speedup`.

**Surfaced live (§3 tie-in).** `code_stream` streams the collapse end-to-end: a closed-form loop now emits a live
`속도향상 실측 중… O(n) 루프 → O(1) 닫힌형 (n=…)` step with the measured ratio + the §X limits, and the RESULT
reports the proven O(1) collapse (`O(n) 루프 → O(1) 닫힌형 n(n+1)(2n+1)/6 — 증명된 붕괴`, grade EXACT) rather than
"no fix". So the user watches the proof AND the measured speedup unfold live.

---

## §4 (ceiling-breaker) — linear-recurrence loop → O(log n) companion collapse, verified + measured

A new ceiling-breaker class: an O(n) state-update loop computing a C-finite sequence (Fibonacci/Pell/tribonacci/…)
collapses to an O(log n) companion-matrix form. `loop_recurrence.decide_recurrence_collapse(source)` decides it
SOUNDLY without parsing the transition algebra: it SAMPLES the user's f(0..N), FITS the shortest exact integer
recurrence (`mathmode.ingest.find_recurrence`, Berlekamp-style), and — the sound gate — VERIFIES
`cfinite.companion_nth(c, init) ≡ the user's ACTUAL loop on HELD-OUT n` (beyond the fit window) and at the
measured n. A wrong fit is rejected ⇒ DECLINE (never a wrong collapse). Measured: Fibonacci O(n) loop → O(log n)
companion `c=[1,1]` **~6× at n = 50 000** (naive ~21 ms → ~3.5 ms), grade EXACT; Pell `c=[2,1]` recognized;
factorial / non-integer loops are NOT C-finite ⇒ honest DECLINE (keep the loop).

Honest framing in the certificate, verbatim: the collapse MEASURABLY wins when the sequence values GROW (bigint
blowup makes the O(n) loop's per-step cost rise — Fibonacci-like); machine-int-bounded sequences stay cheap so the
verified collapse may NOT beat the loop at a given n (`measured_win` is reported truthfully, never assumed). The
loop IS the function (f = 1) ⇒ whole-program FOR THIS FUNCTION; embed it in a larger program and the speedup is ≤
the **Amdahl** ceiling; **DOMAIN-CONDITIONAL** — C-finite sequences only. Per C6 the magnitude is `perf_obs`; the
hard gate is the verified equivalence + the honest-limit certificate. `loop_recurrence.py`, `test_loop_recurrence`.

**Surfaced live (§3 tie-in).** `code_stream` streams the recurrence collapse too: a Fibonacci-style loop shows
`선형 점화식 인식 중: O(n) 상태-갱신 루프 → O(log n) 동반행렬 (order=2, c=[1,1])`, a CERTIFY step
`동반형 ≡ 루프, held-out n 검증 · 3.8× 측정 win`, and a RESULT `O(n) 점화식 루프 → O(log n) 동반형 — 증명된 붕괴`
(grade EXACT). So both the §2 sum-collapse and the §4 recurrence-collapse unfold live in the UI.

**First-class in the optimize RESULT (not only the stream).** `engine_bridge.run_optimize` now carries a structured
`collapse` field — the PROVEN loop collapse the canonical-fix engine doesn't cover: a Σ-loop → O(1) closed form
(or PROVEN-irreducible), a C-finite state-update loop → O(log n) companion (with the measured ratio), each with
its grade + certificate, or `None` when none is proven (honest, never fabricated). The static verify panel renders
it as a "루프 붕괴 (결정 절차)" card. `test_run_optimize_collapse`. So the proven collapse is part of the actual
result, programmatically consumable, not just narrated in the live trace.

**Budget-bounded (§1 enforcement extended).** The collapse analysis EXECS and TIMES the user's loop (sampling,
`f(n)`), so it is bounded by the mode budget (fast 0.5 s / normal 2 s / extend 5 s) via the daemon-thread watchdog:
a pathological loop whose VALUE is C-finite (the fit succeeds) but whose per-call COST is slow returns `None`
within budget rather than hanging the response — fast never blocks on user code, and a partial is never fabricated.
A normal loop still collapses well within budget (no false negative). `test_loop_collapse_budget_bounded`.

---

## §4 (correctness) — in-house SMT broadened: prove strength reductions VALID

The ZERO-DEPENDENCY in-house bit-blasting SMT (`bitblast_smt.py`, no coqc/cvc5/Bitwuzla/Lean/Z3) gained general
`w×w` multiply and logical/arithmetic right-shift, so the engine can now PROVE the strength-reduction transforms
it wants to ACCEPT (not merely refute them), with zero external solver. `prove_strength_reductions()` decides 8
identities VALID (UNSAT of the negation over the whole w-bit domain, EXACT within stated width): `mul8 ↔ shl3`,
`general_mul == mul_const`, the branchless sign-mask `ashr(x,w-1) == neg(lshr(x,w-1))`, the shift round-trips
that clear low/high bits, and the ×-ring laws (commute / associate / distribute). The multiplier still produces a
REAL refutation — `x·x == x` is INVALID with a checked counterexample — so it is never a false VALID. Honest
scope unchanged: still NOT cvc5/Z3 parity — no division, no variable-amount shift, no ite-mux, no
arrays/reals/unbounded ints (those stay on Z3).

---

## §4 (ceiling-breaker) — MODULAR linear recurrence → O(log n): the case where O(log n) genuinely wins

The non-modular recurrence collapse is verified but only modestly faster (bigint multiplies eat the asymptotic
win). The MODULAR case — `f(n) mod M`, the common Fibonacci/Pell-mod kernel in competitive programming and crypto
— is where O(log n) **genuinely wins**: the modulus keeps ints BOUNDED, so the companion-matrix power is true
O(log n) ring work. `loop_recurrence.decide_modular_recurrence_collapse` detects M from the loop's `% M`, fits the
recurrence from the early (unwrapped) samples, and — the sound gate — VERIFIES `cfinite.companion_nth_mod ≡ the
user's ACTUAL loop on HELD-OUT n WHERE IT HAS WRAPPED` (so the modular behaviour, not just the prefix, is checked).
Measured: `Fib(n) mod (10⁹+7)` → **~58× at n = 100 000** (naive ~4 ms → companion-mod ~68 µs), grade EXACT;
Pell-mod `c=[2,1]` → ~80×. A small modulus (early values wrap → no clean fit) and a non-modular loop DECLINE
(honest). `cfinite.companion_nth_mod` (mod inside power-by-squaring), `test_modular_recurrence_collapse`. Honest
limits in the cert verbatim: f=1, Amdahl ceiling for embedding, DOMAIN-CONDITIONAL (C-finite modular recurrences
only); per C6 the magnitude is perf_obs, the gate is the held-out verification. It surfaces end-to-end:
`run_optimize`'s `collapse` field reports `kind=modular_recurrence` for a modular loop, so the proven O(log n)
modular collapse is part of the actual optimize result, not just the recognizer.

---

## §4 (soundness, adversarial) — attack spec fragility: zero wrong collapses

Spec fragility is the dominant failure mode, so we attack it directly. The headline attack: a loop that equals
Fibonacci ON the fit window (n < 30) but DIVERGES beyond it. The Berlekamp fit happily finds `c=[1,1]` — but the
collapse is **rejected** because `companion_nth ≠ the actual loop at held-out n=33` ⇒ DECLINE (no wrong O(log n)
collapse). This proves the held-out verification — not the fit — is the soundness authority. Conversely a genuine
C-finite loop still COLLAPSES (no false negative) and its companion form `≡` a fresh run of the loop. On the sum
side, `loop_decision` emits no wrong closed form (the differential gate rejects a deliberately-wrong `n²` for Σk)
and never falsely claims irreducible. `test_loop_collapse_adversarial`. A wrong "verified" would be a correctness
bug — these gates are what prevent it.

---

## §4 (fold coverage) — MEASURED, domain-conditional loop-collapse coverage

A capstone metric that quantifies the loop-collapse capability honestly, exactly as the MATH §7 benchmark reports
measured coverage (never a fabricated score). `loop_collapse_bench.run()` runs a representative corpus of 13 loops
through the unified §2/§4 collapse decision and grades each: **COLLAPSE 8** (Σk/Σk²/Σk³/Σk·2ᵏ/Σ1/(k(k+1)) → O(1);
Fibonacci/Pell/Lucas → O(log n)), **PROVEN-IRREDUCIBLE 2** (Σ1/k harmonic, Σ1/(k²+1) — a first-class "no closed
form"), **honest DECLINE 3** (factorial Π, Σ(k mod 3) non-hypergeometric, glue — outside the decided class).
**13/13 matched the expected classification; all 10 decided rows carry an EXACT certificate.** The report states
verbatim that this is the MEASURED share of a STRUCTURED corpus — DOMAIN-CONDITIONAL by construction, NEVER a
general-purpose-accelerator claim (the DECLINEs are correct behaviour, not failures). `test_loop_collapse_coverage`.

---

## §X — WHAT WE MUST NOT CLAIM (verbatim)

- fast/normal/extend are distinct roles with TIME BUDGETS (~1s/~30s/~8min); extend is BOUNDED at ~8 minutes,
  NOT unlimited — never described as "time doesn't matter"; it returns the best certified result within budget or
  an honest partial, never fakes to fill time, never weakens a grade to go faster; fast never calls the heavy
  solver.
- EXACT only with a machine-checked certificate / decision procedure; a verified-equivalence speedup ships EXACT
  only with its certificate; otherwise UNVERIFIED or DECLINE; a wrong "proven" is a correctness bug.
- Coverage gains are DOMAIN-CONDITIONAL (near-zero on general/control-flow/graph code) and the ceiling is a
  CEILING not a guarantee (Amdahl p per kernel); never imply a general-purpose accelerator.
- Whole-program/measured for EVERY speed claim; kernel ≠ whole-program; no average 50–100× claims; ratio ≤
  Amdahl ceiling.
- The UI shows the REAL process (actual tier, actual fold, actual proof step, actual budget elapsed) — never
  fabricated progress.
- Reuse of a verified backend is fine but the certificate is ours and co-generated; never imply a
  formal-verification level the implementation lacks; decision-procedure-correct ≠ proof-assistant-verified.
- Never "smarter/faster than a model"; wraps LLMs and adds proven correctness + speedup where structure
  genuinely exists.
