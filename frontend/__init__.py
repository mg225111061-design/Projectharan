"""
§W — FRONTEND COMPLETE: accounts, history, files, progress, errors, many providers — all VERIFIED to work.
================================================================================================================
Make MR.JEFFREY a complete product end-to-end, every feature VERIFIED to function (not assumed), the UI↔frontend↔
backend wiring tested, and the one hard line never crossed: ★ the API key is NEVER stored.

Builds on the existing backend (`auth.py` — accounts + sessions + per-account work history, with NO api_key column
anywhere, by design) and the §S three-pillar UI. This package adds the new, verified pieces:
  • providers.py — the widened provider registry (the major models + compatible gateways), each correctly wired.
  • files.py     — multi-file upload (50+ types, ≤5 at once), fold-assisted ingestion, untrusted-input validation.
  • errors.py    — every failure surfaced as a specific, honest, actionable message (no silent fail, no fake success).
  • progress.py  — live progress showing the REAL pipeline stages, mode-aware (FAST short, EXTEND deep).
  • feature_report.py — verifies every feature works + the security-sensitive paths (auth/key/files) + honest limits.

★ HONEST SCOPE: where the full live stack (real backend process, real provider calls) can't run here (egress BLOCKED),
the work is built correctly and the live-integration test is marked PENDING-REAL-STACK — never a faked passing
integration. Everything verifiable here (logic, wiring, config, the security paths, key-never-stored) is verified.
Engine zero-dep (`forbidden_present == []`); never imported by test_build.
"""
