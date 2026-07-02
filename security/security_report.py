"""
§R — CONDITIONAL VERIFIED SECURITY REPORT (measured): the LLM decides, the verifier proves, the honest negative survives.
================================================================================================================
The capstone. It demonstrates and MEASURES the whole §R contract end to end:

  • the GATE decides NEED (SENSITIVE / NOT-SENSITIVE) — world-knowledge judgment, honestly labeled llm-or-heuristic;
  • the VERIFIER decides FACT — each logical-vuln class PROVEN_ABSENT (z3/exact) or FLAGGED, each side-channel axis
    CT_PROVEN/masking-secure or "NOT VERIFIED"; "safe" is asserted ONLY when proved;
  • HARDENING is applied ONLY to SENSITIVE+flagged code, z3/differential-proved equivalent, with its cost MEASURED;
  • ZERO overhead when the gate is OFF — MEASURED, not asserted (Phase 5);
  • PRECISION = 1.0 means the one thing that must never happen never happens: NO vulnerable snippet is ever claimed
    "safe". Over a labeled adversarial corpus, every known-vulnerable case is FLAGGED (never proven-absent). A false
    "safe" is a correctness violation that fails the build — so the measured number that matters is "false-safes = 0".

Every number is measured at call time. Zero external dependencies.
"""
from __future__ import annotations

from typing import Dict, List

from security.llm_gate import security_gate, SENSITIVE, NOT_SENSITIVE
from security.logical_vulns import (check_bounds, check_injection, check_overflow, check_memory, check_race,
                                    PROVEN_ABSENT, FLAGGED)
from security.sidechannel import constant_time, verify_masking, sidechannel_verify, CT_PROVEN, CT_VIOLATION


# ── labeled adversarial corpus: each case carries the GROUND TRUTH so we can measure false-safes ──────────────
def _logical_corpus() -> List[dict]:
    """Each entry: name, the checker to run, its args, and `vulnerable` ground truth. A 'safe' verdict on a
    vulnerable case is the forbidden false-clear (precision-killer)."""
    return [
        # ── KNOWN-VULNERABLE: the verifier MUST flag (never proven-absent) ──
        {"name": "sql_concat", "kind": "injection", "vulnerable": True,
         "code": "def q(name):\n    cur.execute('SELECT * FROM u WHERE n = ' + name)"},
        {"name": "unguarded_index", "kind": "bounds", "vulnerable": True,
         "code": "def g(c, k):\n    return c[k]"},
        {"name": "overflow_sum", "kind": "overflow", "vulnerable": True,
         "expr": "a + b", "width": 8, "signed": False, "ranges": {"a": (0, 200), "b": (0, 200)}},
        {"name": "use_after_del", "kind": "memory", "vulnerable": True,
         "code": "def h():\n    x = [1]\n    del x\n    return x[0]"},
        {"name": "race_shared", "kind": "race", "vulnerable": True,
         "tasks": [{"name": "t1", "reads": [], "writes": ["acc"]}, {"name": "t2", "reads": ["acc"], "writes": []}]},
        # ── KNOWN-SAFE: the verifier SHOULD prove absent (recall; DECLINE would be honest but here they're provable) ──
        {"name": "param_query", "kind": "injection", "vulnerable": False,
         "code": "def q(name):\n    cur.execute('SELECT * FROM u WHERE n = ?', (name,))"},
        {"name": "guarded_index", "kind": "bounds", "vulnerable": False,
         "code": "def g(c):\n    for i in range(len(c)):\n        c[i] = c[i] + 1"},
        {"name": "norange_overflow", "kind": "overflow", "vulnerable": False,
         "expr": "a + b", "width": 32, "signed": False, "ranges": {"a": (0, 100), "b": (0, 100)}},
        {"name": "clean_memory", "kind": "memory", "vulnerable": False,
         "code": "def h():\n    x = [1]\n    return x[0]"},
        {"name": "disjoint_tasks", "kind": "race", "vulnerable": False,
         "tasks": [{"name": "t1", "reads": [], "writes": ["a"]}, {"name": "t2", "reads": [], "writes": ["b"]}]},
    ]


