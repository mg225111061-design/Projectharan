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

**Decide-only + synchronous (fork-safe).** In the optimize RESULT path `_loop_collapse` DECIDES the collapse
(sample → fit → held-out verify) WITHOUT timing the user's loop — so it is fast and spawns NO threads. (An earlier
timing-under-a-daemon-watchdog design left a thread alive executing slow user-code and could DEADLOCK a later
`multiprocessing.fork` — a real regression, now fixed and gated by `test_loop_collapse_fork_safe`: after a collapse
the live thread count does not increase and a `multiprocessing.Pool` runs without hanging.) Soundness is unchanged
— the held-out `companion ≡ loop` gate is kept — and the MEASURED ratio lives in the live trace (§3), a single
deliberate step, not on every optimize call. The result field carries the proof + certificate (no unmeasured
ratio).

---

## §4 (correctness) — in-house SMT broadened: prove strength reductions VALID

The ZERO-DEPENDENCY in-house bit-blasting SMT (`bitblast_smt.py`, no coqc/cvc5/Bitwuzla/Lean/Z3) gained general
`w×w` multiply, logical/arithmetic right-shift, ite-mux, a restoring **UNSIGNED + SIGNED divider** (`udiv`/`sdiv`,
shift/compare/subtract with the conditional subtract expressed as an ite-mux; sdiv = sign-magnitude wrapper round
udiv, truncating toward zero), AND a **VARIABLE-amount shift** (barrel shifter, ⌈log2 w⌉ ite-mux stages, total: a
shift ≥ w is 0 — no UB), so the engine can now PROVE the strength-reduction transforms it wants to ACCEPT (not
merely refute them), with zero external solver. `prove_strength_reductions()` decides 15 identities VALID (UNSAT of
the negation over the whole w-bit domain, EXACT within stated width): `mul8 ↔ shl3`, `general_mul == mul_const`, the
branchless sign-mask `ashr(x,w-1) == neg(lshr(x,w-1))`, the shift round-trips that clear low/high bits, the ×-ring
laws (commute / associate / distribute), the classic **DIV→SHIFT** `x // 2^k ≡ x >> k` (`udiv4_to_lshr2`,
`udiv2_to_lshr1`), the **MUL-BY-POWER-OF-TWO ↔ VARIABLE SHIFT** `x · 2^k ≡ x << k` for EVERY `k` (`shl_var=mul_pow2`
— barrel shifter cross-checked against the multiplier, overflow included), the **SIGNED DIV→SHIFT WITH ROUND-TOWARD-
ZERO BIAS** `sdiv(x,2^k) ≡ ashr(x + (ashr(x,w-1) ⋙ (w-k)), k)` (`sdiv_pow2_biased=sdiv` — the single most subtle
classic lowering, because the naive `ashr(x,k)` ALONE rounds toward −∞ and is WRONG for `x<0`), and — via the
**ite-mux (bit-select)** — **branchless CONDITIONAL tricks verified ≡ their if-then-else spec**: branchless abs
`(x ^ ashr(x,w-1)) − ashr(x,w-1) ≡ (x<0 ? −x : x)`, `mux(s,a,a) ≡ a`, `(x<0 ? −1 : 0) ≡ ashr`. The solver still
produces REAL refutations — `x·x == x` is INVALID, the divider is correct on a non-power-of-2 (`udiv(v,3) == v//3`)
while `x // 3 ≠ x >> 1` is REFUTED, `x << k ≠ x · k` is REFUTED, the **naive `ashr(x,k) ≠ sdiv(x,2^k)`** is REFUTED
with a NEGATIVE counterexample (proving the bias is mandatory), and the overflow-unsafe `(x+1) >ₛ x` is REFUTED
in-house at INT_MAX via ite-mux — never a false VALID. Honest scope: still NOT cvc5/Z3 parity — no
arrays/reals/unbounded ints (udiv/sdiv-by-zero and the sdiv INT_MIN/−1 overflow left unconstrained); the
overflow-unsafe peepholes stay out of the SOUND cross-check because they are UNSOUND (the in-house solver can now
DECIDE all three — incl. `mul2_div2_id` via sdiv — but the cross-check asserts PROVEN≡PROVEN, so only SOUND
peepholes participate). Signed compare, general multiply, right-shift, ite-mux, UNSIGNED+SIGNED division (udiv/sdiv),
and VARIABLE-amount shift (barrel shifter) ARE in-house now.

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

