# NEWENGINE_INDEX — §BM 10-field new engine branches (certificate-or-DECLINE; 0 new mechanism)

★ The research's verdict: of ~40 candidates across group/ring/set/category theory · control/info/systems/
optimization · continuum mechanics · thermodynamics, **none needs a 15th mechanism** — each is a new *recognition
branch* of one of the existing 14. The most under-mined axis is **Axis B (cheap verifiers for expensive
computations)** — Farkas/KKT, place-invariants, sifting, Pfaffian, resultants are all proposer-verifier
certificates that reduce to a residual / matrix check.

## Reuse (re-build 0)
`recall/core` (single disposer) · `mathmode/optimization` (exact LP → Farkas) · automaton stack (lstar/sfa) ·
`pillar3/equiv`+`zx_normalize` (DPO/IH/spider) · `cfinite`+`qfold/krylov` (Kalman/matrix-exp) ·
`mathmode/free_fermion`+matchgate (Kasteleyn Pfaffian) · `groebner` (Hilbert series) · `mechanisms/m05`+
`qfold/conservation` (place-invariant/Maxwell). `kernel_verdict` grades every output.

## Delivered this build (10 engines) — each a branch of an existing mechanism
| engine (newengine/) | gem | → mechanism (existing) | Axis | certificate (re-checked) |
|---|---|---|---|---|
| **farkas** | LP duality / Farkas infeasibility | relax-dualize **m04** | B | y≥0, Aᵀy=0, bᵀy<0 / KKT+strong-duality |
| **petri_invariant** | place-invariant unreachability | conservation **m05** | B | yᵀN=0 ∧ yᵀM₀≠yᵀM_t |
| **schreier_sims** | group order fold + sifting membership | complete-invariant **m09** | A+B | every gen sifts to identity |
| **markov_exact** | stationary fold + detailed-balance + absorbing | closed-form **m10** | A+B | πP=π / πᵢPᵢⱼ=πⱼPⱼᵢ / (I−Q)t=1 |
| **thermo_identity** | Maxwell relation + Legendre dual checker | m05 + m04 | B | S=−∂F/∂T, ∂S/∂V=∂P/∂T / f(x)+f*(p)=xp |
| **kalman** | controllability/observability rank | complete-invariant **m09** | A | exact-ℚ rank of [B,AB,…] |
| **orbit_count** | Burnside orbits + Hilbert series | structure-by-size **m10** | A | Burnside == union-find / dim==monomial count |
| **resultant** | Sylvester resultant | complete-invariant **m09** | B | (Res=0) ⟺ (deg gcd≥1) |
| **kasteleyn** | planar dimer/Ising Pfaffian (★→free-fermion) | conservation **m05** | A | Pf(K)²=det(K), planar precondition |
| **riccati** | algebraic Riccati (CARE) | guess-and-certify **m03** | B | ‖AᵀP+PA−PBR⁻¹BᵀP+Q‖=0 exact (numeric-alone forbidden) |

★ **0 new mechanism, 0 new disposer** — all 10 are recognition branches; every EXACT rides a re-checked
certificate (a construction bug ⇒ failed cert ⇒ DECLINE, never a false-EXACT). Wired into production via
`webapi/engine_dispatch.newengine_reach()` (NEW-16), output through the verdict ADT.

## Deferred to the next tranche (documented, with mechanism branch + reason)
| engine | branch | why deferred (honest) |
|---|---|---|
| **ws1s/ws2s** (NEW-6) | confluent-normal-form m08 | full automaton construction + minimization is a large build; decidable-fragment + step-budget DECLINE, next tranche |
| **bapa** (NEW-7) | relax-dualize m04 | PA-reduction wrapper over z3; staged after WS1S |
| **cole_hopf** (NEW-8) | canonical-form m02 | PDE-family recognition + irrotational precondition; needs the PDE frontend, next tranche |
| **dpo_rewrite / interacting_hopf** (NEW-13) | confluent-normal-form m08 (★ZX generalize) | hypergraph DPO + IH PROP is a large graph-rewriting build; staged |
| **fusion_law / feferman_vaught** (NEW-15) | m08 + structure-decompose | catamorphism-fusion equality + product-structure decision; staged |
| **submodular / matroid** (within NEW-11) | structure-by-size m10 | minimization (poly) staged; MAXIMIZATION is NP-hard ⇒ never EXACT (approx+bound only) |

★ Deferral is honest scope (the directive's "결정가능 fragment만 + zero-dep + exotic-dep 연기"), not a silent gap.

## Honesty (§4)
- certificate-or-DECLINE: EXACT ⟺ a re-checked certificate passes; <1ms cert or DECLINE. false-EXACT 0.
- Axis A (fold) vs Axis B (cheap verifier) labeled per engine; never summed.
- approximations carry a bound (none of the 10 delivered is approximate — all are EXACT-or-DECLINE; the
  approximate ones, Blahut-Arimoto / submodular-max / numeric-Riccati, are excluded or DECLINE'd).
- preconditions verified FIRST (Kasteleyn planarity, Riccati exact-ℚ residual, Legendre convexity).
- decidable-only: Petri general reachability (Ackermann-hard), submodular maximization (NP-hard) ⇒ never claimed.
- zero-dep (z3 + stdlib + numpy); "quantum/relativistic/ultra-speed" absent (qfold reuse stays classical-sim).
- ★ Sandbox blocks the live server ⇒ end-to-end production use author-validated on Render; the engines + their
  certificates are unit-tested here — code + push only, no false "verified".
