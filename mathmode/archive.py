"""
§B3 — SAFE archive extraction: zip/tar/gz/bz2/xz → enumerate + type every inner file, defended against bombs.
=============================================================================================================
Attached archives are unpacked and every contained file is pulled out for analysis. Safety is MANDATORY and is
achieved by construction:
  • IN-MEMORY extraction (we never write to disk) ⇒ path-traversal / zip-slip CANNOT touch the filesystem; on
    top of that we still parse each entry name and REFUSE absolute / '..' / drive-letter paths (honest report).
  • Decompression-bomb defense: hard caps on per-entry size, total size, entry count, compression ratio, and
    nesting depth. A read is capped at the limit + 1 byte, so a lying header cannot exhaust memory; an entry over
    the cap or over the ratio is REFUSED with a reason (never silently truncated into a wrong analysis).
  • Nested archives (zip-in-zip, tar.gz) are recursed to a bounded depth; beyond it, the inner archive is kept as
    a leaf blob (honest), not expanded.
7z / rar need libraries absent here ⇒ honest UNVERIFIED (we say "unsupported", never fabricate an extraction).
The result is a flat list of SafeEntry{name, data, kind} ready for the §6 ingest pipeline, plus a refusals log.
"""
from __future__ import annotations

import bz2
import gzip
import io
import lzma
import tarfile
import zipfile
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

_ARCHIVE_EXTS = {"zip", "tar", "gz", "tgz", "bz2", "xz", "tbz2", "txz", "jar", "whl"}
_UNSUPPORTED = {"7z", "rar"}


@dataclass
class Limits:
    max_entry_bytes: int = 64 * 1024 * 1024       # 64 MB per file
    max_total_bytes: int = 256 * 1024 * 1024      # 256 MB total
    max_entries: int = 4000
    max_depth: int = 4
    max_ratio: int = 250                          # uncompressed / compressed (bomb signature)


@dataclass
class SafeEntry:
    name: str
    data: bytes
    kind: str                                     # file extension (lower-case), '' if none


@dataclass
class ExtractReport:
    entries: List[SafeEntry] = field(default_factory=list)
    refused: List[Tuple[str, str]] = field(default_factory=list)   # (name, reason)
    total_bytes: int = 0
    truncated: bool = False                       # a cap stopped us early
    formats: List[str] = field(default_factory=list)
    unverified: Optional[str] = None


def _ext(name: str) -> str:
    base = name.rsplit("/", 1)[-1]
    return base.rsplit(".", 1)[-1].lower() if "." in base else ""


def archive_format(name: str) -> Optional[str]:
    e = _ext(name)
    if name.endswith(".tar.gz") or name.endswith(".tar.bz2") or name.endswith(".tar.xz"):
        return "tar"
    if e in _ARCHIVE_EXTS:
        return e
    if e in _UNSUPPORTED:
        return e
    return None


def is_archive(name: str) -> bool:
    return archive_format(name) is not None


def _safe_name(name: str) -> bool:
    """Reject path-traversal / absolute / drive-letter entry names (zip-slip defense, belt-and-suspenders)."""
    if not name or name.endswith("/"):
        return False
    if name.startswith("/") or name.startswith("\\") or (len(name) > 1 and name[1] == ":"):
        return False
    parts = name.replace("\\", "/").split("/")
    return ".." not in parts and "" not in parts[:-1]


def _add(rep: ExtractReport, name: str, data: bytes, lim: Limits, depth: int):
    """Add one extracted blob — recursing into nested archives (bounded), enforcing the total/count caps."""
    if len(rep.entries) >= lim.max_entries:
        rep.truncated = True
        return
    if rep.total_bytes + len(data) > lim.max_total_bytes:
        rep.truncated = True
        rep.refused.append((name, "total-size cap reached ⇒ refused (bomb defense)"))
        return
    rep.total_bytes += len(data)
    if is_archive(name) and depth < lim.max_depth and archive_format(name) not in _UNSUPPORTED:
        sub = extract(data, name, lim, depth + 1)
        rep.entries.extend(sub.entries)
        rep.refused.extend(sub.refused)
        rep.formats.extend(sub.formats)
        rep.total_bytes += sub.total_bytes
        rep.truncated = rep.truncated or sub.truncated
    else:
        rep.entries.append(SafeEntry(name, data, _ext(name)))


