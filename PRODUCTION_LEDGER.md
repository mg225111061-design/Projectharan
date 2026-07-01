# PRODUCTION_LEDGER — 10H directive (tool catalog + SWE-bench) reachability registration

*Purpose: the 10H directive's Task 5 requires every new/modified file from Tasks 1–4 to be registered here so
none are orphans — "wired" means a real, callable, test-verified reach path exists, not a claim. Method: the
**verdict** column is `engine_inventory.classify(path)`'s ACTUAL return value (run directly against this repo,
not eyeballed), using the repo's own established vocabulary (`engine_inventory.py`'s own header comment defines
each term — see lines 6–15) rather than inventing new terms. The **evidence** column names the concrete test(s)
or reach-probe call site that exercises the file — grep/read-confirmed, not assumed. Scope: only the 10H
directive's own files (Tasks 1–4). The separate, much larger repo-wide violation-audit effort (`AUDIT_LEDGER.md`,
task §BS-2 / tracker #309 — CLEAN/FIXED/FLAG/N/A grade-honesty review of the other ~700 pre-existing files) is
NOT duplicated here; the two ledgers answer different questions (this one: "is it reachable, not an orphan?";
that one: "does its grade emission tell the truth?").*

## Files registered (18 changed; 4 docs + `.gitignore` excluded below as non-engine)

