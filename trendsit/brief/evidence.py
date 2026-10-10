"""근거 목록(EvidencePack, S5_TASK 5.3). 표로 저장하지 않고 DB에서 매번 같게 조립한다.

근거 자격: item_card가 있는 글(v2에 원본이 있으면 v2), VideoDigest가 있는 영상, relevant=true RepoCard.
메타데이터만 있는 영상, 카드 없는 글, 관련 없는 레포는 빼고 센다(실행 요약 evidence.excluded).
주차: items.week(ISO 주, 월~일). 트렌딩은 repo_trending의 그 주 목록(그 주 마지막 수집판).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from ..core.budget import estimate_tokens
from ..core.db import DB

Channel = str  # text / video / github
RELEVANCE_RANK = {"high": 0, "mid": 1, "low": 2}


@dataclass
class EvidenceItem:
    """근거 하나. id는 근거 id(CONTRACTS 2장), member는 묶음 구성원 키(it:{item_id} / vd:{video_id} / rp:{full_name})."""

    id: str
    member: str
    channel: Channel
    kind: str  # quote / number / claim / slide_fact / timeline / summary / repo_field
    text: str
    source: dict[str, Any]
    value: str | None = None
    unit: str | None = None
    sec: int | None = None

    def as_dict(self) -> dict[str, Any]:
        d = {"id": self.id, "member": self.member, "channel": self.channel, "kind": self.kind, "text": self.text,
             "source": self.source}
        for k in ("value", "unit", "sec"):
            if getattr(self, k) is not None:
                d[k] = getattr(self, k)
        return d


@dataclass
class Member:
    """묶음 구성원 하나(글 한 건, 영상 한 편, 레포 하나)와 그 근거."""

    key: str
    channel: Channel
    title: str
    line: str  # 한 줄 요약(묶기·선별 입력)
    summary: str
    relevance: str  # high / mid / low
    entities: list[str]
    keywords: list[str]
    source: dict[str, Any]
    items: list[EvidenceItem] = field(default_factory=list)
    item_id: int | None = None
    corrections: dict[str, str] = field(default_factory=dict)  # 영상 안에서만 쓰는 표기 교정(잘못 들은 말 → 화면 표기)


@dataclass
class WeekEvidence:
    week: str
    members: dict[str, Member]
    excluded: dict[str, int]

    def counts(self) -> dict[str, int]:
        out = {"text": 0, "video": 0, "github": 0}
        for m in self.members.values():
            out[m.channel] += 1
        return out


def week_days(week: str) -> tuple[date, date]:
    """'2026-W42' → (월, 일)."""
    y, w = week.split("-W")
    return date.fromisocalendar(int(y), int(w), 1), date.fromisocalendar(int(y), int(w), 7)


def _first_sentence(text: str) -> str:
    text = (text or "").strip()
    m = re.search(r"(?<=[.!?다])\s", text)
    return text[: m.start()] if m else text


def _card_items(item_id: int, card: dict[str, Any], prefix: str, member: str, source: dict[str, Any]) -> list[EvidenceItem]:
    """글 카드 → 근거. quote가 근거 id의 주인이고, 수치·주장은 그 quote id로 붙는다. summary는 글 단위 id."""
    out: list[EvidenceItem] = []
    qid = {q["n"]: f"{prefix}:{item_id}#q{q['n']}" for q in card.get("quotes") or []}
    for q in card.get("quotes") or []:
        src = source | ({"url": q["url"]} if q.get("url") else {})
        out.append(EvidenceItem(qid[q["n"]], member, "text", "quote", q["text"], src))
    for n in card.get("numbers") or []:
        if n["quote_n"] in qid:
            out.append(EvidenceItem(qid[n["quote_n"]], member, "text", "number", n["what"], source,
                                    value=n["value"], unit=n.get("unit") or ""))
    for c in card.get("claims") or []:
        ns = [n for n in c.get("quote_ns") or [] if n in qid]
        if ns:
            out.append(EvidenceItem(qid[ns[0]], member, "text", "claim", c["text"], source))
    if card.get("summary"):
        out.append(EvidenceItem(f"it:{item_id}", member, "text", "summary", card["summary"], source))
    return out


def text_members(db: DB, week: str) -> tuple[list[Member], int]:
    """item_card가 있는 글(같은 URL로 묶인 것은 기준 항목 하나). v2에 원본(origin)이 있으면 v2 근거(og:)."""
    rows = db.conn.execute(
        "SELECT i.id, i.title, i.url, i.day, s.name AS site, "
        "(SELECT card_json FROM item_cards c WHERE c.item_id=i.id AND c.version=1) AS v1, "
        "(SELECT card_json FROM item_cards c WHERE c.item_id=i.id AND c.version=2) AS v2 "
        "FROM items i LEFT JOIN sources s ON s.id=i.source_id "
        "WHERE i.week=? AND i.channel='text' AND i.id NOT IN (SELECT item_id FROM item_same_as WHERE canonical_id!=item_id) "
        "ORDER BY i.id", (week,)).fetchall()
    out, no_card = [], 0
    for r in rows:
        if not r["v1"]:
            no_card += 1
            continue
        v1 = json.loads(r["v1"])
        v2 = json.loads(r["v2"]) if r["v2"] else None
        member = f"it:{r['id']}"
        source = {"site": r["site"], "title": r["title"], "date": r["day"], "url": r["url"]}
        use_v2 = bool(v2 and v2.get("origin") and v2.get("quotes"))
        items = _card_items(r["id"], v1, "it", member, source)
        if use_v2:  # 원본 문장(og:)을 앞에. 글 자체 인용도 근거로 남김(원본과 다른 점을 쓸 수 있게)
            items = _card_items(r["id"], v2, "og", member, source | {"origin": v2["origin"]}) + items
        card = v2 if use_v2 else v1
        out.append(Member(member, "text", r["title"], _first_sentence(card.get("summary") or v1.get("summary") or ""),
                          card.get("summary") or v1.get("summary") or "", v1.get("relevance") or "low",
                          list(v1.get("entities") or []), list(v1.get("keywords") or []), source, items, r["id"]))
    return out, no_card


def video_members(db: DB, week: str) -> tuple[list[Member], int]:
    """VideoDigest가 있는 영상. 근거: 슬라이드 전용 수치(claim만, P4-1), 핵심 포인트, 타임라인, 요약.
    표기 쌍(name_pairs)은 그 영상 안에서만 쓰는 교정이고 전역 별칭으로 올리지 않는다."""
    rows = db.conn.execute(
        "SELECT i.id, i.title, i.url, i.day, s.name AS site, v.video_id, "
        "(SELECT digest_json FROM video_digests d WHERE d.item_id=i.id) AS digest "
        "FROM items i JOIN videos v ON v.item_id=i.id LEFT JOIN sources s ON s.id=i.source_id "
        "WHERE i.week=? AND i.channel='video' ORDER BY i.id", (week,)).fetchall()
    out, no_digest = [], 0
    for r in rows:
        if not r["digest"]:
            no_digest += 1
            continue
        d = json.loads(r["digest"])
        member = f"vd:{r['video_id']}"
        source = {"site": r["site"], "title": r["title"], "date": r["day"], "url": r["url"]}
        items = []
        for f in d.get("slide_only_facts") or []:
            items.append(EvidenceItem(f["evidence"], member, "video", "slide_fact", f["fact"], source,
                                      value=f["value"], unit=f.get("unit") or "", sec=f["sec"]))
        for kp in d.get("key_points") or []:
            if kp.get("evidence"):
                sec = int(kp["evidence"][0].rsplit("@", 1)[1])
                items.append(EvidenceItem(kp["evidence"][0], member, "video", "claim", kp["text"], source, sec=sec))
        for t in d.get("timeline") or []:
            items.append(EvidenceItem(f"vd:{r['id']}@{t['sec']}", member, "video", "timeline", t["label"], source,
                                      sec=t["sec"]))
        if d.get("summary") and d["summary"] != "내용 없음":
            items.append(EvidenceItem(f"vd:{r['id']}", member, "video", "summary", d["summary"], source))
        names = [p["screen"] for p in d.get("name_pairs") or []]
        kws = [k["keyword_id"] for k in db.conn.execute(
            "SELECT keyword_id FROM item_keywords WHERE item_id=? ORDER BY keyword_id", (r["id"],))]
        out.append(Member(member, "video", r["title"], _first_sentence(d.get("summary") or ""), d.get("summary") or "",
                          "high", names, kws, source, items, r["id"],
                          corrections={p["spoken"]: p["screen"] for p in d.get("name_pairs") or []}))
    return out, no_digest


def repo_members(db: DB, week: str) -> tuple[list[Member], int]:
    """relevant=true RepoCard. 근거: 하는 일 한 문장(oneliner), 신호, 이번 주 별, 릴리스."""
    rows = db.conn.execute(
        "SELECT c.full_name, c.card_json, t.stars_this_week, t.rank, t.keywords, r.description, o.output_json AS oneliner "
        "FROM repo_cards c LEFT JOIN repo_trending t ON t.week=c.week AND t.full_name=c.full_name "
        "LEFT JOIN repos r ON r.full_name=c.full_name LEFT JOIN repo_oneliners o ON o.full_name=c.full_name "
        "WHERE c.week=? ORDER BY c.full_name", (week,)).fetchall()
    out, irrelevant = [], 0
    for r in rows:
        card = json.loads(r["card_json"])
        if not card.get("relevant"):
            irrelevant += 1
            continue
        name = r["full_name"]
        member = rid = f"rp:{name}"
        line = (json.loads(r["oneliner"]).get("oneliner") if r["oneliner"] else "") or (r["description"] or "")
        source = {"site": "GitHub", "title": name, "date": None, "url": f"https://github.com/{name}"}
        items = [EvidenceItem(rid, member, "github", "repo_field", f"하는 일: {line}", source)]
        items.append(EvidenceItem(rid, member, "github", "repo_field", f"신호: {card.get('signal')}", source))
        if r["stars_this_week"] is not None:
            items.append(EvidenceItem(rid, member, "github", "repo_field", "이번 주 별", source,
                                      value=f"{r['stars_this_week']:,}", unit="개"))
        if card.get("why_trending"):
            items.append(EvidenceItem(rid, member, "github", "repo_field", f"뜨는 이유: {card['why_trending']}", source))
        rel = card.get("release")
        if rel:
            items.append(EvidenceItem(rid, member, "github", "repo_field",
                                      f"릴리스 {rel['tag']} ({rel['date']}): {rel['line']}", source))
        owner, repo = name.split("/", 1)
        out.append(Member(member, "github", name, line, " ".join(x for x in (line, r["description"] or "") if x),
                          "high", [repo, name], sorted(json.loads(r["keywords"] or "{}")), source, items))
    return out, irrelevant


def week_evidence(db: DB, week: str) -> WeekEvidence:
    texts, no_card = text_members(db, week)
    videos, no_digest = video_members(db, week)
    repos, irrelevant = repo_members(db, week)
    members = {m.key: m for m in [*texts, *videos, *repos]}
    return WeekEvidence(week, members, {"no_card": no_card, "no_digest": no_digest, "irrelevant_repo": irrelevant})


def cap_pack(members: list[Member], max_tokens: int) -> tuple[list[EvidenceItem], list[str]]:
    """토픽 근거를 입력 상한 안으로. 넘치면 관련성 → 채널 다양성 → 출처당 균형 순으로 고른다.

    구성원마다 근거를 차례로 하나씩 돌려 담는 방식(라운드 로빈): 관련성 높은 구성원부터, 같은 관련성이면 아직 안 담은
    채널부터. 한 출처가 상한을 다 쓰지 않게 된다. 반환: (담은 근거, 뺀 근거 id). 근거 id 하나에 항목이 여럿이면
    (quote + 수치 + 주장) 한 묶음으로 담고 뺀다."""
    def groups(m: Member) -> list[list[EvidenceItem]]:
        by_id: dict[str, list[EvidenceItem]] = {}
        for it in m.items:
            by_id.setdefault(it.id, []).append(it)
        return list(by_id.values())

    order = sorted(members, key=lambda m: (RELEVANCE_RANK.get(m.relevance, 3), m.key))
    queues = {m.key: groups(m) for m in order}
    total, kept, dropped = 0, [], []
    seen_channels: set[str] = set()
    while any(queues.values()):
        # 이번 바퀴: 아직 안 담은 채널의 구성원을 먼저, 그다음 관련성 순서
        turn = sorted([m for m in order if queues[m.key]],
                      key=lambda m: (m.channel in seen_channels, RELEVANCE_RANK.get(m.relevance, 3), m.key))
        for m in turn:
            g = queues[m.key].pop(0)
            cost = sum(estimate_tokens(x.as_dict()) for x in g)
            if total + cost <= max_tokens:
                kept += g
                total += cost
                seen_channels.add(m.channel)
            else:
                dropped.append(g[0].id)
    return kept, list(dict.fromkeys(dropped))
