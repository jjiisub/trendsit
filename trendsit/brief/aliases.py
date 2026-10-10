"""표기 정규화 v0(S5_TASK 5.3). 원문은 바꾸지 않고 별칭 표(aliases)를 만들어 묶기 신호·작성자 입력·코드 자동 수정에 쓴다.

| 후보 | status |
| keywords.yaml 별칭 | approved(keyword_id 붙음. 주제어라 묶기의 '같은 대상' 신호로는 쓰지 않음) |
| 표기 차이만(대소문자·띄어쓰기·하이픈·점) | 자동 approved |
| 음차·약어 사전(brief.yaml aliases.transliteration)으로 바꾸면 같은 이름(GPT-6 루나 ↔ GPT-6 Luna) | 자동 approved, 정본은 원문 표기(영문) |
| 이름 속 숫자·버전·크기가 다름 | 후보로도 만들지 않음(rapidfuzz 점수와 무관) |
| 그 밖에 rapidfuzz 점수가 높은 쌍 | candidate. 묶기 신호로만, decide가 같다고 하면 approved |
| 영상 name_pairs | 그 영상 안에서만 교정(EvidencePack Member.corrections), 전역으로 올리지 않음 |
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field

from ..core import config
from ..core.config import KeywordsConfig
from ..core.config_brief import BriefConfig
from ..core.db import DB, now_kst
from .evidence import Member

# 크기·등급 낱말: 이름에 붙으면 다른 제품(GPT-5 ↔ GPT-5 mini)
SIZE_WORDS = {"mini", "nano", "micro", "small", "medium", "large", "xl", "pro", "max", "plus", "lite", "flash",
              "ultra", "turbo", "air", "base", "instruct", "preview"}
_NUM = re.compile(r"\d+(?:\.\d+)?")


def norm_key(name: str) -> str:
    """표기 차이(대소문자, 공백, 하이픈, 점, 밑줄)를 지운 열쇠. 숫자 사이의 점은 남긴다(3.5 ≠ 35)."""
    s = name.lower().strip()
    s = re.sub(r"(?<=\d)\.(?=\d)", "․", s)  # 소수점 보호
    s = re.sub(r"[\s\-._·]+", "", s)
    return s.replace("․", ".")


_SEP = re.compile(r"([\s\-_/]+)")


def _alts(translit: dict[str, str]) -> dict[str, list[str]]:
    """낱말(소문자) → 같은 이름의 다른 표기들. 사전 값은 '소넷|소네트'처럼 여러 음차를 '|'로."""
    out: dict[str, list[str]] = {}
    for en, ko in translit.items():
        forms = [en, *ko.split("|")]
        for f in forms:
            out.setdefault(f.lower(), [])
            out[f.lower()] += [x for x in forms if x.lower() != f.lower() and x not in out[f.lower()]]
    return out


def to_original(name: str, translit: dict[str, str]) -> str:
    """한글 음차 낱말을 영문으로 되돌린 표기(사전에 있는 낱말만)."""
    inv = {v.lower(): k for k, vs in translit.items() for v in vs.split("|")}
    return "".join(inv.get(p.lower(), p) for p in _SEP.split(name))


def translit_pattern(name: str, translit: dict[str, str]) -> re.Pattern[str] | None:
    """이름의 음차 섞인 표기를 모두 잡는 정규식(낱말 사이 띄어쓰기·하이픈은 있어도 없어도). 사전 낱말이 없으면 None.
    예: 'DeepSeek V4.1 Flash' → '딥시크-V4.1 플래시', 'DeepSeek-V4.1 플래시'도(반영 확인 리뷰 F10)."""
    alts = _alts(translit)
    toks = [t for t in _SEP.split(name) if t and not _SEP.fullmatch(t)]
    if not any(t.lower() in alts for t in toks):
        return None
    parts = ["(?:" + "|".join(re.escape(x) for x in sorted({t, *alts.get(t.lower(), [])}, key=len, reverse=True)) + ")"
             for t in toks]
    # 한글 경계: 앞은 글자가 아니고, 뒤는 글자가 아니거나 조사(솔루션의 '솔'은 잡지 않음)
    after = r"(?=$|[^0-9A-Za-z가-힣]|(?:으로|에서|보다|처럼|은|는|이|가|을|를|의|에|와|과|도|로|만)(?:$|[^가-힣]))"
    return re.compile(r"(?<![0-9A-Za-z가-힣])" + r"[\s\-]?".join(parts) + after, re.IGNORECASE)


def numbers_of(name: str) -> tuple[str, ...]:
    return tuple(_NUM.findall(name))


def sizes_of(name: str) -> frozenset[str]:
    return frozenset(w for w in re.findall(r"[a-z]+", name.lower()) if w in SIZE_WORDS)


def differs_in_version(a: str, b: str) -> bool:
    """이름 속 숫자·버전·크기가 다르면 같은 대상 후보로도 만들지 않는다(S5 결정)."""
    return numbers_of(a) != numbers_of(b) or sizes_of(a) != sizes_of(b)


@dataclass
class AliasRow:
    canonical: str
    alias: str
    status: str  # candidate / approved / rejected
    reason: str
    keyword_id: str | None = None
    evidence: list[str] = field(default_factory=list)  # 이 표기가 나온 구성원 키
    origin: str = "normalizer"


@dataclass
class AliasTable:
    rows: list[AliasRow]

    def approved(self) -> dict[str, str]:
        """표기 → 정본(같은 대상 별칭만, 키워드 별칭 제외)."""
        return {r.alias: r.canonical for r in self.rows if r.status == "approved" and r.keyword_id is None}

    def canonical(self, name: str) -> str:
        return self.approved().get(name, name)

    def entity_keys(self, names: list[str]) -> set[str]:
        """묶기 신호용 이름 열쇠: 승인 별칭은 정본으로, 후보 별칭은 두 쪽 모두."""
        amap = self.approved()
        out = {norm_key(amap.get(n, n)) for n in names if n.strip()}
        for r in self.rows:
            if r.status == "candidate" and r.keyword_id is None and (norm_key(r.alias) in out or norm_key(r.canonical) in out):
                out |= {norm_key(r.alias), norm_key(r.canonical)}
        return out

    def counts(self) -> dict[str, int]:
        ent = [r for r in self.rows if r.keyword_id is None]
        return {"candidates": sum(r.status == "candidate" for r in ent),
                "auto_approved": sum(r.status == "approved" and r.reason.startswith("표기 차이") for r in ent),
                "rejected": sum(r.status == "rejected" for r in ent)}


def build(members: list[Member], keywords: KeywordsConfig, fuzz_min: float,
          translit: dict[str, str] | None = None) -> AliasTable:
    """구성원의 이름(글 카드 entities, 영상 판독 표기, 레포 이름)에서 별칭 후보를 만든다(LLM 없음)."""
    from rapidfuzz import fuzz

    rows: list[AliasRow] = []
    for k in keywords.keywords:
        for a in k.aliases:
            if a != k.canonical:
                rows.append(AliasRow(k.canonical, a, "approved", "keywords.yaml 별칭", keyword_id=k.id))
    seen: dict[str, Counter[str]] = {}
    where: dict[str, set[str]] = {}
    for m in members:
        for name in dict.fromkeys(n.strip() for n in m.entities if n and n.strip()):
            key = norm_key(name)
            if not key:
                continue
            seen.setdefault(key, Counter())[name] += 1
            where.setdefault(name, set()).add(m.key)
    canon: dict[str, str] = {}
    for key, forms in seen.items():
        # 정본: 가장 많이 나온 표기. 같으면 대문자가 많은 쪽(Claude Code > claude code), 그다음 사전순
        best = sorted(forms, key=lambda f: (-forms[f], -sum(c.isupper() for c in f), f))[0]
        canon[key] = best
        for f in forms:
            if f != best and numbers_of(f) == numbers_of(best):  # 'Llama 3 8B' ↔ 'Llama 38B'는 표기 차이가 아님
                rows.append(AliasRow(best, f, "approved", "표기 차이만(대소문자·띄어쓰기·하이픈·점)",
                                     evidence=sorted(where[f])))
    # 음차·약어 사전: 한글 음차 낱말을 영문으로 되돌려 같은 열쇠가 되면 같은 이름(PR #9 리뷰 R11, 음차 후보 원천이 없어 0건)
    if translit:
        groups: dict[str, list[str]] = {}
        for best in canon.values():
            groups.setdefault(norm_key(to_original(best, translit)), []).append(best)
        for forms in groups.values():
            if len(forms) < 2:
                continue
            # 정본: 원문 표기(한글이 적은 쪽), 같으면 많이 나온 쪽
            forms.sort(key=lambda f: (sum("가" <= c <= "힣" for c in f), -sum(seen[norm_key(f)].values()), f))
            for f in forms[1:]:
                if numbers_of(f) == numbers_of(forms[0]):
                    rows.append(AliasRow(forms[0], f, "approved", "음차·약어 사전(brief.yaml aliases.transliteration)",
                                         evidence=sorted(where.get(f, set()))))
    keys = sorted(canon)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            ca, cb = canon[a], canon[b]
            if differs_in_version(ca, cb) or min(len(a), len(b)) < 4:
                continue
            score = fuzz.ratio(a, b)
            if score >= fuzz_min:
                first, second = sorted((ca, cb), key=lambda f: (-sum(seen[norm_key(f)].values()), f))
                rows.append(AliasRow(first, second, "candidate", f"rapidfuzz {score:.0f}",
                                     evidence=sorted(where.get(ca, set()) | where.get(cb, set()))))
    return AliasTable(rows)


def save(db: DB, table: AliasTable, run_id: str) -> None:
    """(canonical, alias)마다 한 행. 이미 있으면 seen을 늘리고 상태는 더 확정된 쪽으로(candidate → approved/rejected)."""
    now = now_kst()
    with db.conn:
        for r in table.rows:
            old = db.conn.execute("SELECT id, status FROM aliases WHERE canonical=? AND alias=?",
                                  (r.canonical, r.alias)).fetchone()
            if old is None:
                db.conn.execute(
                    "INSERT INTO aliases(canonical, alias, keyword_id, reason, evidence_json, origin, status, seen, run_id,"
                    " updated_at) VALUES (?,?,?,?,?,?,?,1,?,?)",
                    (r.canonical, r.alias, r.keyword_id, r.reason, json.dumps(r.evidence, ensure_ascii=False), r.origin,
                     r.status, run_id, now))
            else:
                status = old["status"] if old["status"] != "candidate" else r.status
                db.conn.execute("UPDATE aliases SET seen=seen+1, status=?, run_id=?, updated_at=?, evidence_json=? "
                                "WHERE id=?", (status, run_id, now, json.dumps(r.evidence, ensure_ascii=False), old["id"]))


def decided_table(db: DB, members: list[Member], cfg: BriefConfig) -> AliasTable:
    """이번 주 구성원의 별칭 표(keywords.yaml 별칭 + 설정의 임계값·음차 사전)에 지난 판정을 반영."""
    return load_decided(db, build(members, config.load("keywords.yaml"), cfg.aliases.fuzz_min_score, cfg.aliases.transliteration))


def load_decided(db: DB, table: AliasTable) -> AliasTable:
    """지난 실행에서 decide·편집장이 확정한 상태(approved/rejected)를 이번 표에 반영."""
    done = {(r["canonical"], r["alias"]): r["status"] for r in db.conn.execute(
        "SELECT canonical, alias, status FROM aliases WHERE status!='candidate'")}
    for r in table.rows:
        if r.status == "candidate" and (r.canonical, r.alias) in done:
            r.status = done[(r.canonical, r.alias)]
    return table

