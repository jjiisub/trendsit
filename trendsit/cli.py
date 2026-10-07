"""python -m trendsit <명령>"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .core import config
from .core.budget import BudgetExceeded, PriceUnknown
from .core.config import ROOT, ConfigError
from .core.context import open_ctx
from .core.db import DB
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
    n_roles = len(list((root / "roles").glob("*.md")))
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
                                  detail={"replay_of": step_id, "alias": alias},
                                  prompt_hash=step["prompt_hash"])
    if out is not None:
        return out.model_dump()
    return {"content": res.content, "tool_calls": res.tool_calls}


# ---------- eval ----------
def cmd_eval(args: argparse.Namespace) -> int:
    from eval.run_eval import run_eval

    report = run_eval(args.role, model=args.model, limit=args.limit, spec=args.spec, no_cache=args.no_cache,
                      note=args.note)
    s = report["summary"]
    print(f"{report['role']} / {report['model_alias']} ({report['model_id']}): 코드 통과 {s['code_pass']}/{s['n']}")
    for c, v in s["criteria"].items():
        print(f"  {c}: 평균 {v['avg']}, 1점 {v['ones']}개 (n={v['n']})")
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


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="trendsit")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check-config", help="설정 네 파일과 역할 정의 검증")
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
    e.set_defaults(fn=cmd_eval)

    k = sub.add_parser("cost", help="스펙별, 모델별 사용액과 남은 예산")
    k.add_argument("--spec")
    k.set_defaults(fn=cmd_cost)

    t = sub.add_parser("trace", help="실행 1건의 걸음 목록")
    t.add_argument("run_id")
    t.set_defaults(fn=cmd_trace)

    args = p.parse_args(argv)
    try:
        return args.fn(args)
    except ConfigError as e:
        print(f"FAIL {e.file}: {e.path or '(최상위)'}: {e.reason}", file=sys.stderr)
        return 1