## §5 (HARAN / 50 algorithms) — an HONEST catalog over the absorbed arsenal: `algo50.py`

The HARAN campaign tracks **50 NAMED layer-1 algorithms** (20 foundational · 10 frontier · 15 number-theory ·
5 quantum/relativity). The honest framing (§0-A): these are 50 NAMED GENERAL ALGORITHMS — ≈15 truly-fundamental
plus specializations/applications — **NOT 50 fundamentally-distinct structures**. The first deliverable is the
SPINE: `algo50.py`, a single catalog that names all 50 and POINTS each into the real implementation already
living in the absorbed engine (`mathmode/` decision procedures, `pillar3/`, the root frontier kernels, the
`kernel_router` REGISTRY, the `sublinear_layer`, the `broth`). It re-implements nothing.

Its honesty is mechanical, not asserted: a per-commit test (`test_algo50_registry`) IMPORTS every non-GAP entry
point and asserts the named callable EXISTS — so "we have algorithm N" is a **re-checked fact**. The catalog
carries, per algorithm, the BEST grade (ADT: EXACT / PROBABILISTIC / DECLINE), the re-checkable certificate, the
TRUE complexity with the honest ceiling, the decision-procedure flag, the tier (fast/normal/extend), broth-
eligibility, and a status.

**Status (MEASURED, honest):** **50 CONFIRMED + 0 PARTIAL + 0 GAP** — every one of the 50 named algorithms is now
fully built, certificate-bearing, and adversarially tested (Groups A=20, B=10, C=15, D=5 ALL CONFIRMED). The 8
original gaps were each built one-per-commit (#45 Jacobi, #43 sieve, #32 power-towers, #34 Lucas/Granville, #14
Newton-series, #13 Bostan–Mori, #28 autodiff, #19 Gröbner); then all 9 partials were closed one-per-commit: #44
gained Möbius μ, #42 the Stern–Brocot tree, #29 fast multipoint evaluation, #36 the BPSW strong-Lucas component,
#39 Cipolla (cross-checking Tonelli), #40 Pollard-rho (cross-checking BSGS), #38 Pollard p−1, #17 a standalone
Hermite/Horowitz reduction, #25 exact CP rank-1 decomposition. Honest sub-variant caveats remain RECORDED where a
method is genuinely out of exact reach (Risch algebraic case; ECM; general CP/Tucker rank — NP-hard ⇒ certified-
numeric/DECLINE beyond rank-1) — stated, never faked. Grades: 47 EXACT-capable / 3 PROBABILISTIC (matrix-completion
#24, planted #26, sketches #27 — NEVER marked EXACT). Tiers: fast 10 / normal 31 / extend 9. The honest-complexity
caveats are RECORDED and
test-enforced: **CAD (#18) is doubly-exponential — NEVER O(1); Lucas–Lehmer (#37) is O(p)-iteration with a real
ceiling; the sieve (#43) is O(n log log n) enumeration, not a collapse.** Quantum/relativity (#46–50) is the exact
ALGEBRAIC layer only, each EXACT with a recorded exact-only caveat. The heavy decision procedures (Petkovšek, ΠΣ*,
Risch, CAD, Gröbner, Kovacic) are extend-tier — fast never hosts them. Broth measured live: **3,772 entries,
O(1) lookup ≈ 0.05 µs, all-hit** (the precomputed-lookup-fast mechanism — it does NOT make execution O(1)).
The GAPS are the work queue for the next items. `algo50.py`, `test_algo50_registry`.

**Gap-fills (one per commit, each general + certificate-bearing + graded + adversarially tested):**
- **#45 Jacobi symbol / quadratic reciprocity** → `mathmode.number_theory.jacobi_grade`. The O(log) reciprocity-
  flip value is CROSS-CHECKED against the independent definition ∏ Legendre(a|pᵢ) by Euler's criterion over the
  factorization (prime n ⇒ a single O(log) Euler check; composite n ⇒ the product) — two different algorithms must
  agree ⇒ EXACT, mismatch ⇒ DECLINE (a correctness-bug guard). Adversarially tested vs a brute-force quadratic-
  residue scan at 7 primes, full multiplicativity + period-n, the (2|n) supplement law, (1001|9907)=−1, gcd>1→0,
  even/invalid n→DECLINE. EXACT, tier fast, broth-eligible. `test_haran_jacobi_reciprocity`. (34 CONFIRMED now.)
- **#43 Sieve of Eratosthenes** → `mathmode.number_theory.sieve_primes_grade`. EXACT by construction, with a
  certificate verified TWO independent ways: SOUNDNESS (every returned prime re-checked by deterministic
  Miller–Rabin, not the sieve) + COMPLETENESS (full independent trial-division set-equality for n ≤ 30000, else
  the |result| = π(n) checkpoint). Beyond both it honestly DECLINES TO CERTIFY rather than stamp EXACT without a
  witness. HONEST: O(n log log n) ENUMERATION — not a collapse; the classic boolean sieve (segmented/wheel are
  constant-factor optimizations, not yet added). `test_haran_sieve_eratosthenes`. (35 CONFIRMED now.)
- **#32 Power towers via Carmichael-λ** → `mathmode.number_theory.power_tower_grade`. Computes a^(b^c) mod m by
  reducing the exponent with the generalized Euler theorem a^E ≡ a^((E mod λ(m)) + λ(m)) (mod m). EXACT, certified
  two ways: when E=b^c is formable the result is CROSS-CHECKED against direct `pow(a, E, m)`; when E is
  astronomically large the theorem applies (premise E ≥ ⌈log2 m⌉ verified, λ(m) independently validated by
  u^λ ≡ 1 on units). The test ground-truths the pure-theorem branch against a 200001-bit exponent. m<1/negatives →
  DECLINE; m unfactorable → DECLINE (can't certify λ). EXACT, tier fast, broth-eligible.
  `test_haran_power_tower_carmichael`. (36 CONFIRMED now.)
- **#34 Lucas' theorem + Granville lifting** → `mathmode.number_theory.binom_mod_pe_grade`. C(n,k) mod p^e by
  Lucas (e=1) / the Granville–Andrew prime-power method (n! = p^{v_p}·∏ g(⌊n/p^i⌋), Kummer valuation, unit part
  inverted mod p^e) — exact even for ASTRONOMICAL n. Certified two INDEPENDENT ways: full direct math.comb mod p^e
  for n ≤ 2000, and the mod-p Lucas digit-product for ANY n. Exhaustively matched against math.comb (n<60 across
  9 (p,e) incl. prime powers); astronomical C(10^18,10^9) mod p + C(10^18,12345) mod 3^7 cross-checked. Non-prime
  p / p^e>10^6 / negatives → DECLINE. EXACT, tier fast, broth-eligible. `test_haran_lucas_granville`. (37 CONFIRMED;
  **Group C complete.**)
- **#14 Newton iteration on power series** → `newton_series.newton_series_grade`. inv / sqrt / exp / log of a
  formal power series by Newton's method (quadratic convergence — precision doubles each step), EXACT over ℚ
  (`Fraction` coefficients). Each result is certified by its DEFINING IDENTITY verified exactly to the truncation
  order: A·B≡1 (inv), S²≡A (sqrt), exp∘log≡A (log), log∘exp≡A (exp). Cross-checked against the closed-form Taylor
  coefficients (1/(1−x)=Σxᵏ, exp(x)=Σxᵏ/k!, log(1+x)=Σ(−1)^{k+1}xᵏ/k). Precondition violations (A(0)=0 for
  inv/sqrt, ≠1 for log, ≠0 for exp, non-square A(0) for sqrt) are honest DECLINEs. This is the verified series-
  arithmetic core the GF kernels build on. `test_haran_newton_series`. (38 CONFIRMED now.)
- **#13 Bostan–Mori (GF coefficient extraction)** → `newton_series.bostan_mori_grade`. [x^n] P(x)/Q(x) by the
  halving recurrence (multiply by Q(−x) ⇒ even denominator ⇒ take even/odd numerator part, halve n) in
  O(M(d) log n) — astronomical n. EXACT over ℚ, certified two ways: a direct P·Q⁻¹ series cross-check (small n)
  and the GF defining equation Σ_j Q[j]·a_{n−j}=P[n] re-checked at ANY n from independently-extracted neighbours.
  Killer test: F(10^6) (a 208988-digit Fibonacci number) extracted by halving == the direct iteration; also
  geometric/rational/tribonacci. Q(0)=0 / n<0 → DECLINE. EXACT, tier normal, broth-eligible.
  `test_haran_bostan_mori`. (39 CONFIRMED now.)
- **#28 Automatic differentiation (exact dual)** → `autodiff.autodiff_grade`. Forward-mode AD via DUAL NUMBERS
  (a+bε, ε²=0) over `Fraction`: evaluating a polynomial/rational expression on duals propagates (value,
  derivative) by the chain rule EXACTLY — no finite-difference error. We own the forward pass (a `Dual` class
  walking the sympy tree); sympy's symbolic ∂/∂x is the INDEPENDENT cross-check (a different algorithm). EXACT for
  polynomial/rational functions at a rational point, multivariate gradients supported; transcendental / non-integer
  power / divide-by-zero-at-the-point are honest DECLINEs (the value would not be exact). Tested: d/dx(x³−2x+5)@4,
  (x²+1)/(x−1)@3, ∇(x²y+3xy³), rational points. EXACT, tier normal. `test_haran_autodiff_dual`. (40 CONFIRMED;
  **Group B complete.**)
- **#19 Gröbner basis (Buchberger)** → `groebner.ideal_member_grade`. Ideal-membership DECISION by a self-driven
  Buchberger completion (S-polynomials + a TRANSFORMATION matrix tracking g_j = Σ T_{ji} f_i), using sympy for the
  ring arithmetic and as an independent cross-check (`sympy.groebner`). A YES emits explicit cofactors q = Σ H_i f_i
  re-checked by polynomial expansion (a Positivstellensatz-style witness, independent of the basis search); a NO
  emits the nonzero normal form after re-verifying Buchberger's S-pair criterion (sound, not a say-so). Tested:
  cofactor witness [y,1] for xy−1∈⟨x−1,y−1⟩; an 8-case decision battery (incl. 3 variables) AGREES with
  sympy.groebner; parse/empty → DECLINE. HONEST: EXPSPACE worst case ⇒ extend-tier, DECLINE past a 4000-S-pair cap
  (Buchberger built; F4 matrix acceleration not added — same ideal, faster). EXACT. `test_haran_groebner_membership`.
  (**41 CONFIRMED — §1 COMPLETE: all 50 named algorithms present.**)

### §2 — the cross-algorithm BROTH: pre-prove common instantiations offline → O(1) lookup (`haran_broth.py`)

The "instant" mechanism widened beyond the existing sum/recurrence broth (3,772 entries) to span SEVERAL of the
50 named algorithms. `haran_broth.py` brews **1,367 pre-proven instantiations** OFFLINE across **13 of the 50** —
**#9 Faulhaber** Σk^p closed forms, **#10 named C-finite** sequences, **#31 fast modexp**, **#32 power towers**
(generalized-Euler), **#33 fast-doubling Fibonacci**, **#34 binomial mod p** (incl. astronomical n),
**#38 integer factorization**, **#39 Cipolla modular √**, **#40 discrete logarithm**, **#41 Pell** fundamental
solutions, **#44 Möbius μ**, **#45 Jacobi** symbols, **#49 Wigner 3j** symbols — and serves them by an **O(1) hash
lookup measured at ≈ 0.07 µs (size-independent, all-hit)**. The certificate
discipline is the strongest possible: **every cached entry RE-VERIFIES by RE-RUNNING the real algorithm**
(`reverify`) — a corrupted cache is caught (a tampered Faulhaber closed form is rejected), never served on its
say-so. **§0-B honesty (verbatim):** this is PRECOMPUTED-LOOKUP-FAST, NOT execution-O(1) — a MISS returns `None`
and the caller runs the algorithm at its TRUE complexity; widening coverage = pre-proving more common cases, NOT
making any algorithm instant. `test_haran_broth_lookup`.

### §3 — MEASURED collapse coverage over a structured corpus (`algo50_coverage.py`)

The 50 algorithms are GENERAL (one covers many cases). `algo50_coverage.py` MEASURES that breadth: a curated
corpus is dispatched to the REAL algorithms and the actual graded verdicts are counted. Result: **53 covered
cases across 25 distinct algorithm families** (Faulhaber degrees, 7 named C-finite sequences, GF extractions,
Newton inv/exp/log/sqrt, modexp, power-towers, binomial mod p^e, Jacobi, Möbius, Pell, sieve, Wigner, plus Gosper,
Abramov, Hermite, Gröbner, CP rank-1, BPSW, factorize, Cipolla, rho-dlog, forward-mode autodiff, multipoint
evaluation, fast-doubling Fibonacci, Stern–Brocot) — **all 53 certified EXACT**. Crucially, a deliberately ADVERSARIAL block (transcendental Σ1/k / undefined recurrence /
even-modulus Jacobi / out-of-range sieve / transcendental autodiff / non-prime binomial) **DECLINES 6/6** — the
proof that coverage is **DOMAIN-CONDITIONAL**. §X honesty (verbatim): this is the MEASURED coverage on THIS
corpus, near-zero on general/control-flow/graph/I/O code; NOT a general-purpose accelerator, NOT "100%"; the
adversarial DECLINEs are correct behaviour; a "family" is a generalized recognizer family (algorithm × sub-pattern),
NOT a fundamentally-distinct structure. `test_haran_coverage`.

**Code-shape mapping (§3 deepen).** `structure_recognizer.py` now NORMALIZES FIVE code shapes computing the same
accumulation — a `for`-loop, a counter-`while`, a `sum`/`prod` comprehension, a LINEAR self-recursion
(`def f(p): if p<c: return ID; return f(p-1) OP h(p)`), and a `functools.reduce` fold
(`reduce(lambda a,k: a OP h(k), range(lo,hi), ID)`) — to the SAME `_AccLoop` structural key
(`_acc_loop_any_shape`), now BYTE-IDENTICAL across all five (a `_canon_expr` round-trip collapses cosmetic bound
spellings like `(n)+1`≡`n+1`). All five route to the SAME algorithm and the SAME verified O(1) closed form (Σk² →
n(n+1)(2n+1)/6 for all five, lift differential-equivalence verified against each shape's REAL execution — for the
recursion the gate runs the ACTUAL self-calls (single-namespace `_make_callable` so a recursive function's
`__globals__` contains itself); for the reduce fold the gate executes the REAL `reduce`, enabled by a
TIGHTLY-WHITELISTED sandbox `__import__` (`functools`/`operator`/`math` only — all pure, no I/O; `import os`/`sys`/…
still raise `ImportError`)). This widens coverage WITHOUT inventing structures — one algorithm, many code shapes.
Sound: a non-counter `while`, an accumulator-dependent body, BINARY recursion (two self-calls, e.g. Fibonacci
`f(n-1)+f(n-2)`) or a non-monoid-identity base case, and a reduce whose summand references the accumulator or whose
initializer ≠ the identity are all correctly REJECTED (the execution gate can only DECLINE on a misread, never ship
a wrong collapse). `test_haran_code_shape_invariance`.

**Nested loops → O(1) (§3 deepen).** Beyond the single-fold shapes, `structure_recognizer.py` now collapses a
DOUBLY-NESTED accumulation `acc=ID; for i in range(…): for j in range(…): acc += h(i,j); return acc` (O(n²)) to an
O(1) closed form (`_nested_acc` recognizer + `_offload_nested`). The mechanism: close the INNER fold to C(i),
substitute it as the outer summand, close the OUTER fold — the inner bounds MAY depend on the outer var (the
triangular case Σ_i Σ_{j≤i}). The closed form is PROPOSED by the CAS (`sympy.summation`, sound on these
polynomial/hypergeometric sums) and becomes authoritative ONLY after passing DIFFERENTIAL EQUIVALENCE against the
ORIGINAL executed nested loop on ≥5 inputs — exactly the module's propose-then-prove discipline, the execution gate
the sole soundness authority (a bad proposal DECLINEs). Verified on triangular / rectangular / coupled / 0-based
double sums (e.g. Σ_iΣ_{j≤i} j → n(n²+3n+2)/6, plus a degree-2 inner bound → O(n³)), each closed form INDEPENDENTLY
re-checked vs a brute-force double loop; the complexity label is computed PER-CASE from the true iteration-count
degree (honest O(n²)/O(n³)/…, not a fixed string). **Bounded-gate soundness:** every loop bound must be a
polynomial of total degree ≤ 2 in the loop vars — a non-polynomial bound (e.g. `range(1, 2**i)`) is REJECTED so the
equivalence gate can never execute an unbounded/exponential loop (no hang); with polynomial bounds the sampled loop
stays ≤ N² iterations, so the gate is always cheap. Sound: an accumulator-dependent body, triple nesting, an extra
outer statement, a non-identity initializer, and an exponential bound are all correctly REJECTED.
`test_haran_nested_loop_collapse`. **Wired LIVE**: `engine_bridge._loop_collapse` now surfaces the nested collapse
in the real optimize path (kind `nested_sum`, EXACT, certificate) — and because a recognized double-nested
accumulation is never a single-state C-finite recurrence, it returns its collapse-or-NONE WITHOUT falling through to
the loop-SAMPLING recurrence detector (which executes the loop and would hang on an explosive inner bound). The
recurrence/modular paths for genuine single-state loops are unchanged. `test_loop_collapse_fork_safe`.

**Filtered loops → O(1) (§3 deepen).** A modular-FILTERED accumulation `for k in range(lo,hi): if k%M==R: acc +=
h(k)` (O(n)) — one of the most common real-world loop shapes (sum of evens/odds, multiples, strided sums) — now
collapses to an O(1) closed form (`_cond_acc` + `_offload_cond`). The mechanism is the EXACT reindex k = M·t + r₀
(r₀ = the least k ≥ lo with k ≡ R mod M), summing over t with `sympy.summation`; the closed form (with `floor`,
still O(1) to evaluate, e.g. Σ_{k<n} evens → (⌊n/2−½⌋+1)⌊n/2−½⌋) is authoritative ONLY after DIFFERENTIAL
EQUIVALENCE against the ORIGINAL executed loop on affordable samples (the same bounded gate). Verified on Σ evens,
Σ odd-squares, Σ multiples-of-3, Σ k≡1(mod 4), each re-checked vs a brute-force filtered loop. Sound: a non-modular
predicate, an if/else, a summand using a non-loop var, and a degenerate M=1 are all correctly REJECTED.
`test_haran_filtered_loop_collapse`.

**Bounded single-fold gate (§3 harden).** The same no-hang discipline now protects the single-fold OFFLOAD gate
(`_offload_closed_form`): the gate EXECUTES the user's loop, so it NEVER runs a sample whose iteration count exceeds
`_GATE_ITER_BUDGET` (2 M) — a super-linear upper bound like `for j in range(2**n)` would otherwise loop ~2⁶⁴ times
and hang. Unaffordable samples are skipped; the affordable small samples still verify the closed form. Bonus: a
`range(2**n)` sum now OFFLOADS via the small samples to `(2ⁿ−1)·2ⁿ/2` — a genuine O(2ⁿ)-loop → O(1)-closed-form win
(the power is one bigint op, never the loop). `test_haran_code_shape_invariance` (no-hang regression).

**MEASURED code-shape reach (§3 deepen).** `algo50_coverage.measure_code_shapes()` quantifies the CODE recognizer's
collapse breadth, with NO padding — a collapse counts only if `dispatch`→OFFLOADED AND the emitted closed form matches
a brute-force evaluation on fresh inputs. Measured: **30/30** (six Σ-targets — Σk, Σk², Σk³, Σ(2k−1), Σk(k+1),
Σ(3k²−k) — × five shapes) single-fold collapses, all six targets fully SHAPE-INVARIANT (each target's five shapes
agree on ONE closed form); **4/4** nested O(n²)→O(1); **34 total** execution-verified code collapses; and **6/6**
adversarial code shapes correctly REJECTED. This MEASURES the recognizer's reach — it is NOT a claim that arbitrary
code collapses (unstructured code declines — the honest majority). `test_haran_code_shape_coverage`.

### §4 — TIER ROUTING for the 50: fast / normal / extend + broth short-circuit (`algo50_router.py`)

The operational glue tying §1 (each algorithm's tier) + §2 (broth) + the `pillar3/mode.py` contract. `route(algo,
mode, broth_key)` enforces, per-commit-tested: a **BROTH HIT short-circuits in ANY mode** — instant O(1) EXACT
even in fast, even for an extend-tier algorithm (it was pre-proven offline; the UI shows "사전증명된 닫힌형 0.1µs").
On a MISS, the algorithm runs only if its tier ≤ the mode: **fast (~1s) NEVER runs an extend-tier heavy solver**
(CAD/Risch/Gröbner/Kovacic/Petkovšek/ΠΣ*/factorization/Lucas–Lehmer/BSGS) — it returns TIER_UP (40/50 tier up in
fast, 0 heavy hosted); **normal** runs fast+normal; **extend** runs all 50 within its BOUNDED ~8-min budget. The
router decides ROUTING ONLY — it never weakens a grade and never runs past a budget. `test_haran_tier_routing`.

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
