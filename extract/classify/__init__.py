"""
§AQ §1 — CLASSIFIER FRONTEND (the multiplier): AST tag → effect gate (pure/io/nondet) → route. Decomposes arbitrary
================================================================================================================
code into {checksum / parse-arith / periodic-FSM / I/O-residual / genuinely-non-math} and routes the pure math atoms
to the §2..§6 extractors, where the EXISTING §AI/§AP conjecturers + z3 dispose them. ★ S-1: only effect analysis +
routing is new — no new fold mechanism, no new disposer. ★ Soundness: routing is for efficiency; a wrong route costs
one wasted verifier call, never a false fold (the z3 gate at each extractor holds precision = the proposer/verifier
invariant). The classifier multiplies the coverage of every downstream §.
"""
from __future__ import annotations

from extract.classify import ast_tag as AT, effect_gate as EG, route as RT


def classify(src: str) -> dict:
    """The full frontend: tag + effect + route, as one structured decision."""
    t = AT.tag(src)
    eff = EG.classify_effect(src)
    r = RT.route(src)
    return {"effect": eff.effect, "route": r.target, "tags": {
        "checksum": t.checksum, "parse_arith": t.parse_arith, "periodic_fsm": t.periodic_fsm,
        "io": t.io, "nondet": t.nondet, "accumulator": t.accumulator}, "reason": r.reason}


def adversarial_battery() -> dict:
    """★ effect gate + router batteries green; ★★ the determinism gate: a nondet fragment never routes to a fold; ★ the
    layered decomposition routes each shape to its extractor (the multiplier)."""
    eg = EG.adversarial_battery()
    rt = RT.adversarial_battery()
    crc = classify("def crc32(d):\n c=0\n for b in d: c = (c>>8) ^ b\n return c")
    cases = {
        "effect_gate_green": eg["all_ok"],
        "router_green": rt["all_ok"],
        "checksum_classified": crc["route"] == "checksum" and crc["effect"] == "pure",
        "nondet_never_folds": classify("import random\ndef f(n): return random.random()")["route"] == "DECLINE",
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
