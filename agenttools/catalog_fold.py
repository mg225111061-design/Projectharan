"""
agenttools/catalog_fold.py — FOLD-ELIGIBLE tools (10H directive Task 2): genuine structural/numeric cores,
each a thin wrapper delegating to an EXISTING recognizer/fold engine — never new fold logic (RF-5's honesty
trail: every tool here names the real engine it calls via `delegate=`).
=================================================================================================================
  detect_code_structure   -> frontend.dispatch.dispatch          (structure recognition -> engine routing)
  classify_haran_closure  -> haran_parser.parse + closure_classifier.classify_fn (closed-form classification)
  recognize_checksum      -> extract.checksum.fold                (CRC/Adler/Luhn/FNV recognition)
  recognize_parse_arith   -> extract.parse_arith.fold              (Horner/date/bitpack/float recognition)

Each returns the engine's own verdict verbatim (as a dict) — this module does not grade, weaken, or
reinterpret anything; a DECLINE/NONE from the underlying engine stays a DECLINE/NONE here.
"""
from __future__ import annotations

import dataclasses
from typing import Dict

from agenttools.registry import FOLD_ELIGIBLE, Tool, register


def detect_code_structure(code: str, language: str = "python") -> Dict:
    from frontend import dispatch as FD
    d = FD.dispatch(code, language)
    return dataclasses.asdict(d)


def classify_haran_closure(haran_code: str) -> Dict:
    import closure_classifier as CC
    from haran_parser import parse
    prog = parse(haran_code)
    if prog.errors:
        return {"kind": "PARSE_ERROR", "method": "-", "closed_form": "-", "proof": str(prog.errors[0]),
               "speedup": "none"}
    fns = prog.fns()
    if not fns:
        return {"kind": "NONE", "method": "-", "closed_form": "-", "proof": "no function found",
               "speedup": "none"}
    v = CC.classify_fn(fns[0])
    return dataclasses.asdict(v)


def recognize_checksum(code: str) -> Dict:
    from extract.checksum import fold as _fold
    return dataclasses.asdict(_fold(code))


def recognize_parse_arith(code: str) -> Dict:
    from extract.parse_arith import fold as _fold
    return dataclasses.asdict(_fold(code))


def _schema(props: Dict, required=None) -> Dict:
    return {"type": "object", "properties": props, "required": required or []}


register(Tool("detect_code_structure",
              "Recognize a structural pattern in source code (sum/poly loop, linear recurrence, checksum, "
              "Horner, convolution) and report whether/how it routes to a verified fold engine.",
              _schema({"code": {"type": "string"}, "language": {"type": "string"}}, ["code"]),
              detect_code_structure, FOLD_ELIGIBLE, delegate="frontend.dispatch.dispatch",
              keywords=("structure", "fold", "recurrence", "loop", "recognize", "optimize")))
register(Tool("classify_haran_closure",
              "Classify a HARAN function's closed-form structure (CLOSED/UNKNOWN/NO_STRUCTURE/ABSENT) via "
              "the fold-closure classifier (Faulhaber/Gosper/C-finite/Galois/Liouville).",
              _schema({"haran_code": {"type": "string"}}, ["haran_code"]),
              classify_haran_closure, FOLD_ELIGIBLE, delegate="closure_classifier.classify_fn",
              keywords=("haran", "closed", "form", "classify", "closure")))
register(Tool("recognize_checksum",
              "Recognize a checksum/hash algorithm's signature (CRC/Adler/Luhn/FNV) and report the exact "
              "mechanism it reduces to, z3-re-verified.",
              _schema({"code": {"type": "string"}}, ["code"]),
              recognize_checksum, FOLD_ELIGIBLE, delegate="extract.checksum.fold",
              keywords=("checksum", "crc", "hash", "luhn", "adler", "fnv")))
register(Tool("recognize_parse_arith",
              "Recognize parsing-arithmetic (atoi/varint/date/base64/IPv4/float) and report the exact "
              "existing mechanism it reduces to (Horner/C-finite/bitpack), z3-re-verified.",
              _schema({"code": {"type": "string"}}, ["code"]),
              recognize_parse_arith, FOLD_ELIGIBLE, delegate="extract.parse_arith.fold",
              keywords=("parse", "atoi", "horner", "date", "base64", "ipv4")))
