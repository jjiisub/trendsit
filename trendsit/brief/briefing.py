"""저장값 → 화면 데이터.

- export_topic: 예시 JSON(docs/reference/trendsit-example.json) 토픽 칸으로 옮기는 매핑 초안(관문 A13, S6 export의 출발점).
  S5 저장값만 쓴다. 차이: 도식은 anchor로 포인트에 붙음(예시는 페이지 아래 diagrams 묶음), 출처 번호는 s1·g1 식으로 새로 매김
- write_briefing_md: 리뷰용 브리핑 읽기본 reports/S5_brief/briefing_<week>.md(S6 export 전 임시 화면)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..core.artifacts_brief import TopicPage
from ..core.config import ROOT
from ..core.db import DB
from .evidence import EvidenceItem, week_evidence

OUT = ROOT / "reports" / "S5_brief"


def _final_page(db: DB, run_id: str, topic_id: str) -> TopicPage | None:
    r = db.conn.execute("SELECT page_json FROM topic_pages WHERE run_id=? AND topic_id=? ORDER BY round DESC, id DESC LIMIT 1",
                        (run_id, topic_id)).fetchone()
    return TopicPage.model_validate_json(r["page_json"]) if r else None


def export_topic(db: DB, run_id: str, topic_id: str, sources_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """topics + topic_pages(최종판) + topic_evidence → 예시 JSON 토픽 모양. sources_by_id: 근거 id → {channel, site, title, date, url}."""
    t = db.conn.execute("SELECT * FROM topics WHERE run_id=? AND topic_id=?", (run_id, topic_id)).fetchone()
    page = _final_page(db, run_id, topic_id)
    if t is None or page is None:
        raise KeyError(topic_id)
    ev_rows = db.conn.execute("SELECT evidence_id, member FROM topic_evidence WHERE run_id=? AND topic_id=? ORDER BY rowid",
                              (run_id, topic_id)).fetchall()
    # 출처 = 구성원(글·영상·레포) 단위. 근거 id → 출처 번호
    members = list(dict.fromkeys(r["member"] for r in ev_rows))
    sid: dict[str, str] = {}
    counters = {"text": 0, "video": 0, "github": 0}
    prefix = {"text": "s", "video": "v", "github": "g"}
    sources = []
    for mkey in members:
        eid = next(r["evidence_id"] for r in ev_rows if r["member"] == mkey)
        src = sources_by_id.get(eid, {})
        ch = src.get("channel", "text")
        counters[ch] += 1
        sid[mkey] = f"{prefix[ch]}{counters[ch]}"
        sources.append({"id": sid[mkey], "channel": ch, "site": src.get("site"), "title": src.get("title"),
                        "date": src.get("date"), "url": src.get("url")})
    by_eid = {r["evidence_id"]: sid[r["member"]] for r in ev_rows}

    def refs(ids: list[str]) -> list[str]:
        return list(dict.fromkeys(by_eid[i] for i in ids if i in by_eid))

    bars = [{"type": "bars", "anchor": g.anchor, "title": g.title, "unit": g.unit, "context": g.context,
             "items": [{"label": it.label, "value": it.value} | ({"emphasis": True} if it.emphasis else {})
                       | ({"baseline": True} if it.baseline else {}) for it in g.items],
             "ref": (refs([it.ref for it in g.items]) or [None])[0]} for g in page.numbers]
    events = [{"type": "events", "anchor": g.anchor, "title": g.title, "context": g.context,
               "items": [{"date": it.date, "text": it.text} | ({"ref": by_eid.get(it.ref)} if it.ref else {"topic_id": it.topic_id})
                         for it in g.items]} for g in page.events]
    rel: dict[str, Any] = {"type": t["relation_type"] or "new"}
    if t["relation_topic_id"]:
        rel["topic_id"] = t["relation_topic_id"]
    return {"id": t["topic_id"], "week": t["week"].lower(), "rank": t["rank"], "lead": bool(t["lead"]),
            "title": page.title, "summary": page.summary, "relation": rel, "overview": page.overview,
            "points": [{"text": p.text, "refs": refs(p.refs)} | ({"check": True} if p.check else {}) for p in page.points],
            "diagrams": bars + events,
            "concepts": [c.model_dump() for c in page.concepts],
            "contributions": [{"channel": c.channel, "text": c.text} for c in page.contributions],
            "sources": sources, "channels": sorted({s["channel"] for s in sources}),
            "has_check": any(p.check for p in page.points) or t["status"] == "checked"}


def sources_index(db: DB, week: str) -> tuple[dict[str, dict[str, Any]], dict[str, list[EvidenceItem]]]:
    ev = week_evidence(db, week)
    out, items = {}, {}
    for m in ev.members.values():
        for it in m.items:
            out[it.id] = {"channel": m.channel} | it.source
            items.setdefault(it.id, []).append(it)
    return out, items


def write_briefing_md(db: DB, week: str, run_id: str | None = None) -> Path:
    run_id = run_id or db.conn.execute("SELECT current_run_id FROM weeks WHERE week=?", (week,)).fetchone()[0]
    srcs, _items = sources_index(db, week)
    topics = db.conn.execute("SELECT * FROM topics WHERE run_id=? ORDER BY rank", (run_id,)).fetchall()
    plan_row = db.conn.execute("SELECT plan_json, source FROM briefing_plans WHERE run_id=? ORDER BY id DESC LIMIT 1",
                               (run_id,)).fetchone()
    plan = json.loads(plan_row["plan_json"]) if plan_row else {}
    summ = db.conn.execute("SELECT summary_json FROM runs WHERE id=?", (run_id,)).fetchone()
    lines = [f"# 주간 브리핑 {week} (리뷰용 읽기본)", "",
             f"> run `{run_id}`. S6 export 전 임시 화면. 홈 순서대로 토픽, 끝에 홈 레포 목록. "
             "근거 id 옆은 출처 제목. ⚠ = 확인 필요(같은 이슈가 두 번 남았거나 3라운드 뒤 남은 이슈)", ""]
    if plan_row and plan_row["source"] == "fallback":
        lines += ["> 편집장 선별 대체 계획(점수 순)", ""]
    for t in topics:
        page = _final_page(db, run_id, t["topic_id"])
        mark = "리드 · " if t["lead"] else ""
        if page is None or t["status"] == "failed":
            lines += [f"## {t['rank']}. ({mark}작성 실패) {t['topic_id']}", ""]
            continue
        lines += [f"## {t['rank']}. {mark}{page.title}", "",
                  f"`{t['topic_id']}` · 상태 {t['status']} · {t['final_round']}라운드 · 축: {t['angle']}"
                  + (f" · 후속: {t['relation_topic_id']}" if t["relation_topic_id"] else ""), "",
                  f"**요약(홈)** {page.summary}", "", f"**개요** {page.overview}", "", "**핵심 포인트**", ""]
        for i, p in enumerate(page.points, 1):
            refs = "; ".join(f"`{r}` {(srcs.get(r) or {}).get('title', '?')[:50]}" for r in p.refs)
            lines.append(f"{i}. {'⚠ ' if p.check else ''}{p.text}  \n   ← {refs}")
            for g in [g for g in page.numbers if g.anchor == i]:
                lines += ["", f"   **도식(수치): {g.title}** ({g.unit}) — {g.context}", "",
                          "   | 라벨 | 값 | 근거 | 표시 |", "   |---|---|---|---|"]
                lines += [f"   | {it.label} | {it.value} | `{it.ref}` | {'강조' if it.emphasis else ''}{'기준' if it.baseline else ''} |"
                          for it in g.items]
            for g in [g for g in page.events if g.anchor == i]:
                lines += ["", f"   **도식(사건 흐름): {g.title}** — {g.context}", "",
                          "   | 날짜 | 사건 | 근거 |", "   |---|---|---|"]
                lines += [f"   | {it.date} | {it.text} | `{it.ref or it.topic_id}` |" for it in g.items]
        if page.concepts:
            lines += ["", "**핵심 개념**", ""] + [f"- {c.term}: {c.desc}" for c in page.concepts]
        if page.contributions:
            lines += ["", "**소스별로 더한 것**", ""] + [f"- {c.channel}: {c.text}" for c in page.contributions]
        ev = db.conn.execute("SELECT DISTINCT member FROM topic_evidence WHERE run_id=? AND topic_id=?",
                             (run_id, t["topic_id"])).fetchall()
        lines += ["", f"출처 {len(ev)}곳: " + ", ".join(f"`{r['member']}`" for r in ev), ""]
    repos = plan.get("featured_repos") or []
    others = [r["full_name"] for r in db.conn.execute(
        "SELECT full_name FROM repo_cards WHERE week=? ORDER BY full_name", (week,))
        if r["full_name"] not in repos]
    lines += ["## 홈 레포 목록", ""]
    rows = db.conn.execute("SELECT c.full_name, c.card_json, t.stars_this_week FROM repo_cards c LEFT JOIN repo_trending t "
                           "ON t.week=c.week AND t.full_name=c.full_name WHERE c.week=?", (week,)).fetchall()
    info = {r["full_name"]: (json.loads(r["card_json"]), r["stars_this_week"]) for r in rows}
    for name in [*repos, *others]:
        card, stars = info.get(name, ({}, None))
        if not card.get("relevant"):
            continue
        lines.append(f"- {'★ ' if name in repos else ''}{name} · 신호 {card.get('signal')} · 이번 주 별 {stars} · "
                     f"{card.get('why_trending') or ''}")
    if not rows:
        lines.append("- 없음(이 주 트렌딩 없음)")
    if summ and summ["summary_json"]:
        lines += ["", "## 실행 요약", "", "```json", json.dumps(json.loads(summ["summary_json"]), ensure_ascii=False, indent=1),
                  "```"]
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"briefing_{week}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
