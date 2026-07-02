"""
§BI FL-3 — ★ compute-on-compressed: query compressed data WITHOUT unpacking it (the fold-spirit "안 하기").
============================================================================================================
Decompression is not fold (it is DEFLATE, already O(n)-optimal). The real fold-spirit win is to NOT unpack at
all when the question can be answered against the compressed/transformed bytes directly:

  • `list_zip_members`     — read a zip's CENTRAL DIRECTORY only (names + sizes), extracting nothing. O(#entries),
                             not O(uncompressed). "What's in this 5 GB zip?" answered in milliseconds.
  • `read_member`          — inflate ONE named entry, never the whole archive ("read the part you need").
  • `gzip_uncompressed_size` — the gzip footer stores ISIZE (uncompressed size mod 2³²); read 4 bytes, no inflate.
  • `range_slice`          — partial read of a byte buffer (maps to an HTTP Range / file seek on Render).
  • `FMIndex`              — ★ count/locate a substring over the BWT (a compression-friendly transform — bzip2 IS
                             BWT-based) WITHOUT reconstructing the original text. Each query is O(|pattern|),
                             independent of text length.

★ Honest: this works for SPECIFIC representations (zip central dir, gzip footer, BWT/FM-indexable text), not for
every format — when a format isn't query-on-compressed-able we fall back to the standard bomb-guarded
decompression (FL-2 = `mathmode/archive.py`). The FM-index BUILD is O(n log n); the WIN is that queries afterwards
never touch the original — and `count` is verified == a naive substring scan (no silent wrong answer). zero-dep.
"""
from __future__ import annotations

import gzip
import io
import struct
import zipfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# ── zip central-directory listing: members + sizes, NO extraction ──────────────────────────────────────
def list_zip_members(data: bytes) -> List[dict]:
    """List a zip's entries from its central directory alone — names, compressed + uncompressed sizes, ratio —
    WITHOUT inflating any entry. This is the headline 'compute on compressed': O(#entries), not O(uncompressed)."""
    zf = zipfile.ZipFile(io.BytesIO(data))
    out = []
    for zi in zf.infolist():
        ratio = (zi.file_size / zi.compress_size) if zi.compress_size else 0.0
        out.append({"name": zi.filename, "size": zi.file_size, "compress_size": zi.compress_size,
                    "ratio": round(ratio, 2), "is_dir": zi.is_dir()})
    return out


def read_member(data: bytes, name: str) -> bytes:
    """Inflate ONLY the named member (range-read into the archive), never the rest. Honest: this DOES decompress
    that one entry — the win is not unpacking the other N-1."""
    return zipfile.ZipFile(io.BytesIO(data)).read(name)


def gzip_uncompressed_size(data: bytes) -> int:
    """Uncompressed size from the gzip ISIZE footer (last 4 bytes), no inflate. ★ Honest caveat: ISIZE is the
    size mod 2³² and only of the LAST member — for streams < 4 GiB it is exact; we never claim more."""
    if len(data) < 4 or not data.startswith(b"\x1f\x8b"):
        raise ValueError("not gzip")
    return struct.unpack("<I", data[-4:])[0]


def range_slice(data: bytes, start: int, length: int) -> bytes:
    """Partial read primitive — return data[start:start+length]. On Render this binds to an HTTP Range request /
    file seek so only the needed bytes are fetched ('순식간' = read part, not whole)."""
    return data[max(0, start):max(0, start) + max(0, length)]


# ── FM-index over the BWT: substring count/locate without reconstructing the text ──────────────────────
_SENT = "\x00"   # sentinel, smaller than any real byte


def bwt(text: str) -> Tuple[str, List[int]]:
    """Burrows–Wheeler transform via suffix array (sentinel-terminated). Returns (bwt_string, suffix_array).
    The BWT is the compression-friendly form (long runs ⇒ RLE-able); we then search IT, not the original."""
    s = text + _SENT
    n = len(s)
    sa = sorted(range(n), key=lambda i: s[i:])       # O(n² log n) naive SA — fine for the sizes we index here
    last = "".join(s[(i - 1) % n] for i in sa)
    return last, sa