def _run_logical(item: dict):
    """Run the appropriate checker, return (claimed_safe, results)."""
    k = item["kind"]
    if k == "injection":
        rs = check_injection(item["code"])
    elif k == "bounds":
        rs = check_bounds(item["code"])
    elif k == "memory":
        rs = check_memory(item["code"])
    elif k == "overflow":
        rs = [check_overflow(item["expr"], item["width"], item["signed"], item["ranges"])]
    elif k == "race":
        rs = [check_race(item["tasks"])]
    else:
        rs = []
    claimed_safe = bool(rs) and all(r.status == PROVEN_ABSENT for r in rs)
    return claimed_safe, rs


def _sidechannel_corpus() -> List[dict]:
    return [
        # KNOWN-LEAK (CT): secret-dependent branch — must be CT_VIOLATION (never claimed side-channel-safe)
        {"name": "secret_branch", "vulnerable": True, "secrets": {"secret"},
         "code": "def f(secret, a, b):\n    if secret != 0:\n        return a\n    return b"},
        # KNOWN-LEAK (KyberSlash class): variable-time '%' on a secret
        {"name": "secret_mod", "vulnerable": True, "secrets": {"secret"},
         "code": "def f(secret, m):\n    return secret % m"},
        # KNOWN-SAFE (CT): branchless constant-time select — CT_PROVEN
        {"name": "ct_select", "vulnerable": False, "secrets": {"secret"},
         "code": "def f(secret, a, b):\n    m = -(secret != 0)\n    return (a & m) | (b & ~m)"},
    ]


def _masking_audit() -> dict:
    """t-probing security over GF(2): a BROKEN masking (t-subset spans the secret) must be reported NOT-secure; a
    SECURE masking (an unobserved random always remains) must be proved secure. A 'secure' verdict on broken masking
    would be a false-safe."""
    basis = ["secret", "r1", "r2"]
    # secure first-order masking: share0 = secret ^ r1, share1 = r1. Observing either ALONE keeps a random.
    secure = verify_masking({"s0": {"secret", "r1"}, "s1": {"r1"}}, basis, t=1)
    # BROKEN: the two shares XOR back to the secret, and at t=2 both are observable ⇒ secret recoverable.
    broken = verify_masking({"s0": {"secret", "r1"}, "s1": {"r1"}}, basis, t=2)
    return {"secure_case_secure": secure["secure"], "broken_case_secure": broken["secure"],
            "broken_leaking_subset": broken["leaking_subset"],
            "false_safe": secure["secure"] is False or broken["secure"] is True}


