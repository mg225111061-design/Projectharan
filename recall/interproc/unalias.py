"""
§AP §4.2 — UNALIAS: resolve LOCAL aliases of the shared state by copy-propagation (the genuine recall win over §AI §2).
================================================================================================================
A handler often launders the state through an intermediate variable: `t = s; s = 2*t + 1`. The affine extractor reads
the final assignment `s = 2*t + 1` and sees a FREE symbol t ⇒ it DECLINEs, even though semantically t IS s and the
update is affine. unalias performs COPY PROPAGATION — for every local variable assigned exactly once and purely from
another Name, substitute it away — turning the laundered handler back into a plain affine update the extractor accepts.

★ Sound: copy propagation of a single-assignment pure-copy variable is semantics-preserving (standard, verified by the
downstream z3 equivalence in gather). ★ A GENUINE alias — a second STATE parameter the body reads (`def h(s, u): s =
s + u`) — is NOT a local copy; unalias leaves it, and the extractor / gather DECLINEs it (real coupling, not foldable
to a single recurrence). So unalias only ever turns a false-DECLINE into a provable EXACT; it never manufactures one.
"""
from __future__ import annotations

import ast
from typing import Dict, Optional


class _CopyProp(ast.NodeTransformer):
    def __init__(self, sub: Dict[str, str]):
        self.sub = sub

    def visit_Name(self, node: ast.Name):  # noqa: N802
        # resolve transitively (t→s, u→t→s)
        name = node.id
        seen = set()
        while name in self.sub and name not in seen:
            seen.add(name)
            name = self.sub[name]
        node.id = name
        return node


def resolve(src: str) -> str:
    """Copy-propagate single-assignment pure-copy locals in a handler; return the rewritten source (or the original if
    nothing to do / on any parse issue)."""
    try:
        tree = ast.parse(src)
        fn = tree.body[0]
        if not isinstance(fn, ast.FunctionDef) or not fn.args.args:
            return src
        state = fn.args.args[0].arg
        # count assignments per local name; collect pure-copy aliases (name = Name) assigned exactly once
        assign_count: Dict[str, int] = {}
        copies: Dict[str, str] = {}
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                t = node.targets[0].id
                assign_count[t] = assign_count.get(t, 0) + 1
                if isinstance(node.value, ast.Name):
                    copies[t] = node.value.id
        # keep only aliases assigned EXACTLY once and that are not the state var itself
        sub = {t: v for t, v in copies.items() if assign_count.get(t, 0) == 1 and t != state}
        if not sub:
            return src
        # substitute uses, then drop the now-dead `t = <name>` copy statements
        new_body = []
        for stmt in fn.body:
            if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name)
                    and stmt.targets[0].id in sub and isinstance(stmt.value, ast.Name)):
                continue                                          # dead after propagation
            new_body.append(_CopyProp(sub).visit(stmt))
        fn.body = new_body
        ast.fix_missing_locations(tree)
        return ast.unparse(tree)
    except Exception:  # noqa: BLE001
        return src


def unalias(handlers: Dict[str, str]) -> Dict[str, str]:
    """Resolve local state-aliases in every handler (semantics-preserving)."""
    return {name: resolve(src) for name, src in handlers.items()}
