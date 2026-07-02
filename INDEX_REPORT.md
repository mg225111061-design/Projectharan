# INDEX_REPORT — §BA §0 mandatory pre-build code index

**Rule (§BA §0):** index the code *before* building; if an item already exists, **0 code change** for
that item. This is the audit that decides which §BA Axis-1 capabilities are genuinely net-new versus
already-implemented (and therefore skipped). Confirmed by `grep`/`view` over the whole repo on the
`claude/charming-brahmagupta-q4wwgh` branch at HEAD `5f67fb3` (post-§AZ).

> Note on method: an earlier narrow `def <exact-name>` grep returned almost nothing and was *wrong* — the
> primitives exist under different names/files. This index searches the **concept**, then opens the file to
> confirm the actual signature. Every "already-built" row below is a verbatim function that exists today.

---

## A. Directive-asserted prerequisites — ALL CONFIRMED PRESENT (reuse, never rebuild)

| Concept | Actual location & symbol | Note |
|---|---|---|
| Skolem zero-problem (order ≤ 4) | `barrierfold/exppoly_eq.py :: skolem_decidable(order)`, `exppoly_equal` | directive said "cfinite.py near skolem" — **wrong file**; it lives in `barrierfold`. Order ≤ 4 decidable (Vereshchagin), ≥ 5 DECLINE. |
| SOS / Positivstellensatz | `sos_cert.py`, `mathmode/inequalities.py :: verify_sos`, `mechanisms/m04_relax_dualize.py` | Gram-matrix SOS + re-check. |
| Sylvester **inertia / signature** (LDLᵀ-equivalent) | `sos_cert.py :: inertia(Q) -> (n₊,n₀,n₋)`, `inertia_grade` | exact congruence invariant via eigenvalue signs. **Reused by CAP-6.** |
| Presburger QE | `presburger_qe.py` | the canonical automatic structure (ℕ,+) is already decided here. |
| Gröbner / Buchberger ideal membership | `groebner.py :: ideal_member_grade(gens, query, variables, order)` | self-driven Buchberger + **cofactor certificate** q=ΣHᵢfᵢ. **Reused by CAP-5/6/8.** |
| Sturm / Descartes real-root isolation | `native_realroots.py :: sturm_chain, count_roots, isolate_roots, realroots_grade` | exact rational isolating intervals + Sturm-count cert. **Reused by CAP-1.** |
| Smith / Hermite normal form (ℤ) | `native_lattice.py` | |
| C-finite companion-matrix eval | `cfinite.py :: companion_nth, naive_nth, verify_cfinite` | O(log n) exact term eval. **Reused by CAP-1.** |
| Pell / linear Diophantine | `mathmode/number_theory.py :: pell_grade, diophantine_grade(a,b,c)` | `diophantine_grade` is **linear** ax+by=c only. |
| Univariate CAD / real QE | `mathmode/real_qe.py :: decide(quantifier, formula, x)` | **univariate only**; its DECLINE message explicitly says "use virtual substitution / Positivstellensatz" — the TODO CAP-7 targets. |
| §AZ caps (do not touch) | `linear_algebra.py`: sylvester_solvable/similar_decide/jordan_structure; `decision_integration.py`: kovacic_liouvillian/darboux_first_integral/risch_elementary; `lagrangian.py`: morales_ramis; `holonomic.py`: algebraic_gf | committed `5f67fb3`. |

---

## B. §BA Axis-1 proposals — already-built → **SKIP (0 code change)**

| Cap | Proposal | Verdict | Evidence |
|---|---|---|---|
| **CAP-4** | Knuth–Bendix completion → confluence → monoid **word problem** | **ALREADY BUILT — SKIP** | `native_rewrite.py` has `knuth_bendix()`, `normal_form()`, `_critical_pairs()`, `_is_confluent()`, `word_problem_grade(rules,u,v)`, `m8_word_grade`. This is *exactly* the proposal (shortlex completion → confluent rewrite system → NF-equality decision, critical-pair certificate, budget-DECLINE). Building it again = forbidden double-implementation. |

---

## C. §BA Axis-1 proposals — genuinely **NET-NEW → BUILD** (sound, certifiable, repo-first)

Ordered by the directive's priority and by *soundness-buildability* (HONESTY SPINE: DECLINE > wrong).

