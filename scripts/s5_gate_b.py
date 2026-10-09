"""S5 관문 B: 대상 주(W40 + W41) 실제 실행 결과를 표로 + 2차 라벨 시트(D1-3, 리뷰 세션 opus-5.5가 채움).

역할 픽스처 평가(`trendsit eval writer|critic|editor_select|writer_revise`)가 reports/S5_quality.md를 만든 뒤에 돌린다.
이 스크립트는 그 파일 끝에 "실제 실행(W40 + W41)" 절을 붙이고, 라벨 시트를 만든다(이미 채운 칸은 보존).
- 묶기: 2채널 이상 토픽 비율, 묶인 쌍 목록(오병합 라벨용 eval/labels/decide.csv는 묶기 리포트 때 만듦)
- 선별: 실제 실행의 코드 검증 통과(첫 시도), drop 이유 표 → eval/labels/editor_select.csv
- 작성·검수: 토픽별 라운드·상태·check·원자 사실(judge_facts는 writer 평가에서) → eval/labels/critic.csv(라운드별 판정)
- 표현 선택: 토픽별 도식(있음/없음)과 코드 경고 → eval/labels/diagram_labels.json(needed_numbers/needed_events 빈칸)
- 문체: 최종판 코드 정규식 위반 수

실행: uv run python scripts/s5_gate_b.py --weeks 2026-W40 2026-W41
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trendsit.brief import checks  # noqa: E402
from trendsit.core.artifacts_brief import TopicPage  # noqa: E402
from trendsit.core.db import DB  # noqa: E402
from trendsit.core.style import EVAL_ENDINGS, ends_as_sentence, is_haeyo  # noqa: E402

LABELS = ROOT / os.environ.get("S5_LABELS", "eval/labels")  # 1차 라벨 스냅숏: eval/labels/s5_r1
KEEP = ("label", "critique", "labeler")


def merge_csv(path: Path, key: tuple[str, ...], cols: list[str], rows: list[dict]) -> None:
    old = {}
    if path.exists():
        with path.open(encoding="utf-8") as f:
            old = {tuple(r.get(k, "") for k in key): r for r in csv.DictReader(f)}
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            prev = old.get(tuple(str(r[k]) for k in key), {})
            w.writerow(r | {k: prev.get(k, "") for k in KEEP})


def style_violations(page: TopicPage) -> list[str]:
    out = []
    for loc, text in [("summary", page.summary), ("overview", page.overview),
                      *[(f"points[{i}]", p.text) for i, p in enumerate(page.points)]]:
        t = checks.plain(text)
        if any(is_haeyo(s) for s in checks.sentences(t)) or any(e in t for e in EVAL_ENDINGS):
            out.append(f"{loc} 해요체·평가형")
        if loc.startswith("points") and ends_as_sentence(t):
            out.append(f"{loc} 명사형 아님")
        if loc in ("summary", "overview") and t and not t.rstrip(".").endswith("다"):
            out.append(f"{loc} '~다' 아님")
    return out


def judge_final(weeks: list[str], only: set[str] | None = None, prev: dict | None = None) -> dict:
    """두 주 현재판 최종 페이지를 judge(질문 Q1~Q4) + 원자 사실 judge로 채점. 작성자가 받은 입력을 같은 코드로 다시 조립."""
    from eval import graders
    from scripts.s5_eval_fixtures import week_topics
    from trendsit.brief.write import evidence_docs, previous_topic, raw_evidence
    from trendsit.core import config
    from trendsit.core.artifacts import Document
    from trendsit.core.artifacts_brief import PlanBrief, Relation, WriterInput
    from trendsit.core.context import open_ctx

    cfg = config.load("brief.yaml")
    ctx = open_ctx("eval", spec="S5", note="관문 B 최종판 judge(W40 + W41)")
    out = dict(prev or {})
    try:
        for w in weeks:
            for t in week_topics(ctx.db, w, cfg):
                if t["page"] is None or t["status"] not in ("passed", "checked"):
                    continue
                tp = t["topic"]
                if only and tp.topic_id not in only:
                    continue
                inp = WriterInput(plan=PlanBrief(rank=tp.rank, angle=tp.angle,
                                                 relation=Relation(type=tp.relation_type, topic_id=tp.relation_topic_id)),
                                  evidence=evidence_docs(t["pack"]), previous=previous_topic(ctx.db, tp.relation_topic_id),
                                  aliases=t["aliases"])
                # judge 입력은 근거 원문(COMMON 2: 요약 칸이 아니라). 작성자 입력과 같은 id, 글자는 검수자와 같은 원문
                raw = [Document(id=d.id, source=d.source, title=d.title, url=d.url,
                                text=raw_evidence(ctx.db, d.id, t["pack"][d.id])) for d in inp.evidence]
                r = graders.llm_grade("writer", inp.model_copy(update={"evidence": raw}), t["page"].model_dump(), ctx)
                out[tp.topic_id] = {"week": w, "status": t["status"], "verdicts": r["verdicts"], "scores": r["scores"],
                                    "facts": r.get("facts")}
                print(tp.topic_id, {q: v["verdict"] for q, v in r["verdicts"].items()},
                      f"{r['facts']['supported']}/{r['facts']['total']}" if r.get("facts") else "", file=sys.stderr)
    finally:
        ctx.tracer.finish("ok")
    path = ROOT / "reports" / "S5_brief" / "gate_b_final_judge.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def _rows(name: str) -> list[dict]:
    with (LABELS / name).open(encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if (r.get("labeler") or "").strip()]


def agreement(judge: dict) -> list[str]:
    """2차 라벨(D1-3) 기준 관문 B와 judge ↔ 라벨 일치율. 라벨이 단 출력(라벨 시트의 실행)에 대해서만."""
    qs = ("Q0", "Q1", "Q2", "Q3", "Q4")
    w = _rows("writer.csv")
    lines = ["| 항목 | 라벨 기준 | 문턱값 | 판정 | judge ↔ 라벨 일치 |", "|---|---|---|---|---|"]
    names = {"Q0": "근거 충실성", "Q1": "Q1 핵심", "Q2": "Q2 군더더기", "Q3": "Q3 읽기 쉬움", "Q4": "Q4 문체"}
    both = 0
    for q in qs:
        lab = {r["topic_id"]: r[f"{q}_pass"] == "pass" for r in w if r[f"{q}_pass"]}
        if q == "Q0":
            jd = {k: v["facts"]["supported"] == v["facts"]["total"] for k, v in judge.items() if v.get("facts")}
        else:
            jd = {k: v["verdicts"].get(q, {}).get("verdict") == "pass" for k, v in judge.items()}
        ok = sum(lab.values())
        agree = sum(lab[k] == jd[k] for k in lab if k in jd)
        need = 1.0 if q == "Q0" else 0.9
        lines.append(f"| {names[q]} | {ok}/{len(lab)} | {'모든 토픽' if q == 'Q0' else '90%'} | "
                     f"{'통과' if lab and ok / len(lab) >= need else '미달'} | {agree}/{sum(k in jd for k in lab)} |")
    lab_all = {r["topic_id"]: r["label"] == "pass" for r in w}
    jd_all = {k: all(x.get("verdict") == "pass" for x in v["verdicts"].values())
              and v["facts"]["supported"] == v["facts"]["total"] for k, v in judge.items() if v.get("facts")}
    both = sum(lab_all[k] == jd_all[k] for k in lab_all if k in jd_all)
    lines.append(f"| writer 종합(label) | {sum(lab_all.values())}/{len(lab_all)} | - | - | {both}/{len(lab_all)} |")
    c = _rows("critic.csv")
    ok = sum(r["label"] == "pass" for r in c)
    lines.append(f"| 검수(실제 판정이 맞음) | {ok}/{len(c)} ({ok / len(c):.0%}) | 80% | {'통과' if ok / len(c) >= .8 else '미달'} | - |")
    dcs = _rows("decide.csv")
    agree = sum(r["label"] == r["answer"] for r in dcs)
    wrong = sum(1 for r in dcs if r["answer"] == "same" and r["label"] == "diff")
    lines.append(f"| decide | {agree}/{len(dcs)}, 오병합 {wrong} | 오병합 0 | {'통과' if wrong == 0 else '미달'} | - |")
    al = _rows("aliases.csv")
    ok = sum(r["label"] == "correct" for r in al)
    lines.append(f"| 정규화 | {ok}/{len(al)} | 90%, 오병합 0 | {'통과' if al and ok / len(al) >= .9 else '미달'} | - |")
    es = [r for r in _rows("editor_select.csv") if r["action"] == "drop"]
    ok = sum(r["label"] == r["drop_reason"] for r in es)
    lines.append(f"| 선별 drop 이유 | {ok}/{len(es)} | 80% | {'통과' if es and ok / len(es) >= .8 else '미달'} | - |")
    dj = json.loads((LABELS / "diagram_labels.json").read_text(encoding="utf-8"))
    lab = {k: v for k, v in dj.items() if v.get("labeler")}
    over = [k for k, v in lab.items() if len(v["numbers"]) > v["needed_numbers"] or len(v["events"]) > v["needed_events"]]
    miss = [k for k, v in lab.items() if len(v["numbers"]) < v["needed_numbers"] or len(v["events"]) < v["needed_events"]]
    lines.append(f"| 표현 선택 | 남발 {len(over)}({', '.join(over) or '-'}), 누락 {len(miss)}({', '.join(miss) or '-'}) | "
                 f"남발 0, 누락 ≤1 | {'통과' if not over and len(miss) <= 1 else '미달'} | - |")
    labelers = sorted({r["labeler"] for r in w + c + dcs})
    return ["", f"라벨: {', '.join(labelers)}(잠정, D1-3). 일치율은 \"모델 대 모델\"", "", *lines]


DECODE_TPS, PREFILL_TPS = 8.0, 15600 / 101  # 로컬 qwen3.8-27b q4 실측(S5_report 실행 시간 절)


def runtime(db: DB, runs: list[str]) -> list[str]:
    """실행 시간 분해(리뷰 R18): 역할별 호출·토큰과 로컬 추정(디코딩 8 tok/s, 프리필 15.6k 토큰 101초).
    캐시 적중 호출도 센다(새 주 실행에는 캐시가 없음). OpenRouter 실측 초는 캐시 적중이면 0에 가깝다."""
    rows = db.conn.execute(
        f"SELECT role, COUNT(*) n, SUM(tokens_in) ti, SUM(tokens_out) tout, SUM(latency_ms) lat FROM steps WHERE kind='llm' "
        f"AND run_id IN ({','.join('?' * len(runs))}) GROUP BY role ORDER BY role", runs).fetchall()
    lines = ["| 역할 | 호출 | 입력 토큰 | 출력 토큰 | OpenRouter 실측(초) | 로컬 프리필(분) | 로컬 디코딩(분) | 로컬 합(분) |",
             "|---|---|---|---|---|---|---|---|"]
    tot = [0, 0, 0, 0, 0.0, 0.0]
    for r in rows:
        pre, dec = (r["ti"] or 0) / PREFILL_TPS / 60, (r["tout"] or 0) / DECODE_TPS / 60
        lines.append(f"| {r['role']} | {r['n']} | {r['ti']:,} | {r['tout']:,} | {(r['lat'] or 0) / 1000:.0f} | {pre:.1f} | "
                     f"{dec:.1f} | {pre + dec:.1f} |")
        for i, v in enumerate((r["n"], r["ti"] or 0, r["tout"] or 0, (r["lat"] or 0) / 1000, pre, dec)):
            tot[i] += v
    lines.append(f"| 합계 | {tot[0]} | {tot[1]:,} | {tot[2]:,} | {tot[3]:.0f} | {tot[4]:.1f} | {tot[5]:.1f} | "
                 f"**{tot[4] + tot[5]:.0f}** |")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weeks", nargs="+", required=True)
    ap.add_argument("--judge", action="store_true", help="최종판 judge를 새로 돌림(없으면 저장된 결과 사용)")
    ap.add_argument("--topics", nargs="*", help="--judge를 이 토픽만(나머지는 저장된 결과, E2 실패 건만 재실행)")
    ap.add_argument("--agreement", metavar="JUDGE_JSON", help="라벨 기준 관문 B와 judge ↔ 라벨 일치율만 출력")
    ap.add_argument("--runtime", nargs="+", metavar="RUN_ID", help="이 run들(묶기 run 포함)의 실행 시간 분해만 출력")
    args = ap.parse_args()
    if args.runtime:
        print("\n".join(runtime(DB(ROOT / "data" / "trendsit.db"), args.runtime)))
        return 0
    if args.agreement:
        print("\n".join(agreement(json.loads(Path(args.agreement).read_text(encoding="utf-8")))))
        return 0
    db = DB(ROOT / "data" / "trendsit.db")
    jpath = ROOT / "reports" / "S5_brief" / "gate_b_final_judge.json"
    saved = json.loads(jpath.read_text()) if jpath.exists() else {}
    final = judge_final(args.weeks, set(args.topics) if args.topics else None, saved if args.topics else None) \
        if args.judge else saved
    lines = ["", "## 실제 실행(" + " + ".join(args.weeks) + ", 관문 B 대상 주)", "",
             "> `scripts/s5_gate_b.py`가 붙인 절. 라벨이 필요한 항목은 2차 라벨(D1-3, 리뷰 세션 opus-5.5) 전 잠정.", ""]
    sel_rows, crit_rows, diag = [], [], {}
    topics_all = []
    for week in args.weeks:
        run = db.conn.execute("SELECT current_run_id FROM weeks WHERE week=?", (week,)).fetchone()[0]
        summ = json.loads(db.conn.execute("SELECT summary_json FROM runs WHERE id=?", (run,)).fetchone()[0] or "{}")
        cluster_run = summ.get("cluster_run") or run
        topics = db.conn.execute("SELECT * FROM topics WHERE run_id=? ORDER BY rank", (run,)).fetchall()
        sel_step = db.conn.execute("SELECT detail FROM steps WHERE role='editor_select' AND kind='code' AND run_id IN "
                                   "(SELECT id FROM runs WHERE week=? AND kind='weekly') ORDER BY id DESC LIMIT 1",
                                   (week,)).fetchone()
        sel_detail = json.loads(sel_step["detail"]) if sel_step else {}
        plan_run = run
        prow = db.conn.execute("SELECT plan_json, source FROM briefing_plans WHERE run_id=?", (plan_run,)).fetchone()
        plan = json.loads(prow["plan_json"]) if prow else {}
        lines += [f"### {week} (run `{run}`, 묶기 run `{cluster_run}`)", "",
                  f"- 실행 요약: 토픽 {summ.get('write', {}).get('topics')}, 실패 {summ.get('write', {}).get('failed')}, "
                  f"라운드 {summ.get('review', {}).get('rounds')}, 코드 반려 {summ.get('review', {}).get('code_rejects')}, "
                  f"검수 반려 {summ.get('review', {}).get('critic_rejects')}, 되돌림 {summ.get('review', {}).get('reverts')}, "
                  f"check 포인트 {summ.get('review', {}).get('check_points')}, 사용액 ${summ.get('cost_usd', {}).get('total')}, "
                  f"시간 {summ.get('duration_sec', {}).get('total')}초",
                  f"- 선별: 첫 시도 코드 검증 {'통과' if sel_detail.get('errors_by_try', [[1]])[0] == [] else '실패'}"
                  f"({len(sel_detail.get('errors_by_try', []))}회 시도, 계획 {prow['source'] if prow else '-'}), "
                  f"reason 입력 대조 위반 {len(sel_detail.get('reason_mismatch', []))}", ""]
        for d in plan.get("decisions", []):
            sel_rows.append({"week": week, "cluster_id": d["cluster_id"], "action": d["action"],
                             "drop_reason": d.get("drop_reason") or "", "reason": d["reason"]})
        lines += ["| 순위 | 토픽 | 상태 | 라운드 | 채널 | 도식(수치·사건) | 코드 경고 | 문체 위반 | check |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for t in topics:
            page_row = db.conn.execute("SELECT page_json FROM topic_pages WHERE run_id=? AND topic_id=? ORDER BY round DESC, "
                                       "id DESC LIMIT 1", (run, t["topic_id"])).fetchone()
            vs = db.conn.execute("SELECT round, checker, status, issues_json, autofix_json FROM verdicts WHERE run_id=? AND "
                                 "topic_id=? ORDER BY id", (run, t["topic_id"])).fetchall()
            for v in vs:
                if v["checker"] == "critic":
                    crit_rows.append({"week": week, "topic_id": t["topic_id"], "round": v["round"], "status": v["status"],
                                      "issues": json.dumps([{k: i[k] for k in ("loc", "type", "comment")}
                                                            for i in json.loads(v["issues_json"] or "[]")], ensure_ascii=False)})
            if page_row is None:
                lines.append(f"| {t['rank']} | {t['topic_id']} | {t['status']} | - | - | - | - | - | - |")
                continue
            page = TopicPage.model_validate_json(page_row[0])
            warn = [w for v in vs for w in json.loads(v["autofix_json"] or "{}").get("warnings") or []]
            chans = sorted({r["channel"] for r in db.conn.execute(
                "SELECT DISTINCT ci.channel FROM cluster_items ci WHERE ci.cluster_id IN (SELECT value FROM json_each(?))",
                (t["cluster_ids_json"],))})
            sv = style_violations(page)
            topics_all.append((week, t, page, chans, sv))
            diag[t["topic_id"]] = {"week": week, "numbers": [g.title for g in page.numbers],
                                   "events": [g.title for g in page.events], "code_warnings": sorted(set(warn)),
                                   "needed_numbers": None, "needed_events": None, "labeler": None, "critique": None}
            lines.append(f"| {t['rank']} | {t['topic_id']} | {t['status']} | {t['final_round']} | {'+'.join(chans)} | "
                         f"{len(page.numbers)}·{len(page.events)} | {len(set(warn))} | {len(sv)} | "
                         f"{sum(p.check for p in page.points)} |")
        lines.append("")
    n = len(topics_all)
    multi = sum(1 for _, _, _, c, _ in topics_all if len(c) >= 2)
    style = sum(len(sv) for *_, sv in topics_all)
    qs = ("Q1", "Q2", "Q3", "Q4")
    qrate = {q: (sum(1 for v in final.values() if v["verdicts"].get(q, {}).get("verdict") == "pass"),
                 sum(1 for v in final.values() if q in v["verdicts"])) for q in qs}
    facts = [(k, v["facts"]) for k, v in final.items() if v.get("facts")]
    full = sum(1 for _, f in facts if f["supported"] == f["total"])
    lines += ["### 최종판 judge(관문 B, `reports/S5_brief/gate_b_final_judge.json`)", "",
              "| 토픽 | 상태 | Q1 | Q2 | Q3 | Q4 | 원자 사실 | 비지지 |", "|---|---|---|---|---|---|---|---|"]
    for k, v in final.items():
        f = v.get("facts") or {}
        un = "; ".join(f"{u['loc']} {u['fact'][:40]}" for u in (f.get("unsupported") or [])[:2])
        lines.append(f"| {k} | {v['status']} | " + " | ".join(v["verdicts"].get(q, {}).get("verdict", "-") for q in qs)
                     + f" | {f.get('supported')}/{f.get('total')} | {un} |")
    for k, v in final.items():
        for q in qs:
            if v["verdicts"].get(q, {}).get("verdict") == "fail":
                lines.append(f"- {k} {q}: {v['verdicts'][q]['critique'][:200]}")
    lines += ["", "### 관문 B 항목(실제 실행)", "",
              "| 항목 | 결과 | 문턱값 | 판정 |", "|---|---|---|---|",
              f"| 근거 충실성(원자 사실, 토픽별) | {full}/{len(facts)} 토픽 100% | 모든 토픽 100% | "
              f"{'통과(잠정)' if facts and full == len(facts) else '미달(잠정)'} |"]
    for q, name, need in (("Q1", "핵심 포착", .9), ("Q2", "군더더기 없음", .9), ("Q3", "읽기 쉬움", .9), ("Q4", "문체(번역투)", .9)):
        p_, n_ = qrate[q]
        lines.append(f"| {name}({q}) | {p_}/{n_} | {need:.0%} | {'통과(잠정)' if n_ and p_ / n_ >= need else '미달(잠정)'} |")
    lines += [
              f"| 문체(코드 정규식, 최종판) | 위반 {style}건 | 0 | {'통과' if style == 0 else '미달'} |",
              f"| 묶기: 2채널 이상 토픽 비율 | {multi}/{n} | 기록 | - |",
              "| 묶기 오병합 | 라벨 대기(`eval/labels/decide.csv`) | 0 | 잠정 |",
              "| 정규화 | 라벨 대기(`eval/labels/aliases.csv`) | 정확도 90%, 오병합 0 | 잠정 |",
              "| 선별 drop 이유 | 라벨 대기(`eval/labels/editor_select.csv`) | 일치 80% | 잠정 |",
              "| 검수 | 라벨 대기(`eval/labels/critic.csv`), 심은 오류 픽스처는 위 critic 절 | 일치 80% | 잠정 |",
              "| 표현 선택 | 라벨 대기(`eval/labels/diagram_labels.json`) | 남발 0, 누락 20개 중 1 이하 | 잠정 |", ""]
    path = ROOT / "reports" / "S5_quality.md"
    text = path.read_text(encoding="utf-8") if path.exists() else "# S5 품질 리포트 (관문 B)\n"
    marker = "\n## 실제 실행("
    if marker in text:
        text = text[: text.index(marker)]
    path.write_text(text.rstrip("\n") + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    LABELS.mkdir(parents=True, exist_ok=True)
    merge_csv(LABELS / "editor_select.csv", ("week", "cluster_id"),
              ["week", "cluster_id", "action", "drop_reason", "reason", *KEEP], sel_rows)
    merge_csv(LABELS / "critic.csv", ("week", "topic_id", "round"),
              ["week", "topic_id", "round", "status", "issues", *KEEP], crit_rows)
    wrows = [{"topic_id": k, "week": v["week"], "status": v["status"],
              **{f"judge_{q}": v["verdicts"].get(q, {}).get("verdict", "") for q in ("Q1", "Q2", "Q3", "Q4")},
              "judge_facts": f"{(v.get('facts') or {}).get('supported')}/{(v.get('facts') or {}).get('total')}",
              **{f"{q}_pass": "" for q in ("Q0", "Q1", "Q2", "Q3", "Q4")}} for k, v in final.items()]
    if wrows:  # 최종판 라벨(Q0 = 근거 충실성: 모든 문장이 근거로 받쳐지나). 2차 라벨(D1-3)이 채움
        merge_csv(LABELS / "writer.csv", ("topic_id",), list(wrows[0]) + list(KEEP), wrows)
    dpath = LABELS / "diagram_labels.json"
    old = json.loads(dpath.read_text(encoding="utf-8")) if dpath.exists() else {}
    for k, v in diag.items():
        for f in ("needed_numbers", "needed_events", "labeler", "critique"):
            if old.get(k, {}).get(f) is not None:
                v[f] = old[k][f]
    dpath.write_text(json.dumps(diag, ensure_ascii=False, indent=1), encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
