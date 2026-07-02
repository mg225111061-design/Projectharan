# v40 PHASE 2 — structured matrices (numeric coverage) + verifier registration

Campaign cycle 2. Builds on the PHASE-1 router + grade ADT.

## Delivered
- **Toeplitz mat-vec via convolution (32)** — displacement structure (Kailath–Kung–Morf 1979, citation
  verified): T·v is a convolution ⇒ **O(n²) → O(n log n)** via the exact-integer NTT (rust_accel, P=998244353).
  **EXACT under a PROVEN no-wraparound bound** (n·max|t|·max|v| < P/2); over-bound ⇒ honest **DECLINE** (NTT
  could wrap — multi-modular CRT is the stated extension, not faked). Certificate = bound proof + O(n) spot-check.
- **Freivalds (40) reused into the router** — the existing PROBABILISTIC(δ=2⁻ᵏ) matmul verifier adapted from
  SublinearVerdict to the unified Verdict (grades line up); correct⇒PROBABILISTIC, wrong⇒DECLINE. Demonstrates
  the router unifies groups (no rebuild).

## Measured (§0.1)
| n | naive T·v | NTT T·v | bit-exact |
|---|---|---|---|
| 64 | 0.60 ms | 0.39 ms | ✓ |
| 256 | 7.76 ms | 1.07 ms | ✓ |
| 1024 | 134 ms | 4.45 ms | ✓ |
| 4096 | **2226 ms** | **18.5 ms** | ✓ (~120×) |
- crossover n = 64. Router now holds **7 kernels across groups B/C/E/F/G**; contracts all well-formed.

## §0.1 self-check
1. **cost or output-size?** COMPUTE collapse (O(n²)→O(n log n)); the output is still n integers (not collapsed).
2. **domain?** Numeric / structured linear algebra (Toeplitz). EXACT only under the integer bound.
3. **measured?** Yes (table). 4. **grade enforced?** Yes (ADT); over-bound→DECLINE, wrong-matmul→DECLINE.
4. **Amdahl p?** High when the Toeplitz product dominates (signal / linear-system inner loops); else low.

## Honesty
The EXACT grade is gated by a proven magnitude bound — beyond it we DECLINE rather than return a wrapped value.
This is the directive's "sound-or-decline": the worst case is a missed fast path, never a wrong answer.
Full Toeplitz *solve* (Levinson/GKO) and the other F-group matrices remain for later cycles.
