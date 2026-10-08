"""키워드 재판정(rematch, S1 리뷰 M5): 바뀐 config/keywords.yaml을 저장된 제목·요약·본문에 다시 적용한다.

수집(네트워크)을 다시 하지 않는다. S1이 수집 때 부른 것과 같은 입력으로 KeywordMatcher를 부른다.
- 글: match(제목, 피드 요약, 본문) / 영상: match(제목, None, 설명) / 릴리스: match(제목, 노트)
- 트렌딩 레포: match(설명) → 통과면 match(설명, 토픽, README). README는 S1이 받아 둔 것만(없으면 설명과 토픽으로)
items.filter_status/filter_reason/score, item_keywords, repo_trending의 판정 칸을 갱신한다(CONTRACTS 3장: rematch만 허용).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from ..collect.keywords import KeywordMatcher, Match
from ..core.config import KeywordsConfig
from ..core.db import DB


@dataclass
class RematchResult:
    items: int = 0
    items_changed: int = 0
    status_changed: dict[str, int] = field(default_factory=dict)  # "filtered→pass" 등
    repos: int = 0
    repos_changed: int = 0

    def summary(self) -> str:
        moves = ", ".join(f"{k} {v}" for k, v in sorted(self.status_changed.items())) or "없음"
        return (f"항목 {self.items}건 중 {self.items_changed}건 바뀜(판정 이동: {moves}), "
                f"트렌딩 레포 {self.repos}행 중 {self.repos_changed}행 바뀜")


def _item_match(m: KeywordMatcher, row: Any) -> Match:
    if row["channel"] == "video":
        return m.match(row["title"], None, row["body"])
    if row["channel"] == "github":  # 릴리스: 노트가 요약 자리
        return m.match(row["title"], row["body"])
    return m.match(row["title"], row["summary_feed"], row["body"])


def _repo_match(m: KeywordMatcher, row: Any) -> Match:
    first = m.match(row["description"], None)
    if first.filter_status != "pass":
        return first
    topics = " ".join(json.loads(row["topics_json"])) if row["topics_json"] else None
    return m.match(row["description"], topics, row["readme_head"])


def rematch(db: DB, keywords: KeywordsConfig, since: date | None = None, until: date | None = None) -> RematchResult:
    """기간(게시일, 한국 시간)의 항목과 그 기간 주차의 트렌딩 레포를 다시 판정한다. 다시 돌려도 결과가 같다."""
    m = KeywordMatcher(keywords)
    res = RematchResult()
    where, args = "", []
    if since:
        where += " AND i.day >= ?"
        args.append(since.isoformat())
    if until:
        where += " AND i.day <= ?"
        args.append(until.isoformat())
    rows = db.conn.execute(
        "SELECT i.id, i.channel, i.title, i.summary_feed, i.filter_status, i.filter_reason, i.score, t.text AS body, "
        "(SELECT group_concat(keyword_id || ':' || COALESCE(where_matched, ''), ',') FROM "
        " (SELECT keyword_id, where_matched FROM item_keywords k WHERE k.item_id = i.id ORDER BY keyword_id)) AS kws "
        f"FROM items i LEFT JOIN item_texts t ON t.item_id = i.id WHERE 1=1{where} ORDER BY i.id", args).fetchall()
    with db.conn:
        for row in rows:
            res.items += 1
            new = _item_match(m, row)
            kws = ",".join(f"{k}:{w}" for k, w in sorted(new.keywords.items()))
            if (new.filter_status, new.filter_reason, new.score, kws) == (
                    row["filter_status"], row["filter_reason"], row["score"], row["kws"] or ""):
                continue
            res.items_changed += 1
            if new.filter_status != row["filter_status"]:
                key = f"{row['filter_status']}→{new.filter_status}"
                res.status_changed[key] = res.status_changed.get(key, 0) + 1
            db.conn.execute("UPDATE items SET filter_status=?, filter_reason=?, score=? WHERE id=?",
                            (new.filter_status, new.filter_reason, new.score, row["id"]))
            db.conn.execute("DELETE FROM item_keywords WHERE item_id=?", (row["id"],))
            db.conn.executemany("INSERT INTO item_keywords(item_id, keyword_id, where_matched) VALUES (?,?,?)",
                                [(row["id"], k, w) for k, w in new.keywords.items()])

        weeks = [r[0] for r in db.conn.execute(f"SELECT DISTINCT i.week FROM items i WHERE 1=1{where}", args)]
        wsql = "" if not (since or until) else f" WHERE r.week IN ({','.join('?' * len(weeks))})"
        repo_rows = db.conn.execute(
            "SELECT r.week, r.full_name, r.score, r.filter_status, r.filter_reason, r.keywords, p.description, "
            f"p.topics_json, p.readme_head FROM repo_trending r LEFT JOIN repos p ON p.full_name = r.full_name{wsql}",
            weeks if wsql else []).fetchall()
        for row in repo_rows:
            res.repos += 1
            new = _repo_match(m, row)
            old_kws = json.loads(row["keywords"]) if row["keywords"] else {}
            if (new.filter_status, new.filter_reason, new.score, new.keywords) == (
                    row["filter_status"], row["filter_reason"], row["score"], old_kws):
                continue
            res.repos_changed += 1
            db.conn.execute("UPDATE repo_trending SET score=?, filter_status=?, filter_reason=?, keywords=? "
                            "WHERE week=? AND full_name=?",
                            (new.score, new.filter_status, new.filter_reason,
                             json.dumps(new.keywords, ensure_ascii=False), row["week"], row["full_name"]))
    return res
