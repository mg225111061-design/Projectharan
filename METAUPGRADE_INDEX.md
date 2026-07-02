# METAUPGRADE_INDEX — §BQ §2 (index first, rebuild nothing)

Survey of what already exists in the 4 meta-theory areas (proof-carrying/certificate infrastructure,
incremental computation, SMT meta-theory, approximation certificates) **before** building anything new.
★ Everything below is a **systematization target only** — engine source files get **0 diff** in §BQ.
The new code lives entirely under `metakernel/` and wraps/classifies/bridges; it never edits these files.

## 1. CHC independent re-verification — `chc_solve.py`

`prove_safety_chc(varnames, init, trans, prop) -> CHCVerdict` / `chc_grade(...) -> KV.Verdict`.

Already the Necula/Shankar kernel-of-truth pattern: z3's Spacer **synthesizes** an inductive invariant
(creative search, untrusted), then the function **extracts** the invariant and **re-verifies** all three
Horn conditions (`init⇒Inv`, `Inv∧trans⇒Inv'`, `Inv⇒prop`) with **three fresh `z3.Solver()`** instances
(lines 64, 67, 68) — independent of the Spacer fixedpoint engine's internal proof state. EXACT only if all
three re-checks return `unsat`; any extraction/re-check failure ⇒ honest DECLINE, never an unverified SAFE.

**Gap the directive identifies**: both the synthesis (Spacer) and the "independent" re-check use z3 — a z3
bug class affecting `Solver.check()` generally would defeat *both* halves. z3 sits in the TCB twice.
**§BQ NEW-1b systematizes this** (for the propositional/ground-EUF *fragment* of CHC only) by replacing the
fresh-z3 half with a small pure-Python decision procedure — in a **new** module, `chc_solve.py` is not edited.

## 2. fast_certificates / Freivalds / Schwartz-Zippel — `freivalds.py`, `fast_certificates.py`

`verify_matmul(...)`, `freivalds_check(A,B,C,k,seed) -> CertResult`, `sz_identity_check(...) -> CertResult`.

Already certifying-algorithm style: one-sided error (Freivalds δ=2⁻ᵏ, Schwartz-Zippel δ=(d/|S|)^rounds),
correct claims always pass, wrong claims pass with bounded probability. Always graded PROBABILISTIC (never
EXACT) — honest about the one-sided error. **Not touched.**

## 3. IC3/PDR — `ic3_pdr.py`

`prove_safety(varnames, init, trans, prop, max_k, invariant_str) -> SafetyVerdict`.

Implements **k-induction** (the IC3/PDR/BMC family — not full IC3 clause-learning). SAFE only when the
property is verified k-inductive (base case + induction case both proved via z3); UNSAFE only with a
concrete counterexample trace; UNKNOWN otherwise. Never claims SAFE without the inductive proof — "never
false SAFE" was already the discipline, just not previously named that way. **Not touched.**

## 4. Farkas / SOS / LP-duality — `newengine/farkas.py`, `sos_cert.py`, `mathmode/optimization.py`

`verify_farkas_infeasible(A,b,y)`, `verify_lp_optimal(c,A,b,x,y)`, `sos_gram/is_psd/verify_sos/sos_grade`,
`lp_max_grade`.

★ **Already zero-z3, pure-algebraic kernels.** Farkas/LP-KKT use `fractions.Fraction` exact rational
arithmetic only (no z3, no floats). SOS's `is_psd()` counts negative eigenvalues **exactly** via the
characteristic polynomial + Sturm root-counting (sympy, no floating eigen-solve, no SDP solver trusted).
These three files are *already* the minimal-TCB pattern the directive asks for elsewhere — they are the
template NEW-1 generalizes, not a target to rebuild. **§BQ NEW-1 thinly re-exports their checkers under the
unified witness contract; the files themselves get 0 diff.**

## 5. Caching — `proof_cache.py`, `semantic_cache.py`

