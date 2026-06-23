"""
MATH-Ascent §6 — universal file ingestion + FOLD-accelerated analysis (honest about what it cannot read).
=========================================================================================================
Ingest a document, find the mathematical STRUCTURE in it, and route it to the §5 solver. The headline is
fold-accelerated analysis: a column of numbers in a spreadsheet that is secretly a C-finite sequence is RECOGNIZED
(shortest exact linear recurrence, verified) and FOLDED to an O(log n) closed form — a genuine collapse, measured.
A "Σ …" expression in a document is routed to the broth/Gosper fold. Plain prose with no math ⇒ honest DECLINE.

Ingestion is deliberately dependency-light and honest:
  • XLSX / DOCX / PPTX are ZIP+XML — parsed with the STANDARD LIBRARY (zipfile + xml), no fragile third-party deps.
  • CSV / JSON / TXT — standard library.
  • PDF — pypdf is [BLOCKED] in this env (cryptography/_cffi_backend panics) ⇒ honest UNVERIFIED, never a guess.
  • Images / photos of equations — no OCR engine present (no tesseract) ⇒ honest UNVERIFIED (equation→symbolic
    needs OCR; we do not fabricate a transcription).
Honest UNVERIFIED on what we cannot read; honest DECLINE on what has no foldable structure. Never a fabricated result.
"""
from __future__ import annotations

import io
import json
import re
import time
import zipfile
from dataclasses import dataclass, field
from fractions import Fraction
from typing import List, Optional, Sequence, Tuple

import cfinite
import kernel_verdict as KV
from mathmode import linear_algebra as LA
from mathmode import solver as SOLVER


# ── ingestion result ─────────────────────────────────────────────────────────────────────────────────────
@dataclass
class Ingested:
    fmt: str
    text: str = ""
    sequences: List[List[int]] = field(default_factory=list)   # numeric rows/columns found
    unverified: Optional[str] = None                           # honest reason we could not fully read it


