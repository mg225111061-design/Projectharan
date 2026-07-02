# Performance-build — final integrated report (STAGE 0–5)

Branch `claude/funny-maxwell-im9x07`, on top of v37. **All numbers MEASURED on-container, with N.** Three clocks
kept strictly separate. **This build raises Clock B (verification throughput) + Clock C (emitted code) + the
scaling ceiling — it does NOT touch Clock A (LLM latency).** No "real-time/instant" claim is made anywhere.

## ★ #1 success condition — runtime regression 0 ★
- **Add-only.** Since v37 (`cc1810f`) I modified ZERO existing runtime modules. `git diff --name-status` shows
  only **A**dded files (`graph_core.py`, `semantic_cache.py`, `fold_egraph.py`, `hidden_closed.py`,
  `egraph_native.py`, `rust_graph/*`) + appended tests + `.gitignore`. proof_cache, repo_partition, fold_kernels,
  backend_llvm, cfinite, egraph, superopt, translation_validate are **byte-identical** → existing paths cannot
  regress. Every new accelerator is **opt-in** and falls back to the original on absence/decline.
- **phone-home 0.** The new caches are in-memory only — no socket/http/file-write in any new module (grep-verified).
- **Empirical:** the full suite stays green (98 tests, 0 fail), including all pre-existing v31–v37 tests.

## STAGE 0 — environment recon + baseline (measured)
- rustc/cargo 1.94; crates.io reachable (egg/salsa fetchable); **maturin MISSING → ctypes/cdylib** (v34 precedent).
- repo_partition Fiedler ceiling: **2.7s@N=1k, 12.9s@2k, 50.3s@4k, BLOCKED-scale ≥6k** (O(N²) KL + cap 4000).
- fold coverage (Clock C): **18/28 = 64%**, false_folds 0. proof_dag incremental: 328/500 on 1 change.

## STAGE 1 — Rust graph/proof-DAG core (cdylib/ctypes) — ceiling removed
- **DIFFERENTIAL vs Python mirror:** Fiedler vector **bit-identical** (max|Δ|=0.0, cos=1.0 @ N=200/800/2000);
  partition cut identical (11/51/110); transitive-dependents == Python BFS. API contract unchanged.
- **Scaling [Clock B / orchestration]:** ceiling gone —

  | N | pure-Python | Rust | note |
  |---|---|---|---|
  | 1000 | 2,606 ms | 12 ms | 214× |
  | 4000 | 48,325 ms | 129 ms | 374× |
  | 8000 | **BLOCKED-scale** | 454 ms | feasible |
  | 16000 | **BLOCKED-scale** | 1,681 ms | feasible |

  HONEST: the multiple is Python-interpreter overhead removed from the O(N²) KL loop — **same algorithm**, not an
  algorithmic gain. The deliverable is the **ceiling removal (4000 → 16000+)**. Salsa available but unused (cdylib
  ⇒ Python owns orchestration; proof_dag already O(V+E) in Python, not the bottleneck).

## STAGE 2 — e-graph SEMANTIC proof cache [Clock B]
- **5/5 refactoring families HIT semantically vs 0/5 structurally** (assoc, distributivity, const-fold,
  commute-across-structure, comparison-direction). **SMT-bypass +5** solver calls.
- Per-call cost (honest, not free): semantic key **325 µs ≪** the Z3 call it bypasses **2839 µs** (8× cheaper to
  bypass; break-even = solver-cost > key-cost, easily met by real verification).
- **SOUND:** every step equivalence-preserving + one global bijective rename of the universal closure ⇒ same key
  ⟹ same ∀-statement. Audited **LOSSLESS** (0 mismatches); across mixed PROVEN/REFUTED goals **no
  same-key/different-verdict pair**. Entailment (x>5 ⟹ x>0) via **interval subsumption O(1), NOT e-graph**.

## STAGE 3 — FOLD as a first-class e-graph rewrite
- Σk^p (Faulhaber) and C-finite recurrences **register as e-graph rewrite rules**; the rule fires in saturation
  and cost-extraction picks the closed form.
- **SOUND GATE (§3.3):** a rule exists only after its certificate passes; a **forced-wrong** closed form (n² for
  Σk²) is **REJECTED** → no substitution → honest DECLINE (stays O(n)).
- **[Clock C] bit-exact:** Σk² O(n)→O(1) (n=1e5: ~8ms→~0.014ms — the genuine O(n)/O(1) ratio, grows with n);
  C-finite O(n)→O(log n) (Fibonacci). **Fold-equivalent → same cache key.** Faulhaber **cross-validated against
  the INDEPENDENT C-finite companion engine** (recurrence (E−1)^(p+2)) for p=1,2,3 — HARAN-first.

## STAGE 4 — hidden closed-form recovery (the HONEST "O(1)" direction)
- A C-finite sequence with all-unit roots is secretly a polynomial ⇒ **recovered O(log n) → O(1)**, EXACTLY,
  held-out verified (Σk² recurrence → degree-3 polynomial, ×14 held-out points).
- **Recovery by category (held-out verified):** polynomial-sum **100%**, cfinite-nonpoly **0%** (Fibonacci stays
  O(log n) — **EXACT O(1) impossible**), general-noise **0%** (**Ω(N)** respected).
- `2^n` → **THETA_N_OUTPUT** (Ω(n) bits to emit; not O(1) — Ω(N) axiom). Binet float O(1) labeled
  **PROBABILISTIC**, never EXACT. No "universal O(1)" claim — recovery is domain-specific.

## STAGE 5 — optimal e-graph term → LLVM direct emission [Clock C]
- e-graph extract → **Z3-CERTIFIED extraction** (superopt.certified_extract; wrong extraction UNSOUND_BLOCKED) →
  `backend_llvm` native i64 → **Alive2-style translation validation** (bit-exact per-instance). A wrong closed
  form (n² vs Σk²) is **caught per-instance → DECLINE + fallback**.
- **MEASURED direct emission (O(1) native) vs source route (O(n) loop):** Σk² n=1e5 **~8ms → ~0.003ms (≈900–2700×,
  bit-exact)** — the closed form **-O3 on the loop cannot discover**. Grows with N (O(n)/O(1)).

## Discipline checklist
- ★ Measured only, with N; no fabricated multipliers — every speedup has a before/after table.
- ★ Three clocks separate; this build = Clock B + Clock C + scaling ceiling, NOT Clock A (no "real-time" claim).
- ★ Sound-or-decline everywhere: every fold/extraction/emission passes a certificate or DECLINEs; **0 wrong
  answers** (worst case = a missed acceleration). Forced-wrong inputs rejected at every stage.
- ★ Ω(N) never violated (random data → DECLINE; Θ(n)-output → not O(1)). EXACT never claims O(1) when the value
  is Θ(n) bits.
- ★ Runtime regression 0 (add-only, byte-identical existing paths); phone-home 0 (in-memory caches).
- ★ PQC not reintroduced (0). No leaked keys/secrets in new files.