`canonical_key(goal, var_types, assumptions) -> tuple`, `_CACHE: Dict[tuple, ProofResult]` — α-renamed
structural cache, keys a z3 verdict (not a proof). No push/pop incremental-SMT context stack.
`semantic_cache.py` — e-graph normal-form cache (commutativity/associativity/distributivity), **disabled by
default** (`SEMANTIC_ENABLED = False`, gated on a measured break-even hit rate).

Both are flat verdict caches with no dependency graph between entries — exactly what NEW-3 (Adapton DCG,
Stage 2) wraps with a demand-driven dependency layer, without altering either file.

## 6. C-finite — `cfinite.py`

`naive_nth`, `companion_nth` (O(log n) power-by-squaring), `companion_nth_mod`,
`verify_cfinite(c, init, ns) -> (bool, List[int])` — already a self-certifying algorithm (the companion-power
path and the naive path are independently re-derived and compared on probe points). **Not touched** — NEW-1
adds a *third*, even-smaller independent matrix-power check in the kernel itself (not importing cfinite.py's
internals) purely as an extra-minimal-TCB witness type for callers who want it.

## 7. `extract/` catalog

8 subdirectories/files (`checksum/`, `parse_arith/`, `io_arith/`, `periodic_fsm/`, `classify/`,
`tensor_contract.py`, `semiring_lens.py`, `verhoeff.py`) — all **S-1, reduce to existing mechanisms**
(C-finite / telescoping / matrix-power / linear / periodic), zero new mechanisms. This is the home for
**NEW-6** (local theory extension test) in Stage 3 — not touched in Stage 1.

## 8. z3 usage — `z3_adapter.py`

No global `z3.Context`/solver pool; every call site creates its own `z3.Solver()` inline (confirmed in
`chc_solve.py` lines 64/67/68, `ic3_pdr.py` lines 70/83, etc.). There is **no existing chokepoint** to hook;
§BQ's new TCB-reduction path therefore has to be a parallel, opt-in entry point (NEW-1b), not a patch to a
shared factory function that doesn't exist.

## 9. `kernel_verdict.py` — the ADT

`EXACT`/`PROBABILISTIC`/`DECLINE`, `GradeViolation(AssertionError)` (raised explicitly, survives `python -O`),
`Cert(grade, kind, passed, check_cost, epsilon, delta, bound, detail)`, `Verdict(status, result, kernel,
complexity, certificate, ...)`, `decline()/exact()/probabilistic()` constructors, 5 soundness gates enforced
at construction time. **Not touched** — every new `metakernel/` module emits `KV.Verdict`/`KV.Cert` through
this unchanged ADT, so all 5 existing gates apply to the new code automatically.

## 10. `recall/core.py` — "the single disposer"

`fold_via_ai(fn, disguise, probe) -> StripResult` — routes post-strip oracles through the §AI/§AJ z3
∀-proof gate + held-out=200 check. The actual precision spine for the recall/* family is the z3 gate inside
§AI/§AJ, not a monolithic dispatcher; `core.py` is a thin, correctly-scoped re-entry point. **Not touched.**

---

## Net-new for §BQ (the *only* things actually built)

| module | what it adds | touches |
|---|---|---|
| `metakernel/trusted_kernel.py` | unified witness contract (thin wraps of #2/#4/#6) + a genuinely new, zero-dep, pure-Python propositional+ground-EUF decision procedure (DPLL + congruence closure) | nothing existing |
| `metakernel/chc_kernel_bridge.py` | z3-AST fragment classifier + Tseitin extractor + a parallel CHC entry point that uses the kernel instead of a fresh z3 re-check, **only** for the propositional/ground-EUF fragment; falls back to the unchanged `chc_solve.chc_grade()` otherwise | nothing existing (new file calls `chc_solve.py` as a black box) |
| `metakernel/holed_certificate.py` | Why3-style holed certificates over `catalog/ir.py` `StructForm` chains | nothing existing |

Stage 2 (NEW-3 Adapton DCG)/Stage 3 (NEW-5..8)/Stage 4 (NEW-9/10) follow the same "wrap, never touch" rule
and are queued separately.