| Cap | What it decides | Reuses | Soundness route |
|---|---|---|---|
| **CAP-1** ★flagship | **LRS Positivity / Ultimate-Positivity** (∀n. uₙ>0?) — distinct from the Skolem *zero* problem | `cfinite.companion_nth` (exact terms), `native_realroots` (Sturm) | EXACT-YES on the nonneg-coeff ∧ nonneg-init induction class; EXACT-NO on a finite negative witness; **order ≥ 6 ⇒ PROVEN-FRONTIER-DECLINE** (Positivity open; a procedure would settle open Diophantine-approximation problems); order ≤ 5 outside the sound class ⇒ honest DECLINE (needs Baker linear-forms-in-logs bounds, not implemented). |
| **CAP-6** | **Hermite trace-form real-root count** of a 0-dim ideal (# real points = signature of the trace form on ℚ[x]/I) | `groebner` (quotient basis + mult. matrices), `sos_cert.inertia` (signature) | exact in ℚ: #real = n₊−n₋ of the symmetric trace-form Gram matrix; #distinct-complex = rank. 0-dimensionality checked from the basis; else DECLINE. |
| **CAP-5** | **Real radical membership** f ∈ ʳ√I for 0-dim I (does f vanish on V_ℝ(I)?) | **CAP-6 applied twice** | f ∈ ʳ√I ⟺ #real(I)=#real(I+⟨f⟩) (real points only shrink under f=0; equal counts ⟺ containment). Sound for 0-dim. |
| **CAP-8** | **Rabinowitsch radical membership** f ∈ √I (ordinary radical) | `groebner.ideal_member_grade` | f ∈ √I ⟺ 1 ∈ I+⟨1−t·f⟩ in ℚ[x,t]; the cofactor certificate from the existing primitive *is* the witness. Thin sound wrapper. |
| **CAP-2** | **Richardson undecidability recognizer** — identity testing E≡0 over {+,−,×,sin,exp,abs,π,ln2} is undecidable | `decision_integration.risch_elementary` (decidable side) | recognizer: detect the Richardson class ⇒ FRONTIER-DECLINE (Richardson 1968); route the decidable sub-class (polynomial / exp-free elementary) to risch / real_qe. Prevents a false EXACT on an undecidable identity. |
| **CAP-3** | **MRDP / Hilbert-10 structural classifier** of an actual Diophantine system → decidable fragment or undecidable | `number_theory` (pell/linear/single-var), extends `barrierfold/nonlinear_int.classify` | structural front-end: linear→diophantine_grade, Pell-form→pell_grade, single-var→rational-root; general multivariate deg≥2 ⇒ MRDP undecidability FRONTIER-DECLINE. Extends, does not duplicate, nonlinear_int. |
| **CAP-7** | **Virtual substitution** ∃-QE for atoms of degree ≤ 2 (multivariate / parametric) | extends `mathmode/real_qe.py` | Weispfenning finite test-point elimination set; sound for the degree-≤2 fragment with a re-check. **Build only if the sound fragment is clean; else honest defer** (mirrors §AZ CAP-3/CAP-8 deferral). |

---

## D. §BA Axis-1 proposals — **DEFER (honest, soundness-critical / thin marginal value)**

| Cap | Why defer | Honest status |
|---|---|---|
| **CAP-9** | Automatic-structure FO decision (synchronized automata product/projection/complement). The canonical automatic structure (ℕ,+) is **already decided** by `presburger_qe.py`; a general automatic-structure engine reusing lstar/periodic_fsm is heavy and easy to get subtly *unsound* (padding/synchronization). Marginal value over Presburger is thin; soundness risk is high. | **DEFER** — documented, no code. Same discipline as §AZ's deferral of soundness-critical CAP-3/CAP-8. |

---

## E. Axis-2 fold candidates — **MEASUREMENT-FIRST** (no fold-rate claim without measurement)

Per §BA: build a recognition branch **only if the corpus is measured to contain the structure**; the
structureless residue is a permanent DECLINE. Measured in `CORPUS_MEASURE.md` before any build.

| Cand | Structure | Reuse target |
|---|---|---|
| C2-1 | DFA / regular string-scan (Myhill–Nerode / Hopcroft minimization) | `extract/periodic_fsm`, `mech_sfa` |
| C2-2 | bit-trick recognition (popcount already built — *recognition* branch only) | existing popcount kernels |
| C2-3 | DP → holonomic routing | `conjecture/holonomic_guess` → existing Zeilberger |

---

## F. Invariants this round must preserve (HONESTY SPINE)

- precision = 1.0, **false-EXACT = 0** (the only total-freeze trigger); DECLINE > wrong answer.
- zero external deps (z3 + stdlib + numpy + grandfathered sympy only).
- **14 / 22 mechanism saturation UNCHANGED** — every CAP is a new *decision/recognition branch* in an
  existing module, **not** a new mechanism.
- fold-rate impact of Axis-1 = **0** (capability ledger, not a fold). Axis-2 fold-rate only after measurement.
- no model identifier in any pushed artifact; "quantum speedup" remains a banned bigram.
- `test_build` 273 / 0 and `test_catalog` 0-fail preserved; `660` EXACT corpus invariant unchanged
  (new branches are not imported by the corpus engine, so the corpus count is invariant by construction).
