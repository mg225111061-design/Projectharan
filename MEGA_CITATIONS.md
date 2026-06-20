# MEGA-DIRECTIVE — citations (every method verified against a primary source)

Each row: the method we use, the primary source, and an honest note on what the source actually claims (so we
never inflate a KERNEL number into a whole-program claim).

| method (where we use it) | primary source | honest note |
|---|---|---|
| empirical complexity / power-law fit (`complexity.py`, extend sweep) | Goldsmith, Aiken, Wilkerson, **"Measuring Empirical Computational Complexity," ESEC/FSE 2007** | log-log power-law fit of runtime vs input size; we recover O(n)…O(n³). Their method estimates the empirical exponent; it does not prove worst case. |
| accidental-quadratic / performance-bug detection (D1) | Jin, Song, Shi, Scherpelz, Lu, **"Understanding and Detecting Real-World Performance Bugs," PLDI 2012** | catalogues real perf bugs (redundant work, inefficient loops). We detect a subset structurally; we do not claim their full taxonomy. |
| ReDoS / catastrophic-backtracking & algorithmic-complexity attacks (D1) | Petsios, Zhao, Keromytis, Jana, **"SlowFuzz," CCS 2017** | fuzzing to trigger worst-case complexity. We detect nested-quantifier regex statically and replace with a linear matcher; we do not fuzz. |
| GEMM / algorithm idiom recognition (S4, PHASE S) | de Carvalho et al., **"KernelFaRer," ACM TACO 2021** | recognises GEMM idioms and swaps in a library kernel. ★ Their ~2000× is a **KERNEL** number, not whole-program — we report only the measured whole-program ratio (Amdahl-bounded). |
| verified lifting to a spec, re-synthesise + verify (PHASE S) | Bhatia et al., **"Tenspiler," ECOOP 2024** (and Dexter, Cheung et al.) | lift a loop to a DSL spec, synthesise, verify. We do a restricted-subset lift (no pointers/objects) and Z3-verify — honest narrow scope. |
| bounded translation validation / equivalence (the moat, `equiv.py`) | Lopes, Lee, Hur, Liu, Regehr, **"Alive2," PLDI 2021** | translation validation of LLVM optimisations via SMT. We run both implementations on symbolic Z3 inputs and prove output equality for bounded sizes — Alive2 in spirit, Z3 only. |
| Freivalds-style probabilistic verification (MICRO tier) | Freivalds 1977 (matrix-product verification) | one-sided randomized check, no false reject. Used for µs-class verification in fast mode. |
| "instruction superopt is near-useless whole-program" (the honesty floor) | AlphaDev (Mankowitz et al., *Nature* 2023, ~1.7% on sort primitives); Minotaur (~1.5%); Souper | cited to bound expectations: peephole/superopt gains are tiny at whole-program scale. Our value is waste elimination + asymptotic replacement *with proof*, not peephole. |

## Flagged / unconfirmable in this sandbox
- No internet access at build time ⇒ citations are from training knowledge; **page/exact-figure verification is
  UNVERIFIED here** and should be confirmed against the primary PDFs before any external publication.
- KernelFaRer's headline multiplier is explicitly a kernel-level GEMM speedup; we never reproduce or imply it
  as a whole-program number (Amdahl honesty, §X).
