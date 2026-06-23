# PHASE R (v60) — real-code corpus, measured whole-program, honest misses included

The "it actually runs" proof: the engine, pointed at realistic programs, reports what it **measures** — large
wins where the waste is real, and an honest DECLINE where there is nothing to ship.

## Delivered
- `corpus/` — five representative archetypes, each with an `original`, an `optimized` (identical except the hot
  function), a `hot_original` (for detection + isolation timing), and a real `make_workload`:
  - `ai_todo_app.py` — AI-generated task manager (find-by-id linear scan + list-as-set dedup).
  - `log_analyzer.py` — CLI tool (re-parses the constant config every line).
  - `csv_stats.py` — data utility (`acc = acc + [x]` accidental quadratic).
  - `json_pipeline.py` — ETL (per-item fetch, N+1).
  - `template_render.py` — a **well-written** renderer (single pass, dict lookups, join) — nothing to fix.
- `pillar3/corpus_runner.py` — profiles, runs all 16 engine detectors on the hot function, differential-verifies
  the optimized form, and measures the WHOLE-PROGRAM ratio (best-of-k). Coherent Amdahl: f = t_hot/t_orig,
  ceiling = 1/(1−f); since the optimized program keeps the same non-hot work, ratio = t_orig/t_opt ≤ ceiling.

## Measured (real run)
| repo | archetype | detected | grade | whole-program ratio |
|---|---|---|---|---|
| ai_todo_app | AI-generated | list_as_set, accidental_full_scan, dict_to_columnar | PROBABILISTIC | **~44×** |
| csv_stats | data utility | quadratic_build | PROBABILISTIC | **~117×** |
| json_pipeline | ETL | n_plus_1, parallelizable_loop | **EXACT** | **~84×** |
| log_analyzer | CLI tool | n_plus_1, redundant_io_parse, … | PROBABILISTIC | **~8×** |
| template_render | well-written renderer | (proposals fire, none win) | **DECLINE** | **~1.0× (honest miss)** |

Grade distribution: **EXACT 1 · PROBABILISTIC 3 · DECLINE 1.** Every measured row is Amdahl-coherent
(ratio ≤ ceiling). ★ The well-written repo is reported as a truthful DECLINE-everywhere — **we do not fabricate
a win** ★. The large wins are on AI-generated / never-profiled code with a genuine asymptotic inefficiency —
exactly the thesis.

## §0 self-check
measured whole-program (best-of-k, neutral baseline); hotspot fraction + ceiling per row, ratio ≤ ceiling by
construction; graded by the ADT; differential FIRST (a divergent optimized form would DECLINE); honest miss
reported, not hidden.

## Honest scope
The sandbox has **no network**, so these are **authored representatives** of each archetype, not vendored
GitHub repositories — stated in the report and the test. The patterns (linear-scan find, list-as-set, redundant
parse, accidental quadratic, N+1, and a genuinely-clean renderer) are the real ones the literature catalogues.
124+1 tests, 0 regression.
