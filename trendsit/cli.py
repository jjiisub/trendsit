"""python -m trendsit <명령>"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .core import config
from .core.budget import BudgetExceeded, PriceUnknown
from .core.config import ROOT, ConfigError
from .core.context import open_ctx
from .core.db import DB, KST
from .core.llm import LLMError
from .core.role import Role, load_role, record_llm, role_path, run


def _print_json(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


# ---------- check-config ----------
def cmd_check_config(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else ROOT
    errors = config.check_all(root / "config")
    models = None
    try:
        models = config.load("models.yaml", root / "config")
    except ConfigError:
        pass
    if models is not None:
        from .core.role import check_roles

        errors += check_roles(models, root)
    if errors:
        for e in errors:
            print(f"FAIL {e.file}: {e.path or '(최상위)'}: {e.reason}")
        return 1
    from .core.role import role_files

    n_roles = len(role_files(root))
    print(f"OK 설정 {len(config.FILES)}개, 역할 {n_roles}개")
    return 0


# ---------- role ----------
def _read_input(raw: str) -> dict[str, Any]:
    p = Path(raw)
    data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else json.loads(raw)
    return data["input"] if isinstance(data, dict) and "input" in data and "expect" in data else data


def _find_role(name: str, models: config.ModelsConfig) -> Role:
    if role_path(name).exists():
        return load_role(name, models)
    return load_role(f"eval/{name}.md", models)  # 채점자 역할(eval/judge.md)


def cmd_role(args: argparse.Namespace) -> int:
    if args.replay is None and (not args.name or not args.input):
        print("역할 이름과 --input, 또는 --replay <step_id>가 필요함", file=sys.stderr)
        return 2
    ctx = open_ctx("role", spec=args.spec, no_cache=args.no_cache, model=args.model,
                   note=f"replay {args.replay}" if args.replay else f"role {args.name}")
    status = "failed"  # 성공으로 끝났을 때만 ok
    try:
        if args.replay is not None:
            out = _replay(ctx, args.replay, args.model)
        else:
            role = load_role(args.name, ctx.models)
            out = run(role, role.input_cls.model_validate(_read_input(args.input)), ctx).model_dump()
        _print_json(out)
        status = "stopped" if ctx.stopped else "ok"
        if ctx.stopped:
            print(ctx.stopped, file=sys.stderr)
    except (BudgetExceeded, PriceUnknown) as e:
        status = "stopped"
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
    except Exception as e:  # noqa: BLE001 - 어떤 실패든 run을 failed로 닫고 이유를 출력
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
    finally:
        ctx.tracer.finish(status)
    step = ctx.db.step(ctx.last_step_id) if ctx.last_step_id else None
    if step is not None:
        print(f"run_id={ctx.tracer.run_id} step_id={step['id']} model={step['model']} "
              f"cache_hit={step['cache_hit']} cost_usd={step['cost_usd'] or 0:.6f}"
              f"{' (추정)' if step['cost_estimated'] else ''}", file=sys.stderr)
    return 0 if status == "ok" else 1


def _replay(ctx: Any, step_id: int, model: str | None) -> Any:
    step = ctx.db.step(step_id)
    call = ctx.db.llm_call(step_id)
    if step is None or call is None:
        raise LLMError(f"재생할 LLM 호출 기록 없음: step {step_id}")
    role = _find_role(step["role"], ctx.models)
    alias = model or call["request"]["alias"]
    body = ctx.llm.retarget(call["request"]["body"], alias) if model else call["request"]["body"]
    schema = role.output_cls if body.get("response_format") else None
    res = ctx.llm.send(alias, body, schema=schema, no_cache=ctx.no_cache)
    if res.tool_calls:
        text, out = f"재생: 도구 호출 {', '.join(tc['name'] for tc in res.tool_calls)}", None
    elif res.parsed is not None:
        text, out = res.parsed.log, res.parsed
    else:
        text, out = "재생: 스키마 검증 실패", None
    ctx.last_step_id = record_llm(ctx, role, res, text=text, output=out, error=res.parse_error,
                                  attention=bool(out and out.attention),
                                  detail={"replay_of": step_id, "alias": alias, "enforce": "미적용(재생에는 입력이 없음)"},
                                  prompt_hash=step["prompt_hash"])
    if out is not None:
        return out.model_dump()
    return {"content": res.content, "tool_calls": res.tool_calls}


# ---------- eval ----------
def cmd_eval(args: argparse.Namespace) -> int:
    from eval.run_eval import agreement, make_labels, regrade, run_eval

    if args.label:
        path = make_labels(args.role, config.current_spec(args.spec))
        print(f"라벨 파일: {path.relative_to(ROOT)} (Q*_pass에 pass/fail, Q*_critique에 한 줄 비평을 채운다)")
        return 0
    if args.agreement:
        a = agreement(args.role, config.current_spec(args.spec))
        if a is None or not a["n_rows"]:
            print(f"채운 라벨 없음: eval/labels/{args.role}.csv")
            return 1
        if a.get("labelers"):
            print(f"labeler: {', '.join(a['labelers'])}" + (", 잠정(사람 라벨 아님)" if a.get("provisional") else ""))
        print(f"| 질문 | 일치 | 비교 수 | 일치율 |  (라벨 {a['n_rows']}건, {a['report']})")
        print("|---|---|---|---|")
        for q, v in a["questions"].items():
            print(f"| {q} | {v['agree']} | {v['n']} | {v['rate']} |")
        print(f"| 전체 | {a['total']['agree']} | {a['total']['n']} | {a['total']['rate']} |")
        if a.get("judged_enforced"):
            print(f"judge = enforce 후 출력, 라벨 = 원래 출력: {', '.join(a['judged_enforced'])}")
        low = [q for q, v in a["questions"].items() if v["rate"] is not None and v["rate"] < 0.8]
        if low:
            print(f"80% 미만: {', '.join(low)} → 사람 비평을 채점 프롬프트 예시로 넣고 다시 잴 것(COMMON 2장)")
        return 0

    if args.regrade:
        report = regrade(Path(args.regrade).resolve(), note=args.note)
    else:
        report = run_eval(args.role, model=args.model, limit=args.limit, spec=args.spec, no_cache=args.no_cache,
                          note=args.note)
    s = report["summary"]
    print(f"{report['role']} / {report['model_alias']} ({report['model_id']}): 코드 통과 {s['code_pass']}/{s['n']} "
          f"(enforce 후 {s['code_pass_enforced']}/{s['n']}, 통과 판정 기준 {s.get('code_pass_basis', s['code_pass'])}/{s['n']})")
    for q, v in s.get("questions", {}).items():
        print(f"  {q}: 통과 {v['pass']}/{v['n']}")
    for c, v in s["criteria"].items():
        print(f"  {c}(보고용): 평균 {v['avg']} (n={v['n']})")
    if s.get("model_agreement"):
        print("  모델 일치율(코드 소유 칸): " + ", ".join(f"{k} {v}" for k, v in s["model_agreement"].items()))
    print(f"  문턱값: {'통과' if s['passed'] else '미달 - ' + '; '.join(s['fail_reasons'])}")
    print(f"  비용 ${report['cost_usd']:.4f}, 리포트 {report['path']}, reports/{report['spec']}_quality.md")
    return 0 if not report["stopped"] else 1


# ---------- cost ----------
def cmd_cost(args: argparse.Namespace) -> int:
    ctx = open_ctx(None, spec=args.spec)
    spec = ctx.spec if args.spec else None
    rows = ctx.db.cost_by_model(spec)
    print("| 스펙 | 모델 | 호출 | 캐시 적중 | 입력 토큰 | 출력 토큰 | 사용액(달러) |")
    print("|---|---|---|---|---|---|---|")
    total = 0.0
    for r in rows:
        total += r["cost"]
        est = " (일부 추정)" if r["estimated"] else ""
        print(f"| {r['spec']} | {r['model']} | {r['calls']} | {r['cache_hits']} | {r['tokens_in']} | "
              f"{r['tokens_out']} | {r['cost']:.6f}{est} |")
    print(f"| 합계 | | | | | | {total:.6f} |")
    b = ctx.budget
    cap = b.cfg.specs.get(ctx.spec)
    print()
    print(f"- 스펙 {ctx.spec}: 기록 합 ${ctx.db.spent(ctx.spec):.6f} / 상한 ${cap:.2f}")
    if b.source == "key":
        print(f"- 단계({b.cfg.phase}) 사용액: ${b.phase_used:.6f} / 상한 ${b.cfg.phase_total_usd:.2f}, "
              f"남은 예산 ${b.cfg.phase_total_usd - b.phase_used:.6f}")
        print(f"  - 키 기준(현재 usage − 기준값 ${b.baseline:.6f}): ${b.key_phase_used:.6f}, "
              f"실행 기록 합: ${ctx.db.spent():.6f} (키 반영이 늦으면 큰 쪽 사용)")
        print(f"- 키 limit_remaining: {b.limit_remaining}")
    else:
        print(f"- 단계 사용액(실행 기록 합, 키 조회 불가): ${b.phase_used:.6f} / 상한 ${b.cfg.phase_total_usd:.2f}")
    return 0


# ---------- trace ----------
def cmd_trace(args: argparse.Namespace) -> int:
    db = DB(ROOT / "data" / "trendsit.db")
    run_row = db.run(args.run_id)
    if run_row is None:
        print(f"없는 실행: {args.run_id}", file=sys.stderr)
        return 1
    print(f"{run_row['id']} {run_row['kind']} {run_row['spec']} {run_row['status']} "
          f"${run_row['cost_usd'] or 0:.6f} {run_row['note'] or ''}")
    for s in db.steps_of(args.run_id):
        flag = " !" if s["attention"] else ""
        err = f" [오류: {s['error'][:80]}]" if s["error"] else ""
        cost = f" ${s['cost_usd']:.6f}" if s["cost_usd"] else ""
        hit = " (캐시)" if s["cache_hit"] else ""
        print(f"#{s['id']} {s['t'][11:19]} {s['role'] or '-'} {s['kind']} {s['text'] or ''}{flag}{cost}{hit}{err}")
    return 0


# ---------- 수집 (S1) ----------
def _parse_date(text: str | None) -> date | None:
    return date.fromisoformat(text) if text else None


def cmd_collect(args: argparse.Namespace) -> int:
    from .collect.run import collect

    today = datetime.now(KST).date()
    until = _parse_date(args.until) or today
    since = _parse_date(args.since) or until - timedelta(days=1)
    if since > until:
        print("--since가 --until보다 늦음", file=sys.stderr)
        return 2
    res = collect(since, until, only=args.source, no_body=args.no_body, use_http_cache=not args.no_http_cache,
                  max_items=args.max_items, spec=args.spec)
    print(f"run_id={res.run_id} 기간 {res.since}~{res.until} 요청 {res.requests}회")
    for sid, d in res.sources.items():
        if d["status"] == "failed":
            print(f"  {sid}: 실패 - {d['error']}")
        elif "n_new" in d:
            body = ", ".join(f"{k} {v}" for k, v in d.get("body", {}).items())
            print(f"  {sid}: {d['status']} 신규 {d['n_new']}(백필 {d['n_backfilled']}), 기존 {d['n_skipped']}, "
                  f"백필 페이지 {d['backfill_pages']}, 본문 [{body}]" + (" 기간 부족" if not d.get("covered") else ""))
        else:
            print(f"  {sid}: {d['status']} " + ", ".join(f"{k} {v}" for k, v in d.items()
                                                       if k not in ("status", "errors") and v))
    if res.robots_blocked:
        print(f"  robots.txt로 건너뜀 {len(res.robots_blocked)}건")
    return 1 if res.failed else 0


def cmd_items(args: argparse.Namespace) -> int:
    db = DB(ROOT / "data" / "trendsit.db")
    sql = ("SELECT i.*, (SELECT group_concat(keyword_id, ',') FROM item_keywords k WHERE k.item_id=i.id) kws "
           "FROM items i WHERE 1=1")
    params: list[Any] = []
    for col, val in (("week", args.week), ("source_id", args.source), ("filter_status", args.status)):
        if val:
            sql += f" AND i.{col}=?"
            params.append(val)
    sql += " ORDER BY i.published_at DESC LIMIT ?"
    params.append(args.limit)
    rows = db.conn.execute(sql, params).fetchall()
    for r in rows:
        print(f"{r['day']} {r['source_id']:<16} {r['filter_status']:<8} {r['body_status'] or '-':<7} "
              f"[{r['kws'] or r['filter_reason'] or ''}] {(r['title'] or '')[:80]}")
    print(f"({len(rows)}건)", file=sys.stderr)
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    from .collect.report import build

    until = _parse_date(args.until) or datetime.now(KST).date()
    since = _parse_date(args.since) or until - timedelta(days=6)
    path, verdict = build(since, until)
    print(f"{path.relative_to(ROOT)}: 트렌딩 {verdict['trending']}개, 중복 {verdict['duplicates']}, "
          f"GeekNews 원문 확보율 {verdict['origin_rate']}, 본문 미달 {verdict['body_fail'] or '없음'}")
    return 0


def _register(sub: Any, module: str) -> None:
    import importlib

    try:
        mod = importlib.import_module(f"{__package__}.{module}")
    except ModuleNotFoundError as e:
        if e.name == f"{__package__}.{module}":
            return
        raise
    mod.register(sub)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="trendsit")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check-config", help="설정 파일과 역할 정의 검증")
    c.add_argument("--root", help="config/, roles/가 있는 폴더 (기본: 저장소 루트)")
    c.set_defaults(fn=cmd_check_config)

    r = sub.add_parser("role", help="역할 1회 실행 또는 재생")
    r.add_argument("name", nargs="?")
    r.add_argument("--input", help="입력 JSON 파일 경로 또는 JSON 문자열 (픽스처 파일이면 input 칸 사용)")
    r.add_argument("--replay", type=int, metavar="STEP_ID")
    r.add_argument("--model", help="models.yaml 별칭")
    r.add_argument("--no-cache", action="store_true")
    r.add_argument("--spec")
    r.set_defaults(fn=cmd_role)

    e = sub.add_parser("eval", help="픽스처로 실행 → 채점 → 리포트")
    e.add_argument("role")
    e.add_argument("--model")
    e.add_argument("--limit", type=int)
    e.add_argument("--no-cache", action="store_true")
    e.add_argument("--spec")
    e.add_argument("--note", help="반복 기록에 남길 메모(이번 수정의 이유 등)")
    e.add_argument("--label", action="store_true", help="최근 eval 결과로 사람 라벨 CSV(eval/labels/<역할>.csv) 생성")
    e.add_argument("--agreement", action="store_true", help="사람 라벨과 judge 판정의 질문별 일치율")
    e.add_argument("--regrade", metavar="REPORT_JSON", help="저장된 eval 결과를 생성 재실행 없이 지금 규칙으로 다시 채점")
    e.set_defaults(fn=cmd_eval)

    k = sub.add_parser("cost", help="스펙별, 모델별 사용액과 남은 예산")
    k.add_argument("--spec")
    k.set_defaults(fn=cmd_cost)

    t = sub.add_parser("trace", help="실행 1건의 걸음 목록")
    t.add_argument("run_id")
    t.set_defaults(fn=cmd_trace)

    co = sub.add_parser("collect", help="기간 수집(글, 유튜브, GitHub). RSS가 짧으면 백필")
    co.add_argument("--source", help="소스 하나만(sources.yaml의 id, github_trending, github_releases)")
    co.add_argument("--since", help="시작일 YYYY-MM-DD(한국 시간, 포함). 기본: --until 하루 전")
    co.add_argument("--until", help="끝일 YYYY-MM-DD(포함). 기본: 오늘")
    co.add_argument("--no-body", action="store_true", help="본문 추출 생략(목록과 링크만)")
    co.add_argument("--no-http-cache", action="store_true", help="HTTP 캐시(ETag) 끔")
    co.add_argument("--max-items", type=int, help="개발용: 소스마다 앞의 N건만")
    co.add_argument("--spec")
    co.set_defaults(fn=cmd_collect)

    it = sub.add_parser("items", help="수집 항목 목록")
    it.add_argument("--week", help="ISO 주차(예: 2026-W40)")
    it.add_argument("--source")
    it.add_argument("--status", choices=["pass", "filtered"])
    it.add_argument("--limit", type=int, default=50)
    it.set_defaults(fn=cmd_items)

    rp = sub.add_parser("report", help="리포트 생성")
    rp.add_argument("what", choices=["collection"])
    rp.add_argument("--since")
    rp.add_argument("--until")
    rp.set_defaults(fn=cmd_report)

    # 스펙별 명령(COMMON 9장): 각 파일의 register(sub). 여기에는 등록 한 줄씩만. 없는 모듈은 건너뜀
    _register(sub, "cli_text")  # S2~S3
    _register(sub, "cli_video")  # S4

    args = p.parse_args(argv)
    try:
        return args.fn(args)
    except ConfigError as e:
        print(f"FAIL {e.file}: {e.path or '(최상위)'}: {e.reason}", file=sys.stderr)
        return 1
