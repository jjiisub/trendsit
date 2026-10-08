"""S2~S3 명령(COMMON 9장: cli.py에는 등록 한 줄만). register(sub)가 하위 명령을 붙인다.

첫머리에서 선택 의존성(embed 묶음)을 import하지 않는다. 쓰는 함수 안에서만.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
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
        embedder = make_embedder(args.embedder, cfg)
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
            path = write_report(db, cfg, res, FILTER_REPORT, SEED, cmd)
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
    embedder = make_embedder(args.embedder, cfg)
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
    f.add_argument("--report", action="store_true", help="reports/S2_filter/ 검증 산출물 생성")
    f.add_argument("--labels", action="store_true", help="eval/labels/relevance.csv 40건 생성(채운 expected 보존)")
    f.add_argument("--spec")
    f.set_defaults(fn=cmd_filter)

    ff = sub.add_parser("filter-fixtures", help="eval/fixtures/filter 20건 점수(장치별 비교)")
    ff.add_argument("--embedder", choices=["real", "mock"], default="real")
    ff.add_argument("--record", action="store_true")
    ff.set_defaults(fn=cmd_filter_fixtures)
