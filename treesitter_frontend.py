"""
v28 STAGE 20 — error-recovering, comment/string-correct frontend + a common typed IR.
======================================================================================
A regex scanner cannot match NESTED structure (block comments, macros, strings) — so it silently produces
a WRONG HIR (e.g. it ends a comment at the first `*/`, or treats `//` inside a string as a comment). This
frontend fixes that at the lexical level and lowers to the shared HIR, so every downstream verifier (VC
generation, abstract interpretation, taint, separation logic) is written ONCE over the IR.

Two execution paths, same IR:
  • Tree-sitter (if `tree_sitter` + a grammar module is installed) — a real GLR CST with ERROR RECOVERY;
    `node.has_error` subtrees become explicit UNPARSED markers.
  • pure-Python fallback (always available) — a correct char-level state machine for comments / strings /
    nested blocks (the actual soundness fix), then a brace-stack signature scan.

★ HONEST (§1.4, §1.9, §5) ★: (1) an UNPARSED region is lowered to an `assume_unknown` op — the verifier
treats it as UNKNOWN, never a fake PROVEN. (2) Tree-sitter is syntax only (not types); the recovery tree is
heuristic on broken input (labeled). (3) Adding a language is a FRONTEND, not a verifier rewrite — but the
frontend is most of the work (CodeQL: ~95%); language onboarding is NOT free. (4) `tree_sitter` install may
be [BLOCKED]; the pure-Python path then carries the soundness fix unchanged.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from hir import HFunction, HModule, HOp

# ── optional Tree-sitter detection (never required for correctness) ─────────────────────────────────
def _detect_tree_sitter() -> Tuple[bool, Dict[str, object]]:
    try:
        import tree_sitter  # noqa: F401
    except Exception:  # noqa: BLE001
        return (False, {})
    grammars: Dict[str, object] = {}
    for lang, mod in (("go", "tree_sitter_go"), ("c", "tree_sitter_c"), ("rust", "tree_sitter_rust")):
        try:
            m = __import__(mod)
            grammars[lang] = m.language()
        except Exception:  # noqa: BLE001
            pass
    return (True, grammars)


TREE_SITTER_AVAILABLE, _GRAMMARS = _detect_tree_sitter()


# ── language lexical config ─────────────────────────────────────────────────────────────────────────
@dataclass
class LexCfg:
    line: str = "//"
    block: Tuple[str, str] = ("/*", "*/")
    nested_block: bool = False          # Rust nests block comments; C/Go do not
    strings: str = '"'
    chars: str = "'"


_LEX = {"c": LexCfg(), "go": LexCfg(), "javascript": LexCfg(),
        "rust": LexCfg(nested_block=True), "python": LexCfg(line="#", block=("", ""))}


# ── THE SOUNDNESS CORE: correct comment/string/nested stripping (pure Python) ───────────────────────
def strip_comments(source: str, lang: str = "c") -> Tuple[str, List[Tuple[int, str]]]:
    """Replace comments with spaces (preserving newlines/line numbers), correctly handling NESTED block
    comments and ignoring comment markers inside string/char literals. Returns (clean_source, comments)."""
    cfg = _LEX.get(lang, LexCfg())
    s = source
    out = []
    comments: List[Tuple[int, str]] = []
    i, n, line = 0, len(s), 1
    lb, rb = cfg.block
    while i < n:
        ch = s[i]
        if ch == "\n":
            out.append(ch); line += 1; i += 1; continue
        # string / char literal — copy verbatim (comment markers inside are NOT comments)
        if ch in (cfg.strings, cfg.chars):
            q = ch; out.append(ch); i += 1
            while i < n:
                out.append(s[i])
                if s[i] == "\\" and i + 1 < n:
                    out.append(s[i + 1]); i += 2; continue
                if s[i] == q:
                    i += 1; break
                if s[i] == "\n":
                    line += 1
                i += 1
            continue
        # line comment
        if cfg.line and s.startswith(cfg.line, i):
            j = s.find("\n", i)
            j = n if j < 0 else j
            comments.append((line, s[i:j])); out.append(" " * (j - i)); i = j; continue
        # block comment (with nesting if the language allows)
        if lb and s.startswith(lb, i):
            depth, start, j = 1, i, i + len(lb)
            startline = line
            while j < n and depth > 0:
                if s[j] == "\n":
                    line += 1
                if cfg.nested_block and s.startswith(lb, j):
                    depth += 1; j += len(lb); continue
                if s.startswith(rb, j):
                    depth -= 1; j += len(rb); continue
                j += 1
            seg = s[start:j]
            comments.append((startline, seg))
            out.append("".join(c if c == "\n" else " " for c in seg)); i = j; continue
        out.append(ch); i += 1
    return ("".join(out), comments)


def naive_regex_strip(source: str) -> str:
    """The BROKEN baseline (for contrast): regex comment stripping. Mishandles nesting and string-embedded
    markers — exactly the bug S20 removes."""
    s = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)   # non-greedy → stops at the FIRST */
    s = re.sub(r"//[^\n]*", "", s)                          # strips '//' even inside a string literal
    return s


# ── simple object-like C macro expansion pre-pass ───────────────────────────────────────────────────
_DEFINE = re.compile(r"^\s*#define\s+([A-Za-z_]\w*)\s+(.+?)\s*$", re.MULTILINE)


def expand_macros(source: str) -> Tuple[str, Dict[str, str]]:
    """Expand object-like `#define NAME BODY` (function-like macros are left as-is — honest)."""
    macros = {m.group(1): m.group(2) for m in _DEFINE.finditer(source)}
    body = _DEFINE.sub("", source)
    for name, val in macros.items():
        body = re.sub(rf"\b{name}\b", val, body)
    return (body, macros)


# ── common IR fact schema (verification mapping consumes this, written once) ────────────────────────
IR_FACT_SCHEMA = ("function(name,params)", "op(kind,line)", "comment(line)", "unparsed(line,reason)")


def to_facts(mod: HModule) -> List[Tuple]:
    facts: List[Tuple] = []
    for fn in mod.functions:
        facts.append(("function", fn.name, tuple(fn.params)))
        for op in fn.ops:
            facts.append(("op" if op.kind != "assume_unknown" else "unparsed", op.kind, op.line))
    return facts


# ── lowering to HIR (Tree-sitter path if available, else the pure-Python fallback) ──────────────────
_SIG = re.compile(r"\bfunc\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)\s*\(([^)]*)\)"      # Go
                  r"|\b([A-Za-z_][\w*\s]*?)\s+([A-Za-z_]\w*)\s*\(([^)]*)\)\s*\{")  # C-like


def _params(arglist: str) -> List[str]:
    out = []
    for part in arglist.split(","):
        toks = part.replace("*", " ").split()
        if toks:
            out.append(toks[-1] if len(toks) > 1 else toks[0])   # last token ≈ the parameter name
    return [p for p in out if p.isidentifier()]


def _fallback_to_hir(source: str, lang: str) -> HModule:
    clean, comments = strip_comments(source, lang)
    if lang in ("c", "cpp"):
        clean, _macros = expand_macros(clean)
    fns: List[HFunction] = []
    for m in _SIG.finditer(clean):
        if m.group(1):                              # Go: func NAME(args)
            name, args = m.group(1), m.group(2)
        else:                                       # C-like: ret NAME(args) {
            name, args = m.group(4), m.group(5)
        line = clean[:m.start()].count("\n") + 1
        ops = [HOp("call", line, name)]
        fns.append(HFunction(name, _params(args or ""), ops, m.group(0), line, line, lang=lang))
    # mark a region with unbalanced braces as UNPARSED → unknown (honest, no fake confidence)
    if clean.count("{") != clean.count("}"):
        fns.append(HFunction("<unparsed>", [], [HOp("assume_unknown", 0,
                    "unbalanced-braces region — verifier must treat as unknown (honest-defer)")],
                    "", 0, 0, lang=lang))
    return HModule(lang, fns, source)


def _tree_sitter_to_hir(source: str, lang: str) -> Optional[HModule]:
    if not TREE_SITTER_AVAILABLE or lang not in _GRAMMARS:
        return None
    try:
        from tree_sitter import Language, Parser
        parser = Parser(Language(_GRAMMARS[lang]))
        tree = parser.parse(source.encode())
    except Exception:  # noqa: BLE001
        return None
    fns: List[HFunction] = []
    src = source.encode()

    def text(n):
        return src[n.start_byte:n.end_byte].decode("utf-8", "replace")

    def walk(n):
        if n.type in ("function_declaration", "method_declaration", "function_definition"):
            ident = next((c for c in n.children if c.type in ("identifier", "field_identifier")), None)
            params = []
            pl = next((c for c in n.children if c.type in ("parameter_list", "parameters")), None)
            if pl is not None:
                for pc in pl.children:
                    pid = next((g for g in pc.children if g.type == "identifier"), None)
                    if pid is not None:
                        params.append(text(pid))
            name = text(ident) if ident is not None else "<anon>"
            line = n.start_point[0] + 1
            kind = "assume_unknown" if n.has_error else "call"
            fns.append(HFunction(name, params, [HOp(kind, line, name)], text(n), line,
                                 n.end_point[0] + 1, lang=lang))
        for c in n.children:
            walk(c)

    walk(tree.root_node)
    if tree.root_node.has_error:        # the parse hit a syntax error somewhere → mark an UNPARSED region
        fns.append(HFunction("<unparsed>", [], [HOp("assume_unknown", tree.root_node.start_point[0] + 1,
                   "tree-sitter error-recovery region — verifier must treat as unknown (honest-defer)")],
                   "", 0, 0, lang=lang))
    return HModule(lang, fns, source)


def to_hir(source: str, lang: str = "go") -> Tuple[HModule, str]:
    """Lower `source` to the common HIR. Returns (module, path) where path ∈ {"tree-sitter","fallback"}."""
    ts = _tree_sitter_to_hir(source, lang)
    if ts is not None:
        return (ts, "tree-sitter")
    return (_fallback_to_hir(source, lang), "fallback")
