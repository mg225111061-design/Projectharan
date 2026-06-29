"""
§AQ §1.3 — ROUTE (layer 3): send a fragment to the right §2..§6 extractor — but ONLY after the effect gate has
================================================================================================================
isolated what is pure. A pure fragment routes by its tag (checksum / parse_arith / periodic_fsm / io_arith); an I/O
fragment routes to the §5 frame-isolation + §6 call-count path (the I/O stays a residual, the surrounding arithmetic
folds); a nondet fragment is a permanent DECLINE. ★ Dynamic tracing would run the fragment — so it is permitted ONLY
after pure isolation (running an I/O fragment would fire its side effects). Routing is for EFFICIENCY; the z3 gate at
each extractor holds precision, so a wrong route only wastes a verifier call.
"""
from __future__ import annotations

from dataclasses import dataclass

from extract.classify import ast_tag as AT, effect_gate as EG


@dataclass
class Route:
    target: str                          # "checksum" | "parse_arith" | "periodic_fsm" | "io_frame" | "DECLINE"
    effect: str = ""
    reason: str = ""


def route(src: str) -> Route:
    eff = EG.classify_effect(src)
    if eff.effect == EG.NONDET:
        return Route("DECLINE", eff.effect, "nondet ⇒ no ∀-input determinism ⇒ permanent DECLINE (never routed to a fold)")
    t = AT.tag(src)
    if eff.effect == EG.IO:
        return Route("io_frame", eff.effect, "I/O present ⇒ §5 frame-isolate the surrounding arithmetic + §6 count the calls (I/O is residual)")
    # pure ⇒ route by shape (most specific first)
    if t.checksum:
        return Route("checksum", eff.effect, "pure + checksum signature ⇒ §2 checksum recognition")
    if t.parse_arith:
        return Route("parse_arith", eff.effect, "pure + parse signature ⇒ §3 Horner parsing arithmetic")
    if t.periodic_fsm:
        return Route("periodic_fsm", eff.effect, "pure + i%k guard ⇒ §4 periodic FSM")
    if t.accumulator:
        return Route("parse_arith", eff.effect, "pure accumulator loop ⇒ §3 (Horner / C-finite) by default")
    return Route("DECLINE", eff.effect, "pure but no recognized math shape ⇒ defer to the general conjecturers / DECLINE")


def adversarial_battery() -> dict:
    """★ a CRC fragment routes to checksum; ★ an atoi fragment routes to parse_arith; ★ an i%k loop routes to
    periodic_fsm; ★ a read-loop routes to io_frame (I/O residual); ★★ a rand fragment routes to DECLINE (nondet)."""
    crc = route("def crc32(data):\n c = 0xffffffff\n for b in data: c = (c >> 8) ^ b\n return c")
    atoi = route("def atoi(s):\n n = 0\n for ch in s: n = n*10 + ord(ch)\n return n")
    fsm = route("def f(n):\n s=0\n for i in range(n):\n  if i % 3 == 0: s += 1\n return s")
    io = route("def f(fd):\n n=0\n while read(fd, 4096) > 0: n += 1\n return n")
    nd = route("import random\ndef f(n): return random.randint(0,n)")
    cases = {
        "crc_to_checksum": crc.target == "checksum",
        "atoi_to_parse": atoi.target == "parse_arith",
        "imodk_to_periodic": fsm.target == "periodic_fsm",
        "readloop_to_io_frame": io.target == "io_frame",
        "rand_to_decline": nd.target == "DECLINE" and nd.effect == EG.NONDET,    # ★★ nondet permanent DECLINE
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
