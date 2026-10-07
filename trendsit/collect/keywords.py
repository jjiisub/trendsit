"""키워드 매칭과 제외어 규칙(config/keywords.yaml).

- 별칭을 제목, 요약, 본문 앞 2,000자에서 찾음. 영어(ASCII) 별칭은 단어 경계, 한국어가 섞인 별칭은 부분 문자열, 대소문자 무시
- 점수 = 제목 매칭 키워드 × 3 + 본문(요약 포함) 매칭 키워드 × 1. 같은 키워드는 한 번만(제목이 우선)
- 제외어가 있고 제목에 포함 키워드가 하나도 없으면 filtered(이유 excluded:<단어>)
- 점수 1 이상이면 pass, 아니면 filtered(이유 no_keyword)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..core.config import KeywordsConfig

BODY_HEAD = 2000


def _pattern(alias: str) -> re.Pattern[str]:
    if alias.isascii():
        return re.compile(r"(?<![A-Za-z0-9])" + re.escape(alias) + r"(?![A-Za-z0-9])", re.I)
    return re.compile(re.escape(alias), re.I)


@dataclass
class Match:
    score: int
    filter_status: str
    filter_reason: str | None
    keywords: dict[str, str] = field(default_factory=dict)  # keyword_id → title | body


class KeywordMatcher:
    def __init__(self, cfg: KeywordsConfig):
        self.rules = [(k.id, [_pattern(a) for a in k.aliases]) for k in cfg.keywords]
        self.exclude = [(w, _pattern(w)) for w in cfg.exclude]

    def match(self, title: str | None, summary: str | None = None, body: str | None = None) -> Match:
        title = title or ""
        rest = f"{summary or ''}\n{(body or '')[:BODY_HEAD]}"
        found: dict[str, str] = {}
        for kid, pats in self.rules:
            if any(p.search(title) for p in pats):
                found[kid] = "title"
            elif any(p.search(rest) for p in pats):
                found[kid] = "body"
        score = sum(3 if w == "title" else 1 for w in found.values())
        in_title = any(w == "title" for w in found.values())
        for word, pat in self.exclude:
            if not in_title and (pat.search(title) or pat.search(rest)):
                return Match(score, "filtered", f"excluded:{word}", found)
        if score >= 1:
            return Match(score, "pass", None, found)
        return Match(0, "filtered", "no_keyword", found)
