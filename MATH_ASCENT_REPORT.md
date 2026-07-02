# MATH ASCENT — UNIFIED ARSENAL (a + b + c) running report

*Running log of the unified arsenal campaign: (a) the transform system, (b) the ~70 fold families via
foundational generalizations, (c) the physics/engineering tools. Every number is reproduced by `test_build.py`;
`STATUS.md` is the live single source of truth. Branch `claude/charming-brahmagupta-q4wwgh`. This is a LOG, not a
terminal artifact.*

## How the three fit
**(a)** is the outer ROUTER/normalizer (`mathmode/transforms.py`): recognize the structure already present →
re-express into a form a closer can fold → dispatch → check the certificate → EXACT, else a PROVEN DECLINE naming
the obstruction. **(b)** are the closers (foundations G1–G4 + decision procedures). **(c)** are the domain closers
(physics P1–P9). The router dispatches into (b)/(c); where nothing closes, it proves the DECLINE.

## §1 — foundational generalizations (b), the subsumption graph AS BUILT
- **G1 Ore core** (`ore.py`): ℚ(x)[∂;σ,δ] over D (differential), S (shift), Q (q-shift). DECISION: operator
  equality via canonical normal form ([D,x]=1, [S,n]=S decided). Non-commutative product with an operational
  ((A·B)(f)≡A(B(f))) certificate; right-division / GCRD with a cofactor certificate. **Keystone.**
- **G2 holonomic / D-finite** (`holonomic.py`, on G1): annihilator-as-data; closure under + and × computes the new
  annihilator (module of derivatives/shifts), certified two ways (module Σbⱼ·state=0 over ℚ(x) + operational
  L(combo)=0). **Re-homes C-finite (Fibonacci S²−S−1) and hypergeometric terms (1/k!).**
- **G3 creative telescoping** (`telescoping.py`, the meta-method): Zeilberger (WZ-pair certificate ΔₖG=L(F)) +
  Almkvist–Zeilberger (∂ₜG=L(F)) + Gosper (DECISION, re-homed). Σ C(n,k)=2ⁿ→S−2; Σ C(n,k)²=C(2n,n)→(n+1)S−(4n+2);
  ∫e^{xt−t²}→2D−x. **Gosper/Zeilberger/AZ are specializations of this one method.**
- **G4 Schneider ΠΣ*** (`pisigma.py`, on G1): non-holonomic nested sums in ℚ(n)[H], σ(H)=H+1/(n+1). Telescoping
  by a linear ansatz, σ-automorphism + numeric certificate. Σ H_k=(n+1)H_n−n, Σ H_k²=(n+1)H²−(2n+1)H+2n, Σ k·H_k.
  **Σ 1/k → honest ΠΣ* boundary DECLINE (defines H).**

Subsumption: **G1 ⊃ {differential, shift, q-shift operators, QM Heisenberg algebra}; G2 ⊃ {C-finite,
hypergeometric, D-finite closure}; G3 ⊃ {Gosper, Zeilberger, Almkvist–Zeilberger}; G4 ⊃ {harmonic / nested ΠΣ*
sums}.** One certificate type each — these cover a large fraction of the ~70 classical fold families.

## §2 — decision procedures (b's crown jewels): closed form OR proven none
- **Petkovšek/van Hoeij** (`decision_summation.py`): all hypergeometric solutions of a recurrence, or proof of
  none (substitution-certified). y(n+1)=2y(n)→2ⁿ; (n+1)y(n+1)=y(n)→1/n!.
- **Abramov** rational summation (same module): Σ 1/(n(n+1))→−1/n; Σ 1/n & Σ 1/n² PROVEN not rationally summable.
- **Risch** (`decision_integration.py`): ∫2x·e^{x²}=e^{x²} (F′=f certified); ∫e^{x²}, ∫e^x/x PROVEN non-elementary
  (Liouville). Algebraic case honestly out of scope.
- **Kovacic** (same module): y″−y=0→e^{±x}, Euler→{x,1/x} (ODE-substitution certified); Airy→non-Liouvillian DECLINE.
- **CAD / real QE** (`real_qe.py`): univariate sign-invariant-cell DECISION. ∀x²+1>0 ✓, ∀(x−1)²>0 ✗, ∃x²−2=0 ✓.
  Multivariate flagged future.

