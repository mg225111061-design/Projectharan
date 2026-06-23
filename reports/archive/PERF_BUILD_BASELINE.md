# Performance-build baseline (STAGE 0, measured 2026-06-19, branch claude/funny-maxwell-im9x07)

All numbers MEASURED on this container. Three clocks kept separate. This build targets **Clock B**
(verification throughput) + **Clock C** (emitted code) + **scaling ceiling** — NOT Clock A (LLM latency).

## 0.1 Toolchain probe
- rustc/cargo **1.94.1** present. crates.io **reachable** (egg 0.11.0, salsa 0.27.0 fetchable).
- maturin **MISSING** → ctypes/cdylib path (v34 `rust_accel` precedent: zero-dep std-only cdylib). PyO3 not forced.
- cffi MISSING; ctypes OK.
- **Decision:** Rust graph core as a zero-dep std-only cdylib via ctypes (matches existing `rust_accel`,
  builds offline, no crates.io build fragility). Salsa available but not used: cdylib+ctypes means Python owns
  orchestration, which does not fit Salsa's database-owns-computation model; proof_dag.py already does O(V+E)
  incremental dirty-tracking in Python and is NOT the bottleneck.

## 0.2 Clock B baseline
- proof_cache: structural canonical key (α-rename + sorted assumptions); lossless (every hit re-solved == fresh).
- proof_dag incremental: 500-node DAG, change 1 node → 328 transitive dependents rechecked (65.6%), rest cached.
- **repo_partition Fiedler power-iteration — the ~4000 node CEILING (pure-Python):**

  | N | wall-clock | status |
  |---|---|---|
  | 1000 | 2,737 ms | spectral-seed+KL |
  | 2000 | 12,871 ms | spectral-seed+KL |
  | 4000 | 50,344 ms | spectral-seed+KL |
  | 6000 | (19 ms) | **BLOCKED-scale** (short-circuit placeholder) |
  | 8000 | (19 ms) | **BLOCKED-scale** |

  Growth ≈ O(N²) (KL refinement `for a in zeros: for b in ones` is O(N²)/pass); hard cap MAX_PRACTICAL_N=4000.
  → STAGE 1 target: port Fiedler power-iteration + KL refine to Rust (cdylib/ctypes), push the ceiling.

## 0.3 fold coverage baseline (Clock C; false_folds=0)
- all: **18/28 = 64%** folded. Per-category: combinatorial 4/4, multivariate-poly 6/8, ode 5/8,
  q-holonomic 3/5, blackbox 0/3. (No `held_out` split present in the current corpus.)
- → STAGE 3 (fold as e-graph rewrite) and STAGE 4 (hidden closed-form recovery) measure against this.
