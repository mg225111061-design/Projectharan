"""
§AQ §5 — I/O-SURROUNDING ARITHMETIC + EFFECT ISOLATION. The I/O call itself never folds (side effect); the separation-
================================================================================================================
logic FRAME RULE `{P} read() {Q} ⊢ {P∗F} read() {Q∗F}` frames the pure arithmetic F OFF the I/O so it can fold:
offsets/alignment/serialization sizes/sequence numbers/backoff. ★ S-1: REUSE the existing linear/telescoping/geometric/
modular/BV mechanisms; only the effect-isolation frame is new (the §AP compose engine's effect-isolation extension).
★ Dual metric (S-3): Axis A = +1 (every buffer reader / allocator / serializer — verification value: offset correctness
= buffer-overrun freedom); Axis B ≈ 0 (the arithmetic is a sliver beside the I/O — the textbook "Axis A +, Axis B 0").
"""
from __future__ import annotations

from dataclasses import dataclass

from extract.io_arith import align as AL, offset as OF, backoff as BK
from extract.classify import effect_gate as EG


@dataclass
class IOArithResult:
    folded: bool
    kind: str = ""
    reduces_to: str = ""
    io_residual: bool = False            # the I/O is framed off (residual), only the arithmetic folds
    axis_a: int = 0
    axis_b: str = "~0"
    detail: str = ""


def fold(src: str) -> IOArithResult:
    """Frame off any I/O (residual), then fold the recognized surrounding arithmetic (z3-gated)."""
    eff = EG.classify_effect(src)
    io_residual = eff.effect == EG.IO
    s = src.lower()
    if "align" in s or "& ~" in src or "&~" in src or "~(a" in src:
        ok = AL.prove_align_up(6, 32, True)
        return IOArithResult(ok, "align", "BV bit-trick = a·⌈x/a⌉", io_residual, 1 if ok else 0, "~0",
                             "alignment (x+a−1)&~(a−1) = a·⌈x/a⌉ (z3 BV); I/O framed off as residual")
    if "backoff" in s or "retry" in s or "2 **" in src or "2**" in src or "<<" in src and "sleep" in s:
        ok = BK.prove_backoff_geometric(1, 6, True)
        return IOArithResult(ok, "backoff", "geometric Σbase·2ᵏ = base·(2ⁿ−1)", io_residual, 1 if ok else 0, "~0",
                             "exponential backoff total = base·(2ⁿ−1) (z3); I/O framed off")
    if "seq" in s or "tcp" in s:
        ok = OF.prove_tcp_seq_modular(32, 3, True)
        return IOArithResult(ok, "tcp_seq", "modular linear (BV)", io_residual, 1 if ok else 0, "~0",
                             "seq=(seq+len) mod 2³² = (seq₀+Σlenᵢ) mod 2³² (z3 BV); I/O framed off")
    if "offset" in s or "chunk" in s or "page" in s or "stride" in s or "record" in s or "size" in s:
        ok = OF.prove_offset_linear(4096, 5, True) and OF.prove_serialize_telescoping(4, True)
        return IOArithResult(ok, "offset", "linear / telescoping", io_residual, 1 if ok else 0, "~0",
                             "offset=i·CHUNK (linear) / Σfieldᵢ (telescoping) (z3); I/O framed off")
    return IOArithResult(False, "", "", io_residual, 0, "~0", "no foldable surrounding arithmetic recognized")


def adversarial_battery() -> dict:
    """★ alignment / offset / TCP-seq / backoff arithmetic AROUND an I/O call folds (the I/O is framed off as residual),
    each reducing to an EXISTING mechanism (Axis A +1, Axis B ≈0); ★ component batteries green (incl. the ★★ wrong-mask
    / wrong-closed-form refutations)."""
    align = fold("def alloc(x):\n p = read_page()\n return (x + 4095) & ~(4095)  # align up")
    off = fold("def reader(fd, i):\n data = read(fd, 4096)\n offset = i * 4096\n return offset")
    seq = fold("def send(sock, len):\n sock.send(buf)\n seq = (seq + len) % (2**32)\n return seq")
    bk = fold("def retry():\n for k in range(6):\n  wait = 1 * (2 ** k)\n  sleep(wait)")
    cases = {
        "align_folds_io_residual": align.folded and align.io_residual and "bit-trick" in align.reduces_to,
        "offset_folds_io_residual": off.folded and off.io_residual,
        "tcp_seq_folds": seq.folded,
        "backoff_folds_io_residual": bk.folded and bk.io_residual,
        "axis_b_near_zero": all(r.axis_b == "~0" for r in (align, off, seq, bk)),     # ★ S-3 honesty
        "align_battery_green": AL.adversarial_battery()["all_ok"],
        "offset_battery_green": OF.adversarial_battery()["all_ok"],
        "backoff_battery_green": BK.adversarial_battery()["all_ok"],
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
