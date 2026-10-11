"""S6a export: DB → data/site.json (예시 JSON 최상위 구조, published 주만).

토픽은 briefing.export_topic()을 그대로 쓴다. 칸마다 원천이 없으면 칸을 빼고(화면에서도 빠짐), published 주가 없거나
토픽 출처 번호(C-2)가 어긋나면 ExportError로 파일을 쓰지 않는다(기존 site.json 유지).
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .brief.briefing import export_topic, sources_index
from .core import config
from .core.db import DB, now_kst

APPROX_NOTE = "trending monthly approx"
SIGNAL_LABELS = {"trending": "트렌딩", "rising": "급상승", "release": "릴리스", "needs_check": "확인 필요"}
CHANNELS = ("text", "video", "github")


class ExportError(Exception):
    pass


# ---------- 주차 표기(5.2) ----------
def week_id(week: str) -> str:
    return week.lower()


def week_label(week: str) -> tuple[str, str, date, date]:
    """'2026-W42' → ('10월 3주차', '10.12 ~ 10.18', 월, 일). 라벨은 그 주 목요일이 속한 달과 그 달의 몇째 목요일."""
    y, w = week.upper().split("-W")
    mon = date.fromisocalendar(int(y), int(w), 1)
    sun, thu = mon + timedelta(days=6), mon + timedelta(days=3)
    return f"{thu.month}월 {(thu.day - 1) // 7 + 1}주차", f"{mon.month}.{mon.day} ~ {sun.month}.{sun.day}", mon, sun


def stars_text(n: int | None) -> str | None:
    if n is None:
        return None
    return f"+{n / 1000:.1f}k" if n >= 1000 else f"+{n}"


def _json(raw: str | None) -> Any:
    return json.loads(raw) if raw else None


# ---------- 주 하나(토픽, 레포) ----------
def _topics(db: DB, week: str, run_id: str) -> list[dict[str, Any]]:
    """그 주 현재판 토픽을 rank 순으로. 작성 실패(페이지 없음)는 뺀다. C-2: 모든 포인트의 refs가 그 토픽 출처 안에 있어야 함."""
    srcs = sources_index(db, week)
    out = []
    # 작성 실패(최종 페이지 없음)는 SQL로 거르고, 그 밖의 오류는 숨기지 않고 올린다
    rows = db.conn.execute("SELECT t.topic_id FROM topics t WHERE t.run_id=? AND t.status!='failed' AND EXISTS "
                           "(SELECT 1 FROM topic_pages p WHERE p.run_id=t.run_id AND p.topic_id=t.topic_id) ORDER BY t.rank", (run_id,))
    for r in rows.fetchall():
        t = export_topic(db, run_id, r["topic_id"], srcs)
        ids = {s["id"] for s in t["sources"]}
        for loc, refs in _topic_ref_slots(t):
            if not refs or not set(refs) <= ids:
                raise ExportError(f"C-2 위반: {t['id']} {loc} refs={refs} (출처 {sorted(ids)})")
        out.append(t)
    return out


def _topic_ref_slots(t: dict[str, Any]) -> list[tuple[str, list[str]]]:
    """토픽의 refs 칸 전부(C-2 검사용): 단락은 refs 1개 이상 필수, 나머지는 있으면 검사."""
    slots = [(f"head_tiles[{i}]", x["refs"]) for i, x in enumerate(t["head_tiles"])]
    for i, s in enumerate(t["sections"]):
        slots += [(f"sections[{i}].paragraphs[{j}]", p["refs"]) for j, p in enumerate(s["paragraphs"])]
        v = s["visual"]
        if v and v["type"] == "bars" and v.get("ref"):
            slots.append((f"sections[{i}].bars", [v["ref"]]))
        elif v and v["type"] == "table":
            slots.append((f"sections[{i}].table", v["refs"]))
        elif v and v["type"] == "tiles":
            slots += [(f"sections[{i}].tiles[{k}]", x["refs"]) for k, x in enumerate(v["items"])]
        elif v and v["type"] == "events":
            slots += [(f"sections[{i}].events.items[{k}]", [x["ref"]]) for k, x in enumerate(v["items"]) if x.get("ref")]
    return slots


def _repos(db: DB, week: str, run_id: str, topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """그 주 트렌딩(관련 있는 것) + 토픽 근거로 쓴 레포. 설명(what)은 repo_oneliners."""
    topic_of: dict[str, str] = {}
    for t in topics:  # rank 순이라 먼저 쓴 토픽이 이김
        for (m,) in db.conn.execute("SELECT DISTINCT member FROM topic_evidence WHERE run_id=? AND topic_id=? AND member LIKE 'rp:%'",
                                    (run_id, t["id"])):
            topic_of.setdefault(m[3:], t["id"])
    cards = {r["full_name"]: _json(r["card_json"]) for r in db.conn.execute("SELECT full_name, card_json FROM repo_cards WHERE week=?", (week,))}
    oneliners = {r["full_name"]: (_json(r["output_json"]) or {}).get("oneliner") for r in db.conn.execute("SELECT full_name, output_json FROM repo_oneliners")}
    rows = {r["full_name"]: r for r in db.conn.execute("SELECT * FROM repo_trending WHERE week=?", (week,))}
    out = []
    for name in dict.fromkeys([*rows, *topic_of]):
        card, row = cards.get(name), rows.get(name)
        what = oneliners.get(name)
        if name not in topic_of:  # 토픽 근거가 아니면 관련 있는 트렌딩만(카드가 있으면 relevant, 없으면 키워드 필터 통과 + 설명 있음)
            ok = card["relevant"] if card else bool(what) and row["filter_status"] != "filtered"
            if not ok:
                continue
        sig = (card or {}).get("signal")
        stars = row["stars_this_week"] if row else None
        out.append({"week": week_id(week), "name": name, "stars_7d": stars_text(stars),
                    "signal": "needs_check" if sig == "check" else sig, "what": what, "topic_id": topic_of.get(name),
                    "url": f"https://github.com/{name}", "_sort": (stars is None, -(stars or 0), row["rank"] if row else 999)})
    out.sort(key=lambda r: r.pop("_sort"))
    return out


def _page_checks(t: dict[str, Any]) -> list[str]:
    """절 밖에서 화면에 표시되는 확인 필요 위치(build의 shown_checks와 같은 규칙, S6-1 v2: summary·title만)."""
    return [c for c in t.get("checks", []) if c in ("summary", "title")]


# ---------- 실행 기록(5.6) ----------
def _hm(ts: str) -> str:
    return ts[11:16]


def _minutes(start: str, end: str | None) -> float | None:
    return round((datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds() / 60, 1) if end else None


def _weekly_counts(db: DB, run_id: str, summary: dict[str, Any], published: int, needs_check: int) -> dict[str, Any]:
    c: dict[str, Any] = {}
    sel, past, rev = summary.get("select") or {}, (summary.get("cluster") or {}).get("past"), summary.get("review") or {}
    if "candidates" in sel:
        c["candidates"] = sel["candidates"]
    if past:
        c["related"] = {k: past.get(k, 0) for k in ("follow_up", "new", "duplicate")}
    if "selected" in sel:
        c["selected"] = sel["selected"]
    c["evidence_ids"] = db.conn.execute("SELECT COUNT(DISTINCT evidence_id) FROM topic_evidence WHERE run_id=?", (run_id,)).fetchone()[0]
    c["written"] = db.conn.execute("SELECT COUNT(*) FROM steps WHERE run_id=? AND role='writer' AND kind='code'", (run_id,)).fetchone()[0]
    if rev.get("rounds"):
        c["review"] = {"passed_first": rev["rounds"].get("1", 0), "rejected": rev.get("code_rejects", 0) + rev.get("critic_rejects", 0),
                       "needs_check": needs_check}
    c["published"] = published
    return c


def _weekly_summary(c: dict[str, Any]) -> str:
    rev = c.get("review")
    return f"토픽 {c['published']}개 발행" + (f", 검수 반려 {rev['rejected']}회, 확인 필요 {rev['needs_check']}문장" if rev else "")


def _night_week(r: Any, summary: dict[str, Any]) -> str:
    """매일 수집의 주차: 처리한 마지막 날이 속한 ISO 주(02:00 실행은 어제까지를 처리하므로 기록이 없으면 시작일의 전날)."""
    days = summary.get("days")
    d = date.fromisoformat(days[-1]) if days else date.fromisoformat(r["started_at"][:10]) - timedelta(days=1)
    y, w, _ = d.isocalendar()
    return week_id(f"{y}-W{w:02d}")


def _run(db: DB, r: Any, published: dict[str, tuple[int, int]]) -> dict[str, Any]:
    """runs 행 하나. 주간은 steps 표(역할 문장, 확인 표시), 매일은 summary_json.steps(단계, 종료 코드)."""
    summary = _json(r["summary_json"]) or {}
    out: dict[str, Any] = {"id": r["id"], "kind": r["kind"], "at": r["started_at"], "duration_min": _minutes(r["started_at"], r["finished_at"]),
                           "status": r["status"], "cost_usd": round(summary["cost_usd"] if r["kind"] == "nightly" and "cost_usd" in summary else r["cost_usd"], 4)}  # 매일 수집은 하위 프로세스 run이 비용을 가져 summary_json.cost_usd(숫자)에. 주간의 그 칸은 단계별 dict
    if r["kind"] == "weekly":
        out["week"] = week_id(r["week"])
        out["counts"] = _weekly_counts(db, r["id"], summary, *published[r["week"]])
        out["summary"] = _weekly_summary(out["counts"])
        plan_row = db.conn.execute("SELECT source FROM briefing_plans WHERE run_id=? ORDER BY id DESC LIMIT 1", (r["id"],)).fetchone()
        if plan_row and plan_row["source"] == "fallback":  # D-37-인접(C-30): 선별이 대체 계획으로 돈 run
            out["fallback_select"] = True
        steps = []
        for s in db.conn.execute("SELECT t, role, text, attention, detail FROM steps WHERE run_id=? AND text IS NOT NULL ORDER BY seq", (r["id"],)):
            step: dict[str, Any] = {"role": s["role"], "text": s["text"], "t": _hm(s["t"]), "attention": bool(s["attention"])}
            d = _json(s["detail"])
            if isinstance(d, dict) and "draft" in d and "evidence" in d:  # 반려 비교는 detail에 초안·근거가 있을 때만
                step["detail"] = d
            steps.append(step)
        out["steps"] = steps
    else:
        out["week"] = _night_week(r, summary)
        steps = summary.get("steps") or []
        bad = [s for s in steps if s.get("exit")]
        out["summary"] = f"날 {len(summary.get('days') or [])}개, 단계 {len(steps)}개 중 실패 {len(bad)}개"
        out_steps = []
        for s in steps:
            step: dict[str, Any] = {"role": s["name"], "text": (f"{s['day']} " if s.get("day") else "") + (s.get("error") or f"성공, {s.get('sec', 0)}초"),
                                    "attention": bool(s.get("exit"))}
            if s.get("name") == "plan" and s.get("day"):  # C-30: 그날 계획이 대체 계획(점수 순)으로 돈 경우
                plan_row = db.conn.execute("SELECT source FROM plans WHERE day=? ORDER BY id DESC LIMIT 1", (s["day"],)).fetchone()
                if plan_row and plan_row["source"] == "fallback":
                    step["fallback"] = True
            out_steps.append(step)
        out["steps"] = out_steps
    return out


def _runs(db: DB, weeks: list[dict[str, Any]], counts: dict[str, tuple[int, int]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    published = counts  # 주 → (발행 토픽 수, 화면에 표시되는 확인 필요 수)
    ids = [w["_run_id"] for w in weeks]
    marks = ",".join("?" * len(ids))
    rows = db.conn.execute(f"SELECT * FROM runs WHERE kind='nightly' OR id IN ({marks}) ORDER BY started_at DESC", ids).fetchall()
    runs = [_run(db, r, published) for r in rows]
    ids_ok = {w["id"] for w in weeks}
    runs = [r for r in runs if r["kind"] != "nightly" or r["week"] in ids_ok]  # C-1: 발행 주의 nightly만(명세 5.1 표의 "전부"보다 C-1이 앞)
    by_id = {r["id"]: r for r in runs}
    rws = []
    for w in weeks:
        wk = w["_db_week"]
        nights = [r for r in runs if r["kind"] == "nightly" and r["week"] == w["id"]]
        c = by_id[w["_run_id"]].get("counts", {})
        rev = c.get("review", {})
        rws.append({"week": w["id"], "label": w["label"], "range": w["range"], "nightly": len(nights),
                    "nightly_failed": sum(r["status"] in ("partial", "failed", "stopped") for r in nights), "collected": sum(w["collected"].values()),
                    "candidates": c.get("candidates"), "published": published[wk][0], "rejected": rev.get("rejected"),
                    "needs_check": rev.get("needs_check")})
    return runs, [{k: v for k, v in r.items() if v is not None} for r in rws]


# ---------- 소스(5.1) ----------
def _sources(db: DB, weeks: list[dict[str, Any]], members: dict[str, set[tuple[str, str]]]) -> list[dict[str, Any]]:
    out = []
    yaml = config.load("sources.yaml")  # 원천은 sources.yaml: 거기서 지운 소스는 DB 표에 남아 있어도 내보내지 않는다(github는 고정 id 둘)
    known = {s.id for s in yaml.text} | {s.id for s in yaml.video} | {"github_trending", "github_releases"}
    for s in db.conn.execute("SELECT * FROM sources ORDER BY channel, name"):
        if s["id"] not in known:
            continue
        cfg = _json(s["config_json"])
        cfg = cfg if isinstance(cfg, dict) else {}
        entry: dict[str, Any] = {"id": s["id"], "name": s["name"], "type": s["kind"], "channel": s["channel"],
                                 "url": s["feed"] or cfg.get("url") or None, "enabled": bool(s["enabled"]), "weeks": {}}
        if cfg.get("note"):
            entry["note"] = cfg["note"]
        for w in weeks:
            if s["id"] == "github_trending":  # 트렌딩 레포는 items가 아니라 repo_trending에 쌓임
                n = db.conn.execute("SELECT COUNT(*) FROM repo_trending WHERE week=?", (w["_db_week"],)).fetchone()[0]
            else:
                n = db.conn.execute("SELECT COUNT(*) FROM items WHERE source_id=? AND week=?", (s["id"], w["_db_week"])).fetchone()[0]
            failed = db.conn.execute("SELECT COUNT(DISTINCT day) FROM fetch_log WHERE source_id=? AND status='failed' AND day BETWEEN ? AND ?",
                                     (s["id"], w["_start"].isoformat(), w["_end"].isoformat())).fetchone()[0]
            used = sum(1 for _, src in members[w["_db_week"]] if src == s["id"])
            entry["weeks"][w["id"]] = {"collected": n, "failed_days": failed, "used_in_topics": used}
            if n and s["id"] != "github_trending":  # 요일별(월~일) 수집 수. repo_trending에는 요일이 없어 칸을 두지 않음
                daily = [0] * 7
                for (day,) in db.conn.execute("SELECT day FROM items WHERE source_id=? AND week=? AND day IS NOT NULL", (s["id"], w["_db_week"])):
                    daily[date.fromisoformat(day).weekday()] += 1
                entry.setdefault("daily", {})[w["id"]] = daily
        last = db.conn.execute("SELECT t, n_new, status, error FROM fetch_log WHERE source_id=? ORDER BY t DESC, id DESC LIMIT 1", (s["id"],)).fetchone()
        entry["last"] = {"at": last["t"], "count": last["n_new"], "status": last["status"]} if last else None
        entry["last_error"] = last["error"] if last and last["status"] != "ok" and last["error"] else None
        out.append(entry)
    return out


def _used_members(db: DB, week: str, run_id: str, topic_ids: list[str]) -> set[tuple[str, str]]:
    """그 주 토픽이 근거로 쓴 (구성원, 소스). 구성원 it:글 / vd:영상 → items.source_id, rp:레포 → github_trending."""
    src = {f"it:{r['id']}": r["source_id"] for r in db.conn.execute("SELECT id, source_id FROM items WHERE week=?", (week,))}
    src |= {f"vd:{r['video_id']}": r["source_id"] for r in db.conn.execute(
        "SELECT v.video_id, i.source_id FROM videos v JOIN items i ON i.id=v.item_id WHERE i.week=?", (week,))}
    marks = ",".join("?" * len(topic_ids))  # 사이트에 실린(export된) 토픽만
    members = [r[0] for r in db.conn.execute(f"SELECT DISTINCT member FROM topic_evidence WHERE run_id=? AND topic_id IN ({marks})", (run_id, *topic_ids))]
    return {(m, "github_trending" if m.startswith("rp:") else src[m]) for m in members if m.startswith("rp:") or m in src}


def _keywords(db: DB, weeks: list[dict[str, Any]], run_ids: list[str], topic_ids: list[str]) -> dict[str, Any]:
    recent = sorted(w["_db_week"] for w in weeks)[-4:]
    marks = ",".join("?" * len(recent))
    mentions: dict[tuple[str, str], int] = {}
    for r in db.conn.execute(f"SELECT k.keyword_id, i.week, COUNT(DISTINCT k.item_id) n FROM item_keywords k JOIN items i ON i.id=k.item_id "
                             f"WHERE i.week IN ({marks}) GROUP BY 1, 2", recent):
        mentions[(r["keyword_id"], r["week"])] = r["n"]
    rmarks = ",".join("?" * len(run_ids))
    topics: dict[str, list[str]] = {}
    for r in db.conn.execute(
            f"SELECT DISTINCT k.keyword_id, e.topic_id FROM topic_evidence e JOIN item_keywords k ON "
            f"e.member = 'it:' || k.item_id OR e.member IN (SELECT 'vd:' || video_id FROM videos WHERE item_id=k.item_id) "
            f"WHERE e.run_id IN ({rmarks}) AND e.topic_id IN ({','.join('?' * len(topic_ids))}) ORDER BY e.topic_id", [*run_ids, *topic_ids]):
        topics.setdefault(r["keyword_id"], []).append(r["topic_id"])
    items = [{"id": k.id, "name": k.canonical, "aliases": list(k.aliases), "mentions": [mentions.get((k.id, wk), 0) for wk in recent],
              "topics": topics.get(k.id, [])} for k in config.load("keywords.yaml").keywords]
    return {"weeks": [week_id(wk) for wk in recent], "items": items}


# ---------- 전체 ----------
def build(db: DB, with_week: str | None = None) -> dict[str, Any]:
    """published 주(+ with_week: 발행 직전의 그 주)만. with_week는 publish가 상태를 바꾸기 전에 export·build를 돌리기 위한 것."""
    rows = db.conn.execute("SELECT week, current_run_id, published_at FROM weeks WHERE (status='published' OR week=?) AND current_run_id IS NOT NULL "
                           "ORDER BY week DESC", (with_week,)).fetchall()
    if not rows:
        raise ExportError("published 주가 없음")
    weeks, topics, repos, members, counts = [], [], [], {}, {}
    for r in rows:
        wk = r["week"]
        label, rng, start, end = week_label(wk)
        ts = _topics(db, wk, r["current_run_id"])
        collected = {c: db.conn.execute("SELECT COUNT(*) FROM items WHERE week=? AND channel=?", (wk, c)).fetchone()[0] for c in CHANNELS}
        approx = db.conn.execute("SELECT EXISTS(SELECT 1 FROM repo_trending t JOIN runs x ON x.id=t.run_id WHERE t.week=? AND x.note=?)",
                                 (wk, APPROX_NOTE)).fetchone()[0]
        members[wk] = _used_members(db, wk, r["current_run_id"], [t["id"] for t in ts])
        counts[wk] = (len(ts), sum(bool(s.get("check")) for t in ts for s in t["sections"]) + sum(len(_page_checks(t)) for t in ts))
        cited = {(s["channel"], s["url"] or s["title"]) for t in ts for s in t["sources"]}
        weeks.append({"id": week_id(wk), "label": label, "range": rng,
                      "published_at": r["published_at"] or now_kst(), "collected": collected, "topic_ids": [t["id"] for t in ts],
                      "topic_count": len(ts), "source_count": len(cited), "trending_approx": bool(approx),
                      "_db_week": wk, "_run_id": r["current_run_id"], "_start": start, "_end": end})
        topics += ts
        repos += _repos(db, wk, r["current_run_id"], ts)
    runs, run_weeks = _runs(db, weeks, counts)
    site = {
        "meta": {"product": "TrendsIT", "generated_at": now_kst()[:10], "signal_labels": SIGNAL_LABELS,
                 "channel_labels": {"text": "글", "video": "영상", "github": "GitHub"},
                 "channel_labels_topic": {"text": "글", "video": "영상", "github": "레포"}},
        "weeks": weeks, "topics": topics, "repos": repos,
        "sources": _sources(db, weeks, members), "keywords": _keywords(db, weeks, [w["_run_id"] for w in weeks], [t["id"] for t in topics]),
        "runs": runs, "run_weeks": run_weeks,
    }
    for w in weeks:
        for k in [k for k in w if k.startswith("_")]:
            del w[k]
    return site


def export(db: DB, out: Path, with_week: str | None = None) -> None:
    site = build(db, with_week)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(json.dumps(site, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, out)
