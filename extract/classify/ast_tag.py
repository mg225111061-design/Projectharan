"""
§AQ §1.1 — AST TAG (layer 1: broad, cheap, NON-judgemental). Tag a fragment's shape; precision is layer 2's job.
================================================================================================================
A coarse signature scan — library calls (crc32/lfilter), accumulator loops (x = x*B + c / x += …), I/O calls
(read/write/socket), state machines (while + state + i%k) — that ROUTES a fragment toward a §2..§6 extractor. ★ This
only tags; it never decides foldability (the z3 gate does). A wrong tag wastes one verifier call, never a false fold.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import List, Set

_CHECKSUM_NAMES = ("crc", "adler", "fletcher", "luhn", "isbn", "ean", "upc", "rabin", "karp", "djb2", "sdbm",
                   "fnv", "checksum", "rolling_hash", "polyhash", "murmur", "pearson")
_PARSE_NAMES = ("atoi", "parse_int", "parseint", "to_int", "fromhex", "b64decode", "base64", "varint", "leb128",
                "inet_aton", "strptime", "uuid", "from_bytes", "decode")
_IO_NAMES = ("read", "write", "open", "recv", "send", "socket", "fetch", "request", "get", "post", "flush",
             "readline", "readinto", "sendall", "connect", "accept", "sleep", "print", "input")
_NONDET_NAMES = ("random", "randint", "rand", "uniform", "shuffle", "time", "now", "urandom", "uuid4", "getrandbits")


@dataclass
class Tags:
    checksum: bool = False
    parse_arith: bool = False
    periodic_fsm: bool = False
    io: bool = False
    nondet: bool = False
    accumulator: bool = False
    called: List[str] = field(default_factory=list)


def _call_names(tree) -> List[str]:
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                out.append(f.id.lower())
            elif isinstance(f, ast.Attribute):
                out.append(f.attr.lower())
    return out


def tag(src: str) -> Tags:
    """Tag the fragment's shape. Pure scan — no foldability decision."""
    try:
        tree = ast.parse(src)
    except Exception:  # noqa: BLE001
        return Tags()
    calls = _call_names(tree)
    low = src.lower()
    t = Tags(called=calls)
    t.io = any(any(io == c or io in c for io in _IO_NAMES) for c in calls)
    t.nondet = any(any(nd == c or nd in c for nd in _NONDET_NAMES) for c in calls)
    t.checksum = any(k in low for k in _CHECKSUM_NAMES)
    t.parse_arith = any(k in low for k in _PARSE_NAMES) or "* base" in low or "*base" in low
    # accumulator loop: an augmented assign or `x = x <op> …` inside a loop
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.While)):
            for s in ast.walk(node):
                if isinstance(s, ast.AugAssign):
                    t.accumulator = True
                if (isinstance(s, ast.Assign) and len(s.targets) == 1 and isinstance(s.targets[0], ast.Name)
                        and isinstance(s.value, ast.BinOp)):
                    names = {x.id for x in ast.walk(s.value) if isinstance(x, ast.Name)}
                    if s.targets[0].id in names:
                        t.accumulator = True
    # periodic FSM: a guard on i % k
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
            t.periodic_fsm = True
    return t
