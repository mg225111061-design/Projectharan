"""
v40 PHASE 7 — alternative representations + I/O boundary.
=========================================================
  • 60 RNS (residue number system) : big-int arithmetic in coprime residues (componentwise, parallel-friendly),
        reconstruct via CRT. EXACT-correct — BUT in pure single-thread Python, CPython's C big-int is already
        fast, so there is NO measured speed crossover here. Per Constitution §0.1/§4.5 we DO NOT fake one:
        the kernel is tagged @status("UNVERIFIED") (correctness proven, speed unverified in this environment)
        and the router does NOT auto-select it. The structural win (parallel/SIMD/fixed-width host) is real but
        unrealized here — stated honestly, not claimed.
  • I/O boundary : a VALUE that depends on external input is permanently DECLINE (causality — unpredictable);
        only the DISPATCH/pattern collapses to O(1) (an evidence-passing-style table). EXACT for the dispatch,
        never for the value.
"""
from __future__ import annotations

import time
from math import gcd, prod
from typing import Any, List

import kernel_verdict as KV
import kernel_router as R


# ── 60 · RNS arithmetic (EXACT correctness; speed UNVERIFIED in pure Python) ───────────────────────────
def _crt_reconstruct(residues: List[int], moduli: List[int]) -> int:
    x, M = residues[0] % moduli[0], moduli[0]
    for r, m in zip(residues[1:], moduli[1:]):
        inv = pow(M % m, -1, m)
        x = x + M * ((r - x) * inv % m)
        M *= m
    return x % M


def _rns_detect(d: Any) -> bool:
    return (isinstance(d, dict) and d.get("kind") == "rns_compute"
            and {"a", "b", "op", "moduli"} <= d.keys() and d["op"] in ("+", "*"))


def _rns_run(d: Any, **kw) -> KV.Verdict:
    a, b = int(d["a"]), int(d["b"])
    moduli = [int(m) for m in d["moduli"]]
    op = d["op"]
    for i in range(len(moduli)):
        for j in range(i + 1, len(moduli)):
            if gcd(moduli[i], moduli[j]) != 1:
                return KV.decline("RNS moduli not pairwise coprime", "rns")
    M = prod(moduli)
    true = a + b if op == "+" else a * b
    if not (0 <= true < M):
        return KV.decline(f"result {true} outside RNS range [0,∏m={M}) — would alias; add moduli ⇒ DECLINE", "rns")
    ra = [a % m for m in moduli]
    rb = [b % m for m in moduli]
    rres = [((x + y) if op == "+" else (x * y)) % m for x, y, m in zip(ra, rb, moduli)]
    val = _crt_reconstruct(rres, moduli)
    cert = KV.Cert(KV.EXACT, "rns_crt", passed=(val == true), check_cost="O(k)",
                   detail=f"componentwise {op} in {len(moduli)} residues, CRT-reconstructed; == direct big-int")
    if val != true:
        return KV.decline("RNS reconstruction disagreed with direct compute", "rns")
    return KV.exact(val, "rns", "O(k) residue ops (parallel-friendly)", cert)


def measure_rns() -> dict:
    """HONEST negative result: in pure single-thread Python, RNS does NOT beat CPython's C big-int — no
    crossover. The structural win is parallel/fixed-width hardware, not realized here ⇒ speed UNVERIFIED."""
    import random
    rng = random.Random(0)
    moduli = [2147483647, 2147483629, 2147483587, 2147483563, 2147483549, 2147483543, 2147483497, 2147483423]
    M = prod(moduli)
    a, b = rng.randrange(M // 4), rng.randrange(M // 4)
    t = time.perf_counter()
    for _ in range(2000):
        _ = a * b
    t_direct = (time.perf_counter() - t) * 1e6 / 2000
    t = time.perf_counter()
    for _ in range(2000):
        _rns_run({"kind": "rns_compute", "a": a, "b": b, "op": "*", "moduli": moduli})
    t_rns = (time.perf_counter() - t) * 1e6 / 2000
    return {"kernel": "rns", "correctness": "EXACT (CRT-verified)",
            "direct_bigint_us": round(t_direct, 3), "rns_us": round(t_rns, 2),
            "speed_crossover": None, "status": "UNVERIFIED",
            "note": "pure-Python single-thread: RNS slower than CPython C big-int (no crossover) ⇒ NOT "
                    "auto-routed; parallel/SIMD/fixed-width host would change this (unrealized here — not faked)"}


# ── I/O boundary: value ⇒ permanent DECLINE (causality); dispatch ⇒ O(1) EXACT (pattern, not value) ───
def _io_detect(d: Any) -> bool:
    return isinstance(d, dict) and d.get("kind") in ("io_value", "io_dispatch")


def _io_run(d: Any, **kw) -> KV.Verdict:
    if d["kind"] == "io_value":
        # the next external read / network byte / clock value is NOT a function of the program ⇒ unpredictable
        return KV.decline("external I/O value depends on the outside world (causality) — permanently DECLINE; "
                          "no collapse can predict an unread input", "io_boundary")
    # io_dispatch: a finite pattern→handler map collapses to an O(1) table lookup (EXACT for the DISPATCH only)
    table = d.get("table", {})
    key = d.get("key")
    if not isinstance(table, dict) or key is None or key not in table:
        return KV.decline("io_dispatch needs a table containing key (the pattern must be known)", "io_boundary")
    cert = KV.Cert(KV.EXACT, "dispatch_table", passed=True, check_cost="O(1)",
                   detail="evidence-passing-style O(1) dispatch on a KNOWN pattern — the handler, NOT the I/O value")
    return KV.exact({"handler": table[key]}, "io_boundary", "O(1) dispatch (value NOT predicted)", cert)


def measure_io() -> dict:
    vv = _io_run({"kind": "io_value", "source": "network"})
    dd = _io_run({"kind": "io_dispatch", "table": {"GET": "h_get", "POST": "h_post"}, "key": "GET"})
    return {"kernel": "io_boundary", "io_value": vv.status, "io_dispatch": dd.status,
            "note": "value→DECLINE (causality, permanent); dispatch→EXACT O(1) (pattern only, never the value)"}


def register_all():
    # RNS: correctness EXACT but speed UNVERIFIED in this environment ⇒ NOT auto-selected (honest, §4.5)
    R.register(R.Kernel(60, "rns", "H",
                        "requires pairwise-coprime moduli ∧ result < ∏m  ensures a op b exact ∧ grade=EXACT ∧ "
                        "cost=O(k) residue ops; SPEED unverified in pure Python ⇒ not auto-routed",
                        _rns_detect, _rns_run, status="UNVERIFIED"))
    R.register(R.Kernel(57, "io_boundary", "H",
                        "requires io request  ensures value⇒DECLINE (causality) ∧ dispatch⇒EXACT O(1) (pattern)",
                        _io_detect, _io_run))


register_all()
