"""마크다운·HTML 기호를 걷어 내 본문만 남긴다(S1 Q3: README 입력 정리). 레포 분석가(S3) 입력 조립에서도 쓴다."""

from __future__ import annotations

import html
import re

_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"<!--.*?-->", re.S), ""),  # HTML 주석
    (re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I), ""),
    (re.compile(r"<br\s*/?>", re.I), "\n"),
    (re.compile(r"</?(p|div|h[1-6]|li|ul|ol|tr|table|section)\b[^>]*>", re.I), "\n"),
    (re.compile(r"<[^>]+>"), ""),  # 나머지 태그(img 포함)
    (re.compile(r"\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)"), ""),  # 링크 걸린 이미지(배지)
    (re.compile(r"!\[[^\]]*\]\([^)]*\)"), ""),  # 이미지
    (re.compile(r"!\[[^\]]*\]\[[^\]]*\]"), ""),  # 참조형 이미지
    (re.compile(r"^\s*\[[^\]]+\]:\s*\S+.*$", re.M), ""),  # 참조 링크 정의
    (re.compile(r"\[([^\]]+)\]\([^)]*\)"), r"\1"),  # [글](주소) → 글
    (re.compile(r"\[([^\]]+)\]\[[^\]]*\]"), r"\1"),  # [글][참조] → 글
    (re.compile(r"\[([^\]\n]+)\](?![(\[:])"), r"\1"),  # [글] → 글(참조 축약형)
    (re.compile(r"^#{1,6}\s*", re.M), ""),  # 제목 기호
    (re.compile(r"^\s*>\s?", re.M), ""),  # 인용 기호
    (re.compile(r"(\*\*|__)(.+?)\1", re.S), r"\2"),  # 굵게
    (re.compile(r"(?<![\w*])\*(?!\s)([^*\n]+?)\*(?!\w)"), r"\1"),  # 기울임(*)
    (re.compile(r"`{1,3}([^`]*)`{1,3}"), r"\1"),  # 인라인 코드
    (re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$", re.M), ""),  # 가로줄
    (re.compile(r"^\s*\|?(\s*:?-{3,}:?\s*\|)+\s*:?-*:?\s*$", re.M), ""),  # 표 구분선
]


def clean_markdown(text: str) -> str:
    out = text or ""
    for pat, rep in _RULES:
        out = pat.sub(rep, out)
    out = html.unescape(out)
    lines = [" ".join(line.split()) for line in out.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
