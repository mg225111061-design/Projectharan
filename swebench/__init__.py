"""
§U — SWE-BENCH SCORE AMPLIFIER: Opus generates, MR.JEFFREY verifies-filters-repairs.
================================================================================================================
This package wraps an LLM's raw patch-generation in the proposer–verifier machinery: the model proposes N candidate
patches (some wrong); a LAYERED GATE (build → visible tests → regression → ★formal-beyond-tests) filters to the
proven ones; failures are REPAIRED from their precise failure (richest of all: a concrete formal counterexample); the
formally-strongest VERIFIED patch is submitted — never an unverified one gambled on the hidden suite.

★ THE DIFFERENTIATOR — formal verification is STRONGER than running the visible tests. Tests check the inputs that
exist; the formal check proves correctness over the input DOMAIN, so a patch that passes every visible test yet is
wrong on the edge case the HIDDEN test exercises is caught BEFORE submission. That is exactly the gap that caps a
test-only pipeline around ~90%.

★ HONEST SCOPE (read first). The real SWE-bench Verified/Pro harness needs the task repos and their test runners, and
a LIVE Opus egress — neither is available here (egress BLOCKED, like the GPU throughput was device-pending). So:
  • the real Verified/Pro SCORE is MODELED-PENDING-REAL-STACK — never fabricated;
  • the MECHANISMS are REAL and MEASURED on a self-contained, EXECUTABLE mini-benchmark of Python tasks (each a buggy
    function + issue + visible tests + HIDDEN tests + a reference oracle + recorded candidate patches standing in for
    Opus's N diverse outputs). Every gate layer runs on real code execution and real z3; the per-mechanism ladder is
    measured by actually running the pipeline, not asserted.
Live generation/repair is the only pending-real-stack piece (Clock A BLOCKED); everything verifiable here is verified.

Modules: harness · multi_candidate · fix_loop · regression · localization · formal_check · score_report.
Engine zero-dep (`forbidden_present == []`); never imported by test_build.
"""
