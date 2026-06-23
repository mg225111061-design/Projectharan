# MATH-ASCENT — live tracker (post-OMEGA, GREENLIT choice B)

OMEGA's high-value core is DONE (Rounds 1+2+3 = 90/90 dispositioned; EXACT-share 68%; §B mode-separation
per-commit; deterministic suite green). MATH-Ascent builds the second top-level mode on top of it.

DoD per item: structure recognized → method produces a result → **certificate co-generated** (folding and proving
are one act) → graded by the ADT (EXACT machine-checked / PROBABILISTIC(ε,δ) / honest DECLINE) → closed form
cross-checked vs brute-force ground truth (never a fabricated formula) → adversarial-wrong ⇒ DECLINE → committed
→ ticked with test. Suite green each item. §A2: substitute on genuine failure, never fake. NEVER stop.

Constitution carried verbatim: EXACT only with a machine-checked certificate; approximation/numeric is
PROBABILISTIC(ε,δ), never EXACT even at δ≤1e-18; fold DECLINEs honestly where there is no structure / no closed
form (never a fabricated formula); never "smarter/faster than a model"; keys session-only; phone-home = 0 except
provider API; No Lean/Coq/Isabelle (Z3 only); fast/normal/extend separation preserved INSIDE both CODE and MATH.

Legend: ☑ done(new, tested) · ◩ wired-from-existing (cite) · ☐ pending · ⚠ UNVERIFIED[reason]

## §1 — CODE / MATH top-level split (fast/normal/extend preserved inside each)
1. ☑ TopMode {CODE, MATH}: route() gives each a different toolset + first-move + verifier emphasis. CODE first
   move = profile→recognize (fold NOT central); MATH first move = fold (central, structure-first). Per-commit
   invariant `routes_differ()` asserts the split AND `inner_modes()` proves §B is preserved VERBATIM inside both
   (fast=MICRO/never-Z3; extend=EXACT-or-DECLINE; normal=EXACT+PROBABILISTIC). [test_mathascent_topmode_split;
   mathmode/topmode.py]

## §2 — FOLD: the central ZFC-grade universal structure-folding tool
2. ☑ fold(object) → FoldResult{closed_form | canonical_form | DECLINE, certificate}. Recognizes structure FIRST,
   routes to the method, co-generates a machine-checked certificate. Folders, each EXACT-or-DECLINE:
     • power_sum → Faulhaber, k-induction-proven ∀n (base cz(0)=0 ∧ polynomial step cz(n)−cz(n−1)=n^p over ℝ;
       nlsat decides it; ℝ⊇ℤ ⇒ integer-valid), p=0..4, O(1). Beyond-stock degree ⇒ DECLINE.
     • linear_recurrence → companion-matrix O(log n) (cfinite verify ≡ naive), exact integers. [fib, tribonacci]
     • geometric_sum → (r^n−1)/(r−1), verified ≡ naive on a probe.
     • telescoping_sum → g(n)−g(0), verified ≡ naive.
     • polynomial_identity → e-graph equality saturation, Z3-certified term≡rewrite.
   Every EXACT closed form cross-checked vs brute-force ground truth. Unstructured / non-object / beyond-stock ⇒
   honest DECLINE (no fabricated formula). The k-induction GATE refutes a wrong identity (anti-fabrication moat).
   [test_mathascent_fold_universal; mathmode/fold.py]

## §3 — verified solving/proving arsenal (fold central, computation offloaded from the LLM)
3a. ☑ number_theory — egcd/Bézout, modular inverse, CRT, modexp O(log b), linear Diophantine; each EXACT with
    the checked identity AS the certificate; no-inverse / inconsistent-CRT / gcd∤c ⇒ honest DECLINE; 300-case
    exact fuzz (every EXACT cert holds, every DECLINE genuinely unsolvable). [test_mathascent_number_theory;
    mathmode/number_theory.py]
3b. ☑ combinatorics_sums — Gosper creative-telescoping (DECISION procedure): indefinite/definite hypergeometric
    summation, EXACT closed form certified by OUR telescoping check (T(k+1)−T(k)=t(k) ∧ exact brute-force
    cross-check), PROVEN-no-closed-form (1/k, 1/k!) ⇒ DECLINE, wrong antidifference ⇒ cert refuses; binomial
    (Pascal) + Catalan (two-forms) recurrence-checked. sympy searches, our checker proves.
    [test_mathascent_combinatorics_gosper; mathmode/combinatorics.py]
    Remaining: ☐ algebra_symbolic · ◩ linear_algebra (v40 Toeplitz/WHT/matmul exist — wire) · ☐ geometry ·
    ◩ logic_verification (Z3 wired) · ◩ certified_numeric (Freivalds/interval exist) · ☐ optimization_or ·
    ☐ science_engineering · ☐ Zeilberger (definite-sum recurrences).

## §4 — ultra-fast certificate proving over the 3000+ broth (O(1) lookup)
   ☐ index the proven-closed-form broth; O(1) certificate retrieval on a recognized structure.

## §5 — visible grade-tagged reasoning in both modes
   ☐ surface fold's recognized-structure + certificate kind + grade in the UI reasoning trace (CODE and MATH).

## §6 — universal file ingestion + fold-accelerated analysis
   ☐ PDF/DOCX/PPTX/XLSX/images (incl. photos of equations → symbolic); honest DECLINE on unstructured/OCR limits.

## §7 — MATH deliverables + honest HLE push (measured deltas only)
   ☐ MATH demo set; measured-only deltas; never an unmeasured score claim.

## §8 — grow Layer-2 LEAP reports + Layer-3 mathematical broth
   ☐ LEAP{1..5} math reports; Layer-3 mathematical broth entries.

RESUME POINTER: §1 + §2 landed (the split + the central fold, both tested). Next: §3 arsenal — start with
combinatorics_sums (Gosper/Zeilberger creative-telescoping for hypergeometric sums) and number_theory, each
fold-routed, certificate co-generated, adversarial-wrong ⇒ DECLINE. Then §4 O(1) certificate index over the broth.