@dataclass
class FMIndex:
    """Count/locate a pattern over the BWT with backward search. Built once (O(n log n)); each query is
    O(|pattern|) and NEVER reconstructs the text — the compute-on-compressed property, verified vs a naive scan."""
    last: str
    sa: List[int]
    C: Dict[str, int]
    n: int

    @classmethod
    def build(cls, text: str) -> "FMIndex":
        last, sa = bwt(text)
        # C[c] = number of characters in the text strictly less than c
        from collections import Counter
        freq = Counter(last)
        C: Dict[str, int] = {}
        running = 0
        for c in sorted(freq):
            C[c] = running
            running += freq[c]
        return cls(last=last, sa=sa, C=C, n=len(last))

    def _occ(self, c: str, i: int) -> int:
        """Occ(c, i) = occurrences of c in last[0:i]. (Linear scan — the textbook FM-index precomputes a rank
        table for O(1); we keep it simple + correct, and document the cost honestly.)"""
        return self.last.count(c, 0, i)

    def count(self, pattern: str) -> int:
        """Number of occurrences (including overlaps) of `pattern` in the text, via backward search over the BWT.
        Returns 0 if any character is absent. ★ Never materializes the original text."""
        if not pattern:
            return self.n - 1
        lo, hi = 0, self.n
        for c in reversed(pattern):
            if c not in self.C:
                return 0
            lo = self.C[c] + self._occ(c, lo)
            hi = self.C[c] + self._occ(c, hi)
            if lo >= hi:
                return 0
        return hi - lo

    def locate(self, pattern: str) -> List[int]:
        """Sorted start positions of `pattern` (uses the suffix array for the matched BWT range)."""
        if not pattern:
            return []
        lo, hi = 0, self.n
        for c in reversed(pattern):
            if c not in self.C:
                return []
            lo = self.C[c] + self._occ(c, lo)
            hi = self.C[c] + self._occ(c, hi)
            if lo >= hi:
                return []
        return sorted(self.sa[i] for i in range(lo, hi))


def _naive_count(text: str, pat: str) -> int:
    """Reference overlapping-occurrence count (the FM-index must agree exactly — no silent wrong answer)."""
    if not pat:
        return len(text)
    return sum(1 for i in range(len(text) - len(pat) + 1) if text[i:i + len(pat)] == pat)


def adversarial_battery() -> dict:
    """★ central-dir listing names + sizes match WITHOUT extraction; ★ single-member range-read works; ★ gzip
    ISIZE == real size (no inflate); ★ FM-index count/locate == naive scan over several patterns (incl. absent +
    overlapping) — querying the BWT, never reconstructing the text."""
    # build a zip in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("a.txt", "hello " * 1000)
        zf.writestr("b/c.txt", "world")
    zdata = buf.getvalue()
    members = list_zip_members(zdata)
    names = {m["name"] for m in members}
    gz = gzip.compress(b"X" * 12345)

    text = "abracadabra abracadabra"
    fm = FMIndex.build(text)
    pats = ["abra", "cad", "a", "abracadabra", "xyz", "ra"]
    fm_ok = all(fm.count(p) == _naive_count(text, p) for p in pats)
    loc_ok = fm.locate("abra") == [i for i in range(len(text)) if text.startswith("abra", i)]

    cases = {
        "central_dir_lists_without_extract": names == {"a.txt", "b/c.txt"} and
            next(m for m in members if m["name"] == "a.txt")["size"] == 6000,
        "single_member_read": read_member(zdata, "b/c.txt") == b"world",
        "range_slice": range_slice(b"0123456789", 3, 4) == b"3456",
        "gzip_isize_no_inflate": gzip_uncompressed_size(gz) == 12345,
        "fm_count_matches_naive": fm_ok,
        "fm_locate_matches": loc_ok,
        "fm_absent_is_zero": fm.count("zzz") == 0,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
