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
    exact fuzz. +PRIMALITY (deterministic Miller–Rabin < 3.317e24 ⇒ EXACT proof; above ⇒ PROBABILISTIC(δ=4⁻ᵏ) for
    prime, EXACT witness for composite) + FACTORIZATION (Pollard rho; ∏pᵢ^eᵢ=n ∧ each prime) + Euler φ +
    DISCRETE LOG (BSGS O(√m), cert g^x≡h; no-solution/non-invertible ⇒ DECLINE).
    [test_mathascent_number_theory, test_mathascent_b4_primality; mathmode/number_theory.py]
3b. ☑ combinatorics_sums — Gosper creative-telescoping (DECISION procedure): indefinite/definite hypergeometric
    summation, EXACT closed form certified by OUR telescoping check (T(k+1)−T(k)=t(k) ∧ exact brute-force
    cross-check), PROVEN-no-closed-form (1/k, 1/k!) ⇒ DECLINE, wrong antidifference ⇒ cert refuses; binomial
    (Pascal) + Catalan (two-forms) recurrence-checked. sympy searches, our checker proves.
    [test_mathascent_combinatorics_gosper; mathmode/combinatorics.py]
3c. ☑ linear_algebra — exact ℚ (Fraction, never float), SELF-CERTIFYING: solve A·x=b [residual A·x−b=0],
    inverse [A·A⁻¹=I], determinant [fraction-free Bareiss ≡ cofactor (n≤7) / sympy exact (n>7)]; singular ⇒
    honest DECLINE; 200-case fuzz. +EIGENPAIRS [exact, self-certified by A·v=λ·v; rational+algebraic closed form;
    generic 5×5 RootOf ⇒ DECLINE]. [test_mathascent_linear_algebra, test_mathascent_b4_eigen; mathmode/linear_algebra.py]
3d. ☑ algebra_symbolic — factor [expand(∏factors)≡poly], polynomial gcd [g|p ∧ g|q exact division], root-solving
    [every root explicit ∧ p(root)≡0]; general quintic ⇒ honest DECLINE (Abel–Ruffini, RootOf ≠ closed form).
    sympy searches, our exact check proves. [test_mathascent_algebra_symbolic; mathmode/algebra.py]
3e. ☑ geometry — exact rational (no float): polygon area [shoelace≡triangulation], convex hull [convex ∧
    contains every input], segment intersection [point on both segments / else DECLINE], point-in-polygon
    [ray-cast≡winding]; 120-case random-hull fuzz. [test_mathascent_geometry; mathmode/geometry.py]
3f. ☑ certified_numeric — EXACT enclosures (Sturm real-root count ≡ isolation; IVT sign-change root bracket;
    √n rational bracket lo²≤n≤hi²; ε=width not δ) vs honest PROBABILISTIC Monte-Carlo (Hoeffding ε,δ — never
    EXACT); no sign change / neg √ ⇒ DECLINE. [test_mathascent_certified_numeric; mathmode/certified_numeric.py]
3g. ☑ optimization — exact LP (max cᵀx s.t. Ax≤b, x≥0) by rational vertex enumeration, SELF-CERTIFYING via
    STRONG DUALITY (feasible primal x* + feasible dual y* + zero gap ⇒ x* PROVABLY optimal); unbounded/infeasible
    ⇒ honest DECLINE. [test_mathascent_optimization_and_science; mathmode/optimization.py]
3h. ☑ science_engineering — dimensional analysis over the 7 SI base dims (exponent-vector algebra): an equation
    is EXACT iff both sides share a dimension vector; a dimensionally-wrong formula (E=m·v) ⇒ DECLINE (a real
    bug-catcher); derive a result's units EXACT. [test_mathascent_optimization_and_science; mathmode/science_engineering.py]
    Arsenal = 10 families. Remaining/honest-blocked: ◩ logic_verification (Z3 wired) · ⚠ Zeilberger definite-sum
    recurrences [BLOCKED: ore_algebra absent — not faked] · ☐ ODE/PDE · ☐ tensor · ☐ probability · ☐ inequalities/SOS.

## §4 — ultra-fast certificate proving over the 3000+ broth (O(1) lookup)
4. ☑ broth proving — prove() does O(1) dict lookup over 3,772 entries + a CHEAP recheck (PRA finite-base for sums,
   companion-equality for C-finite) ⇒ EXACT, never a re-search; miss ⇒ honest DECLINE (fall back to fold). §8
   GROWTH: the base library could NOT brew the hypergeometric family ([BLOCKED: ore_algebra]); GOSPER (sympy,
   dependency-light) brews it — +65 NEW hypergeometric entries kept (only those passing the cheap recheck),
   closed forms cross-checked vs brute force. Lookup ~0.08µs CONSTANT (offline brew paid once: ~6.6s).
   [test_mathascent_broth_proving; mathmode/broth.py]

## §5 — visible grade-tagged reasoning in both modes
5. ☑ unified MATH-mode solver (mathmode/solver.py): one entry point following the §1 route (MATH ⇒ first move =
   fold), broth-accelerated (O(1)) before paying for a fold, arsenal for the rest — RECORDING every step with its
   grade. `MathSolution.trace()` renders the visible reasoning: route → recognize → broth/fold/arsenal → grade.
   Honest DECLINE shows exactly where structure ran out. [test_mathascent_solver_reasoning; mathmode/solver.py]