def report() -> dict:
    import dependency_audit as DA

    # ── 1. GATE: a SENSITIVE and a NOT-SENSITIVE example, honestly labeled ──
    sens = security_gate("def login(password):\n    return hmac.compare_digest(password, stored)")
    nons = security_gate("def fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a")

    # ── 2. LOGICAL vulns: measure false-safes over the labeled corpus (the precision-killer) ──
    log_rows, log_false_safe = [], []
    for it in _logical_corpus():
        claimed_safe, rs = _run_logical(it)
        flagged = any(r.status == FLAGGED for r in rs)
        row = {"name": it["name"], "kind": it["kind"], "vulnerable": it["vulnerable"],
               "claimed_safe": claimed_safe, "flagged": flagged,
               "verdict": "PROVEN_ABSENT" if claimed_safe else "FLAGGED"}
        log_rows.append(row)
        if it["vulnerable"] and claimed_safe:                       # a vulnerable case claimed safe ⇒ false-safe
            log_false_safe.append(it["name"])

    # ── 3. SIDE-CHANNEL: measure false-safes (a leak claimed side-channel-safe) ──
    sc_rows, sc_false_safe = [], []
    for it in _sidechannel_corpus():
        v = sidechannel_verify(it["code"], it["secrets"])
        sc_rows.append({"name": it["name"], "vulnerable": it["vulnerable"], "safe": v.safe,
                        "ct_status": v.constant_time.status})
        if it["vulnerable"] and v.safe:
            sc_false_safe.append(it["name"])
    mask = _masking_audit()

    # ── 4. HARDENING (SENSITIVE+flagged only) + measured cost ──
    from security.hardening import harden_constant_time
    ORIG = "def select(secret, a, b):\n    if secret != 0:\n        return a\n    else:\n        return b"
    HARD = "def select(secret, a, b):\n    m = -(secret != 0)\n    return (a & m) | (b & ~m)"
    battery = [(1, 10, 20), (0, 10, 20), (5, 7, 9), (255, 3, 4), (0, 0, 99), (1, 0, 0), (0, 1, 1)]
    g = security_gate(ORIG)
    hr = harden_constant_time(g.security_on, ORIG, HARD, "select", {"secret"}, battery)
    # gate binding: hardening NOT-SENSITIVE code is refused
    refused = harden_constant_time(False, ORIG, HARD, "select", {"secret"}, battery)

    # ── 5. ZERO-OVERHEAD-WHEN-OFF (Phase 5, measured) ──
    import security.overhead_report as OH
    oh = OH.report()

    # ── precision: the ONE thing that must never happen — NO false-safe anywhere ──
    all_false_safe = log_false_safe + sc_false_safe + (["masking"] if mask["false_safe"] else [])
    precision_one = (not all_false_safe)
    # recall (honest, NOT required to be 1.0 — DECLINE is allowed): provable-safe cases actually proved
    safe_logical = [r for r in log_rows if not r["vulnerable"]]
    logical_recall = round(sum(1 for r in safe_logical if r["claimed_safe"]) / len(safe_logical), 3) if safe_logical else 0.0

    fd = DA.final_dependency_set()["forbidden_present"]

    return {
        "thesis": "the LLM is the GATE (judges NEED via world-knowledge), the verifier is the JUDGE (proves FACT); "
                  "'safe' is claimed ONLY when proved, hardening is applied ONLY where needed with a MEASURED cost, "
                  "and there is ZERO overhead when the gate is OFF — measured, not asserted",
        "gate": {
            "sensitive_example": {"verdict": sens.verdict, "categories": sens.categories, "method": sens.method},
            "not_sensitive_example": {"verdict": nons.verdict, "method": nons.method},
            "note": "the gate judges the NEED, never the fact; method is honestly labeled — LLM egress is BLOCKED "
                    "here so the verdict is the conservative STATIC HEURISTIC, never presented as the LLM judgment",
        },
        "logical_verification": {
            "rows": log_rows, "false_safes": log_false_safe,
            "recall_on_provable_safe": logical_recall,
            "note": "every KNOWN-VULNERABLE case is FLAGGED (never proven-absent); 'safe' appears only where z3/exact "
                    "proved it. recall<1.0 would be honest DECLINE, not a defect — but a false-safe IS a defect",
        },
        "sidechannel_verification": {
            "rows": sc_rows, "false_safes": sc_false_safe, "masking": mask,
            "note": "secret-branch and KyberSlash-class '%' are CT_VIOLATION; the branchless select is CT_PROVEN; "
                    "broken first-order masking is reported NOT-secure at t=2 (the two shares XOR to the secret)",
        },
        "hardening": {
            "applied_on_sensitive": hr.applied, "vuln_closed": hr.vuln_closed, "equivalent": hr.equivalent,
            "measured_cost_ratio_C": hr.cost_ratio, "gate_binding_refusal_on_nonsensitive": (not refused.applied),
            "note": "hardening applied ONLY to SENSITIVE+flagged code (constant-time select), z3/differential-proved "
                    "equivalent, cost MEASURED (Clock C); refused outright on NOT-SENSITIVE code (gate binding)",
        },
        "zero_overhead_when_off": {
            "all_gate_off": oh["not_sensitive"]["all_gate_off"],
            "all_byte_identical": oh["not_sensitive"]["all_byte_identical"],
            "structural_zero_overhead": oh["not_sensitive"]["structural_zero_overhead"],
            "worst_runtime_deviation_from_1x": oh["not_sensitive"]["worst_runtime_deviation_from_1x"],
            "note": "NOT-SENSITIVE code is byte-identical and runs at native speed (measured ≈1.0×); the cost is paid "
                    "ONLY on the SENSITIVE+flagged path — measured, not asserted",
        },
        "precision": {
            "is_one": precision_one, "value": 1.0 if precision_one else 0.0,
            "false_safes_total": all_false_safe,
            "note": "PRECISION 1.0 ⇔ false-safes == 0: no vulnerable snippet (logical, side-channel, or broken "
                    "masking) is EVER claimed safe. A false-safe is a correctness violation that fails the build",
        },
        "zero_dep_forbidden_present": fd, "zero_dep_ok": fd == [],
        "one_line": "잘못된 답보다 DECLINE이 항상 옳다 — LLM이 필요를 정하고, 검증기가 사실을 증명한다: security turns on only "
                    "where it is needed and proves vulnerability-absence or says 'NOT VERIFIED' — never a false safe "
                    f"(precision {1.0 if precision_one else 0.0}, false-safes {len(all_false_safe)}), with zero "
                    "measured overhead where the gate is OFF.",
    }
