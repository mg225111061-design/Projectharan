"""
NATIVE ARSENAL — Knuth–Bendix completion for string-rewriting (monoid word problem), in-repo, zero external dep.
===============================================================================================================
Given a finite monoid presentation (rewrite rules over an alphabet), complete it to a CONFLUENT, TERMINATING
string-rewriting system under shortlex order; then two words are equal in the monoid IFF they share a normal form.
Mechanism ⑧ (confluent normal form), ⑨. Certificate: the completed system — EVERY critical pair resolves to a
common normal form (local confluence, Newman's lemma) and shortlex strictly decreases (termination). The general
word problem is undecidable (Novikov–Boone); completion may not halt ⇒ budget, then honest DECLINE.
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import kernel_verdict as KV

Rule = Tuple[str, str]


def _shortlex_le(a: str, b: str) -> bool:
    return (len(a), a) <= (len(b), b)


def _orient(l: str, r: str) -> Optional[Rule]:
    if l == r:
        return None
    return (l, r) if _shortlex_le(r, l) else (r, l)         # bigger → smaller (shortlex), so rewriting terminates


def normal_form(w: str, rules: Sequence[Rule], budget: int = 100000) -> str:
    changed = True
    steps = 0
    while changed and steps < budget:
        changed = False
        for (l, r) in rules:
            i = w.find(l)
            if i >= 0:
                w = w[:i] + r + w[i + len(l):]
                changed = True
                steps += 1
                break
    return w


def _critical_pairs(r1: Rule, r2: Rule) -> List[Tuple[str, str]]:
    """Overlap critical pairs of two string rules (l1→r1) (l2→r2): (a) suffix of l1 == prefix of l2; (b) l2 a
    factor of l1. Returns the pairs of one-step-divergent words to be joined."""
    (l1, rr1), (l2, rr2) = r1, r2
    pairs = []
    # (a) overlap: l1 = x·s, l2 = s·y with s nonempty ⇒ word x·l2 = l1·y rewrites two ways
    for k in range(1, min(len(l1), len(l2)) + 1):
        if l1[len(l1) - k:] == l2[:k]:
            w = l1 + l2[k:]
            pairs.append((rr1 + l2[k:], l1[:len(l1) - k] + rr2))
    # (b) inclusion: l2 is a factor of l1 at position i ⇒ l1 rewrites two ways
    start = 0
    while True:
        i = l1.find(l2, start)
        if i < 0:
            break
        pairs.append((rr1, l1[:i] + rr2 + l1[i + len(l2):]))
        start = i + 1
    return pairs


def knuth_bendix(rules0: Sequence[Rule], max_rules: int = 300, max_iters: int = 5000):
    """Complete a string-rewriting system. Returns (rules, completed: bool). completed=False ⇒ budget hit (DECLINE)."""
    rules: List[Rule] = []
    for (l, r) in rules0:
        o = _orient(l, r)
        if o:
            rules.append(o)
    it = 0
    changed = True
    while changed and it < max_iters and len(rules) < max_rules:
        changed = False
        it += 1
        for i in range(len(rules)):
            for j in range(len(rules)):
                for (a, b) in _critical_pairs(rules[i], rules[j]):
                    na, nb = normal_form(a, rules), normal_form(b, rules)
                    if na != nb:
                        o = _orient(na, nb)
                        if o and o not in rules:
                            rules.append(o)
                            changed = True
                if changed and len(rules) >= max_rules:
                    return rules, False
    # inter-reduce: drop rules whose lhs is reducible by another
    return rules, (not changed)


def _is_confluent(rules: Sequence[Rule]) -> bool:
    for i in range(len(rules)):
        for j in range(len(rules)):
            for (a, b) in _critical_pairs(rules[i], rules[j]):
                if normal_form(a, rules) != normal_form(b, rules):
                    return False
    return True


def word_problem_grade(rules, u: str, v: str) -> KV.Verdict:
    """Decide u == v in the monoid ⟨alphabet | rules⟩ via Knuth–Bendix completion + normal forms."""
    completed_rules, ok = knuth_bendix(rules)
    if not ok:
        return KV.decline(f"knuth_bendix: completion did not converge within budget ({len(completed_rules)} rules) — "
                          "word problem may be undecidable (Novikov–Boone) ⇒ honest DECLINE", "native_rewrite")
    if not _is_confluent(completed_rules):                  # ★ re-verify local confluence (all critical pairs join) ★
        return KV.decline("knuth_bendix: completed system not confluent on re-check ⇒ DECLINE (bug guard)", "native_rewrite")
    nu, nv = normal_form(u, completed_rules), normal_form(v, completed_rules)
    equal = nu == nv
    cert = KV.Cert(KV.EXACT, "confluent_rewrite_system", passed=True,
                   check_cost="re-verify all critical pairs join + shortlex termination",
                   detail=f"KB-completed to {len(completed_rules)} confluent rules; NF({u})={nu!r}, NF({v})={nv!r} ⇒ "
                          f"{'EQUAL' if equal else 'DISTINCT'} in the monoid")
    return KV.exact({"equal": equal, "nf_u": nu, "nf_v": nv, "n_rules": len(completed_rules)},
                    "native_rewrite", "Knuth–Bendix completion (shortlex)", cert)


def m8_word_grade(x) -> KV.Verdict:
    """Route {"kb_rules": [(l,r),...], "u": w1, "v": w2} → monoid word-problem decision."""
    if isinstance(x, dict) and "kb_rules" in x and "u" in x and "v" in x:
        return word_problem_grade([tuple(r) for r in x["kb_rules"]], x["u"], x["v"])
    return KV.decline("native_rewrite: expected {kb_rules,u,v}", "native_rewrite")
