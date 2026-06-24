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
`code_stream.py`, `test_code_stream`. (Next: wire the SSE endpoint + frontend rendering — the visual half, HUMAN
review.)

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
