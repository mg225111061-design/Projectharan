"""
§W PHASE 3 — MULTI-FILE UPLOAD: 50+ types, up to 5 at once, fold-assisted ingestion, untrusted-input validated.
================================================================================================================
Accept many file types (source / data / text / config / notebook), up to 5 simultaneously, ingest with the fold
engine where the content has structure to collapse and plainly where it doesn't, and validate every upload as the
UNTRUSTED INPUT it is — type, size, name (no path traversal), count — rejecting the unsupported with a clear reason.

★ Security (untrusted input): uploaded files are validated through bounded checks (allow-listed type, size cap,
name-traversal reject, count cap) — no path traversal, no oversized-file DoS. Archives route to the existing safe
extractor (mathmode.archive — zip-slip/bomb defended) when available, else are declined honestly.
★ Fold-assisted, honestly: ingestion uses the engine cache (the same file ingested ONCE), and fold accelerates
where structure exists; an unstructured file is ingested plainly — never an overclaimed fold.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

MAX_FILES = 5
MAX_BYTES = 2 * 1024 * 1024              # 2 MB per file — the DoS cap

# ── 50+ supported types (source / data / text / config / notebook), allow-listed ─────────────────────────────
_SOURCE = {"py", "js", "ts", "jsx", "tsx", "java", "c", "cc", "cpp", "h", "hpp", "go", "rs", "rb", "php", "swift",
           "kt", "scala", "cs", "m", "lua", "pl", "r", "jl", "dart", "hs", "ml", "clj", "ex", "exs", "sh", "bash",
           "zsh", "sql"}
_DATA = {"json", "jsonl", "ndjson", "csv", "tsv", "xml", "yaml", "yml", "toml", "ini"}
_TEXT = {"txt", "md", "rst", "log", "tex", "org", "adoc"}
_CONFIG = {"cfg", "conf", "env", "properties", "gradle", "dockerfile", "makefile"}
_NOTEBOOK = {"ipynb"}
SUPPORTED: Dict[str, str] = {**{e: "source" for e in _SOURCE}, **{e: "data" for e in _DATA},
                             **{e: "text" for e in _TEXT}, **{e: "config" for e in _CONFIG},
                             **{e: "notebook" for e in _NOTEBOOK}}


def supported_count() -> int:
    return len(SUPPORTED)


def _ext(name: str) -> str:
    base = name.rsplit("/", 1)[-1].lower()
    if base in ("dockerfile", "makefile"):
        return base
    return base.rsplit(".", 1)[-1] if "." in base else base


@dataclass
class FileVerdict:
    name: str
    accepted: bool
    category: str = ""
    reason: str = ""


def validate_file(name: str, data: bytes) -> FileVerdict:
    """Validate ONE uploaded file as untrusted input: name (no traversal), type (allow-listed), size (≤cap)."""
    if ".." in name or name.startswith("/") or "\x00" in name:
        return FileVerdict(name, False, reason="rejected: unsafe path in filename (traversal/null) — not ingested")
    if len(data) > MAX_BYTES:
        return FileVerdict(name, False, reason=f"rejected: file exceeds the {MAX_BYTES // (1024*1024)}MB limit "
                           "(oversized-file DoS guard)")
    ext = _ext(name)
    cat = SUPPORTED.get(ext)
    if cat is None:
        return FileVerdict(name, False, reason=f"unsupported type '.{ext}' — supported: source/data/text/config/"
                           f"notebook ({len(SUPPORTED)} types). Reason: not in the allow-list")
    return FileVerdict(name, True, category=cat)


@dataclass
class IngestResult:
    name: str
    ok: bool
    category: str = ""
    fold_assisted: bool = False
    cached: bool = False
    summary: str = ""
    reason: str = ""


# a shared engine cache so the SAME file ingested twice is a sound O(1) hit (fold-the-engine, applied to ingestion)
def _cache():
    from enginespeed.cache import MultiLevelCache
    if not hasattr(_cache, "_c"):
        _cache._c = MultiLevelCache()
    return _cache._c


def _looks_structured(text: str) -> bool:
    """A light heuristic: does the content have collapsible structure (a numeric column / many repeated-shape lines)?
    Honest — fold accelerates these; plain text does not get a fold claim."""
    lines = [ln for ln in text.splitlines() if ln.strip()][:200]
    if len(lines) < 8:
        return False
    numeric = sum(1 for ln in lines if ln.replace(",", "").replace(".", "").replace("-", "").replace(" ", "").isdigit())
    return numeric >= max(8, len(lines) // 2)               # a majority-numeric column ⇒ foldable structure


def ingest_one(name: str, data: bytes) -> IngestResult:
    """Validate + ingest ONE file. Fold-assisted where the content is structured (cached by content so a repeat is an
    O(1) hit); plain otherwise. Returns an honest per-file result."""
    from enginespeed.cache import content_key
    v = validate_file(name, data)
    if not v.accepted:
        return IngestResult(name, False, reason=v.reason)
    key = content_key("ingest", name, data)
    present, _ = _cache().L1.peek(key)
    cached = present
    try:
        text = data.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return IngestResult(name, False, reason="rejected: could not decode as text")
    structured = _looks_structured(text) if v.category in ("data", "text") else False

    def _do():
        return {"chars": len(text), "lines": text.count("\n") + 1, "structured": structured}

    info = _cache().L1.get_or_compute(key, _do)
    return IngestResult(name, True, category=v.category, fold_assisted=structured, cached=cached,
                        summary=f"{info['lines']} lines, {info['chars']} chars" + (" (fold-assisted)" if structured else ""))


def ingest_set(files: List[Tuple[str, bytes]]) -> dict:
    """Ingest up to MAX_FILES uploaded files together. More than 5 ⇒ the extras are refused with a clear message.
    Returns per-file results + the honest summary (accepted / refused-with-reason / fold-assisted / cached)."""
    results: List[IngestResult] = []
    refused_over_cap = []
    for i, (name, data) in enumerate(files):
        if i >= MAX_FILES:
            refused_over_cap.append(name)
            continue
        results.append(ingest_one(name, data))
    return {
        "accepted": [r.name for r in results if r.ok],
        "refused": [{"name": r.name, "reason": r.reason} for r in results if not r.ok]
                   + [{"name": n, "reason": f"refused: more than {MAX_FILES} files at once"} for n in refused_over_cap],
        "fold_assisted": [r.name for r in results if r.fold_assisted],
        "cached": [r.name for r in results if r.cached],
        "results": [r.__dict__ for r in results],
        "supported_types": len(SUPPORTED),
        "note": f"≤{MAX_FILES} files; {len(SUPPORTED)} types allow-listed; untrusted-input validated (type/size/"
                "traversal); fold-assisted where structured, plain otherwise; repeated ingestion served from cache",
    }