## §3 — physics / engineering arsenal (c): P1–P9 COMPLETE
P1 Butler–Portugal tensor canonicalization (`tensor_canon.py`, mono-term DECISION via signed-group orbit +
Schreier–Sims BSGS; F_aa=0, Riemann R_bacd=−R_abcd); P2 curvature+Einstein (`curvature.py`, Schwarzschild
Ricci-flat + K=48M²/r⁶); P3 Petrov (`petrov.py`, PND-multiplicity partition: Schwarzschild→D); P4 Cartan–Karlhede
SPI discriminator (`cartan_karlhede.py`, Schwarzschild≠Minkowski rigorous NO); P5 operator algebra
(`operator_algebra.py`, Heisenberg≅G1, Wick normal order, [x,p]=iℏ); P6 Wigner/Clebsch–Gordan (`wigner.py`, exact,
CG unitarity certified); P7 Buckingham-Pi (`buckingham.py`, exact nullity over ℚ, pipe flow→Reynolds+Euler); P8
Lagrangian/Noether/Lie (`lagrangian.py`, EL, energy conservation mod EL, Lie prolongation); P9 holonomic
special-function bridge (`special_holonomic.py`, Legendre/Hermite/Bessel annihilators feed G2/G3).

## §4 — the transform system (a): the outer router
`transforms.py` routes across **five categories**, each reusing a verified closer + co-generated certificate:
T-algebraic-differential (∫→Risch / Σ→Gosper), **T-symbolic-dynamics** (`transforms_symdyn.py`: chaos→subshift
integer matrix→entropy=log φ, ζ=1/(1−t−t²), N_n=tr(Aⁿ) — EXACT), **T-number-system** (`transforms_number.py`:
modular→rational, series→BM rational GF, real→algebraic via PSLQ [EXACT only if symbolically verified, else
PROBABILISTIC]), **T-structure+randomness** (`transforms_random.py`: fold the C-finite part; PROVE the rest has no
short linear recurrence [Massey] + exact statistics, NO predictive rule — Kolmogorov-honest), T-physics (→ §3).
**MEASURED coverage:** 13/13 on the CURATED capability corpus (one structured object per category) + 2 honest
DECLINEs — explicitly NOT a universal-coverage claim; coverage is domain-conditional.

## PHASE 1 — MATH input recognition (made to fully work)
Robust parser (`parse.py`): Σ/sum(f,k,lo,hi), a^b mod m / pow / towers, fibonacci/lucas/catalan [mod m],
Lucas–Lehmer / isprime(2^p−1), collatz, n!, C(n,k), gcd/lcm, det/eigenvalues/inverse, factor/solve/integrate/diff.
Fast kernels (`fastkernels.py`, O(log)/O(1) + honest O(n) ceilings): 2^(2^1000) mod p instant; fibonacci(10^15)
mod p instant; Σ_{1}^{10^12}k^50 exact; isprime(2^31−1)=M31; LucasLehmer(10^17)→honest infeasibility (not a hang);
collatz(27)=111. THREE-WAY DECLINE (parse-fail / infeasible / no-closed-form). NL pipeline (`nl_solve.py`):
symbolic-first key-free; LLM→structured→echo UNVERIFIED; offline honest [BLOCKED].

## Reproduce
```
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 test_build.py
# … 232 passed (deterministic; load-flakes listed in STATUS.md pass in isolation)
```

## §X — WHAT WE MUST NOT CLAIM (verbatim)
- EXACT only with a machine-checked certificate / decision procedure / exhaustive-bounded domain (bound stated);
  approximation/numeric is PROBABILISTIC(ε,δ), never EXACT even at δ≤10⁻¹⁸.
- A decision procedure's / transform's "no closed form / no structure" is a PROVEN DECLINE (the moat), with a
  PRECISE reason — never a fabricated formula, never a blunt catch-all.
- Coverage gains are DOMAIN-CONDITIONAL (near-zero on general/control-flow/graph software) and the ceiling is a
  CEILING not a guarantee (Amdahl p per kernel); never imply a general-purpose accelerator.
- Whole-program/measured for EVERY speed claim; kernel ≠ whole-program; no average 50–100× claims; ratio ≤ ceiling.
- fast-exp/fast-doubling/Faulhaber handle astronomical sizes (O(log)/O(1)); Lucas-Lehmer/Collatz are O(n)-iteration
  with a REAL ceiling — never imply they scale; decline-with-reason, never hang/fake.
- USE existing rules, never invent rules — on randomness, exact statistics + proven irreducibility only, never a
  predictive rule for individual values (Kolmogorov).
- NL understanding is UNVERIFIED (echo interpretation); only computation is EXACT. Symbolic needs no key; NL needs
  the LLM.
- Never "smarter/faster than a model"; MR.JEFFREY wraps LLMs and adds proven exactness where structure exists.
- Reuse of a verified backend is fine but the certificate is ours and co-generated; decision-procedure-correct ≠
  proof-assistant-verified; Butler–Portugal decides mono-term tensor symmetries only (multi-term/Bianchi needs
  Young projectors); the PDE/spectral wall and data-driven Koopman/DMD are certified-numeric or DECLINE, never EXACT.
