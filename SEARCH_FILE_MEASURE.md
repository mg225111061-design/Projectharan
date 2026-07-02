# SEARCH_FILE_MEASURE — §BI measured (honest)

★ Rule (unchanged): mechanisms, not magic; every "instant" claim is a measured number. CPU numbers reproduced by
`python3` on this build's machine — ratios + O() are the point, absolute ms vary. ★ The live web path (real
`web_search`/`web_fetch`) + per-format library extraction are **author-validated on Render** (the sandbox
egress-blocks the web and lacks most format libraries); what is measured here is the pure orchestration + the
stdlib compute-on-compressed gems.

## WORKSTREAM B — file attachment

### FL-1 registry — the honest "300+" is a measured count
`fileattach.registry.format_count()` = **457** distinct extensions, by honest depth tier:

| depth | count | meaning |
|---|---|---|
| TEXT_EXACT | 192 | deterministic byte-exact full text (extraction EXACT) |
| OFFICE_LOSSY | 49 | text high; tables/layout may be lossy |
| STRUCT | 51 | structure/values exact; semantics best-effort |
| OCR_LIMITED | 41 | metadata always; text via OCR (limited, never certified) |
| MEDIA_META | 40 | tags/metadata only; no transcript without ASR |
| ARCHIVE | 38 | route to the FL-2 bomb-guarded extractor |
| BINARY_PARTIAL | 28 | container metadata only |
| ENCRYPTED_BLOCKED | 14 | BLOCKED — never fabricated |
| PDF_TEXT | 4 | text layer high; tables/scan need OCR |

★ "300+" is this number, not a slogan. Each tier is the honest CEILING for that family.

### FL-3 compute-on-compressed — query without unpacking (the fold-spirit gem), measured
| operation | this build | baseline (unpack) | reading |
|---|---|---|---|
| zip 500 members: **central-dir list** | 1.56 ms | 6.99 ms (full extract) | **≈4× here**, and listing is O(#entries) vs extract O(uncompressed) — the gap **grows without bound** at GB scale |
| gzip ISIZE (uncompressed size) | 4 bytes read, **no inflate** | full inflate | size known without decompressing (exact for <4 GiB) |
| single-member range-read | 1 entry inflated | whole archive | "read the part you need" |
| **FM-index** count, N=2,000 | 0.015 ms/query | 0.276 ms naive scan | correct (== naive) **and never reconstructs the text** |
| **FM-index** count, N=8,000 | 0.074 ms/query | 0.689 ms naive scan | same — faster by a constant factor |

★ **Honest reading of the FM-index** (no overclaim): the headline compute-on-compressed property is that it
counts/locates a substring over the **BWT** (the transform bzip2 already stores) **without reconstructing the
original text**, and the answer is *verified equal to a naive scan* (no silent wrong answer). The query is faster
than the naive scan by a constant factor here — but in THIS implementation `Occ` is a linear BWT-prefix scan, so a
query is O(|pattern|·n), and you can see it grow with n (0.015 → 0.074 ms). The textbook O(|pattern|) (independent
of n) needs a precomputed rank table — that is the honest next step, documented in the code, not claimed as done.
The BUILD is O(n log n) (1.2 → 10.7 ms). So the real win is **repeated queries over a fixed compressed text** +
**never materializing it**, not an asymptotic free lunch.

### FL-2 / FL-5 — reused, not rebuilt (measured: imports + behaves)
`fileattach.reuse_status()` ⇒ `{FL2_bomb_guard: true, FL5_fold_route: true}` — the compression-bomb guard
(`mathmode/archive.py`: `Limits(max_depth=4, max_ratio=250, per-entry/total/count caps)`, in-memory, zip-slip
`_safe_name`) and the extracted-code/math→fold route (`mathmode/ingest.py`, cfinite/Gosper) are the existing,
robust implementations. Net-new added 0 new bomb mechanism and 0 new disposer.

### FL-4 completeness — extraction EXACT vs understanding uncertified (the honesty split, structural)
`check_completeness(declared, extracted)`: all unit counts equal ⇒ `kernel_verdict` **EXACT** (a passed
`extraction_completeness` cert); any shortfall ⇒ **DECLINE** with the exact gap. `certify_understanding()` ALWAYS
raises `UnderstandingCertificationError` (a `python -O`-proof guard) and every verdict carries
`understanding_certified == False`. ★ You can prove extraction is complete; you can NEVER get a certificate that
the file was understood (false-EXACT 0 on the comprehension claim).

## WORKSTREAM A — search engine (pure orchestration; live exec on Render)
| mechanism | measured | reading |
|---|---|---|
| **SR-1/SR-5** multi-query | "vector databases" @ deep ⇒ **16 distinct** sub-queries (breadth 16) | parallel coverage, **no padded repeats** (each meaningfully different) |
| **SR-3** cache | workload `[a,b,a,c,a,b,d,a]` ⇒ hits=4 misses=4, **hit-rate 0.50** | reuse = instant; the win IS the measured hit-rate, never asserted |
| **SR-2** deep-fetch | primary sources rank above aggregators; 1-hop follow stays ≥ page tier | better grounding; ranking is a prior, not a truth oracle |
| **SR-4** comprehend | quote forced **<15 words**, ≤1/source; conflicts shown both-sides | better CONTEXT, ★ never an understanding guarantee |

★ "순식간 (instant)" = parallel (SR-1) + reuse (SR-3) + bounded deep-fetch (SR-2) + compute-on-compressed (FL-3) —
all mechanisms above, each measured. No magic.

## Honesty (§4) — same constitution
- fold = loop-collapse ONLY; decompression is standard DEFLATE; FL-3 (query-without-unpacking) is the fold-spirit
  gem. No "fold로 압축 해제" anywhere (tested: banned bigrams absent).
- false-EXACT 0 → understanding-guarantee 0: extraction completeness is EXACT (count match, `kernel_verdict`);
  understanding is best-effort, certification structurally refused.
- per-format honest depth labels (measured table above); honest degrade (NEEDS_LIB via `file_ingest.HAVE`).
- security reused (bomb-guard + zip-slip from `mathmode/archive.py`); copyright quote-limit enforced in code.
- zero-dep core (stdlib + kernel_verdict); os-import-0 in `claude_agent.py` untouched.
- ★ Sandbox blocks external domains + most format test files ⇒ the live search execution + library-based
  extraction (docx/pdf/parquet/…) are **author-validated on Render**; code + push only here, no false "verified".
