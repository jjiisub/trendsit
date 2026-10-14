"""S7a export: runs·run_weeks(실행 기록 화면). 새 기록 없이 runs·steps·cluster_pairs·plans 등 있는 행에서 뽑는다(D-6).
오류 원문은 읽지 않고 종료 코드·상태만 쓴다(D-7). 글자 칸은 300자에서 자른다(C-5). 원천 행이 없는 단계는 line만 낸다."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import date, datetime
from itertools import groupby
from typing import Any
from urllib.parse import urlsplit

from .core.db import DB

CAP = 300
EVIDENCE_ID = re.compile(r"\[?\b(it|og|vd|rp|sl):([A-Za-z0-9_./-]+)(?:#[A-Za-z0-9]+|@\d+)?\]?")  # 검수 지적에 섞인 근거 id: 공개 화면에는 `it 8` 꼴로(M-2)
STEP_KINDS = ("collect", "filter", "summarize", "plan", "deep-text", "video", "repo-analyze")


def _j(raw: str | None) -> Any:
    return json.loads(raw) if raw else None


def _dig(d: Any, *path: str) -> Any:
    for k in path:
        d = d.get(k) if isinstance(d, dict) else None
    return d


def _cap(x: Any) -> Any:
    if isinstance(x, str):
        return EVIDENCE_ID.sub(lambda m: f"{m[1]} {m[2]}", x)[:CAP]
    if isinstance(x, list):
        return [_cap(v) for v in x]
    if isinstance(x, dict):
        return {k: _cap(v) for k, v in x.items()}
    return x


def _iso(ts: str | None) -> str | None:
    """끝 시각이 옛 형식('2026-10-14 06:59:08', 시간대 없음)이면 KST ISO로 맞춘다."""
    return ts if not ts or re.search(r"[+-]\d\d:\d\d$", ts) else ts.replace(" ", "T") + "+09:00"


def _sec(start: str, end: str | None) -> int | None:
    return round((datetime.fromisoformat(_iso(end)) - datetime.fromisoformat(_iso(start))).total_seconds()) if end else None


def _md(day: str) -> str:
    return f"{int(day[5:7])}.{int(day[8:10])}"


def _iso_week(day: str) -> str:
    y, w, _ = date.fromisoformat(day[:10]).isocalendar()
    return f"{y}-w{w:02d}"


def _who(kind: str, role: str | None = None, model: str | None = None, n: int | None = None) -> dict[str, Any]:
    return {"kind": kind, "role": role, "model": (model or "").split("/")[-1] or None, "n": n}


def _kv(*items: tuple[str, Any]) -> dict[str, Any]:
    """값이 dict면 `키 값 / 키 값`으로 한 줄."""
    return {"type": "kv", "items": [[k, " / ".join(f"{a} {b}" for a, b in v.items()) if isinstance(v, dict) else str(v)] for k, v in items if v not in (None, "", {})]}


def _table(head: list[str], rows: list[list[Any]]) -> dict[str, Any]:
    return {"type": "table", "head": head, "rows": [[str(c) for c in r] for r in rows]}


def _step(t: str, name: str, who: list[dict[str, Any]], line: str, dur: float | None = None, cost: float | None = None,
          attention: bool = False, detail: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return _cap({"t": t[11:16], "name": name, "who": who, "line": line, "duration_sec": None if dur is None else round(dur),
                 "cost_usd": round(cost, 4) if cost else None, "attention": bool(attention),
                 "detail": [b for b in detail or [] if b.get("items") or b.get("rows")]})


def _title(db: DB, member: str) -> str:
    """cluster_pairs·cluster_items 구성원(it:/vd:/rp:) → 제목 (소스 이름). 참조 행이 없으면 `item <n>` 꼴(M-2: 근거 id 모양을 피함)."""
    kind, _, key = member.partition(":")
    if kind == "rp":
        return key
    where = "i.id=?" if kind == "it" else "i.id=(SELECT item_id FROM videos WHERE video_id=?)"
    r = db.conn.execute(f"SELECT i.title, s.name FROM items i LEFT JOIN sources s ON s.id=i.source_id WHERE {where}", (key,)).fetchone()
    if not r or not r["title"]:
        return f"item {key}"
    return f"{r['title']} ({r['name']})" if r["name"] else r["title"]


# ---------- run 선택(5.2-1) ----------
def _common(r: Any, kind: str, week: str, mode: str, cost: float | None, label: str, **kw: Any) -> dict[str, Any]:
    return {"id": kw.get("id", r["id"]), "kind": kind, "at": r["started_at"], "end": _iso(r["finished_at"]),
            "duration_sec": _sec(r["started_at"], r["finished_at"]), "day": r["started_at"][:10], "week": week, "mode": mode,
            "status": r["status"], "cost_usd": round(cost or 0, 4), "current": kw.get("current", False), "label": label,
            "sub": kw.get("sub", False), "topic_id": kw.get("topic_id"), "result": kw["result"], "summary": None, "steps": []}


def _nightly(r: Any, sj: dict[str, Any]) -> dict[str, Any] | None:
    days, steps = sj.get("days") or [], sj.get("steps") or []
    if not days or not steps:  # D-12: 범위 없음·건너뜀은 안 냄
        return None
    label = "nightly " + (_md(days[0]) if len(days) == 1 else f"{_md(days[0])}~{_md(days[-1])}")
    d = _common(r, "nightly", _iso_week(days[0]), "manual" if sj.get("manual") else "auto", sj.get("cost_usd"), label,
                result={"steps": len(steps), "failed": sum(bool(s.get("exit")) for s in steps)})
    d["_days"], d["_sj"] = days, sj
    return d


def _weekly(db: DB, r: Any, sj: dict[str, Any], current: str | None) -> dict[str, Any]:
    label = re.sub(rf"^weekly {r['week']} ", "", re.sub(r"\s*\(.*$", "", r["note"] or ""))
    topic = re.search(r"topic (\S+)$", label)
    full = label.startswith(("from cluster", "cluster"))
    n_steps = db.conn.execute("SELECT COUNT(*) FROM steps WHERE run_id=?", (r["id"],)).fetchone()[0] if topic else 0
    result: dict[str, Any] = {"topics": 1, "steps": n_steps} if topic else {
        "clusters": _dig(sj, "cluster", "clusters"), "candidates": _dig(sj, "select", "candidates"), "selected": _dig(sj, "select", "selected"),
        "topics": _dig(sj, "write", "topics"), "code_rejects": _dig(sj, "review", "code_rejects"), "check_topics": _dig(sj, "review", "check_topics")}
    d = _common(r, "weekly", r["week"].lower(), "auto" if (r["spec"] or "").startswith("RUN-") else "manual", r["cost_usd"], label,
                current=current == r["id"], sub=not full, topic_id=topic[1] if topic else None, result=result)
    d["_sj"] = sj
    return d


def _step_groups(db: DB) -> list[dict[str, Any]]:
    """③ 수동 단계별 run(nightly 하위가 아닌 손 실행)을 실행 날짜별 한 줄로."""
    days: dict[str, list[Any]] = {}
    for r in db.conn.execute(f"SELECT * FROM runs WHERE kind IN ({','.join('?' * len(STEP_KINDS))}) AND COALESCE(spec,'') NOT LIKE 'RUN-%' "
                             "ORDER BY started_at", STEP_KINDS):
        days.setdefault(r["started_at"][:10], []).append(r)
    out = []
    for day, rs in days.items():
        kinds = {k: Counter(r["status"] for r in rs if r["kind"] == k) for k in STEP_KINDS if any(r["kind"] == k for r in rs)}
        ends = [_iso(r["finished_at"]) for r in rs if r["finished_at"]]
        first = dict(rs[0]) | {"finished_at": max(ends, default=None), "status": "ok" if all(r["status"] == "ok" for r in rs) else "partial"}
        out.append(_common(first, "steps", _iso_week(day), "manual", sum(r["cost_usd"] or 0 for r in rs), "steps", id=f"steps-{day}",
                           result={"kinds": {k: dict(sorted(c.items(), key=lambda x: (x[0] != "ok", x[0]))) for k, c in kinds.items()}}))
    return out


# ---------- weekly run 1건(5.2-3) ----------
def _weekly_detail(db: DB, d: dict[str, Any], ex: dict[str, Any]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    sj, rid = d["_sj"], d["id"]
    rows = db.conn.execute("SELECT seq, t, role, kind, text, attention, detail, model, tokens_in, tokens_out, cost_usd FROM steps "
                           "WHERE run_id=? ORDER BY seq", (rid,)).fetchall()
    by: dict[str, list[Any]] = defaultdict(list)
    for s in rows:
        by[s["role"]].append(s)
    dur, cost = (sj.get(k) if isinstance(sj.get(k), dict) else {} for k in ("duration_sec", "cost_usd"))
    steps = [x for x in (by.get("evidence") and _s_evidence(by, dur), by.get("normalize") and _s_normalize(db, by, rid),
                         by.get("cluster") and _s_cluster(db, by, rid, dur, cost), by.get("editor_select") and _s_select(db, by, rid, sj, dur, cost),
                         _s_write(db, by, rid, sj, dur, cost, d["topic_id"]), _s_end(by, dur, cost)) if x]
    pub = ex[d["week"]]["topic_count"] if d["current"] and d["week"] in ex else None  # 현재판이면 사이트에 실리는 토픽 수
    if d["topic_id"]:  # 토픽 1개 재실행 run: summary_json은 주 누적치라 published만(NG-6)
        return ({"published": pub} if pub is not None else None), steps
    rev = _dig(sj, "review") or {}
    res = d["result"]
    return {"clusters": res["clusters"], "candidates": res["candidates"], "selected": res["selected"], "topics": res["topics"], "published": pub,
            "rounds": rev.get("rounds"), "code_rejects": rev.get("code_rejects"), "critic_rejects": rev.get("critic_rejects"),
            "check_topics": rev.get("check_topics")}, steps


def _s_evidence(by: dict[str, list[Any]], dur: dict[str, Any]) -> dict[str, Any] | None:
    ev = by["evidence"]
    c = _j(ev[0]["detail"]) or {}
    detail = [_kv(("counts", c.get("counts")), ("excluded", c.get("excluded")),
                  ("영상 관련성", ev[1]["text"].split(": ", 1)[-1] if len(ev) > 1 else None))]
    return _step(ev[0]["t"], "evidence", [_who("code")], ev[0]["text"] or "", dur.get("evidence"), detail=detail)


def _s_normalize(db: DB, by: dict[str, list[Any]], rid: str) -> dict[str, Any] | None:
    nm = by["normalize"]
    al = db.conn.execute("SELECT alias, canonical, reason FROM aliases WHERE run_id=? AND origin='normalizer' AND status='approved' ORDER BY id", (rid,))
    detail = [_kv(*((_j(nm[0]["detail"]) or {}).get("counts") or {}).items()),
              {"type": "list", "items": [f"{a['alias']} → {a['canonical']}" + (f" / {a['reason']}" if a["reason"] else "") for a in al]}]
    return _step(nm[0]["t"], "normalize", [_who("code")], nm[0]["text"] or "", detail=detail)


def _s_cluster(db: DB, by: dict[str, list[Any]], rid: str, dur: dict[str, Any], cost: dict[str, Any]) -> dict[str, Any] | None:
    cl, dec = by["cluster"], by.get("decide", [])
    llm = [s for s in dec if s["kind"] == "llm"]
    att = sum(bool(s["attention"]) for s in dec)
    pairs = [[_title(db, p["a"]), _title(db, p["b"]), "같음" if p["answer"] else "다름", p["reason"] or "", f"{p['confidence'] or 0:.2f}"]
             for p in db.conn.execute("SELECT * FROM cluster_pairs WHERE run_id=? AND decided=1 ORDER BY id", (rid,))]
    detail = [_kv(*(_j(cl[-1]["detail"]) or {}).items()), _table(["a", "b", "판정", "이유", "확신도"], pairs)]
    return _step(cl[0]["t"] if not dec else min(cl[0]["t"], dec[0]["t"]), "cluster + decide",
                 [_who("code")] + ([_who("llm", "decide", llm[0]["model"], len(llm))] if llm else []),
                 (cl[-1]["text"] or "") + (f" / attention {att}" if att else ""), dur.get("cluster"), cost.get("decide"), bool(att), detail)


def _s_select(db: DB, by: dict[str, list[Any]], rid: str, sj: dict[str, Any], dur: dict[str, Any], cost: dict[str, Any]) -> dict[str, Any] | None:
    es = by["editor_select"]
    llm = [s for s in es if s["kind"] == "llm"]
    code = next((s for s in reversed(es) if s["kind"] == "code"), None)
    cd = (_j(code["detail"]) if code else None) or {}
    plan = db.conn.execute("SELECT plan_json FROM briefing_plans WHERE run_id=? ORDER BY id DESC LIMIT 1", (rid,)).fetchone()
    rank = {}
    for t in db.conn.execute("SELECT rank, title, cluster_ids_json FROM topics WHERE run_id=?", (rid,)):
        for cid in json.loads(t["cluster_ids_json"] or "[]"):
            rank[cid] = (t["rank"], t["title"])
    rows = []
    for x in (_j(plan["plan_json"]) if plan else {}).get("decisions") or []:
        first = db.conn.execute("SELECT member FROM cluster_items WHERE cluster_id=? ORDER BY rowid LIMIT 1", (x["cluster_id"],)).fetchone()
        r, name = rank.get(x["cluster_id"]) or ("-", None)
        name = name or (_title(db, first[0]) if first else f"cluster {x['cluster_id']}")
        rows.append([r if x["action"] == "select" else "-", name, "select" if x["action"] == "select" else f"drop({x.get('drop_reason')})", x.get("reason") or ""])
    rows.sort(key=lambda r: (r[0] == "-", r[0] if r[0] != "-" else 0))
    detail = [_kv(("source", cd.get("source")), ("reconciled", "; ".join(cd.get("reconciled") or [])),
                  ("past", _dig(sj, "cluster", "past"))), _table(["순위", "후보", "판정", "이유"], rows)]
    fb = " / fallback" if cd.get("source") == "fallback" else ""
    return _step(es[0]["t"], "editor_select", [_who("llm", "editor_select", llm[0]["model"])] if llm else [_who("code")],
                 ((llm or es)[-1]["text"] or "") + fb, dur.get("select"), cost.get("editor_select"), any(s["attention"] for s in es), detail)


def _topic_blocks(db: DB, by: dict[str, list[Any]], rid: str, tid: str | None = None) -> list[dict[str, Any]]:
    """토픽 경계 = writer code 행(detail.topic_id). 그 행 이전, 직전 경계 이후의 writer·writer_revise·critic 행들이 그 토픽.
    마지막 경계 뒤에 남은 행(중단·진행 중)은 경계 없는 블록 하나로(D-20)."""
    seq = sorted((s for r in ("writer", "writer_revise", "critic") for s in by.get(r, [])), key=lambda s: s["seq"])
    revise = {s["seq"]: _j(s["output"]) for s in db.conn.execute(
        "SELECT seq, output FROM steps WHERE run_id=? AND role='writer_revise' AND output IS NOT NULL", (rid,))}
    meta = {t["topic_id"]: t for t in db.conn.execute("SELECT * FROM topics WHERE run_id=?", (rid,))}
    out, seg = [], []
    for s in seq:
        dt = _j(s["detail"]) if s["role"] == "writer" and s["kind"] == "code" else None
        if not (isinstance(dt, dict) and dt.get("topic_id")):
            seg.append(s)
            continue
        out.append(_topic(seg, dt, meta.get(dt["topic_id"]), revise, len(out) + 1))
        seg = []
    return out + ([_topic(seg, {"topic_id": tid or "-"}, None, revise, len(out) + 1)] if seg else [])


def _topic(seg: list[Any], dt: dict[str, Any], t: Any, revise: dict[int, Any], n: int) -> dict[str, Any]:
    status = t["status"] if t else None
    rounds = dt.get("rounds") or []
    rejects = [x for x in rounds if x["status"] == "reject"]
    fixed = {c["loc"]: c["action"] for s in seg for c in (revise.get(s["seq"]) or {}).get("changed") or []}
    chain: list[list[str]] = []
    k = 0
    for s in seg:
        if s["kind"] == "code":
            chain.append(["code", "stopped"])
            continue
        if s["role"] == "writer_revise":
            rj = rejects[k] if k < len(rejects) else None
            if rj and rj["checker"] == "code":
                chain.append(["code", f"반려 {len(rj['issues'])}"])
            k += 1
        chain.append([s["role"], s["text"] or ""])
    chain.append(["code", (status or "-") + (f" {len(dt['checks'])}" if dt.get("checks") else "")])
    llm = [s for s in seg if s["kind"] == "llm"]
    issues = [[i["loc"], i["type"], i["comment"], fixed.get(i["loc"], "-")] for x in rounds for i in x.get("issues") or []]
    return {"rank": t["rank"] if t else n, "title": (t["title"] if t and t["title"] else dt["topic_id"]), "topic_id": dt["topic_id"], "status": status,
            "final_round": t["final_round"] if t else None, "tokens_in": sum(s["tokens_in"] or 0 for s in llm),
            "tokens_out": sum(s["tokens_out"] or 0 for s in llm), "cost_usd": round(sum(s["cost_usd"] or 0 for s in llm), 4), "chain": chain, "issues": issues}


def _s_write(db: DB, by: dict[str, list[Any]], rid: str, sj: dict[str, Any], dur: dict[str, Any], cost: dict[str, Any],
             tid: str | None = None) -> dict[str, Any] | None:
    rows = [s for r in ("writer", "writer_revise", "critic") for s in by.get(r, [])]
    if not rows:
        return None
    topics = _topic_blocks(db, by, rid, tid)
    rev = _dig(sj, "review") or {}
    rounds = ", ".join(f"{k} ×{v}" for k, v in (rev.get("rounds") or {}).items() if v)
    line = " / ".join([f"topics {len(topics)}"] + ([f"rounds {rounds}"] if rounds else []) +
                      [f"{k} {rev[k]}" for k in ("code_rejects", "critic_rejects", "check_topics") if k in rev])
    if tid:  # 토픽 1개 run: review는 주 누적치(NG-6)라 경계 행이 없어도 쓰지 않고 이 run의 토픽 블록으로
        t = topics[0]
        cr = sum(c[0] == "code" and c[1].startswith("반려") for c in t["chain"])
        line = (f"topics 1 / rounds {'-' if t['final_round'] is None else t['final_round']} / code_rejects {cr} / "
                f"critic_rejects {sum(c[0] == 'writer_revise' for c in t['chain']) - cr} / check_topics {int(t['status'] == 'checked')}")
    who = [_who("llm", r, llm[0]["model"], len(llm)) for r in ("writer", "critic", "writer_revise")
           if (llm := [s for s in by.get(r, []) if s["kind"] == "llm"])]
    c = sum(cost.get(k) or 0 for k in ("writer", "writer_revise", "critic"))
    return _step(min(s["t"] for s in rows), "writer ⇄ critic", who, line, dur.get("write_review"), c, any(s["attention"] for s in rows),
                 [{"type": "topics", "items": topics}] if topics else [])


def _s_end(by: dict[str, list[Any]], dur: dict[str, Any], cost: dict[str, Any]) -> dict[str, Any] | None:
    end = next((s for s in reversed(by.get("weekly", [])) if "duration_sec" in (_j(s["detail"]) or {})), None)
    return _step(end["t"], "weekly 끝", [_who("code")], end["text"] or "", dur.get("total"), cost.get("total"),
                 detail=[_kv(*dur.items())]) if end else None


# ---------- nightly run 1건(5.2-3) ----------
def _day_runs(subs: list[Any], days: list[str]) -> dict[tuple[str, str], list[Any]]:
    """plan 하위 run(노트의 날짜)을 날의 기준점으로, 그 뒤에 시작한 run을 그날에 짝짓는다(하루치 단계가 여러 날일 때)."""
    plans = sorted((s for s in subs if s["kind"] == "plan"), key=lambda s: s["started_at"])
    anchors = [(p["started_at"], (re.search(r"\d{4}-\d\d-\d\d", p["note"] or "") or [days[min(i, len(days) - 1)]])[0]) for i, p in enumerate(plans)]
    out: dict[tuple[str, str], list[Any]] = {}
    for s in subs:
        day = next((dd for at, dd in reversed(anchors) if at <= s["started_at"]), days[0])
        out.setdefault((s["kind"], day), []).append(s)
    return out


def _q(db: DB, sql: str, runs: list[Any], *args: Any) -> list[Any]:
    """sql의 `IN (?)` 자리에 runs의 id를 넣어 실행한다."""
    return db.conn.execute(sql.replace("(?)", f"({','.join('?' * len(runs))})"), (*(r["id"] for r in runs), *args)).fetchall()


def _agg(db: DB, runs: list[Any], expr: str, where: str = "") -> Any:
    """하위 run들의 steps 행에 대한 집계 하나(run이 없으면 None)."""
    return _q(db, f"SELECT {expr} FROM steps WHERE run_id IN (?){where}", runs)[0][0] if runs else None


def _b_collect(db: DB, runs: list[Any], day: str | None, days: list[str]) -> tuple:
    rows = _q(db, "SELECT source_id, status, n_new FROM fetch_log WHERE run_id IN (?) ORDER BY n_new DESC, source_id", runs)
    zero = [r["source_id"] for r in rows if not r["n_new"] and r["status"] == "ok"]
    items = [f"{r['source_id']} {r['n_new']}" + ("" if r["status"] == "ok" else f" ({r['status']})") for r in rows if r["n_new"] or r["status"] != "ok"]
    items += [f"{', '.join(zero)} 0"] if zero else []
    return [_who("code")], f"new {sum(r['n_new'] for r in rows)} / sources {len(rows)} / failed {sum(r['status'] != 'ok' for r in rows)}", [{"type": "list", "items": items}], False


def _b_filter(db: DB, runs: list[Any], day: str | None, days: list[str]) -> tuple:
    q = "SELECT {0}, COUNT(*) FROM items WHERE day BETWEEN ? AND ? AND {0} IS NOT NULL GROUP BY 1 ORDER BY 2 DESC, 1"
    status = db.conn.execute(q.format("filter_status"), (min(days), max(days))).fetchall()
    reason = db.conn.execute(q.format("filter_reason"), (min(days), max(days))).fetchall()
    text = _q(db, "SELECT text, attention FROM steps WHERE run_id IN (?) ORDER BY seq", runs)
    return ([_who("code")], text[0]["text"] if text else "", [_kv(("filter_status", " / ".join(f"{a} {b}" for a, b in status)),
                                                                ("filter_reason", " / ".join(f"{a} {b}" for a, b in reason)))], False)


def _b_summarize(db: DB, runs: list[Any], day: str | None, days: list[str]) -> tuple:
    r = _q(db, "SELECT COUNT(*) n, SUM(tokens_in) ti, SUM(tokens_out) to_, SUM(cost_usd) c, SUM(attention) a, MAX(model) m FROM steps "
               "WHERE run_id IN (?) AND kind='llm' AND role='item_card'", runs)[0]
    return ([_who("llm", "item_card", r["m"], r["n"])], f"item_card {r['n']} / attention {r['a'] or 0}",
            [_kv(("tokens_in", r["ti"]), ("tokens_out", r["to_"]), ("cost_usd", round(r["c"] or 0, 4)), ("attention", r["a"] or 0))], False)


def _plan_row(db: DB, day: str) -> Any:
    r = db.conn.execute("SELECT source, plan_json FROM plans WHERE day=? ORDER BY id DESC LIMIT 1", (day,)).fetchone()
    return (r["source"], _j(r["plan_json"]) or {}) if r else (None, {})


def _b_plan(db: DB, runs: list[Any], day: str | None, days: list[str]) -> tuple:
    source, p = _plan_row(db, day or days[0])
    if not p:
        return [_who("llm", "editor_plan")], "", [], False
    text = [f"text_queue / {_title(db, 'it:' + str(x['item_id']))} / {x.get('reason')} / depth {x.get('max_depth')}" for x in p.get("text_queue") or []]
    vid = [f"video_queue / {_title(db, 'vd:' + str(x['video_id']))} / {x.get('reason')} / {x.get('mode')}" for x in p.get("video_queue") or []]
    repo = [f"repo_queue / {x['full_name']} / {x.get('reason')}" for x in p.get("repo_queue") or []]
    line = f"text_queue {len(text)} / video_queue {len(vid)} / repo_queue {len(repo)}" + (" / fallback" if source == "fallback" else "")
    return ([_who("llm", "editor_plan", _agg(db, runs, "MAX(model)"))], line,
            [{"type": "list", "items": text + vid + repo}, _kv(("log", p.get("log")))], bool(p.get("attention")))


def _b_deep(db: DB, runs: list[Any], day: str | None, days: list[str]) -> tuple:
    rows = []
    for c in _q(db, "SELECT i.title, c.card_json, c.model FROM item_cards c JOIN items i ON i.id=c.item_id WHERE c.version=2 AND c.run_id IN (?) ORDER BY c.item_id", runs):
        card = _j(c["card_json"]) or {}
        trail = card.get("trail") or []
        rows.append([c["title"] or "-", " → ".join(k for k, _ in groupby(urlsplit(t.get("url") or "").netloc.removeprefix("www.") for t in trail)) or "-", max((t.get("depth") or 0 for t in trail), default="-"), card.get("log") or ""])
    return ([_who("agent", "text_analyst", _agg(db, runs, "MAX(model)"), len(rows))],
            f"items {len(rows)} / tool {_agg(db, runs, 'COUNT(*)', " AND kind='tool'") or 0}", [_table(["항목", "원본 추적 경로", "깊이", "대조"], rows)], False)


def _b_video(db: DB, runs: list[Any], day: str | None, days: list[str]) -> tuple:
    items = []
    for v in _q(db, "SELECT d.video_id, d.digest_json, d.model, i.title FROM video_digests d LEFT JOIN items i ON i.id=d.item_id WHERE d.run_id IN (?) ORDER BY d.created_at", runs):
        g = _j(v["digest_json"]) or {}
        span = g.get("span") or {}
        frames = db.conn.execute("SELECT COUNT(*) FROM video_frames WHERE video_id=?", (v["video_id"],)).fetchone()[0]
        items.append(" / ".join(x for x in (v["title"] or f"video {v['video_id']}", f"mode {g.get('mode')}", f"span {span.get('start')}~{span.get('end')}" if span else "",
                                            f"segments {g.get('segments_count')}", f"quality {g.get('transcript_quality')}", f"frames {frames}" if frames else "") if x))
    return [_who("agent", "video_analyst", _agg(db, runs, "MAX(model)"), len(runs) or None)], f"video {len(runs)} / digests {len(items)}", [{"type": "list", "items": items}], False


def _b_repo(db: DB, runs: list[Any], day: str | None, days: list[str]) -> tuple:
    items = []
    for c in _q(db, "SELECT full_name, card_json FROM repo_cards WHERE run_id IN (?) ORDER BY full_name", runs):
        card = _j(c["card_json"]) or {}
        one = card.get("log") or card.get("summary") or next((v for v in card.values() if isinstance(v, str)), "")
        items.append(one if one.startswith(c["full_name"]) else f"{c['full_name']} / {one}")
    return ([_who("agent", "repo_analyst", _agg(db, runs, "MAX(model)"), len(items) or None)],
            f"repos {len(items)} / tool {_agg(db, runs, 'COUNT(*)', " AND kind='tool'") or 0}", [{"type": "list", "items": items}], False)


# nightly 단계 이름 → (하위 run kind, 단계 만들기)
NIGHT: dict[str, tuple[str, Callable[..., tuple]]] = {
    "collect": ("collect", _b_collect), "filter": ("filter", _b_filter), "summarize": ("summarize", _b_summarize), "plan": ("plan", _b_plan),
    "deep_text": ("deep-text", _b_deep), "video": ("video", _b_video), "repo_analyze": ("repo-analyze", _b_repo)}


def _nightly_detail(db: DB, d: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    sj, days, r = d["_sj"], d["_days"], d["_row"]
    subs = db.conn.execute("SELECT * FROM runs WHERE spec=? AND started_at>=? AND started_at<? AND id!=? ORDER BY started_at",
                           (r["spec"], r["started_at"], _iso(r["finished_at"]) or "9", r["id"])).fetchall()
    by_day = _day_runs(subs, days)
    steps = []
    for st in sj["steps"]:
        name, day = st["name"], st.get("day")
        kind, build = NIGHT.get(name, (name, lambda *a: ([_who("code")], "", [], False)))  # 모르는 단계 이름은 line만(5.7)
        runs = by_day.get((kind, day), []) if day else [s for s in subs if s["kind"] == kind]
        who, line, detail, attention = build(db, runs, day, days)
        if not runs and name != "plan":  # 하위 run이 없으면 line만(summary_json.steps의 exit)
            who, line, detail = [{**w, "n": None} for w in who], "", []
        line = f"{line} / exit {st['exit']}" if line and st.get("exit") else line or f"exit {st['exit']}"
        label = name + (f" {_md(day)}" if day and len(days) > 1 else "")
        steps.append(_step((runs or [r])[0]["started_at"], label, who, line, st.get("sec"), sum(s["cost_usd"] or 0 for s in runs),
                           attention or bool(st.get("exit")), detail))
    if site := sj.get("site"):  # 이 스펙 뒤 run만 있음(5.1-1). 없으면 단계 생략
        steps.append(_step(r["finished_at"] or r["started_at"], "export + build", [_who("code")], f"exit {site.get('exit')}", site.get("sec"),
                           attention=bool(site.get("exit"))))
    return _night_summary(db, d, subs), steps


def _night_summary(db: DB, d: dict[str, Any], subs: list[Any]) -> dict[str, Any]:
    days = d["_days"]
    coll = [s for s in subs if s["kind"] == "collect"]
    summ = [s for s in subs if s["kind"] == "summarize"]
    plans = [_plan_row(db, x)[1] for x in days]
    keep = db.conn.execute("SELECT COUNT(*) FROM items WHERE filter_status='pass' AND day BETWEEN ? AND ?", (min(days), max(days))).fetchone()[0]
    return {"collected": _q(db, "SELECT COALESCE(SUM(n_new),0) FROM fetch_log WHERE run_id IN (?)", coll)[0][0] if coll else 0, "filter_keep": keep,
            "cards": _agg(db, summ, "COUNT(*)", " AND kind='llm' AND role='item_card'") or 0, "deep_text": sum(len(p.get("text_queue") or []) for p in plans),
            "video": sum(len(p.get("video_queue") or []) for p in plans), "repo": sum(len(p.get("repo_queue") or []) for p in plans),
            "exit_nonzero": d["result"]["failed"]}


def build_runs(db: DB, weeks: list[dict[str, Any]], week_label: Callable[[str], tuple]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(runs, run_weeks). weeks = export가 내는 주(발행 주 + with_week). 진행 주 = 그 밖에 run이 있는 주."""
    ex = {w["id"]: w for w in weeks}
    wrow = {r["week"].lower(): r for r in db.conn.execute("SELECT * FROM weeks")}
    cands = []
    for r in db.conn.execute("SELECT * FROM runs WHERE kind IN ('nightly','weekly') ORDER BY started_at DESC"):
        try:
            sj = _j(r["summary_json"]) or {}
            if r["kind"] == "weekly" and r["week"]:
                w = wrow.get(r["week"].lower())
                d = _weekly(db, r, sj, w["current_run_id"] if w else None)
            else:
                d = _nightly(r, sj) if r["kind"] == "nightly" else None
        except Exception as e:  # noqa: BLE001 - 깨진 run 1건은 그 run만 뺀다(5.7 run 단위 격리)
            print(f"export: run {r['id']} 를 뺌: {type(e).__name__}", file=sys.stderr)
            continue
        if d:
            d["_row"] = r
            cands.append(d)
    cands += _step_groups(db)
    all_weeks = set(ex) | {c["week"] for c in cands}  # 발행 주 ∪ run이 있는 주(진행 주)
    runs = sorted(cands, key=lambda c: c["at"], reverse=True)
    for d in runs:
        try:
            if d["kind"] == "weekly":
                d["summary"], d["steps"] = _weekly_detail(db, d, ex)
            elif d["kind"] == "nightly":
                d["summary"], d["steps"] = _nightly_detail(db, d)
        except Exception as e:  # noqa: BLE001 - 한 run의 원천이 이상해도 다른 run·쪽은 만든다(5.7 run 단위 격리)
            print(f"export: run {d['id']} 상세를 뺌: {type(e).__name__}", file=sys.stderr)
            d["summary"], d["steps"] = None, []
    run_weeks = [_run_week(wk, ex, wrow, runs, week_label) for wk in sorted(all_weeks, reverse=True)]
    return [{k: v for k, v in d.items() if not k.startswith("_")} for d in runs], run_weeks


def _run_week(wk: str, ex: dict[str, Any], wrow: dict[str, Any], runs: list[dict[str, Any]], week_label: Callable[[str], tuple]) -> dict[str, Any]:
    label, rng, _, _ = week_label(wk.upper())
    in_week = [r for r in runs if r["week"] == wk]
    weekly = [r for r in in_week if r["kind"] == "weekly"]
    w = wrow.get(wk)
    return {"week": wk, "label": label, "range": rng, "status": "published" if wk in ex else (w["status"] if w else "open"),
            "nightly_days": len({x for r in runs if r["kind"] == "nightly" for x in r["_days"] if _iso_week(x) == wk}),
            "weekly": {"total": len(weekly), "full": sum(not r["sub"] for r in weekly), "partial": sum(1 for r in weekly if r["sub"] and not r["topic_id"]),
                       "topic": sum(1 for r in weekly if r["topic_id"])},
            "published_at": ex[wk]["published_at"] if wk in ex else None, "current_run_id": w["current_run_id"] if w else None}
