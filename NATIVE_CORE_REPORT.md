# NATIVE-CORE — final report

*One report for the whole NATIVE-CORE campaign (per the §0.5/C2 "single report, not forty" discipline). Every
number here is reproduced by `test_build.py`; the live current-state table is `STATUS.md`. Branch:
`claude/charming-brahmagupta-q4wwgh`. Suite at completion: **210 passed / 210** (deterministic run).*

The directive was adopted 100%: first an entropy cleanup (§0.5), then a native term/arithmetic core (§1), a
zero-dependency SMT (§2), a fast-triage layer (§3), a multi-LLM routing abstraction (§4), and dependency
elimination (§5). Each item is MEASURED or honestly UNVERIFIED, deterministic, and shipped with a test.

---

## §X — what we must NOT claim (kept verbatim; the governing honesty constraints)

- **Native = speed, not a correctness license.** Rewriting a path in Rust changes the RUNTIME; it never changes a
  grade. Every EXACT keeps a checkable certificate; the grade is the same or stricter after a native rewrite.
- **Our in-house solver is NOT cvc5/Z3-parity.** State exactly which theories/bitwidths it decides; never imply
  general SMT completeness.
- **Whole-program / measured only.** Speed claims carry the hotspot fraction f, the Amdahl ceiling 1/(1−f), n, and
  ratio ≤ ceiling. A kernel speedup is not a whole-program speedup.
- **SIMD / threads are deterministic.** No floating point in proof/grade paths; fixed reduction order; the result
  is bit-identical regardless of vectorization or thread count. Nondeterminism in a proof/grade layer is a
  build-failing bug.
- **Live multi-provider is UNVERIFIED while egress is blocked — mocked ≠ live.** A mock is never presented as a
  live response.
- **Native numbers are UNVERIFIED where there is no toolchain — and the Python fallback is never faked.** If rustc
  is absent the Python path runs and says so; we never print a Rust number we did not measure.
- **EXACT only with a machine-checked certificate, a decision procedure, or an exhaustive-bounded domain** (with
  the bound stated). Everything else is PROBABILISTIC(ε,δ) or an honest DECLINE.

These constraints are enforced, not just stated: the grade ADT (`kernel_verdict.py`) rejects fake-EXACT at
construction, and the tests below assert the bounds, the determinism, the UNVERIFIED postures, and the zero-dep
closure directly.

---

## §0.5 — entropy cleanup (done first, on purpose)

