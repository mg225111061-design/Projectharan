"""
§AQ §1.2 — EFFECT GATE (layer 2: the KEY gate). Classify a fragment pure / io / nondet — the precondition for every
================================================================================================================
compositional fold downstream. Non-math code is not "is it math" but "WHICH part is pure". An expression is:
  nondet  — it (transitively) calls a randomness / wall-clock source ⇒ ∀-input determinism fails ⇒ permanent DECLINE;
  io      — it calls a side-effecting I/O primitive ⇒ the I/O is a RESIDUAL frame, only the surrounding pure
            arithmetic can fold (§5 frame rule, §6 counts the calls);
  pure    — no io / nondet effect ⇒ a fold candidate (route to §2..§6).
★ Sound by OVER-APPROXIMATION: an ordinary call is treated as effan-propagating only via its own name; the
classification is conservative (nondet dominates), and since it only ROUTES, a misclassification costs at most one
verifier call — never a false fold. REUSE the source/sink vocabulary spirit of `taint_ifds`.
"""
from __future__ import annotations

from dataclasses import dataclass

from extract.classify import ast_tag as AT

PURE, IO, NONDET, OPAQUE = "pure", "io", "nondet", "opaque"

# ★ §AS/§2.3 — UNANALYZABLE constructs: reflection / dynamic code / namespace introspection. A static analyzer cannot
# know what these resolve to, so they must be treated WORST-CASE-CONSERVATIVE (DECLINE), never silently "pure".
_OPAQUE_NAMES = ("eval", "exec", "compile", "getattr", "setattr", "delattr", "__import__", "globals", "locals", "vars")


@dataclass
class Effect:
    effect: str                          # "pure" | "io" | "nondet" | "opaque"
    reason: str = ""


def classify_effect(src: str) -> Effect:
    """opaque > nondet > io > pure (conservative). ★ §2.3: an UNANALYZABLE construct (eval/exec/getattr/...) is the
    strongest "can't classify" verdict ⇒ OPAQUE ⇒ DECLINE-route — never a silent fall-through to pure (a false-negative).
    nondet ⇒ permanent DECLINE (no ∀-input determinism); io ⇒ residual frame."""
    t = AT.tag(src)
    opaque = [c for c in t.called if any(op == c for op in _OPAQUE_NAMES)]
    if opaque:
        return Effect(OPAQUE, f"calls an UNANALYZABLE/reflective construct {opaque[:3]} ⇒ static analysis impossible ⇒ "
                              f"worst-case-conservative DECLINE (never a silent 'pure' fall-through — §2.3)")
    if t.nondet:
        return Effect(NONDET, f"calls a randomness/clock source {[c for c in t.called if any(n in c for n in AT._NONDET_NAMES)][:3]} ⇒ non-deterministic ⇒ permanent DECLINE")
    if t.io:
        return Effect(IO, f"calls an I/O primitive {[c for c in t.called if any(n == c or n in c for n in AT._IO_NAMES)][:3]} ⇒ I/O is a residual frame; only surrounding pure arithmetic folds")
    return Effect(PURE, "no io / nondet / opaque effect ⇒ a pure fold candidate")


def is_pure(src: str) -> bool:
    return classify_effect(src).effect == PURE


def adversarial_battery() -> dict:
    """★ a pure arithmetic loop classifies PURE; ★ a read-loop classifies IO (residual frame); ★★ a rand/time fragment
    classifies NONDET (permanent DECLINE — the determinism gate); ★ effect dominance: a fragment with BOTH io and rand
    classifies NONDET (the stronger effect wins)."""
    pure = classify_effect("def f(n):\n s=0\n for i in range(n): s += i\n return s")
    io = classify_effect("def f(fd):\n n=0\n while read(fd, 4096) > 0: n += 1\n return n")
    nd = classify_effect("import random\ndef f(n): return random.randint(0, n)")
    both = classify_effect("import random\ndef f(fd): write(fd, random.random())")
    # ★ §AS/§2.3 regression: reflective / dynamic-code constructs must be OPAQUE (DECLINE), never a silent 'pure'
    ev = classify_effect("def f(s): return eval(s)")
    ex = classify_effect("def f(s): exec(s)")
    seta = classify_effect("def f(o, n, v): setattr(o, n, v)")
    cases = {
        "pure_arith_is_pure": pure.effect == PURE,
        "read_loop_is_io": io.effect == IO,
        "rand_is_nondet": nd.effect == NONDET,                    # ★★ determinism gate
        "nondet_dominates_io": both.effect == NONDET,             # ★ stronger effect wins
        "eval_is_opaque": ev.effect == OPAQUE,                    # ★ §2.3: was 'pure' (fall-through) → now OPAQUE
        "exec_is_opaque": ex.effect == OPAQUE,
        "setattr_is_opaque": seta.effect == OPAQUE,               # ★ no silent 'pure' for unanalyzable constructs
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