def _localname(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _xml_texts(xml_bytes: bytes, want: str) -> List[str]:
    import xml.etree.ElementTree as ET
    out = []
    try:
        root = ET.fromstring(xml_bytes)
    except Exception:                                          # noqa: BLE001
        return out
    for el in root.iter():
        if _localname(el.tag) == want and el.text:
            out.append(el.text)
    return out


def _extract_docx(data: bytes) -> Ingested:
    import xml.etree.ElementTree as ET
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    paras = []                                                # one line per <w:p> paragraph (preserve structure)
    for p in root.iter():
        if _localname(p.tag) != "p":
            continue
        runs = [t.text for t in p.iter() if _localname(t.tag) == "t" and t.text]
        paras.append("".join(runs))
    return Ingested("docx", text="\n".join(paras))


def _extract_pptx(data: bytes) -> Ingested:
    text = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for n in sorted(x for x in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", x)):
            text.extend(_xml_texts(z.read(n), "t"))
    return Ingested("pptx", text="\n".join(text))


def _extract_xlsx(data: bytes) -> Ingested:
    import xml.etree.ElementTree as ET
    cols: dict = {}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        sheets = sorted(x for x in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", x))
        for sn in sheets:
            root = ET.fromstring(z.read(sn))
            for row in root.iter():
                if _localname(row.tag) != "row":
                    continue
                for c in row:
                    if _localname(c.tag) != "c":
                        continue
                    ref = c.get("r", "")
                    col = re.match(r"[A-Z]+", ref)
                    v = next((ch.text for ch in c if _localname(ch.tag) == "v"), None)
                    if v is not None and col is not None:
                        try:
                            cols.setdefault(col.group(), []).append(int(round(float(v))))
                        except ValueError:
                            pass
    seqs = [v for _, v in sorted(cols.items()) if len(v) >= 4]
    return Ingested("xlsx", sequences=seqs)


def _extract_csv(data: bytes) -> Ingested:
    import csv
    rows = list(csv.reader(io.StringIO(data.decode("utf-8", "replace"))))
    cols: dict = {}
    for r in rows:
        for j, cell in enumerate(r):
            try:
                cols.setdefault(j, []).append(int(round(float(cell))))
            except (ValueError, TypeError):
                pass
    seqs = [v for _, v in sorted(cols.items()) if len(v) >= 4]
    return Ingested("csv", text=data.decode("utf-8", "replace"), sequences=seqs)


def ingest(path: str = None, data: bytes = None, fmt: str = None) -> Ingested:
    """Ingest a file by extension/content. PDF and images ⇒ honest UNVERIFIED (no working reader/OCR here)."""
    if data is None:
        with open(path, "rb") as f:
            data = f.read()
    fmt = (fmt or (path.rsplit(".", 1)[-1].lower() if path and "." in path else "txt"))
    try:
        if fmt == "docx":
            return _extract_docx(data)
        if fmt == "pptx":
            return _extract_pptx(data)
        if fmt == "xlsx":
            return _extract_xlsx(data)
        if fmt == "csv":
            return _extract_csv(data)
        if fmt == "json":
            return Ingested("json", text=json.dumps(json.loads(data.decode("utf-8", "replace"))))
        if fmt in ("pdf",):
            return Ingested("pdf", unverified="PDF reader [BLOCKED]: pypdf/cryptography unavailable in this env")
        if fmt in ("png", "jpg", "jpeg", "gif", "bmp", "tif", "tiff", "webp"):
            return Ingested(fmt, unverified="image OCR [BLOCKED]: no OCR engine (tesseract absent) — "
                                            "equation→symbolic not attempted (never fabricated)")
        return Ingested("txt", text=data.decode("utf-8", "replace"))
    except Exception as e:                                     # noqa: BLE001
        return Ingested(fmt, unverified=f"ingest failed ({type(e).__name__}: {e})")


# ── the fold accelerator: a numeric sequence → shortest verified C-finite recurrence ────────────────────
def find_recurrence(seq: Sequence[int], max_order: int = None) -> Optional[Tuple[List[int], List[int]]]:
    """Shortest exact linear recurrence f(n)=Σ c_j f(n−1−j) that fits the WHOLE sequence (verified on every
    term). Exact Fraction arithmetic; returns (c, init) in the cfinite convention, or None (not C-finite)."""
    s = [int(x) for x in seq]
    m = len(s)
    if m < 4:
        return None
    max_order = max_order or m // 2
    for d in range(1, max_order + 1):
        if m < 2 * d + 1:                                     # need d equations to solve + ≥1 to verify
            break
        A = [[s[d + i - 1 - j] for j in range(d)] for i in range(d)]
        b = [s[d + i] for i in range(d)]
        X = LA._rref_solve(LA._F(A), [[Fraction(v)] for v in b])
        if X is None:
            continue                                          # singular window — try a longer order
        c = [row[0] for row in X]
        if any(x.denominator != 1 for x in c):
            continue                                          # non-integer ⇒ not a clean C-finite recurrence
        ci = [int(x) for x in c]
        if all(s[n] == sum(ci[j] * s[n - 1 - j] for j in range(d)) for n in range(d, m)):
            return ci, s[:d]
    return None


@dataclass
class Finding:
    provenance: str
    solution: "SOLVER.MathSolution"


def analyze(ing: Ingested) -> dict:
    """Find math in the ingested content and route it to the solver. Sequences ⇒ fold to a closed form;
    'Σ …' / 'sum: …' lines ⇒ broth/Gosper. Returns findings + honest declines/unverified, measured."""
    t0 = time.perf_counter()
    findings: List[Finding] = []
    declines: List[str] = []
    if ing.unverified:
        return dict(fmt=ing.fmt, findings=[], declines=[], unverified=ing.unverified, ms=0.0)

    # 1) numeric sequences → C-finite recurrence → FOLD (the headline acceleration)
    for i, seq in enumerate(ing.sequences):
        rec = find_recurrence(seq)
        if rec is None:
            declines.append(f"sequence#{i} (len {len(seq)}): no C-finite recurrence ⇒ DECLINE (not foldable)")
            continue
        c, init = rec
        sol = SOLVER.solve({"fold": {"kind": "linear_recurrence", "c": c, "init": init}})
        if sol.verdict.status == KV.EXACT:
            findings.append(Finding(f"sequence#{i}: order-{len(c)} recurrence c={c} → O(log n) companion fold", sol))
        else:
            declines.append(f"sequence#{i}: recurrence c={c} failed to fold ⇒ DECLINE")

    # 2) text math: a documented convention — 'sum: <expr in k>' or 'Σ <expr in k>' → the solver
    import sympy as sp
    _k = sp.Symbol("k", integer=True)
    for line in (ing.text or "").splitlines():
        m = re.match(r"\s*(?:sum\s*[:=]\s*|Σ\s*)(.+)$", line.strip(), re.IGNORECASE)
        if not m:
            continue
        summand = m.group(1).strip().rstrip(".").replace("^", "**")
        if "k" not in summand:
            continue
        try:
            sp.sympify(summand, locals={"k": _k})             # only route what actually parses
        except Exception:                                     # noqa: BLE001
            declines.append(f"text '{line.strip()}': not a parseable summand ⇒ DECLINE")
            continue
        sol = SOLVER.solve({"sum": summand})
        if sol.verdict.status in (KV.EXACT, KV.PROBABILISTIC):
            findings.append(Finding(f"text Σ {summand}", sol))
        else:
            declines.append(f"text Σ {summand}: {sol.verdict.reason}")

    if not findings and not declines:
        declines.append("no mathematical structure found (unstructured content) ⇒ DECLINE")
    return dict(fmt=ing.fmt, findings=findings, declines=declines, unverified=None,
                ms=round((time.perf_counter() - t0) * 1000, 2))


def analyze_file(path: str = None, data: bytes = None, fmt: str = None) -> dict:
    """Ingest + analyze in one call."""
    return analyze(ingest(path=path, data=data, fmt=fmt))
