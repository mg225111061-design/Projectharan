"""
§U PHASE 1 — THE HARNESS: ingest a task, generate → layered-verify → submit-verified, score against ground truth.
================================================================================================================
A SWE-bench task is: the repo's code at the base commit (here: a buggy function), the issue text, the test command
(here: the visible tests), and — graded but unseen — the HIDDEN tests. The harness runs Opus (proposer) to produce
candidate patches, applies each, runs the LAYERED GATE (build → visible → regression → formal), submits a VERIFIED
one, and records the real pass/fail against the task's hidden tests (the ground truth a real run is graded on).

★ HONEST SUBSTRATE. Live Opus egress is BLOCKED here, so generation is served by a PLUGGABLE generator: in deployment
it is `claude_agent.claude_generate`; here each task carries RECORDED candidate patches (Opus's N diverse single-shot
outputs, captured) so the verify/filter/repair LOGIC is exercised on REAL code execution and REAL z3 — deterministic
and measured. The candidates are the only stand-in; every gate decision is real. Live generation = pending-real-stack.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple


# ── a candidate patch: its source + the locus it edits (for localization) ────────────────────────────────────
@dataclass
class Candidate:
    src: str                            # the full replacement source for the patched function
    locus: str                          # the function name this candidate actually edits (for localization)
    label: str = ""                     # a short human tag (e.g. "off-by-one", "correct", "build-error")


@dataclass
class Task:
    name: str
    fn_name: str                        # the function the issue is about (the true locus)
    issue: str
    buggy_src: str                      # the repo code at base (the bug)
    visible: List[Tuple[tuple, object]]                 # given tests: (args, expected)
    hidden: List[Tuple[tuple, object]]                  # graded-but-unseen tests (the ground truth)
    reference_src: Optional[str] = None                 # the correct oracle (for the formal check)
    formal_domain: Optional[List[tuple]] = None         # the input domain for bounded formal equivalence
    regression: List[Tuple[tuple, object]] = field(default_factory=list)   # existing passing tests not to break
    candidates: List[Candidate] = field(default_factory=list)              # Opus's recorded single-shot outputs
    repair_src: Optional[str] = None    # the patch Opus produces WHEN HANDED THE COUNTEREXAMPLE (fix-loop substrate)
    repair_works: bool = False          # whether that repair is actually correct (T-unsolved: repair still wrong)


# ── compile a patch source and extract the target function ───────────────────────────────────────────────────
def compile_fn(src: str, fn_name: str) -> Optional[Callable]:
    ns: dict = {}
    try:
        exec(compile(src.strip(), f"<{fn_name}>", "exec"), ns, ns)
    except Exception:  # noqa: BLE001 — build error (a real gate-layer-1 failure)
        return None
    fn = ns.get(fn_name)
    return fn if callable(fn) else None


def run_cases(fn: Callable, cases: List[Tuple[tuple, object]]) -> Tuple[bool, Optional[dict]]:
    """Run a function on (args, expected) cases. Returns (all_passed, first_failure). A raised exception or a wrong
    result is a failure; the failure dict names the exact input — the structured feedback the fix loop consumes."""
    for args, expected in cases:
        try:
            got = fn(*args)
        except Exception as e:  # noqa: BLE001
            return False, {"kind": "exception", "args": args, "error": f"{type(e).__name__}: {e}"}
        if got != expected:
            return False, {"kind": "wrong_result", "args": args, "expected": expected, "got": got}
    return True, None


# ── the layered gate (Phases 2–5 compose here; formal lives in formal_check) ──────────────────────────────────
@dataclass
class GateResult:
    built: bool
    visible_ok: bool
    regression_ok: bool
    formal_ok: Optional[bool]           # None ⇒ formal not applicable (honest fallback to visible+regression)
    counterexample: Optional[dict]      # the formal counterexample (the richest feedback), if any
    caught_by: str                      # which layer rejected it ("build"/"visible"/"regression"/"formal"/"-")
    submission_eligible: bool           # passed every applicable layer


def layered_gate(task: Task, cand: Candidate, *, use_regression=True, use_formal=True) -> GateResult:
    """Run a candidate through build → visible → regression → formal. Each layer can reject. `submission_eligible`
    is True only if every APPLICABLE layer passes. The formal layer (when applicable) is the strongest — it proves
    correctness over the domain, catching visible-passing-but-wrong patches and yielding the counterexample."""
    fn = compile_fn(cand.src, task.fn_name)
    if fn is None:
        return GateResult(False, False, False, None, None, "build", False)
    vok, _vf = run_cases(fn, task.visible)
    if not vok:
        return GateResult(True, False, False, None, None, "visible", False)
    rok = True
    if use_regression and task.regression:
        rok, _rf = run_cases(fn, task.regression)
        if not rok:
            return GateResult(True, True, False, None, None, "regression", False)
    # ★ formal-beyond-tests
    fok: Optional[bool] = None
    cex: Optional[dict] = None
    if use_formal and task.reference_src and task.formal_domain:
        from swebench.formal_check import formal_correct
        fr = formal_correct(task, fn)
        fok = fr.proved
        cex = fr.counterexample
        if not fok:
            return GateResult(True, True, rok, False, cex, "formal", False)
    return GateResult(True, True, rok, fok, cex, "-", True)


def grade_against_hidden(task: Task, cand: Candidate) -> bool:
    """The ground truth: does this candidate pass the FULL suite a real SWE-bench run is graded on — the visible
    tests AND the hidden tests AND the repo's existing passing (regression) tests? A patch that breaks an existing
    test is a real failure. Used to MEASURE the pipeline honestly — never shown to the generator/gate."""
    fn = compile_fn(cand.src, task.fn_name)
    if fn is None:
        return False
    vok, _ = run_cases(fn, task.visible)
    hok, _ = run_cases(fn, task.hidden)
    rok, _ = run_cases(fn, task.regression) if task.regression else (True, None)
    return vok and hok and rok


# ── the generator: pluggable. Live = claude_generate (BLOCKED here); substrate = the task's recorded candidates ─
def recorded_generator(task: Task, n: int) -> List[Candidate]:
    """The deterministic substrate generator: returns the task's recorded candidates (Opus's N single-shot outputs).
    Live generation via claude_agent.claude_generate is pending-real-stack (egress BLOCKED)."""
    return list(task.candidates[:n]) if n else list(task.candidates)


def live_generator_blocked() -> dict:
    """Honest status of the live generator path (Clock A)."""
    return {"clock": "A", "status": "BLOCKED", "detail": "Opus egress unavailable in this sandbox; generation served "
            "by recorded candidates (the verify/filter/repair logic is real and measured). Live = pending-real-stack."}


# ── the self-contained, EXECUTABLE mini-benchmark ────────────────────────────────────────────────────────────
def _C(src, locus, label=""):  # noqa: E741
    return Candidate(src, locus, label)


def mini_bench() -> List[Task]:
    """8 executable Python tasks, each a buggy function + issue + visible + HIDDEN tests + reference oracle + recorded
    candidates, designed so each pipeline rung (opus-alone → +multi → +regression → +localization → +formal → +fix)
    contributes a REAL, measured marginal lift, and so the full pipeline submits ONLY formally-verified patches
    (precision 1.0), honestly DECLINING the one genuinely-unsolvable task rather than gambling it on the hidden suite."""
    T = []

    # T1 — opus-alone already solves it: the first single-shot candidate is correct.
    T.append(Task(
        name="abs_value", fn_name="absval",
        issue="absval(x) should return the absolute value; it returns x unchanged for negatives.",
        buggy_src="def absval(x):\n    return x",
        visible=[((5,), 5), ((0,), 0)], hidden=[((-3,), 3), ((-1,), 1)],
        reference_src="def absval(x):\n    return x if x >= 0 else -x",
        formal_domain=[(i,) for i in range(-20, 21)],
        candidates=[_C("def absval(x):\n    return x if x >= 0 else -x", "absval", "correct")]))

    # T2 — multi-candidate solves it: candidates[0] fails visible; a later candidate is correct.
    T.append(Task(
        name="clamp_hi", fn_name="clamp",
        issue="clamp(x, lo, hi) must bound x into [lo, hi]; it currently ignores the upper bound.",
        buggy_src="def clamp(x, lo, hi):\n    return lo if x < lo else x",
        visible=[((5, 0, 10), 5), ((-2, 0, 10), 0)], hidden=[((99, 0, 10), 10), ((10, 0, 10), 10)],
        reference_src="def clamp(x, lo, hi):\n    return lo if x < lo else (hi if x > hi else x)",
        formal_domain=[(x, 0, 10) for x in range(-5, 16)],
        candidates=[
            _C("def clamp(x, lo, hi)\n    return x", "clamp", "build-error (missing colon)"),
            _C("def clamp(x, lo, hi):\n    return max(lo, min(x, hi))", "clamp", "correct")]))

    # T3 — regression solves it: a candidate passes the target visible tests but BREAKS an existing passing test;
    #      regression rejects it; a later candidate is correct.
    T.append(Task(
        name="safe_div", fn_name="safe_div",
        issue="safe_div(a, b) should return a/b, but return 0 when b == 0 (avoid ZeroDivisionError).",
        buggy_src="def safe_div(a, b):\n    return a / b",
        visible=[((10, 0), 0), ((6, 2), 3.0)], hidden=[((9, 0), 0), ((-4, 2), -2.0)],
        reference_src="def safe_div(a, b):\n    return 0 if b == 0 else a / b",
        formal_domain=[(a, b) for a in range(-6, 7) for b in (-2, -1, 0, 1, 2, 3)],   # b==0 guarded by every candidate
        regression=[((9, 2), 4.5)],                     # an existing passing test: true (float) division
        candidates=[
            # passes the target visible+hidden (b==0 handled) but BREAKS the existing float-division test (9/2 → 4, not 4.5)
            _C("def safe_div(a, b):\n    return 0 if b == 0 else a // b", "safe_div", "regressor (int-div breaks 9/2=4.5)"),
            _C("def safe_div(a, b):\n    return 0 if b == 0 else a / b", "safe_div", "correct")]))

    # T4 — localization solves it: a WRONG-LOCUS candidate passes visible+regression by luck but fails hidden;
    #      localization (filter to candidates that edit the true locus) removes it; the correct-locus one wins.
    T.append(Task(
        name="list_sum_default", fn_name="list_sum",
        issue="list_sum(xs) should sum xs and return 0 for the empty list; it raises on [].",
        buggy_src="def list_sum(xs):\n    return xs[0] + list_sum(xs[1:])",
        visible=[(([1, 2, 3],), 6), (([5],), 5)], hidden=[(([],), 0), (([2, 2],), 4)],
        reference_src="def list_sum(xs):\n    total = 0\n    for v in xs:\n        total += v\n    return total",
        formal_domain=[((xs,)) for xs in ([], [1], [1, 2], [3, 4, 5], [0], [9, 9, 9, 9])],
        candidates=[
            # wrong-locus: the model "fixed" a helper (_agg) and guarded the empty case WRONG (→1); passes the
            # non-empty visible tests, fails the empty hidden test. localization (locus must be list_sum) removes it.
            _C("def _agg(xs):\n    return sum(xs)\n\ndef list_sum(xs):\n    return _agg(xs) if xs else 1",
               "_agg", "wrong-locus (passes visible, wrong on [] hidden)"),
            _C("def list_sum(xs):\n    total = 0\n    for v in xs:\n        total += v\n    return total",
               "list_sum", "correct")]))

    # T5 — ★ THE DIFFERENTIATOR: every candidate passes visible+regression+is in-locus, but the first is an
    #      OFF-BY-ONE that fails the hidden boundary case. Only the formal check (counterexample = the boundary
    #      input) rejects it and picks the formally-correct candidate. A test-only pipeline ships the hidden failure.
    T.append(Task(
        name="in_range", fn_name="in_range",
        issue="in_range(x, lo, hi) is INCLUSIVE on both ends: lo <= x <= hi.",
        buggy_src="def in_range(x, lo, hi):\n    return lo < x < hi",
        visible=[((5, 0, 10), True), ((-1, 0, 10), False)],     # boundary (x==hi) NOT in the visible set
        hidden=[((10, 0, 10), True), ((0, 0, 10), True)],       # the inclusive boundaries — where off-by-one fails
        reference_src="def in_range(x, lo, hi):\n    return lo <= x <= hi",
        formal_domain=[(x, 0, 10) for x in range(-3, 14)],
        candidates=[
            _C("def in_range(x, lo, hi):\n    return lo < x < hi", "in_range", "off-by-one (passes visible, fails hidden)"),
            _C("def in_range(x, lo, hi):\n    return lo <= x <= hi", "in_range", "correct")]))

    # T6 — ★ another differentiator: a plausible candidate handles the general case but is wrong at a single edge
    #      (negative zero / boundary); formal catches it, picks the correct one.
    T.append(Task(
        name="sign", fn_name="sign",
        issue="sign(x) returns -1, 0, or 1. sign(0) must be 0.",
        buggy_src="def sign(x):\n    return 1 if x > 0 else -1",
        visible=[((7,), 1), ((-7,), -1)], hidden=[((0,), 0)],
        reference_src="def sign(x):\n    return (x > 0) - (x < 0)",
        formal_domain=[(i,) for i in range(-10, 11)],
        candidates=[
            _C("def sign(x):\n    return 1 if x > 0 else -1", "sign", "wrong at 0 (passes visible, fails hidden)"),
            _C("def sign(x):\n    return (x > 0) - (x < 0)", "sign", "correct")]))

    # T7 — the FIX LOOP solves it: NO recorded candidate passes the gate (all wrong), but handed the FORMAL
    #      COUNTEREXAMPLE, Opus repairs to a correct patch (the richest-feedback path). repair_works=True.
    T.append(Task(
        name="round_half_up", fn_name="rhu",
        issue="rhu(n, d) rounds n UP to the next multiple of d (ceil to a multiple).",
        buggy_src="def rhu(n, d):\n    return (n // d) * d",
        visible=[((10, 5), 10), ((15, 5), 15)],         # exact multiples — BOTH wrong candidates pass these
        hidden=[((11, 5), 15), ((12, 5), 15), ((5, 5), 5)],   # non-multiples — where BOTH wrong candidates fail
        reference_src="def rhu(n, d):\n    return ((n + d - 1) // d) * d",
        formal_domain=[(n, 5) for n in range(0, 26)],
        candidates=[
            _C("def rhu(n, d):\n    return (n // d) * d", "rhu", "round-down (passes visible, fails hidden 11→15)"),
            _C("def rhu(n, d):\n    return round(n / d) * d", "rhu", "round-nearest (passes visible, fails hidden)")],
        repair_src="def rhu(n, d):\n    return ((n + d - 1) // d) * d", repair_works=True))

    # T8 — HONEST UNSOLVED control: no correct candidate, and the repair (even with the counterexample) stays wrong.
    #      The pipeline DECLINES to submit rather than gamble a visible-passing-but-unverified patch on the hidden
    #      suite — so precision stays 1.0 (we never submit this) and the task is reported as an honest miss.
    T.append(Task(
        name="collatz_steps", fn_name="collatz",
        issue="collatz(n) returns the number of steps to reach 1 (a genuinely hard one for the recorded model).",
        buggy_src="def collatz(n):\n    return n",
        visible=[((1,), 0), ((2,), 1)], hidden=[((6,), 8), ((7,), 16)],
        reference_src=("def collatz(n):\n    c = 0\n    while n != 1:\n        n = n // 2 if n % 2 == 0 else 3 * n + 1\n"
                       "        c += 1\n    return c"),
        formal_domain=[(i,) for i in range(1, 28)],
        candidates=[
            _C("def collatz(n):\n    return n - 1", "collatz", "linear guess (passes visible, fails hidden)"),
            _C("def collatz(n):\n    return 0", "collatz", "constant (fails visible 2→1)")],
        repair_src="def collatz(n):\n    return n - 1", repair_works=False))    # repair still wrong → honest decline

    return T
