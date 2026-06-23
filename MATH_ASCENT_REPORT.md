# MATH-ASCENT — report (the second top-level mode: CODE + MATH)

*A measured account. Every number below is reproduced by `test_build.py` (run with the deterministic thread
caps). Where a capability is blocked by the environment, it is marked UNVERIFIED, never faked.*

## What was built

OMEGA gave HARAN one top-level mode — **CODE**: take a program, emit faster *verified* code, grade
EXACT / PROBABILISTIC(ε,δ) / DECLINE. MATH-Ascent adds the second top-level mode — **MATH**: solve hard
mathematics, fold-first, with the same grade discipline and the same refusal to fabricate. The split is
enforced in code and re-asserted on every commit.

**20 new modules, ~2,570 lines, 23 new tests, deterministic suite 198/198 green.** The arsenal spans **15
verified families**; the served app gained a **CODE ⇄ MATH toggle**, **universal file attachment**, and **safe
archive extraction** (§B). (Three more families beyond the table below: `differential.py` — closed-form ODEs
verified by back-substitution; `graph.py` — shortest paths with an LP-duality optimality certificate +
bipartiteness witnesses; `special_functions.py` — exact Γ and ζ.)

| § | capability | module | grade story |
|---|------------|--------|-------------|
| 1 | CODE/MATH top-level split | `topmode.py` | routes differ + §B (fast/normal/extend) preserved inside BOTH |
| 2 | the central universal **fold** | `fold.py` | power-sum / recurrence / geometric / telescoping / poly-identity → EXACT or honest DECLINE |
| 3 | number theory | `number_theory.py` | egcd, modinv, CRT, modexp, Diophantine — certificate = the checked identity |
| 3 | combinatorics / sums | `combinatorics.py` | **Gosper** creative-telescoping (decision procedure), binomial, Catalan |
| 3 | linear algebra | `linear_algebra.py` | exact ℚ solve / inverse / det — self-certifying (residual, A·A⁻¹=I) |
| 3 | symbolic algebra | `algebra.py` | factor / gcd / roots — self-certified; quintic ⇒ Abel–Ruffini DECLINE |
| 3 | geometry | `geometry.py` | exact rational area / hull / intersection / point-in-polygon |
| 3 | certified numerics | `certified_numeric.py` | EXACT enclosures (Sturm, IVT, √) vs honest PROBABILISTIC (Monte-Carlo) |
| 3 | optimization | `optimization.py` | exact LP — self-certifying **strong-duality** (zero gap ⇒ optimal) |
| 3 | science / engineering | `science_engineering.py` | dimensional analysis over 7 SI base dims (catches `E=mv`) |
| B4 | probability / statistics | `probability.py` | exact distributions + **proven** Markov/Chebyshev bounds (EXACT, not δ) |
| B4 | inequalities | `inequalities.py` | polynomial nonnegativity — certified, or an exact counterexample |
| 4 | O(1) broth proving | `broth.py` | lookup + cheap recheck over 3,772 entries |
| 5 | visible grade-tagged reasoning | `solver.py` | one MATH entry point; `trace()` shows route→recognize→fold/broth/arsenal→grade |
| 6 | universal file ingestion | `ingest.py` | XLSX/DOCX/PPTX via stdlib; fold-accelerated sequence analysis |
| B3 | safe archive extraction | `archive.py` | zip/tar/gz → enumerate; zip-slip + bomb defenses (in-memory) |
| 7 | measured capability benchmark | `benchmark.py` | 36 problems / 14 domains, measured deltas only |

## The center: fold (§2)

Mathematics always has structure, so MATH's default first move is **fold**: recognize the structure FIRST, route
to the right method, and **co-generate a machine-checked certificate** — folding and proving are one act.

- **power sums** → Faulhaber, proven for ALL n by induction: base `cz(0)=0` ∧ the polynomial step
  `cz(n)−cz(n−1)=n^p` (decided over ℝ by nlsat; ℝ ⊇ ℤ ⇒ integer-valid). O(1) evaluation.
- **C-finite recurrences** → companion-matrix O(log n), exact integers (companion ≡ naive, verified).
- **geometric / telescoping** → closed form, verified ≡ the naive partial sum on a probe.
- **polynomial identities** → e-graph equality saturation, Z3-certified `term ≡ rewrite`.

Where there is no foldable structure — or no stocked closed form — fold **DECLINEs honestly**. The anti-fabrication
moat is real and tested: the same k-induction gate that licenses a Faulhaber fold *refuses* a wrong identity
(`Σk²` is not `n³`), and a wrong Gosper antidifference fails the telescoping certificate.

## Ultra-fast proving over the broth (§4 + §8)

The expensive proof is paid **once, offline**; at runtime a recognized identity is proven by an **O(1) dict
lookup + a cheap recheck** (PRA finite-base for sums, companion-equality for C-finite) — never a re-search.

- Measured lookup cost: **~0.09 µs**, constant across the index.
- The base library could **not** brew the hypergeometric family (it needs `ore_algebra`, **[BLOCKED]** here).
  **Gosper** (sympy, dependency-light) brews it anyway: we generate a hypergeometric summand family, Gosper-sum
  each, and keep only the closed forms that pass the same cheap recheck — and cross-check each against the exact
  brute-force partial sum.