## §6 — universal file ingestion + fold-accelerated analysis
6. ☑ ingest (mathmode/ingest.py): XLSX/DOCX/PPTX via STDLIB zip+XML (no fragile deps), CSV/JSON/TXT too. Fold
   acceleration: a numeric column → shortest exact C-finite recurrence (find_recurrence, verified every term) →
   O(log n) companion FOLD «EXACT»; a 'Σ …' / 'sum: …' line → broth/Gosper fold. Non-C-finite column (primes) /
   prose ⇒ honest DECLINE; PDF (pypdf [BLOCKED]) & images (no OCR/tesseract) ⇒ honest UNVERIFIED — never a
   fabricated transcription. [test_mathascent_file_ingestion; mathmode/ingest.py]

## §7 — MATH deliverables + honest HLE push (measured deltas only)
7. ☑ capability benchmark (mathmode/benchmark.py): 24 problems across 7 domains run through the solver and graded;
   measured inventory EXACT=18 / PROBABILISTIC=1 / DECLINE=5 (all 24 matching expected grade — the DECLINEs are
   CORRECT: harmonic, singular, Abel–Ruffini quintic, parallel segments, no modular inverse); every EXACT
   certificated; 15 answers cross-checked vs ground truth. HLE itself UNVERIFIED (no dataset/harness) — measured
   coverage reported, never a fabricated score. [test_mathascent_benchmark; mathmode/benchmark.py]

## §8 — grow Layer-2 LEAP reports + Layer-3 mathematical broth
8. ☑ Layer-3 broth grown +65 Gosper hypergeometric entries (§4, the family the base could not brew without
   ore_algebra). Layer-2 report: MATH_ASCENT_REPORT.md (the comprehensive measured account of the ascent).

STATUS: §1–§8 all landed and tested. MATH-Ascent core complete; arsenal = 10 families. Now in §B (UI + power).

## §B — the four additions (UI toggle, file attach, archives, both-stronger)
B1. ☑ CODE ⇄ MATH mode toggle (UI). Prominent OUTER segmented control (코드/수학) in the top bar; re-themes
    (data-top="math", green accent) AND re-routes (MATH screen map: mathLanding→mathMode→mathProblem→mathResult).
    INNER fast/normal/extend preserved inside MATH (scrMathMode binds S.mathMode; extend EXACT-or-DECLINE via the
    §B grade floor in solver.solve_in_mode). Wired to the real engine: MATH → POST /api/math/solve (mathmode.solver),
    CODE → /api/optimize. Reasoning visible in both (the grade-tagged trace + expandable certificate). Korean,
    design unchanged. Node DOM-stub smoke renders both surfaces; invariant test asserts toggle + routing + floor.
    [test_mathascent_b1_mode_toggle; mrjeffrey.html, server.py /api/math/solve, mathmode/solver.solve_in_mode]
B2. ☑ universal file attachment. UI: drag-drop zone + picker in the MATH problem screen, attached-file list with
    remove + per-file progress + grade-tagged findings. Backend: POST /api/math/ingest (base64 JSON, 300MB guard)
    → mathmode.ingest.analyze_upload → detect→extract→fold-accelerated analysis, JSON-safe. Office (xlsx/docx/pptx)
    via stdlib zip+XML; CSV/JSON/text; archives via B3; PDF/images ⇒ honest UNVERIFIED. Fold acceleration: a
    sequence column → O(log n) closed form. [test_mathascent_b2_file_attachment; mathmode/ingest.py, server.py]
B3. ☑ archive extraction (mathmode/archive.py). zip/tar/gz/bz2/xz → enumerate+type every inner file; nested
    zip-in-zip bounded recursion; SAFE BY CONSTRUCTION (in-memory, no disk writes ⇒ zip-slip can't touch FS) plus
    name refusal; bomb defense (per-entry/total/count/ratio/depth caps); 7z/rar ⇒ honest UNVERIFIED. Security-
    tested (zip-slip + bombs refused, never crashes). [test_mathascent_b3_archive_safety; mathmode/archive.py]
B4. ◩ in progress (both stronger). MATH arsenal broadened to 12 families: +optimization (LP duality),
    +science_engineering (dimensional analysis), +probability (exact distributions + PROVEN Markov/Chebyshev
    bounds), +inequalities (polynomial nonnegativity, certified or counterexample). §7 benchmark grown to 30
    problems / 11 domains (EXACT=22, PROBABILISTIC=1, DECLINE=7, all matching expected; 17 cross-checked). Broth
    3,772 (Gosper-grown). +differential (closed-form ODEs verified by back-substitution; no closed form ⇒ DECLINE)
    +graph (shortest paths with the LP-duality optimality certificate; bipartiteness via 2-coloring / odd-cycle
    witness — both EXACT) ⇒ arsenal = **14 families**. [test_mathascent_b4_probability_inequalities,
    test_mathascent_b4_differential, test_mathascent_b4_graph; mathmode/{optimization,science_engineering,
    probability,inequalities,differential,graph}.py]. CONTINUE: tensor/special functions, grow broth, code-side
    EXACT levers, richer reasoning.
