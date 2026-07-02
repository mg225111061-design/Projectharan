"""
swebench/patch_integrity.py — BI(패치 무결성) 최소 구현 + "문법 제약 diff"의 정직한 재구현.
=================================================================================================================
지시서 작업 4: patch-apply 실패(즉시 0점)를 없앤다. 토큰 수준 제약 디코딩(XGrammar/outlines류)은 로짓 접근이
필요한데 이 스택은 provider-무관 HTTP 경로라 로짓이 없다 — 지시서가 명시적으로 승인한 대안 경로
**"생성후 검증+재생성 루프"**를 구현한다:

  strip_fences → parse_unified(구조 검증) → repair_hunk_counts(기계적 수리) → ok / regenerate 신호

수리는 **기계적으로 안전한 것만**:
  * 마크다운 펜스 제거(```diff ... ``` — LLM 출력의 고전),
  * 헝크 헤더 라인수 재계산(@@ -a,b +c,d @@의 b/d를 본문에서 다시 센다 — LLM의 고전적 miscount;
    본문 자체는 한 글자도 안 바꾼다),
  * 꼬리 개행 보정.
컨텍스트 불일치(대상 파일에 없는 문맥) 같은 **의미적 손상은 수리하지 않는다** — 그건 조작이다.
ok=False + regenerate=True로 반환해 샘플 루프가 재생성하게 한다(그게 "제약"의 사후 등가물).

no_op 탐지: 비어 있거나 +/- 변경이 0인 diff는 적용엔 성공하지만 아무것도 못 고친다 — 이슈를 고치는 패치가
행동을 안 바꿀 수는 없으므로(건전한 구조 신호, 채점 세트 훔쳐보기 아님) selector가 후순위로 민다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*$")
_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")


@dataclass
class IntegrityResult:
    ok: bool
    diff: str                            # 수리 적용된 최종 텍스트 (ok=False면 원문 그대로)
    repairs: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    regenerate: bool = False             # True = 기계 수리 불가 → 샘플 루프의 재생성 신호
    no_op: bool = False                  # 변경 0 — 적용은 되지만 아무것도 못 고침(후순위 신호)


def strip_fences(text: str) -> Tuple[str, bool]:
    """마크다운 코드펜스 제거. diff 본문에 펜스가 남으면 git apply가 'corrupt patch'로 죽는다."""
    lines = text.splitlines()
    kept = [ln for ln in lines if not _FENCE_RE.match(ln)]
    return "\n".join(kept), len(kept) != len(lines)


def repair_hunk_counts(diff: str) -> Tuple[str, int]:
    """@@ -a,b +c,d @@ 의 b(구 라인수)/d(신 라인수)를 헝크 본문에서 재계산. LLM이 가장 자주 틀리는
    지점이고, git apply는 카운트 불일치를 'corrupt patch'로 즉시 거부한다. 본문은 불변."""
    lines = diff.splitlines()
    out: List[str] = []
    fixed = 0
    i = 0
    while i < len(lines):
        m = _HUNK_RE.match(lines[i])
        if not m:
            out.append(lines[i])
            i += 1
            continue
        a, b_claim, c, d_claim, tail = (m.group(1), m.group(2), m.group(3), m.group(4), m.group(5))
        j = i + 1
        old_ct = new_ct = 0
        while j < len(lines):
            ln = lines[j]
            if ln.startswith("@@") or ln.startswith("diff ") or ln.startswith("--- ") or ln.startswith("+++ "):
                break
            if ln.startswith("-"):
                old_ct += 1
            elif ln.startswith("+"):
                new_ct += 1
            elif ln.startswith(" ") or ln == "" or ln.startswith("\\"):
                if not ln.startswith("\\"):
                    old_ct += 1
                    new_ct += 1
            else:
                break                    # 헝크 본문이 아닌 줄 — 헝크 종료
            j += 1
        claimed = (int(b_claim) if b_claim is not None else 1,
                   int(d_claim) if d_claim is not None else 1)
        if claimed != (old_ct, new_ct):
            fixed += 1
        out.append(f"@@ -{a},{old_ct} +{c},{new_ct} @@{tail}")
        out.extend(lines[i + 1:j])
        i = j
    return "\n".join(out), fixed


def parse_unified(diff: str) -> Dict:
    """구조 검증(수리 없음): 파일 헤더/헝크 헤더/본문 접두(' '/'+'/'-'/'\\')의 정합성. errors가 비면 구조 OK."""
    lines = diff.splitlines()
    files: List[str] = []
    hunks = 0
    adds = dels = 0
    errors: List[str] = []
    in_hunk = False
    saw_header = False
    for k, ln in enumerate(lines, 1):
        if ln.startswith("diff ") or ln.startswith("index "):
            in_hunk = False
            continue
        if ln.startswith("--- "):
            saw_header = True
            in_hunk = False
            continue
        if ln.startswith("+++ "):
            files.append(ln[4:].strip())
            continue
        if ln.startswith("@@"):
            if not _HUNK_RE.match(ln):
                errors.append(f"line {k}: malformed hunk header {ln!r}")
            elif not saw_header:
                errors.append(f"line {k}: hunk before ---/+++ file header")
            else:
                hunks += 1
                in_hunk = True
            continue
        if in_hunk:
            if ln.startswith("+"):
                adds += 1
            elif ln.startswith("-"):
                dels += 1
            elif ln == "" or ln.startswith(" ") or ln.startswith("\\"):
                pass
            else:
                errors.append(f"line {k}: bad hunk body prefix {ln[:20]!r}")
                in_hunk = False
    if not files and diff.strip():
        errors.append("no +++ file header found")
    if files and hunks == 0:
        errors.append("file header(s) but zero hunks")
    return {"ok": not errors, "files": files, "hunks": hunks, "adds": adds, "dels": dels, "errors": errors}


def validate_and_repair(raw: str) -> IntegrityResult:
    """BI 게이트: 펜스 제거 → 헝크 카운트 수리 → 구조 검증. 통과 못 하면 regenerate=True(수리 불가는
    정직하게 재생성으로 — 의미 손상을 조용히 '고치는' 일은 없다)."""
    if not raw.strip():
        return IntegrityResult(True, "", repairs=[], no_op=True)
    text, fenced = strip_fences(raw)
    repairs: List[str] = (["stripped markdown fences"] if fenced else [])
    text, fixed = repair_hunk_counts(text)
    if fixed:
        repairs.append(f"recounted {fixed} hunk header(s)")
    if not text.endswith("\n"):
        text += "\n"
        repairs.append("added trailing newline")
    p = parse_unified(text)
    if not p["ok"]:
        return IntegrityResult(False, raw, repairs=repairs, errors=p["errors"], regenerate=True)
    return IntegrityResult(True, text, repairs=repairs, no_op=(p["adds"] + p["dels"]) == 0)


def apply_rate(diffs: List[str], repo_dir: str) -> Dict:
    """★before/after 실측: 같은 diff 집합을 (수리 전 원문 / BI 게이트 통과본) 각각 REAL `git apply --check`로
    적용 시도해 성공 수를 센다 — 작업 4의 완료 기준 '말포드 생성률 감소'의 측정기. 적용은 --check(무변경)라
    레포를 더럽히지 않고, 수리 불가(regenerate)는 after에서도 실패로 정직하게 남는다."""
    import subprocess
    from swebench.live_harness import _GIT_ENV

    def _applies(d: str) -> bool:
        if not d.strip():
            return True
        p = subprocess.run(["git", "apply", "--check", "-"], cwd=repo_dir, env=_GIT_ENV,
                           input=d, capture_output=True, text=True, timeout=60)
        return p.returncode == 0

    before = sum(1 for d in diffs if _applies(d))
    after = 0
    regen = 0
    for d in diffs:
        ir = validate_and_repair(d)
        if ir.regenerate:
            regen += 1
            continue
        if _applies(ir.diff):
            after += 1
    return {"n": len(diffs), "apply_ok_before": before, "apply_ok_after": after,
            "regenerate_signalled": regen,
            "note": "after는 BI 수리(펜스/헝크카운트/개행)만 반영 — 의미 손상은 수리 없이 재생성 신호"}