def _capped_read(fileobj, declared: int, lim: Limits, name: str, comp: int, rep: ExtractReport) -> Optional[bytes]:
    """Read at most max_entry_bytes (+1 to detect overflow); refuse oversize or bomb-ratio entries."""
    if declared > lim.max_entry_bytes:
        rep.refused.append((name, f"declared {declared}B > per-entry cap {lim.max_entry_bytes}B ⇒ refused"))
        return None
    data = fileobj.read(lim.max_entry_bytes + 1)
    if len(data) > lim.max_entry_bytes:
        rep.refused.append((name, "expanded past per-entry cap ⇒ refused (bomb defense)"))
        return None
    if comp > 0 and len(data) // max(comp, 1) > lim.max_ratio and len(data) > 1 << 16:
        rep.refused.append((name, f"compression ratio {len(data)//max(comp,1)}× > {lim.max_ratio}× ⇒ refused (bomb)"))
        return None
    return data


def extract(data: bytes, name: str = "archive.zip", lim: Limits = None, depth: int = 0) -> ExtractReport:
    """Safely extract an archive (in-memory) → enumerate + type every inner file. Honest UNVERIFIED for 7z/rar."""
    lim = lim or Limits()
    rep = ExtractReport()
    fmt = archive_format(name) or "zip"
    rep.formats.append(fmt)
    if fmt in _UNSUPPORTED:
        rep.unverified = f"{fmt} not supported (py7zr/rarfile absent) — honest UNVERIFIED, no extraction attempted"
        return rep
    try:
        if fmt == "zip" or fmt in ("jar", "whl"):
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                for info in z.infolist():
                    if info.is_dir():
                        continue
                    if len(rep.entries) >= lim.max_entries:
                        rep.truncated = True
                        break
                    if not _safe_name(info.filename):
                        rep.refused.append((info.filename, "unsafe path (zip-slip) ⇒ refused, not materialized"))
                        continue
                    with z.open(info) as f:
                        blob = _capped_read(f, info.file_size, lim, info.filename, info.compress_size, rep)
                    if blob is not None:
                        _add(rep, info.filename, blob, lim, depth)
        elif fmt in ("tar", "tgz", "tbz2", "txz"):
            with tarfile.open(fileobj=io.BytesIO(data)) as t:    # tarfile auto-detects gz/bz2/xz compression
                for m in t.getmembers():
                    if not m.isfile():
                        continue
                    if len(rep.entries) >= lim.max_entries:
                        rep.truncated = True
                        break
                    if not _safe_name(m.name):
                        rep.refused.append((m.name, "unsafe path (tar-slip) ⇒ refused, not materialized"))
                        continue
                    ex = t.extractfile(m)
                    if ex is None:
                        continue
                    blob = _capped_read(ex, m.size, lim, m.name, m.size, rep)
                    if blob is not None:
                        _add(rep, m.name, blob, lim, depth)
        elif fmt in ("gz", "bz2", "xz"):                          # single-stream: one inner file
            dec = {"gz": gzip, "bz2": bz2, "xz": lzma}[fmt]
            with dec.open(io.BytesIO(data)) as f:
                blob = _capped_read(f, 0, lim, name, len(data), rep)
            if blob is not None:
                inner = name.rsplit(".", 1)[0] if "." in name else name + ".out"
                _add(rep, inner.rsplit("/", 1)[-1], blob, lim, depth)
    except Exception as e:                                        # noqa: BLE001
        rep.unverified = f"archive read failed ({type(e).__name__}: {e})"
    return rep
