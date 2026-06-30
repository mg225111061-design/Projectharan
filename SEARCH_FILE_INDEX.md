# SEARCH_FILE_INDEX — §BI search + file-attachment upgrade, pre-build index (§2)

★ Two honesty corrections are the SPINE (state them or we misuse fold / false-EXACT):

**Correction 1 — "decompress via fold" is a fold MISUSE.** fold = collapse a loop to a closed form
(Σk → n(n+1)/2). zip decompression is DEFLATE (Huffman + LZ77), already O(n)-optimal — there is no loop to
collapse. The honest + genuinely strong version is (a) **standard fast decompression** (NOT fold — say so) +
(b) ★ **compute-on-compressed**: query the compressed bytes *without unpacking* (zip central-directory listing,
range-read, FM-index substring search, columnar predicate-pushdown). THAT is the fold spirit ("안 하기" — don't do
the work). The phrase "fold로 압축 해제" is banned.

**Correction 2 — "100% understanding" splits into two claims.** 100% **extraction** (deterministically pull all
text/structure + verify completeness) is **possible, verifiable, EXACT**. 100% **understanding** (the LLM grasps
meaning) is **probabilistic — never guaranteeable**; certifying it would be a false-EXACT. So the goal is *100%
extraction with honest per-format depth limits*; LLM understanding stays **best-effort + stated limits**, never
certified. false-EXACT 0 applies to the understanding claim.

★ "순식간 (instant)" honest definition: **parallel** (concurrent multi-query) + **caching** (reuse) +
**range-read** (partial) + **compute-on-compressed** (don't unpack). Mechanisms, not magic.

## Already built — reuse map (re-build 0)
| item | gem | already-built | net-new this build |
|---|---|---|---|
| **A search** | gate OFF=0 / ON=judged | `search_gate.py` (§SEC PART 2) — `tools_for`/`system_suffix`, fail-safe OFF | — (built; the contract) |
| **A search** | no live backend (honest) | `SEARCH_INDEX.md` — no web tool wired; sandbox egress-blocks the web | — (live exec author-validated on Render) |
| **SR-3** | result/page caching | `pillar3.detectors2.detect_interproc_memoize` (content-hash reuse pattern) | thin `search/cache.py` over the same idea |
| **B file** | format detect + honest degrade | `file_ingest.py` (S21) + `mathmode/ingest.py` (LIVE, `/api/math/ingest`) — ext/magic, EXTRACTED/LOWCONF/BLOCKED/FAILED, never fabricate | FL-1 generalizes the *labeling* to 300+ |
| **FL-2** | ★ compression-bomb guard | ★ **`mathmode/archive.py`** — `Limits(max_depth=4, max_ratio=250, per-entry/total/count caps)`, in-memory (no zip-slip), `_safe_name`, refuse-with-reason | — (built, robust; reuse) |
| **FL-5** | extracted code/math → fold | ★ **`mathmode/ingest.py`** — C-finite recognition (`cfinite`) + Gosper, honest UNVERIFIED/DECLINE | — (built; rides `recall/core`) |
| **FL-5** | single disposer | `recall/core.fold_via_ai` (false-EXACT 0) | — (every fold rides it) |
| office | stdlib extraction | `mathmode/ingest.py` — XLSX/DOCX/PPTX via `zipfile`+`xml` (no fragile deps) | — (built) |

## net-new this build (§3) — orchestration / registry / index logic (pure, testable offline)
**WORKSTREAM A — search engine** (live `web_search`/`web_fetch` execution is author-validated on Render; the
*logic* below is pure and tested here):
1. `search/multi_query.py` — **SR-1** decompose a broad query into *distinct* sub-queries (no repeats) + **SR-5**
   breadth dial (1 for a simple fact → 8–20 for deep research) + result dedup by URL/content-hash.
2. `search/deep_fetch.py` — **SR-2** source-priority ranking (original/company/peer-reviewed/gov/SEC > aggregator)
   + a 1-hop link-selection plan. The fetch is an injected callable ⇒ testable without network.
3. `search/cache.py` — **SR-3** content-hash cache for search results + fetched pages (reuse = instant).
4. `search/comprehend.py` — **SR-4** structured extraction (title/date/author/key-claims) + credibility ranking +
   ★ conflict surfacing (disagreeing sources shown both-sides w/ attribution) + recency weighting + ★ copyright
   (quote <15 words · 1 per source · paraphrase-preferred). ★ This is *better context*, NOT an understanding
   guarantee — LLM comprehension stays probabilistic.

**WORKSTREAM B — file attachment** (reuses FL-2 bomb-guard + FL-5 fold-route above):
5. `fileattach/registry.py` — **FL-1** 300+ extension/magic → (category, ★honest depth-label) map. Depth tiers:
   `TEXT_EXACT` (txt/md/json/csv/code…) / `OFFICE_LOSSY` (docx/xlsx/pptx/odt… tables/layout may be lossy) /
   `PDF_TEXT` (text layer high; tables/scan limited) / `OCR_LIMITED` (images) / `STRUCT` (parquet/hdf5/npy… structure) /
   `BINARY_PARTIAL` (proprietary) / `ENCRYPTED_BLOCKED` / `NEEDS_LIB` (honest degrade if optional lib absent).
6. `fileattach/compute_on_compressed.py` — **FL-3 ★the gem**: zip central-directory listing (members + sizes,
   *no extraction*) + single-member range-read + gzip ISIZE (no inflate) + an in-repo **FM-index/BWT** that counts a
   substring's occurrences in the transformed text *without materializing the original*. Falls back to FL-2 standard
   decompress when a format isn't query-on-compressed-able. ★ honest: specific formats only, not universal.
7. `fileattach/completeness.py` — **FL-4 ★100% extraction**: verify declared count (pages/sheets/slides/entries) ==
   extracted count ⇒ completeness EXACT (or an explicit gap). ★ Splits extraction (verified) from understanding
   (best-effort) — never claims "100% understanding".

## Honesty (§4)
- fold = loop-collapse ONLY; decompression is standard; the compute-on-compressed gem is the fold-spirit win. No
  "fold로 압축 해제".
- false-EXACT 0 → understanding-guarantee 0: extraction completeness is verified (count match); understanding is
  never certified.
- per-format honest depth labels (TEXT_EXACT … ENCRYPTED_BLOCKED); honest degrade (NEEDS_LIB, never fabricate).
- "순식간" = parallel + cache + range-read + compute-on-compressed (mechanisms, measured in SEARCH_FILE_MEASURE.md).
- security: bomb-guard (size/ratio/depth) + path-traversal reuse `mathmode/archive.py`; copyright quote-limit in
  `comprehend.py`. zero-dep core (stdlib); format libs optional + honest degrade. os-import-0 in `claude_agent.py`.
- ★ Sandbox blocks external domains + most format test files ⇒ the live search execution + the per-format library
  extraction are **author-validated on Render**; code + push only here, no false "verified".
