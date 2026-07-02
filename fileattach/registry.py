"""
§BI FL-1 — 300+ format ingestion registry with ★ honest per-format extraction depth.
=======================================================================================
Map an extension (or magic bytes) to (category, ★ depth-label, note). The depth-label is the HONEST ceiling for
that family — never a promise we can't keep:

  TEXT_EXACT        deterministic, byte-exact full text (txt/md/json/csv/code…)              → extraction EXACT
  OFFICE_LOSSY      text high, but tables/layout may be lossy (docx/xlsx/pptx/odt…)          → best-effort
  PDF_TEXT          text layer high; tables + scanned pages need OCR                          → mixed
  OCR_LIMITED       metadata always; text only via OCR, limited + never certified (images)    → best-effort
  STRUCT            structure/values extracted; meaning best-effort (parquet/hdf5/npy…)        → values exact, sense not
  MEDIA_META        tags/metadata only; no transcript without ASR (audio/video)               → metadata only
  BINARY_PARTIAL    container metadata only; payload not interpreted (exe/font/proprietary)    → partial
  ARCHIVE           route to the bomb-guarded extractor (FL-2 = mathmode/archive.py)           → see FL-2
  ENCRYPTED_BLOCKED cannot extract without a key → BLOCKED, content NEVER fabricated           → BLOCKED

★ This is the honest-label table the directive (§1.3) demands; it does NOT itself parse files — it tells the
caller the truthful depth + whether the optional library is present (NEEDS_LIB degrade, never a fabricated read).
zero-dep (stdlib only); reuses `file_ingest.HAVE` for live library availability.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

# depth labels (the honest ceiling per family)
TEXT_EXACT = "TEXT_EXACT"
OFFICE_LOSSY = "OFFICE_LOSSY"
PDF_TEXT = "PDF_TEXT"
OCR_LIMITED = "OCR_LIMITED"
STRUCT = "STRUCT"
MEDIA_META = "MEDIA_META"
BINARY_PARTIAL = "BINARY_PARTIAL"
ARCHIVE = "ARCHIVE"
ENCRYPTED_BLOCKED = "ENCRYPTED_BLOCKED"

# ── families: (category, depth, [extensions]) — enumerated honestly to 300+ real formats ────────────────
_FAMILIES: List[Tuple[str, str, List[str]]] = [
    ("code", TEXT_EXACT, [  # ~95 source languages — all plain text ⇒ 100%
        "py", "pyi", "pyw", "ipynb", "js", "mjs", "cjs", "ts", "tsx", "jsx", "java", "kt", "kts", "scala", "sc",
        "c", "h", "cpp", "cc", "cxx", "c++", "hpp", "hh", "hxx", "cs", "go", "rs", "rb", "rake", "php", "phtml",
        "swift", "m", "mm", "lua", "pl", "pm", "t", "r", "jl", "dart", "hs", "lhs", "ml", "mli", "ex", "exs",
        "erl", "hrl", "clj", "cljs", "cljc", "edn", "fs", "fsx", "fsi", "vb", "bas", "pas", "pp", "d", "nim",
        "zig", "v", "sv", "vh", "sol", "sql", "ddl", "sh", "bash", "zsh", "fish", "ksh", "ps1", "psm1", "bat",
        "cmd", "awk", "sed", "vim", "el", "lisp", "lsp", "cl", "scm", "ss", "rkt", "asm", "s", "nasm", "f", "f90",
        "f95", "f03", "for", "cob", "cbl", "ada", "adb", "ads", "tcl", "groovy", "gradle", "vala", "cr", "hx"]),
    ("text", TEXT_EXACT, [  # ~70 text/markup/config/data-text formats
        "txt", "text", "md", "markdown", "mdx", "rst", "org", "adoc", "asciidoc", "tex", "latex", "ltx", "bib",
        "log", "out", "err", "csv", "tsv", "psv", "json", "json5", "jsonl", "ndjson", "geojson", "yaml", "yml",
        "toml", "ini", "cfg", "conf", "config", "properties", "env", "dotenv", "xml", "xsd", "xsl", "xslt", "dtd",
        "html", "htm", "xhtml", "rss", "atom", "vtt", "srt", "sub", "sbv", "diff", "patch", "po", "pot", "gitignore",
        "gitattributes", "editorconfig", "dockerfile", "containerfile", "makefile", "mk", "cmake", "bazel", "bzl",
        "proto", "graphql", "gql", "csl", "rdf", "ttl", "n3", "sparql", "cypher", "ics", "vcf", "tsx_", "plist"]),
    ("office", OFFICE_LOSSY, [
        "docx", "doc", "docm", "dotx", "dot", "xlsx", "xls", "xlsm", "xlsb", "xltx", "xlt", "pptx", "ppt", "pptm",
        "potx", "pot", "odt", "ott", "ods", "ots", "odp", "otp", "odg", "odf", "rtf", "pages", "numbers", "key",
        "wpd", "wps", "hwp", "hwpx", "sxw", "sxc", "sxi"]),
    ("pdf", PDF_TEXT, ["pdf", "xps", "oxps", "fdf"]),
    ("image", OCR_LIMITED, [
        "png", "jpg", "jpeg", "jpe", "jfif", "gif", "webp", "tiff", "tif", "bmp", "dib", "heic", "heif", "avif",
        "ico", "cur", "jp2", "j2k", "jpx", "psd", "psb", "xcf", "ai", "eps", "ps", "tga", "pcx", "ppm", "pgm",
        "pbm", "pnm", "exr", "hdr", "dds", "raw", "cr2", "nef", "arw", "dng", "orf", "raf"]),
    ("data", STRUCT, [
        "parquet", "arrow", "feather", "orc", "avro", "avsc", "hdf5", "h5", "hdf", "he5", "nc", "nc4", "cdf",
        "netcdf", "mat", "npy", "npz", "pickle", "pkl", "pck", "pb", "onnx", "tflite", "msgpack", "mpk", "bson",
        "fits", "fit", "sav", "dta", "sas7bdat", "xpt", "rds", "rdata", "rda", "dbf", "sqlite", "sqlite3", "db",
        "duckdb", "accdb", "mdb", "shp", "gpkg", "las", "laz", "ply", "stl", "obj", "gltf", "glb"]),
    ("ebook", OFFICE_LOSSY, ["epub", "mobi", "azw", "azw3", "azw4", "fb2", "djvu", "djv", "lit", "lrf", "pdb",
                             "cbz", "cbr", "ibooks", "kfx"]),
    ("email", TEXT_EXACT, ["eml", "msg", "mbox", "mbx", "pst", "ost", "emlx", "nws", "mht", "mhtml"]),
    ("archive", ARCHIVE, [
        "zip", "tar", "gz", "tgz", "gzip", "bz2", "tbz", "tbz2", "bzip2", "xz", "txz", "lzma", "lz", "lz4", "zst",
        "zstd", "7z", "rar", "cab", "arj", "ace", "z", "cpio", "ar", "deb", "rpm", "war", "jar", "ear", "apk",
        "ipa", "iso", "dmg", "whl", "egg", "crx", "xpi", "nupkg"]),
    ("media", MEDIA_META, [
        "mp3", "wav", "flac", "ogg", "oga", "opus", "m4a", "aac", "wma", "aiff", "aif", "alac", "amr", "ape",
        "mid", "midi", "mp4", "m4v", "mkv", "avi", "mov", "qt", "wmv", "flv", "webm", "mpeg", "mpg", "mpe", "3gp",
        "3g2", "ts", "mts", "m2ts", "vob", "ogv", "rm", "rmvb", "asf", "divx", "f4v", "mxf"]),
    ("binary", BINARY_PARTIAL, [
        "exe", "dll", "so", "dylib", "o", "a", "lib", "obj", "bin", "dat", "class", "pyc", "pyo", "wasm", "elf",
        "ttf", "otf", "woff", "woff2", "eot", "fon", "pfb", "pfm", "swf", "fla", "blend", "fbx", "max", "psf"]),
    ("encrypted", ENCRYPTED_BLOCKED, ["gpg", "pgp", "asc", "age", "enc", "aes", "kdbx", "axx", "p12", "pfx",
                                      "jks", "keystore", "crypt", "locked"]),
]

# extension → (category, depth)
_BY_EXT: Dict[str, Tuple[str, str]] = {}
for _cat, _depth, _exts in _FAMILIES:
    for _e in _exts:
        _BY_EXT.setdefault(_e.lower(), (_cat, _depth))

_DEPTH_NOTE = {
    TEXT_EXACT: "deterministic full text, byte-exact (extraction EXACT)",
    OFFICE_LOSSY: "text high; tables/layout may be lossy (best-effort)",
    PDF_TEXT: "text layer high; tables + scanned pages need OCR",
    OCR_LIMITED: "metadata always; text only via OCR — limited, never certified",
    STRUCT: "structure/values extracted; semantics best-effort",
    MEDIA_META: "tags/metadata only; no transcript without ASR",
    BINARY_PARTIAL: "container metadata only; payload not interpreted",
    ARCHIVE: "route to the bomb-guarded extractor (FL-2)",
    ENCRYPTED_BLOCKED: "cannot extract without a key — BLOCKED, never fabricated",
}

# magic bytes → category (for extensionless / mislabeled files)
_MAGIC: List[Tuple[bytes, str]] = [
    (b"%PDF", "pdf"), (b"PK\x03\x04", "archive"), (b"\x89PNG", "image"), (b"\xff\xd8\xff", "image"),
    (b"GIF8", "image"), (b"BM", "image"), (b"\x1f\x8b", "archive"), (b"7z\xbc\xaf\x27\x1c", "archive"),
    (b"Rar!", "archive"), (b"\xfd7zXZ", "archive"), (b"PAR1", "data"), (b"\x93NUMPY", "data"),
    (b"\x89HDF", "data"), (b"SQLite format 3", "data"), (b"-----BEGIN PGP", "encrypted"), (b"\x7fELF", "binary"),
    (b"MZ", "binary"), (b"OTTO", "binary"), (b"\x00\x01\x00\x00", "binary"),
]


def _ext_of(filename: str) -> str:
    name = (filename or "").lower().rstrip(".")
    if name.endswith((".tar.gz", ".tar.bz2", ".tar.xz")):
        return "tar"
    base = name.rsplit("/", 1)[-1]
    if "." not in base:                                  # extensionless well-knowns (Dockerfile, Makefile)
        return base if base in _BY_EXT else ""
    return base.rsplit(".", 1)[-1]


def classify(filename: str = "", data: bytes = b"") -> dict:
    """Return the honest classification: {category, depth, note, by, optional_lib, available}. Extension first
    (zip-container formats need it), magic bytes as a fallback, else UNKNOWN — never a fabricated category."""
    ext = _ext_of(filename)
    cat = depth = None
    by = "extension"
    if ext and ext in _BY_EXT:
        cat, depth = _BY_EXT[ext]
    else:
        for magic, c in _MAGIC:
            if data.startswith(magic):
                cat, depth = c, _FAMILY_DEPTH[c]; by = "magic"; break
    if cat is None:
        try:
            (data or b"").decode("utf-8"); cat, depth, by = "text", TEXT_EXACT, "utf8-probe"
        except UnicodeDecodeError:
            return {"category": "unknown", "depth": "UNKNOWN", "note": "unrecognized format — honest FAILED, no "
                    "fabrication", "by": "none", "optional_lib": None, "available": False}
    lib = _OPTIONAL_LIB.get(cat)
    return {"category": cat, "depth": depth, "note": _DEPTH_NOTE[depth], "by": by,
            "optional_lib": lib, "available": _lib_available(cat)}


_FAMILY_DEPTH = {cat: depth for cat, depth, _ in _FAMILIES}
_OPTIONAL_LIB = {"office": "python-docx / openpyxl", "pdf": "pypdf", "image": "pytesseract + tesseract",
                 "data": "pyarrow / h5py / numpy (per subtype)", "ebook": "ebooklib"}


def _lib_available(category: str) -> bool:
    """Honest live availability (NEEDS_LIB degrade). TEXT_EXACT/archive/email need only stdlib ⇒ always True."""
    if category not in _OPTIONAL_LIB:
        return True
    try:
        import file_ingest as FI
        m = {"office": FI.HAVE.get("docx") or FI.HAVE.get("xlsx"), "pdf": FI.HAVE.get("pdf"),
             "image": FI.HAVE.get("ocr")}
        return bool(m.get(category, False))
    except Exception:  # noqa: BLE001
        return False


def format_count() -> int:
    """Total distinct extensions recognized (the honest '300+' claim is this number — measured, not asserted)."""
    return len(_BY_EXT)


def by_depth() -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for _, depth in _BY_EXT.values():
        counts[depth] = counts.get(depth, 0) + 1
    return counts


def adversarial_battery() -> dict:
    """★ 300+ formats; ★ each family's honest depth label is correct; ★ encrypted ⇒ BLOCKED (never extracted);
    ★ unknown bytes ⇒ honest UNKNOWN (no fabricated category); ★ magic-byte fallback works extensionless."""
    n = format_count()
    cases = {
        "over_300_formats": n >= 300,
        "txt_text_exact": classify("notes.txt")["depth"] == TEXT_EXACT,
        "py_text_exact": classify("main.py")["depth"] == TEXT_EXACT,
        "docx_office_lossy": classify("report.docx")["depth"] == OFFICE_LOSSY,
        "pdf_pdftext": classify("paper.pdf")["depth"] == PDF_TEXT,
        "png_ocr_limited": classify("scan.png")["depth"] == OCR_LIMITED,
        "parquet_struct": classify("data.parquet")["depth"] == STRUCT,
        "mp4_media_meta": classify("clip.mp4")["depth"] == MEDIA_META,
        "exe_binary_partial": classify("app.exe")["depth"] == BINARY_PARTIAL,
        "gpg_encrypted_blocked": classify("secret.gpg")["depth"] == ENCRYPTED_BLOCKED,
        "zip_archive": classify("bundle.zip")["depth"] == ARCHIVE,
        "unknown_honest": classify("x.zzz", b"\x00\x01\x02\x99\xab")["category"] == "unknown",
        "magic_fallback_pdf": classify("", b"%PDF-1.7 ...")["category"] == "pdf",
    }
    return {"format_count": n, "by_depth": by_depth(), "cases": cases, "all_ok": all(cases.values()),
            "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