| # | file | pkg | role | verdict (`classify()`) | reachability evidence | commit |
|---|------|-----|------|------------------------|------------------------|--------|
| 1 | `agenttools/__init__.py` | agenttools | package entry (defines `adversarial_battery()`; module-level side effect imports the 3 catalog submodules) | `package_init` | Runs on any `import agenttools` — which is exactly what `webapi/engine_dispatch.py::agenttools_reach()` does. Its own module-level `from agenttools import catalog_accel, catalog_fold, catalog_plain` (line near EOF) reaches those 3 files directly on import; `adversarial_battery()` (called by the reach-probe) additionally imports `capability`/`executor`/`registry`/`router`. Verified by direct read of the file, not assumed. | 804b62b (created), 4727079 (catalog imports added) |
| 2 | `agenttools/registry.py` | agenttools | the `Tool` dataclass + `_REGISTRY` dict (RF-5 tier enforcement, `register`/`unregister`/`get`/`all_tools`/`counts_by_tier`) | `transitive` | Imported by `adversarial_battery()` (`agenttools_reach()`'s target) AND directly exercised by `test_10h_tool_registry_tiers`, `test_10h_registry_register_and_get`, `test_10h_catalog_measured_count`. | 804b62b, 4727079 (added `unregister`) |
| 3 | `agenttools/router.py` | agenttools | `select_tools()` (exposure cap) + `to_wire_shape()` (provider split) | `transitive` | Imported by `adversarial_battery()`; directly exercised by `test_10h_router_exposes_small_subset`, `test_10h_wire_shape_provider_split`, and the Task 4 extension to `test_v22_local_provider_parity` (`inspect.signature(AT_ROUTER.select_tools)`). | 804b62b |
| 4 | `agenttools/executor.py` | agenttools | `execute()` — never-crash tool invocation, `ToolResult` | `transitive` | Imported by `adversarial_battery()`; directly exercised by `test_10h_executor_never_crashes` and the Task 4 parity extension (`inspect.signature(AT_EXECUTOR.execute)`). | 804b62b |
| 5 | `agenttools/capability.py` | agenttools | `ollama_supports_tools()` live `/api/show` capability gate | `transitive` | Imported by `adversarial_battery()`; directly exercised by `test_10h_capability_gate_failsafe`, `test_10h_tools_for_call_ollama_gate`, and the Task 4 parity extension (monkeypatches `AT_CAP.ollama_supports_tools`). | 804b62b |
| 6 | `agenttools/toolcall.py` | agenttools | `run_with_tools()` execution-feedback loop | `transitive` | **Not** touched by `adversarial_battery()` itself (verified by reading `agenttools/__init__.py` — it isn't imported there) — reachability instead comes from a STRONGER path: `agentic.py:38` (`import agenttools.toolcall as AT_TOOLCALL`, an unconditional top-level import in the real production app-layer module, not just a test harness). Also directly exercised by `test_10h_toolcall_graceful_fallback` and the Task 4 parity extension (`inspect.getsource` counts its 2 `_execute(name, args)` call sites). | 804b62b |
| 7 | `agenttools/catalog_plain.py` | agenttools | 15 PLAIN tools (file I/O ×7, git ×7, `run_python_file`) | `transitive` | Imported at `agenttools/__init__.py` module level (reached by `agenttools_reach()` directly). Exercised by `test_10h_catalog_measured_count`, `test_10h_catalog_plain_never_fold_labeled`, `test_10h_catalog_file_tools_sandboxed`, `test_10h_catalog_tools_functionally_real`. | 4727079 |
| 8 | `agenttools/catalog_fold.py` | agenttools | 4 FOLD-ELIGIBLE tools delegating to `frontend.dispatch`/`closure_classifier`/`extract.checksum`/`extract.parse_arith` | `transitive` | Same import path as row 7. Exercised by the same 4 Task 2 tests (measured-count, no-fold-mislabel, functionally-real). | 4727079 |
| 9 | `agenttools/catalog_accel.py` | agenttools | 2 ACCEL-ELIGIBLE tools delegating to `accel.verified_parallel` | `transitive` | Same import path as row 7. Exercised by the same 4 Task 2 tests. | 4727079 |
| 10 | `swebench/real_dataset.py` | swebench | real SWE-bench schema (`RealInstance`, `parse_instance`, `load_dataset_file`, `live_fetch`, `harness_conversion_gap`) | `transitive` | Directly imported and called by `webapi/engine_dispatch.py::swebench_reach()` (`from swebench import real_dataset as RD`; calls `RD.parse_instance()` and `RD.live_fetch()` inside the probe itself — the strongest form of evidence, not just same-package membership). Also exercised by `test_10h_real_dataset_schema`, `test_10h_swebench_live_fetch_honest`. | 0cbf7f1 |
| 11 | `agentic.py` | (root) | app-layer orchestrator — `_tools_for_call()`, `enable_tools` threading through `write_verify_fix`/`agentic_code`/`agentic_stream` | `app_layer` | The production CALLER itself (server-facing entry point) — `classify()` correctly names it as the caller, not an engine target. Its NEW surface is exercised by `test_10h_agentic_enable_tools_mock_unchanged`, `test_10h_tools_for_call_ollama_gate`, and the Task 4 parity block (`AG._tools_for_call(...)` for both providers). | 804b62b |
| 12 | `webapi/engine_dispatch.py` | webapi | dispatcher — added `agenttools_reach()` (Task 1) + `swebench_reach()` (Task 3) | `transitive` | The two new functions are called directly by `test_10h_agenttools_production_wiring` and `test_10h_swebench_reach` respectively — the SAME convention as the pre-existing `newengine_reach`/`newengine5_reach`/`newengine3_reach`/`metakernel_reach`/`qmkernel_reach` (verified: none of those are aggregated into `full_inventory()`/`production_reach()` either — `grep` confirms they're called only from their own `test_catalog.py` lock-in tests). Not a weaker convention invented for this directive; the established one. | 804b62b, 0cbf7f1 |
| 13 | `engine_inventory.py` | (root) | added `"agenttools"` to `_WIRED_PACKAGES` (with an explanatory inline comment matching the style of the `newengine5`/`newengine3`/`metakernel`/`qmkernel` entries above it) | `observability` | `classify()` special-cases this specific filename as `observability` (it's the scanner itself, not a scanned target) — its own rule, not a gap in this ledger's method. The allowlist entry is what makes rows 1–9's `transitive` verdict possible; `test_bl_full_repo_gap_zero` (and `test_bn`/`test_bo`/`test_bq`/`test_br`, which share the same `gap_count == 0` assertion) re-verify this holds after the change. (`"swebench"` was already present in `_WIRED_PACKAGES` before this directive — Task 3 added no new entry for it, only the `swebench_reach()` probe in row 12.) | 804b62b |

## Explicitly out of scope (named, not hidden)
- **`test_catalog.py`** (touched in all 4 tasks) — a test file. Per `AUDIT_LEDGER.md`'s own established convention
  (its row #9 on this exact file: "test (role: skip unless tautological/wrong-grade-assert)... N/A"), test files
  are not ledger subjects — a test asserting real engine output is its job, not a violation to register.
- **`.gitignore`** (one line added in Task 2: `agenttools_scratch/`) — a repo config file, not code; has no
  `classify()` verdict because `engine_inventory.scan()` only walks `.py` files.

## Result
**0 orphans.** Every one of the 9 non-test, non-config `.py` files added by this directive (rows 1–10, excluding
the 3 pre-existing files modified in rows 11–13) resolves to a named, evidence-backed reachability path —
either a direct reach-probe call, a module-level import chain from that reach-probe's entry point, or (row 6,
`toolcall.py`) a genuine unconditional import from the real production app-layer module. None rely on
`classify()`'s coarse "same package as something wired" rule alone without a concrete test/call-site citation
also confirmed above.
