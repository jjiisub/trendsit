"""S2~S3 명령(COMMON 9장: cli.py에는 등록 한 줄만). register(sub)가 하위 명령을 붙인다.

첫머리에서 선택 의존성(embed 묶음)을 import하지 않는다. 쓰는 함수 안에서만.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

from .core import config
from .core.config import ROOT
from .core.db import DB
from .core.trace import Tracer

FILTER_REPORT = ROOT / "reports" / "S2_filter"
FILTER_FIXTURES = ROOT / "eval" / "fixtures" / "filter"
SEED = ROOT / "eval" / "labels" / "relevance_seed.csv"
RELEVANCE_LABELS = ROOT / "eval" / "labels" / "relevance.csv"


def _date(text: str | None) -> date | None:
    return date.fromisoformat(text) if text else None


def _db() -> DB:
    return DB(ROOT / "data" / "trendsit.db")


def _period(args: argparse.Namespace) -> str:
    return " ".join(f"--{k} {v}" for k, v in (("since", args.since), ("until", args.until)) if v)


# ---------- rematch ----------
def cmd_rematch(args: argparse.Namespace) -> int:
    from .filter.rematch import rematch

    db = _db()
    tracer = Tracer(db, "rematch", config.current_spec(args.spec or "S2"), note=f"rematch {_period(args)}".strip())
    res = rematch(db, config.load("keywords.yaml"), _date(args.since), _date(args.until))
    tracer.step(kind="code", role="rematch", text=res.summary(), detail=res.__dict__)
    tracer.finish("ok")
    print(res.summary())
    return 0


# ---------- filter ----------
def cmd_filter(args: argparse.Namespace) -> int:
    from .filter.embed import make_embedder, run_filter

    cfg = config.load("filter.yaml")
    db = _db()
    tracer = Tracer(db, "filter", config.current_spec(args.spec or "S2"),
                    note=f"filter {args.embedder} {_period(args)}".strip())
    status = "failed"
    try:
        embedder = make_embedder(args.embedder, cfg, args.device)
        res = run_filter(db, cfg, embedder, tracer.run_id, _date(args.since), _date(args.until))
        dropped = res.decisions.get("low_similarity", 0)
        tracer.step(kind="code", role="filter", text=res.summary(),
                    detail={k: v for k, v in res.__dict__.items() if k != "rows"},
                    attention=cfg.thresholds_status == "provisional")
        print(res.summary())
        if cfg.thresholds_status == "provisional":
            print(f"문턱값 잠정(drop_below {cfg.drop_below}, rescue_above {cfg.rescue_above}). 떨어뜨린 글 {dropped}건 확인 필요")
        if args.report:
            from .filter.report import write_report

            cmd = f"uv run python -m trendsit filter {_period(args)} --report".replace("  ", " ")
            path = write_report(db, cfg, res, FILTER_REPORT, SEED, cmd, RELEVANCE_LABELS)
            print(f"검증 산출물: {path.relative_to(ROOT)}")
        if args.labels:
            from .filter.report import make_relevance_labels

            n = make_relevance_labels(res.rows, RELEVANCE_LABELS)
            print(f"라벨 파일: {RELEVANCE_LABELS.relative_to(ROOT)} {n}행(expected에 keep/drop)")
        status = "ok"
    finally:
        tracer.finish(status)
    return 0


def load_filter_fixtures() -> list[tuple[str, dict[str, Any]]]:
    return [(p.stem, json.loads(p.read_text(encoding="utf-8"))) for p in sorted(FILTER_FIXTURES.glob("*.json"))]


def cmd_filter_fixtures(args: argparse.Namespace) -> int:
    """재현 픽스처 20건의 점수만 계산(DB 없음). --record면 장치별 점수를 reports/S2_filter/fixture_scores.json에 기록."""
    from .filter.embed import best_interest, make_embedder

    cfg = config.load("filter.yaml")
    embedder = make_embedder(args.embedder, cfg, args.device)
    interests = list(zip([x.keyword_id for x in cfg.interests],
                         embedder.embed_queries([x.text for x in cfg.interests]), strict=True))
    fx = load_filter_fixtures()
    vecs = embedder.embed_docs([f["input"]["text"] for _, f in fx])
    ref_path = FILTER_REPORT / "fixture_scores.json"
    ref = json.loads(ref_path.read_text(encoding="utf-8")) if ref_path.exists() else {}
    key = f"{embedder.model_id}@{embedder.device}"
    others = {k: v for k, v in ref.items() if k.startswith(f"{embedder.model_id}@") and k != key}
    scores, worst = {}, 0.0
    print(f"| 픽스처 | 점수({key}) | 관심사 | " + " | ".join(f"차이({k})" for k in others) + " |")
    for (fid, _), v in zip(fx, vecs, strict=True):
        s, kid = best_interest(v, interests)
        scores[fid] = s
        diffs = [abs(s - o[fid]) for o in others.values() if fid in o]
        worst = max([worst, *diffs])
        print(f"| {fid} | {s:.4f} | {kid} | " + " | ".join(f"{d:.4f}" for d in diffs) + " |")
    if others:
        print(f"다른 장치와의 최대 차이 {worst:.4f} (기준 0.001 이하)")
    if args.record:
        ref[key] = scores
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        ref_path.write_text(json.dumps(ref, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"기록: {ref_path.relative_to(ROOT)} [{key}]")
    return 0 if worst <= 0.001 else 1


# ---------- summarize (2b) ----------
def cmd_summarize(args: argparse.Namespace) -> int:
    from .core.context import open_ctx
    from .summarize import run_summarize, targets

    ctx = open_ctx("summarize", spec=args.spec or "S2", model=args.model, no_cache=args.no_cache,
                   note=f"summarize {_period(args)}".strip())
    status = "failed"
    try:
        ids = targets(ctx.db, _date(args.since), _date(args.until), redo=args.redo, limit=args.limit)
        res = run_summarize(ctx, ids, config.load("keywords.yaml"))
        ctx.tracer.step(kind="code", role="summarize", text=res.summary(), detail=res.__dict__,
                        attention=bool(res.stopped or res.fallback))
        print(res.summary())
        status = "stopped" if res.stopped else "ok"
    finally:
        ctx.tracer.finish(status)
    return 0 if status == "ok" else 1


# ---------- repo-analyze (3c) ----------
REPO_TRACES = ROOT / "reports" / "S3_traces" / "repo"


def _queue_from_file(path: str) -> list[Any]:
    from .deep.repo_agent import QueueItem

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = data.get("repo_queue", data) if isinstance(data, dict) else data
    from .tools.github import valid_name

    bad = [r["full_name"] for r in rows if not valid_name(r["full_name"])]
    if bad:
        raise config.ConfigError(Path(path).name, "full_name", f"레포 이름 형식 오류: {', '.join(bad)[:80]}")
    return [QueueItem(r["full_name"], min(max(int(r.get("max_depth", 2)), 1), 3), r.get("reason", "")) for r in rows]


def cmd_repo_analyze(args: argparse.Namespace) -> int:
    from .core.context import open_ctx
    from .deep.repo_agent import build_input, rule_queue, run_repo_analysis, write_traces

    ctx = open_ctx("repo-analyze", spec=args.spec or "S3", model=args.model, no_cache=args.no_cache,
                   note=f"repo-analyze {args.week}")
    status = "failed"
    try:
        queue = _queue_from_file(args.queue) if args.queue else rule_queue(ctx.db, args.week, args.top)
        kw = config.load("keywords.yaml")
        if args.fixtures:  # 관문 B 픽스처: 입력만 만든다(한 줄 설명이 없으면 repo_oneliner 실행)
            out = Path(args.fixtures)
            out.mkdir(parents=True, exist_ok=True)
            for q in queue:
                inp = build_input(ctx, q, args.week, kw)
                (out / f"{q.full_name.replace('/', '__')}.json").write_text(json.dumps(
                    {"input": inp.model_dump(), "expect": {}, "note": f"{args.week} 트렌딩, {q.reason}"},
                    ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            print(f"픽스처 {len(queue)}개: {out}")
            status = "ok"
            return 0
        res = run_repo_analysis(ctx, queue, args.week, kw)
        ctx.tracer.step(kind="code", role="repo-analyze", text=res.summary(),
                        detail={k: v for k, v in res.__dict__.items() if k != "traces"},
                        attention=bool(res.stopped or res.fallback))
        print(res.summary())
        if args.traces:
            paths = write_traces(res.traces, REPO_TRACES, f"uv run python -m trendsit repo-analyze --week {args.week}")
            print(f"검증 산출물 {len(paths)}개: {REPO_TRACES.relative_to(ROOT)}")
        status = "stopped" if res.stopped else "ok"
    finally:
        ctx.tracer.finish(status)
    return 0 if status == "ok" else 1


# ---------- plan (3a) ----------
PLAN_REPORT = ROOT / "reports" / "S3_plan.md"
PLAN_LABELS = ROOT / "eval" / "labels" / "editor_plan_mode.csv"  # 영상 mode 동의(설계 결정 Q5). judge 라벨은 editor_plan.csv


def cmd_plan(args: argparse.Namespace) -> int:
    from .core.artifacts_text import CollectionPlan, PlanInput
    from .core.budget import BudgetExceeded, PriceUnknown
    from .core.context import open_ctx
    from .core.llm import LLMError
    from .core.role import RoleFailed, load_role, run
    from .deep import plan as P

    day = date.fromisoformat(args.day)
    if args.action == "show":
        db = _db()
        got = P.latest_plan(db, args.day)
        if got is None:
            print(f"{args.day} 계획 없음", file=sys.stderr)
            return 1
        print(json.dumps(P.video_queue_json(got) if args.video_queue else got, ensure_ascii=False, indent=2))
        return 0
    if args.action == "agreement":
        a = P.mode_agreement(PLAN_LABELS)
        print(a if a else f"채운 라벨 없음: {PLAN_LABELS.relative_to(ROOT)}")
        return 0 if a else 1
    ctx = open_ctx("plan", spec=args.spec or "S3", model=args.model, no_cache=args.no_cache, note=f"plan {args.day}")
    status = "failed"
    try:
        cfg = config.load("deep.yaml")
        inp: PlanInput = P.build_plan_input(ctx, day, cfg, config.load("keywords.yaml"), hype=not args.no_hype)
        if args.fixture:
            Path(args.fixture).parent.mkdir(parents=True, exist_ok=True)
            Path(args.fixture).write_text(json.dumps({"input": inp.model_dump(), "expect": {},
                                                      "note": f"{args.day} 계획 입력(영상 {len(inp.new_videos)}, 글 "
                                                              f"{len(inp.text_candidates)}, 레포 {len(inp.repo_candidates)})"},
                                                     ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            print(f"픽스처: {args.fixture}")
            status = "ok"
            return 0
        source = "model"
        try:
            out: CollectionPlan = run(load_role("editor_plan", ctx.models), inp, ctx)  # type: ignore[assignment]
        except (RoleFailed, BudgetExceeded, LLMError, PriceUnknown) as e:
            out, source = P.fallback_plan(inp, f"{type(e).__name__}: {str(e)[:60]}"), "fallback"
            ctx.tracer.step(kind="code", role="editor_plan", text=out.log, attention=True, error=str(e),
                            output=out.model_dump(), detail={"enforced": out.enforced})
        pid = P.save_plan(ctx.db, args.day, out, source, ctx.tracer.run_id)
        print(f"계획 {pid} ({source}): 글 {len(out.text_queue)}, 영상 {len(out.video_queue)}, 레포 {len(out.repo_queue)} / {out.log}")
        if args.report:
            P.write_plan_report(inp, out, source, PLAN_REPORT, f"uv run python -m trendsit plan run --day {args.day} --report")
            print(f"검증 산출물: {PLAN_REPORT.relative_to(ROOT)}")
        if args.labels:
            n = P.make_mode_labels(inp, out.model_dump(), PLAN_LABELS)
            print(f"라벨 파일: {PLAN_LABELS.relative_to(ROOT)} {n}행(agree에 y/n)")
        status = "ok"
    finally:
        ctx.tracer.finish(status)
    return 0


# ---------- deep text (3b) ----------
TEXT_TRACES = ROOT / "reports" / "S3_traces" / "text"


def cmd_deep(args: argparse.Namespace) -> int:
    from .core.context import open_ctx
    from .deep.plan import latest_plan
    from .deep.text_agent import queue_from_plan, run_text_analysis, write_traces

    if not args.day and args.item is None:
        print("--day(계획의 text_queue) 또는 --item이 필요함", file=sys.stderr)
        return 2
    ctx = open_ctx("deep-text", spec=args.spec or "S3", model=args.model, no_cache=args.no_cache,
                   note=f"deep text {args.day or args.item}")
    status = "failed"
    try:
        if args.item is not None:
            queue = [(args.item, args.max_depth or config.load("deep.yaml").default_text_depth)]
        else:
            plan = latest_plan(ctx.db, args.day)
            if plan is None:
                print(f"{args.day} 계획 없음(plan run --day 먼저)", file=sys.stderr)
                return 1
            queue = queue_from_plan(plan)
        if args.fixtures:  # 관문 B 픽스처: 입력만 만든다
            from .deep.text_agent import build_input

            out = Path(args.fixtures)
            out.mkdir(parents=True, exist_ok=True)
            for item_id, depth in queue:
                inp = build_input(ctx.db, item_id, depth)
                (out / f"it{item_id}.json").write_text(json.dumps(
                    {"input": inp.model_dump(), "expect": {}, "note": f"{args.day or ''} 계획 text_queue, {inp.title[:40]}"},
                    ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            print(f"픽스처 {len(queue)}개: {out}")
            status = "ok"
            return 0
        res = run_text_analysis(ctx, queue)
        ctx.tracer.step(kind="code", role="deep-text", text=res.summary(),
                        detail={k: v for k, v in res.__dict__.items() if k != "traces"}, attention=bool(res.stopped))
        print(res.summary())
        if args.traces:
            cmd = f"uv run python -m trendsit deep text {'--day ' + args.day if args.day else '--item ' + str(args.item)}"
            paths = write_traces(res.traces, TEXT_TRACES, cmd)
            print(f"검증 산출물 {len(paths)}개: {TEXT_TRACES.relative_to(ROOT)}")
        status = "stopped" if res.stopped else "ok"
    finally:
        ctx.tracer.finish(status)
    return 0 if status == "ok" else 1


def register(sub: Any) -> None:
    r = sub.add_parser("rematch", help="바뀐 keywords.yaml로 저장된 항목의 키워드 판정을 다시 계산(네트워크 없음)")
    r.add_argument("--since")
    r.add_argument("--until")
    r.add_argument("--spec")
    r.set_defaults(fn=cmd_rematch)

    f = sub.add_parser("filter", help="임베딩 관련성 필터(keep/drop) + 같은 URL 연결")
    f.add_argument("--since")
    f.add_argument("--until")
    f.add_argument("--embedder", choices=["real", "mock"], default="real", help="mock: 단어 해시(개발, 테스트용)")
    f.add_argument("--device", choices=["cpu", "mps", "cuda"], help="기본: mps → cuda → cpu 자동")
    f.add_argument("--report", action="store_true", help="reports/S2_filter/ 검증 산출물 생성")
    f.add_argument("--labels", action="store_true", help="eval/labels/relevance.csv 40건 생성(채운 expected 보존)")
    f.add_argument("--spec")
    f.set_defaults(fn=cmd_filter)

    sm = sub.add_parser("summarize", help="글 1차 요약(item_card): 필터 keep이고 같은 URL 기준 항목인 글")
    sm.add_argument("--since")
    sm.add_argument("--until")
    sm.add_argument("--limit", type=int)
    sm.add_argument("--model", help="models.yaml 별칭")
    sm.add_argument("--redo", action="store_true", help="이미 v1이 있는 글도 다시")
    sm.add_argument("--no-cache", action="store_true")
    sm.add_argument("--spec")
    sm.set_defaults(fn=cmd_summarize)

    ra = sub.add_parser("repo-analyze", help="레포 분석가(repo_analyst): 규칙 기반 큐 또는 --queue 파일")
    ra.add_argument("--week", required=True, help="ISO 주차(예: 2026-W41)")
    ra.add_argument("--top", type=int, default=10)
    ra.add_argument("--queue", help="큐 JSON(편집장 계획의 repo_queue 또는 [{full_name, max_depth, reason}])")
    ra.add_argument("--fixtures", help="실행하지 않고 관문 B 픽스처(입력)만 이 폴더에")
    ra.add_argument("--traces", action="store_true", help="reports/S3_traces/repo/ 검증 산출물")
    ra.add_argument("--model")
    ra.add_argument("--no-cache", action="store_true")
    ra.add_argument("--spec")
    ra.set_defaults(fn=cmd_repo_analyze)

    pl = sub.add_parser("plan", help="편집장 계획(editor_plan): run(실행) / show(보기) / agreement(영상 mode 동의율)")
    pl.add_argument("action", nargs="?", choices=["run", "show", "agreement"], default="run")
    pl.add_argument("--day", required=True, help="YYYY-MM-DD(이날 포함 최근 lookback_days의 후보)")
    pl.add_argument("--video-queue", action="store_true", help="show: CONTRACTS 1장 형식 JSON 배열(S4 입력)")
    pl.add_argument("--report", action="store_true", help="reports/S3_plan.md")
    pl.add_argument("--labels", action="store_true", help="eval/labels/editor_plan_mode.csv(영상 mode 동의)")
    pl.add_argument("--fixture", help="실행하지 않고 관문 B 픽스처(입력)만 이 파일에")
    pl.add_argument("--no-hype", action="store_true", help="레포 과열 규칙 API를 부르지 않음")
    pl.add_argument("--model")
    pl.add_argument("--no-cache", action="store_true")
    pl.add_argument("--spec")
    pl.set_defaults(fn=cmd_plan)

    dp = sub.add_parser("deep", help="깊게 보기: text(글 분석가, 원본 추적)")
    dp.add_argument("what", choices=["text"])
    dp.add_argument("--day", help="이날 계획(plan)의 text_queue")
    dp.add_argument("--item", type=int, help="한 항목만(items.id)")
    dp.add_argument("--max-depth", type=int, help="--item일 때 깊이(기본 deep.yaml default_text_depth)")
    dp.add_argument("--traces", action="store_true", help="reports/S3_traces/text/ 검증 산출물")
    dp.add_argument("--fixtures", help="실행하지 않고 관문 B 픽스처(입력)만 이 폴더에")
    dp.add_argument("--model")
    dp.add_argument("--no-cache", action="store_true")
    dp.add_argument("--spec")
    dp.set_defaults(fn=cmd_deep)

    ff = sub.add_parser("filter-fixtures", help="eval/fixtures/filter 20건 점수(장치별 비교)")
    ff.add_argument("--embedder", choices=["real", "mock"], default="real")
    ff.add_argument("--record", action="store_true")
    ff.add_argument("--device", choices=["cpu", "mps", "cuda"])
    ff.set_defaults(fn=cmd_filter_fixtures)