- **Broth grown 3,707 → 3,772** (+65 genuinely-new hypergeometric entries). The recheck — not sympy's word —
  licenses EXACT.

## Visible reasoning (§5)

One entry point, `mathmode.solver.solve`, with the reasoning as the product:

```
[MATH mode]
  → route: top_mode=MATH; first move = fold; fold_is_central=True
  → recognize: summation Σ_(k≥1) k**4*2**k — try the broth, then Gosper fold
  → broth: O(1) lookup MISS — pay for the Gosper fold
  → fold: Gosper creative-telescoping — T(k+1)−T(k)=f(k) verified ⇒ Σ f = T(b+1)−T(a) ∀ range «EXACT»
  ⇒ EXACT: gosper_telescoping
```

An honest DECLINE shows exactly where the structure ran out; a Monte-Carlo answer is tagged «PROBABILISTIC», never
EXACT. The grade discipline carries verbatim from CODE into MATH.

## File ingestion (§6) — honest about its limits

- **XLSX / DOCX / PPTX** parsed with the **standard library** (zip + XML), no fragile dependencies; CSV/JSON/TXT
  too. The headline is fold acceleration: a spreadsheet column that is secretly a C-finite sequence is recognized
  (shortest exact recurrence, verified on every term) and folded to an O(log n) closed form.
- **PDF** — `pypdf` is broken in this environment (`cryptography/_cffi_backend` panics) ⇒ honest **UNVERIFIED**.
- **Images / photos of equations** — no OCR engine (no `tesseract`) ⇒ honest **UNVERIFIED**; equation→symbolic is
  not attempted rather than fabricated.

## Measured capability (§7) — and the honest HLE position

A representative benchmark of **36 problems across 14 domains**, run through the solver and graded:

- **EXACT = 28, PROBABILISTIC = 1, DECLINE = 7** — and all **36/36 match their expected grade**. The seven DECLINEs
  are *correct behaviour*: the harmonic sum `Σ1/k`, a singular linear system, the Abel–Ruffini quintic `x⁵−x+1`,
  parallel segments, a non-existent modular inverse, a dimensionally-wrong formula (`E=mv`), and `x²−1` (which is
  *not* globally nonnegative — the certifier returns the exact counterexample `x=0`).
- **22** of the EXACT answers are independently cross-checked against ground truth (an EXACT here is a *verified*
  answer, not a claim); every EXACT carries a passed certificate (the ADT enforces it, the bench re-asserts it).

**On HLE:** Humanity's Last Exam is **UNVERIFIED** in this environment — there is no HLE dataset and no scoring
harness here. Reporting an HLE number would be a fabricated score, which "measured deltas only" forbids. What is
measured is the arsenal's coverage on this representative set; the honest path to a higher HLE is *more verified
tools + more broth*, each measured the same way.

## §B — the second mode made usable: toggle, attachment, archives

- **B1 — the CODE ⇄ MATH toggle.** A prominent segmented control in the top bar (`코드` ⇄ `수학`) re-themes the
  whole surface (green MATH accent via `data-top="math"`) and re-routes it: CODE → the wizard → `/api/optimize`;
  MATH → the fold-first solver → `POST /api/math/solve`. The **fast/normal/extend** sub-selector is preserved
  inside each mode — MATH `extend` is EXACT-or-DECLINE (`solver.solve_in_mode` applies the §B grade floor). The
  reasoning + certificate are visible in both. An invariant test asserts the toggle wiring, the different routing,
  and the floor.
- **B2 — universal file attachment.** A drag-drop zone + file picker in the MATH surface; `POST /api/math/ingest`
  (base64, 300 MB guard) runs `ingest.analyze_upload`: detect → safely extract → fold-accelerated analysis. A
  spreadsheet column that is a C-finite sequence folds to an O(log n) closed form (EXACT); a `Σ …` line routes to
  the broth/Gosper fold. PDF/images ⇒ honest UNVERIFIED.
- **B3 — safe archive extraction.** `archive.py` unpacks zip/tar/gz/bz2/xz **in memory** (so zip-slip cannot
  touch the filesystem), enumerates + types every inner file, recurses nested archives to a bounded depth, and
  refuses decompression bombs (per-entry / total / count / ratio / depth caps) and traversal names. 7z/rar ⇒
  honest UNVERIFIED. Security-tested: a crafted zip-slip / bomb is refused safely, never crashes, never escapes.

## Constitution held, verbatim

- **EXACT only with a machine-checked certificate.** Approximation / randomization is PROBABILISTIC(ε,δ) and
  **never** EXACT — not even the Monte-Carlo at a tiny δ (a sample count is not a proof, §0.2).
- **fold DECLINEs honestly** where there is no structure / no closed form — never a fabricated formula.
- **Never "smarter/faster than a model."** MATH wraps exact engines (Z3, sympy as a *search* engine behind our own
  checks) — the certificate, not the library's word, is what licenses a grade.
- **No Lean/Coq/Isabelle.** Z3 for the proofs; sympy searches, our checker proves.
- **fast / normal / extend** separation preserved **inside both** CODE and MATH, asserted per commit.
- **Keys session-only; phone-home = 0** except the provider API. Unchanged.

## Reproduce

```
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 test_build.py
# … 198 passed, 0 failed
```

The 23 MATH-Ascent tests are `test_mathascent_*`. The progress ledger is `MATH_ASCENT_PROGRESS.md`.