| | |
|---|---|
| **C1** | `HANDOFF.md` rewritten to the true current state; the obsolete "push haran-web" task explicitly retired (a stale handoff is an honesty violation at the onboarding layer). |
| **C2** | `STATUS.md` is the single source of truth; ~38 historical campaign reports moved to `reports/archive/`. This is the only top-level report going forward. |
| **C3** | Key-security wording scoped precisely: the web-UI path never reads the key from env (`claude_agent.py` imports no `os`); the gateway/CLI path uses the standard `HARAN_KEY` env var via `provider.resolve_key()`. |
| **C4** | Module families (e-graph ×4, spec_* ×6, frontends ×6) dependency-mapped: they are layered/distinct, not literal dups. The genuine e-graph core overlap was sequenced INTO §1 (merge-then-rewrite would be wasted work). |
| **C5** | One monotonic version timeline (this file's history + git); legacy v-labels mapped, no new campaign names. |
| **C6** | Perf gates split from correctness gates: `perf_obs()` logs measurements without asserting, so "0 regression" holds on any hardware (load-induced perf flakes can't fail the correctness suite). |
| **C-process** | `test_docs_not_stale` makes the docs' claimed test count a CHECKED invariant — STATUS.md and HANDOFF.md must equal `len(ALL)`, so onboarding docs cannot silently drift. |

---

## §1 — dependency-0 Rust native core  ·  `rust_core/` + `rust_core.py`  ·  `test_native_s1_rust_core`

Std-only cdylib (crate `haran_core`, **zero crates**, ctypes ABI — no PyO3/maturin/cffi/flint/faer). Delivers
exactly what the v34 Rust stage deferred ("multimodular CRT / arena-DOD / explicit SIMD noted as future"):

- **Flat arena AST** — op/arg/lhs/rhs parallel arrays, children-before-parents, evaluated in one deterministic
  forward pass (the index-based term core).
- **Deterministic fixed-precision multimodular (CRT) ring** — evaluate the arena under a fixed ordered 4-prime
  basis, then Garner-combine the residues into the EXACT integer with a native big-uint (base-2³² limbs),
  *replacing Python bignum* for the arithmetic. **EXACT while |value| ≤ MAX_ABS = (∏primes−1)/2 ≈ 2¹²³**; beyond it
  the symmetric representation wraps EXACTLY at the bound — stated honestly (widen the basis or DECLINE; never a
  false EXACT).
- **Bounded rational reconstruction** — recover p/q from a residue via the extended-Euclid remainder-sequence stop.
- **Deterministic fixed-reduction-order modular dot product** — the "SIMD" demonstrator: pure integer arithmetic
  summed left-to-right ⇒ bit-identical regardless of autovectorization or thread count (no FP, fixed order).

**Verification.** Rust ≡ Python bit-exact differential; a FORMAL exhaustive-bounded equivalence to spec —
**12,789 enumerated (arena × assignment) checks, 0 mismatches** (a fully-swept finite domain, not sampled); an
exhaustive CRT round-trip over a contiguous window + the ±MAX_ABS boundary; determinism asserted across runs.
**Measured honestly:** at this granularity there is **no speed crossover** (ctypes overhead vs C-fast CPython int)
⇒ speed is **UNVERIFIED**, correctness is the deliverable — mirroring the existing v40-phase7 RNS honesty. Degrades
to `[BLOCKED]` + the Python ring where rustc is absent. `target/` is environment-built (gitignored, like the other
crates); source + `Cargo.lock` + bridge are committed.

## §2 — zero-dependency bit-blasting SMT  ·  `bitblast_smt.py`  ·  `test_native_s2_bitblast_smt`

In-house DPLL SAT + bit-blaster + independent certificate checker — **no coqc/cvc5/Bitwuzla/Lean/Z3**. Decides
fixed-width **quantifier-free bitvector** obligations (add / sub / mul-by-constant / and / or / xor / not / shift /
eq / unsigned-lt). A validity result is **EXACT within the stated width** (bound = 2^w); DETERMINISTIC (same input
⇒ same result AND same certificate); CERTIFICATE-PRODUCING (every SAT model is re-checked by a tiny independent
checker — that one function is the whole TCB; ∀-validity is UNSAT of the negation over the w-bit domain).

**Wired into the engine.** `pillar3/bv_validate.bv_equiv_inhouse` gives the machine-semantics validator a
zero-dependency backend, and `cross_check_inhouse_vs_z3` proves every SOUND peephole (`mul2_to_shl1`,
`mul8_to_shl3`, `xor_via_or_minus_and`, `add_sub_cancel`, `clear_low_bit`) BOTH in-house and with Z3 at the same
width and asserts agreement — a faithful zero-dep replacement on its decidable subset.

**Honest scope (§X).** NOT cvc5/Z3 parity: no signed `>`, no division, no ite-mux, no arrays/reals/unbounded ints.
The overflow-unsafe peepholes (`succ_gt_self`, `mul2_div2_id`, `add_monotone`) need exactly those and stay on Z3 —
the cross-check declares them out-of-scope. Small TCB, zero deps: that is the point.

## §3 — AST-depth fast-triage before the proof cache  ·  `proof_triage.py`  ·  `test_native_s3_triage_layer`

The structural proof cache α-renames + walks + sorts on every call; for a LARGE-but-SIMPLE goal that
canonicalization costs MORE than just solving, so the cache regresses. A cheap O(size) meter (nodes / depth /
hardness = nonlinear var·var + quantifiers; no renaming, no strings, no sorting) routes such goals straight to the
solver. It is a DETERMINISTIC function of the AST (same goal ⇒ same route) ⇒ it changes only the PATH, never the
verdict (LOSSLESS — the solver still decides). `proof_cache.measure_triage` demonstrates the regression
(cache-without-triage > uncached) and the fix (triage removes the overhead), with 0 verdict mismatches.

## §4 — multi-LLM routing abstraction + high-fidelity offline mock  ·  `llm_router.py`  ·  `test_native_s4_llm_routing`

One router over `provider.py` (config) and `claude_agent.py` (live SDK paths). It selects the wire TRANSPORT
(Anthropic Messages / OpenAI chat.completions / Gemini generateContent), shapes the request EXACTLY as the live
path (in lockstep with `claude_agent._build_kwargs`/`_build_openai_kwargs`), runs a **high-fidelity offline mock**
that returns PROVIDER-SHAPED raw responses (realistic ids/usage/finish_reason, zero network), and parses the reply
back — so routing + serialization + parsing for every gateway (anthropic, openai-compat incl. **OpenRouter / Z.ai /
DeepSeek**, native openai, gemini, groq) runs offline and deterministically.

**Honest (§X).** A mock is ALWAYS `live=False` / `source="mock-sim:<transport>"` — never dressed as live. The
real-egress LIVE path is **UNVERIFIED** here: `route(mode="live")` with no sender returns an explicit UNVERIFIED
result and NEVER fabricates a response; `live_status()` reports `EGRESS_BLOCKED`. Keys are per-call arguments only —
never read from env here, never stored, never logged (`redact()` masks to a length tag). The LLM only PROPOSES; the
HARAN verifier still decides the grade.

## §5 — dependency elimination (toward zero), measured + enforced  ·  `dependency_audit.py`  ·  `test_native_s5_dependency_audit`

An AST scan classifies every third-party package; the test makes the result a gate:

- **FORBIDDEN big provers / native binders = 0 imports** (coqc/cvc5/Bitwuzla/Lean/PyO3/maturin/cffi). Coq is
  reachable only as an OPTIONAL `subprocess` call in `haran_coq.py`, `[BLOCKED]` when `coqc` is absent ⇒ runtime
  dep 0. §2 removes even the Z3 need for the bitvector obligations.
- **CORE is STDLIB-ONLY.** The grade ADT + the whole NATIVE-CORE — `kernel_verdict`, `bitblast_smt`,
  `proof_triage`, `rust_core`, `llm_router`, `provider`, `haran_ast` — have an **empty third-party top-level import
  closure**, proven BOTH statically (AST closure) AND at runtime (a subprocess imports every one of them with
  `numpy/sympy/z3/anthropic/openai/numba/llvmlite` all hidden, and all 7 load).
- **numpy is OPTIONAL-not-required for the core** — it is in NO core closure. With sympy and z3 it is a heavy dep of
  specific CODE/MATH numeric kernels only, documented honestly (not pretended away).
- **17 optional packages** (LLM SDKs, JIT, file-ingest, exotic frontends) are imported LAZILY ⇒ graceful-degrade,
  now enforced so a hard top-level import can't sneak back.

**Final hard top-level dependency set:** `fastapi, numpy, pydantic, sympy, z3` (web layer + the heavy kernels). The
verified native core needs none of them.

---

## Constitution / standing decisions honored

- Native rewrite changes RUNTIME not GRADES; same-or-stricter grade; every EXACT keeps a checkable certificate.
- Determinism in every proof/grade layer (no FP, fixed order); nondeterminism would be a build-failing bug.
- Rust = native host, HARAN = domain logic, Python = glue/LLM-IO. No Lean/Coq/Isabelle runtime dep (= 0). PQC
  dropped. Keys session-only, never logged. fast/normal/extend (and CODE/MATH) separation preserved per commit.
- Design approved unchanged — extension only, no redesign.

## Reproduce

```bash
cd /home/user/Projectharan
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 test_build.py
# … 210 passed, 0 failed
```

Native (`§1`) runs the full OK path where rustc is present; elsewhere it is `[BLOCKED]` with the Python ring as the
verified fallback. Live multi-provider (`§4`) is `UNVERIFIED` while egress is blocked — the offline mock is the
verified substitute. Neither is ever faked.
