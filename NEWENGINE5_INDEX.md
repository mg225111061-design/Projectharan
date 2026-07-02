# NEWENGINE5_INDEX — §BN 5-domain new engine branches (certificate-or-DECLINE; decidable-fragment guards FIRST)

★ The directive's spine: build new *recognition branches* across five domains — program-verification decision
theory, advanced automata, graph polynomial-exact islands, computable topology/geometry, deep number theory —
and **check the decidable fragment FIRST**, DECLINEing the undecidable / not-known-poly residual rather than
guessing. **0 new mechanism** (each is a branch of an existing one of the 14); **0 new disposer**; every EXACT
rides an INDEPENDENTLY re-checked certificate ⇒ a construction bug ⇒ failed cert ⇒ DECLINE, never a false-EXACT.

## Reuse (re-build 0)
`native_lattice.smith_normal_form` (Smith NF → homology) · `catalog/mech_knot` (Kauffman/Laurent — amplified by
Alexander) · `catalog/mech_persistence` + `catalog/mech_sheaf` (amplified by smith_homology + morse) ·
`presburger_qe` (semilinear-set backing for Parikh) · `catalog/mech_sfa` (automata family) · `kernel_verdict`
(grades every output). zero-dep (z3 + stdlib + numpy).

## Delivered this build (7 engines) — each a branch of an existing mechanism, with its decidable-fragment guard
| engine (newengine5/) | domain | gem | → mechanism | Axis | certificate (re-checked) | ★ guard (DECLINE) |
|---|---|---|---|---|---|---|
| **tree_automata** | automata | bottom-up (N)FTA emptiness + membership | structure-by-size **m10** | A | bottom-up run / saturated fixpoint + witness re-run | equality/**disequality** constraints ⇒ UNDECIDABLE |
| **wl_refine** | graph islands | Weisfeiler–Leman non-iso + explicit-π iso | complete-invariant **m09** | B | color-histogram mismatch / substitute π, match edges | WL-equal w/o explicit π ⇒ general **GI** not decided |
| **smith_homology** | topology | Betti + torsion of a chain complex | m09 / **m10** | A | ∂∂=0 + unimodular U∂V=S + Smith-rank == ℚ-rank | ∂∂≠0 ⇒ not a complex; cost cap |
| **morse_inequalities** | topology | discrete-Morse data ⊣ homology | conservation **m05** / m09 | B | weak + strong Morse + Euler equation | a violated inequality ⇒ unrealizable |
| **alexander_poly** | topology / knots | Δ(t)=det(V−tVᵀ) from a Seifert matrix | complete-invariant **m09** | B | Δ(1)=±1 (direct det) + palindrome + \|Δ(−1)\|=knot det | Δ(1)∉{±1} ⇒ not a knot Seifert matrix |
| **hasse_minkowski** | number theory | ternary quadratic-form rational solvability | guess-and-certify **m03** / m04 | A+B | explicit zero (substitute) / Legendre congruence; real + p-adic obstruction | outside squarefree/coprime/small fragment; cost cap |
| **parikh_image** | automata | regular-language Parikh-vector reachability | structure-by-size **m10** / m04 | A | witness word re-simulated / exhaustive closed DP | **ε-transitions** break length-boundedness; cost cap |

★ **0 new mechanism, 0 new disposer** — all 7 are recognition branches; every EXACT rides a re-checked
certificate. Wired into production via `webapi/engine_dispatch.newengine5_reach()`, output through the verdict ADT.
Adding `newengine5` to `engine_inventory._WIRED_PACKAGES` keeps the full-repo audit at **gap == 0**.

## Decidable-boundary discipline (the directive's hard requirement)
- **tree automata WITH equality/disequality constraints** — emptiness is UNDECIDABLE ⇒ DECLINE (we decide only
  the constraint-free (N)FTA fragment).
- **general graph isomorphism** — not known polynomial; WL-equivalence does NOT imply isomorphism (e.g. C₆ vs
  2·C₃, strongly-regular graphs). Non-iso via WL is always sound; **isomorphism is claimed ONLY with an explicit,
  re-checked permutation**; the WL-blind residual ⇒ DECLINE.
- **Hasse–Minkowski** — decided only inside the small-solution / squarefree-pairwise-coprime Legendre fragment;
  outside (and beyond the coefficient cost cap) ⇒ DECLINE.
- **Parikh** — ε-transitions break the Σv length bound ⇒ DECLINE; the count space ∏(vℓ+1) is capped ⇒ DECLINE on
  cost.

## Deferred to the next tranche (documented, with mechanism branch + reason)
| engine | branch | why deferred (honest) |
|---|---|---|
| **Büchi/ω-automata + LTL satisfiability** | complete-invariant m09 | LTL→Büchi tableau + nested-DFS/SCC emptiness is a sizable build; staged after the FTA core |
| **Courcelle MSO on bounded treewidth** | structure-by-size m10 | MSO→tree-automaton is non-elementary; only the bounded-tw DP island is in scope, staged |
| **array property fragment / ADT (z3 theories)** | guess-and-certify m03 | thin z3-theory wrappers; staged with their fragment guards (no nested array reads / well-founded ADT) |
| **separation-logic list-segment entailment** | m08 | amplifies `sep_alias`; the established-fragment entailment is staged (SL non-established ⇒ DECLINE) |
| **Schoof full point counting / WL-k** | m09 / m10 | full Schoof is a large modular build; Hasse bound + small-p count is the in-scope island, staged |
| **Jones polynomial (alternating)** | — | **#P-hard** (Jaeger–Vertigan–Welsh) ⇒ excluded; only Kauffman small-diagram island (mech_knot) + Alexander stay |

★ Deferral is honest scope (the directive's "결정가능 fragment만 + zero-dep"), not a silent gap. Class groups,
modular forms, and large-rank LLL stay excluded (zero-dep boundary).

## Honesty (§4)
- certificate-or-DECLINE: EXACT ⟺ a re-checked certificate passes; the undecidable/not-poly residual DECLINEs.
  false-EXACT 0.
- Axis A (fold) vs Axis B (cheap verifier) labeled per engine; never summed.
- decidable-only: tree-automata disequality, general GI, #P-hard Jones, non-squarefree Hasse residual ⇒ never
  claimed EXACT.
- preconditions verified FIRST (∂∂=0, Δ(1)=±1, squarefree+coprime, no-ε).
- zero-dep (z3 + stdlib + numpy); "quantum/relativistic" speedup language absent.
- ★ Sandbox blocks the live server ⇒ end-to-end production use is author-validated on Render; the engines + their
  certificates are unit-tested here (test_bn) — code + push only, no false "verified".
