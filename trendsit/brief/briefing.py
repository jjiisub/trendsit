"""저장값 → 화면 데이터(S6-1 5.7, v2).

- export_topic: topics + topic_pages(최종판) + topic_evidence → site.json 토픽 v2 모양(관문 A8)
- write_briefing_md: 리뷰용 브리핑 읽기본 reports/S5_brief/briefing_<week>.md(S6 export 전 임시 화면, v2)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..core.artifacts_brief import TopicPage
from ..core.db import DB
from . import report
from .evidence import week_evidence


def visible_checks(checks: list[str], page: TopicPage) -> list[str]:
    """⚠ 위치가 없는 절(코드가 visual을 뺀 것)을 가리키면 "빠진 시각 요소"로."""
    out = []
    for loc in checks:
        m = re.match(r"^sections\[(\d+)\]$", loc)
        out.append(f"빠진 시각 요소({loc})" if m and int(m[1]) >= len(page.sections) else loc)
    return out


def _final_page(db: DB, run_id: str, topic_id: str) -> TopicPage | None:
    r = db.conn.execute("SELECT page_json FROM topic_pages WHERE run_id=? AND topic_id=? ORDER BY round DESC, id DESC LIMIT 1",
                        (run_id, topic_id)).fetchone()
    return TopicPage.model_validate_json(r["page_json"]) if r else None


def _video_timeline(db: DB, video_id: str) -> dict[int, dict[str, Any]]:
    r = db.conn.execute("SELECT digest_json FROM video_digests WHERE video_id=?", (video_id,)).fetchone()
    if not r:
        return {}
    return {m["sec"]: m for m in json.loads(r["digest_json"]).get("timeline") or []}


def _slide_reading(db: DB, video_id: str, sec: int) -> dict[str, Any]:
    r = db.conn.execute("SELECT reading_json FROM video_frames WHERE video_id=? AND t=?", (video_id, float(sec))).fetchone()
    return json.loads(r["reading_json"]) if r and r["reading_json"] else {}


def export_topic(db: DB, run_id: str, topic_id: str, sources_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """topics + topic_pages(최종판) + topic_evidence → 사이트 데이터 토픽 v2 모양.
    sources_by_id: 근거 id → {channel, site, title, date, url, [origin]}."""
    t = db.conn.execute("SELECT * FROM topics WHERE run_id=? AND topic_id=?", (run_id, topic_id)).fetchone()
    page = _final_page(db, run_id, topic_id)
    if t is None or page is None:
        raise KeyError(topic_id)
    ev_rows = db.conn.execute("SELECT evidence_id, member FROM topic_evidence WHERE run_id=? AND topic_id=? ORDER BY rowid",
                              (run_id, topic_id)).fetchall()
    members = list(dict.fromkeys(r["member"] for r in ev_rows))
    sid: dict[str, str] = {}
    counters = {"text": 0, "video": 0, "github": 0}
    prefix = {"text": "s", "video": "v", "github": "g"}
    sources = []
    video_ids: dict[str, str] = {}  # member(vd:{video_id}) → video_id
    for mkey in members:
        eid = next(r["evidence_id"] for r in ev_rows if r["member"] == mkey)
        src = sources_by_id.get(eid, {})
        ch = src.get("channel", "text")
        counters[ch] += 1
        sid[mkey] = f"{prefix[ch]}{counters[ch]}"
        entry = {"id": sid[mkey], "channel": ch, "site": src.get("site"), "title": src.get("title"),
                 "date": src.get("date"), "url": src.get("url")}
        if src.get("origin"):
            entry["origin"] = o.get("url") if isinstance(o := src["origin"], dict) else o
        if ch == "video" and mkey.startswith("vd:"):
            video_id = mkey[3:]
            video_ids[mkey] = video_id
            timeline = _video_timeline(db, video_id)
            entry["video_id"] = video_id
            entry["timeline"] = [{"sec": m["sec"], "label": m["label"], "slide": bool(m.get("slide"))}
                                 for m in sorted(timeline.values(), key=lambda m: m["sec"])]
        sources.append(entry)
    by_eid = {r["evidence_id"]: sid[r["member"]] for r in ev_rows}

    def refs(ids: list[str]) -> list[str]:
        return list(dict.fromkeys(by_eid[i] for i in ids if i in by_eid))

    def visual_of(s: Any) -> dict[str, Any] | None:
        if s.visual == "none":
            return None
        if s.visual == "bars" and s.bars:
            g = s.bars
            r = (refs([it.ref for it in g.items]) or [None])[0]
            return {"type": "bars", "title": g.title, "context": g.context, "unit": g.unit,
                    "items": [{"label": it.label, "value": it.value} | ({"emphasis": True} if it.emphasis else {})
                              | ({"baseline": True} if it.baseline else {}) for it in g.items], "ref": r}
        if s.visual == "table" and s.table:
            tb = s.table
            return {"type": "table", "title": tb.title, "note": tb.note, "columns": tb.columns, "rows": tb.rows,
                    "refs": refs(tb.refs)}
        if s.visual == "tiles":
            return {"type": "tiles", "items": [{"value": x.value, "label": x.label, "note": x.note, "refs": refs(x.refs)}
                                               for x in s.tiles]}
        if s.visual == "events" and s.events:
            g = s.events
            return {"type": "events", "title": g.title, "context": g.context,
                    "items": [{"date": it.date, "text": it.text} | ({"ref": by_eid.get(it.ref)} if it.ref else
                              {"topic_id": it.topic_id}) for it in g.items]}
        return None

    def slide_of(s: Any) -> dict[str, Any] | None:
        if not s.slide:
            return None
        m = re.match(r"^sl:(\d+)@(\d+)$", s.slide)
        if not m:
            return None
        sec = int(m[2])
        row = db.conn.execute("SELECT video_id FROM videos WHERE item_id=?", (int(m[1]),)).fetchone()
        video_id = row[0] if row else None
        from ..core.config import ROOT

        path = ROOT / "data" / "slides" / f"{video_id}_{sec}.jpg"
        if video_id is None or not path.is_file():
            return None
        reading = _slide_reading(db, video_id, sec)
        return {"sec": sec, "title": reading.get("title") or "", "caption": s.slide_caption,
                "image": f"slides/{video_id}_{sec}.jpg"}

    timeline_by_sec: dict[int, dict[str, Any]] = {}
    for vid in video_ids.values():
        timeline_by_sec |= _video_timeline(db, vid)
    sections = []
    for s in page.sections:
        sections.append({"heading": s.heading, "paragraphs": [{"text": p.text, "refs": refs(p.refs)} for p in s.paragraphs],
                         "visual": visual_of(s), "slide": slide_of(s),
                         "video_secs": [{"sec": sec, "label": timeline_by_sec.get(sec, {}).get("label", ""),
                                        "slide": bool(timeline_by_sec.get(sec, {}).get("slide"))} for sec in s.video_secs],
                         "check": s.check})
    checks = visible_checks(json.loads(t["checks_json"] or "[]"), page)
    rel: dict[str, Any] = {"type": t["relation_type"] or "new"}
    if t["relation_topic_id"]:
        rel["topic_id"] = t["relation_topic_id"]
    if t["relation_label"]:
        rel["label"] = t["relation_label"]
    return {"id": t["topic_id"], "week": t["week"].lower(), "rank": t["rank"], "lead": bool(t["lead"]),
            "title": page.title, "summary": page.summary, "relation": rel,
            "head_tiles": [{"value": x.value, "label": x.label, "note": x.note, "refs": refs(x.refs)} for x in page.head_tiles],
            "sections": sections, "sources": sources, "channels": sorted({s["channel"] for s in sources}),
            "has_check": any(s.check for s in page.sections) or bool(checks), "checks": checks}


def sources_index(db: DB, week: str) -> dict[str, dict[str, Any]]:
    ev = week_evidence(db, week)
    return {it.id: {"channel": m.channel} | it.source for m in ev.members.values() for it in m.items}


def write_briefing_md(db: DB, week: str, run_id: str | None = None) -> Path:
    run_id = run_id or db.conn.execute("SELECT current_run_id FROM weeks WHERE week=?", (week,)).fetchone()[0]
    srcs = sources_index(db, week)
    topics = db.conn.execute("SELECT * FROM topics WHERE run_id=? ORDER BY rank", (run_id,)).fetchall()
    plan_row = db.conn.execute("SELECT plan_json, source FROM briefing_plans WHERE run_id=? ORDER BY id DESC LIMIT 1",
                               (run_id,)).fetchone()
    plan = json.loads(plan_row["plan_json"]) if plan_row else {}
    summ = db.conn.execute("SELECT summary_json FROM runs WHERE id=?", (run_id,)).fetchone()
    lines = [f"# 주간 브리핑 {week} (리뷰용 읽기본, v2)", "",
             f"> run `{run_id}`. S6 export 전 임시 화면. 근거 id 옆은 출처 제목. ⚠ = 확인 필요(같은 이슈가 두 번 "
             "남았거나 3라운드 뒤 남은 이슈)", ""]
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
                  *([f"> ⚠ 확인 필요: {', '.join(checks)}", ""]
                    if (checks := visible_checks(json.loads(t["checks_json"] or "[]"), page)) else []),
                  f"**요약(홈)** {page.summary}", ""]
        if page.head_tiles:
            lines += ["**핵심 수치**", ""] + [f"- {x.value} — {x.label}({x.note}) `{', '.join(x.refs)}`" for x in page.head_tiles] + [""]
        for i, s in enumerate(page.sections, 1):
            lines.append(f"### {i}. {'⚠ ' if s.check else ''}{s.heading}")
            lines.append("")
            for p in s.paragraphs:
                refs = "; ".join(f"`{r}` {((srcs.get(r) or {}).get('title') or '?')[:50]}" for r in p.refs)
                lines += [p.text, f"← {refs}", ""]
            if s.bars:
                lines += [f"표/막대: {s.bars.title} ({s.bars.unit}) — {s.bars.context}", "",
                          "| 라벨 | 값 | 근거 | 표시 |", "|---|---|---|---|"]
                lines += [f"| {it.label} | {it.value} | `{it.ref}` | {'강조' if it.emphasis else ''}{'기준' if it.baseline else ''} |"
                          for it in s.bars.items]
                lines.append("")
            if s.table:
                lines += [f"표: {s.table.title} — {s.table.note}", "", f"| {' | '.join(s.table.columns)} |",
                          "|" + "---|" * len(s.table.columns)]
                lines += [f"| {' | '.join(row)} |" for row in s.table.rows]
                lines.append("")
            if s.events:
                lines += [f"사건 흐름: {s.events.title} — {s.events.context}", "", "| 날짜 | 사건 | 근거 |", "|---|---|---|"]
                lines += [f"| {it.date} | {it.text} | `{it.ref or it.topic_id}` |" for it in s.events.items]
                lines.append("")
            if s.slide:
                lines += [f"슬라이드: `{s.slide}` — {s.slide_caption}", ""]
            if s.video_secs:
                lines += [f"영상 구간: {s.video_secs}", ""]
        ev = db.conn.execute("SELECT DISTINCT member FROM topic_evidence WHERE run_id=? AND topic_id=?",
                             (run_id, t["topic_id"])).fetchall()
        lines += [f"출처 {len(ev)}곳: " + ", ".join(f"`{r['member']}`" for r in ev), ""]
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
        star_text = f"이번 주 별 {stars:,}" if stars is not None else "별 정보 없음"
        lines.append(f"- {'★ ' if name in repos else ''}{name} · 신호 {card.get('signal')} · {star_text} · "
                     f"{card.get('why_trending') or ''}")
    if not rows:
        lines.append("- 없음(이 주 트렌딩 없음)")
    if summ and summ["summary_json"]:
        lines += ["", "## 실행 요약", "", "```json", json.dumps(json.loads(summ["summary_json"]), ensure_ascii=False, indent=1),
                  "```"]
    report.OUT.mkdir(parents=True, exist_ok=True)
    path = report.OUT / f"briefing_{week}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
