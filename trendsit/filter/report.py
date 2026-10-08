"""필터 검증 산출물(reports/S2_filter/, COMMON 10장)과 사람 라벨 파일(eval/labels/relevance.csv).

리뷰어가 모델을 돌리지 않고 파일만 보고 판단할 수 있게: 실행 환경, 점수 분포, 판정 CSV, 문턱값 근처 사례,
되살린 글과 떨어뜨린 글, 시드 라벨 13건 결과, 유사 쌍 상위 N, 재현 명령.
"""

from __future__ import annotations

import csv
import json
import platform
from pathlib import Path
from typing import Any

from ..core.config import FilterConfig, labeler_info
from ..core.db import DB
from .embed import FilterResult, library_versions, similar_pairs

BIN = 0.05


def _cell(text: Any) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def _norm_title(t: str) -> str:
    return " ".join((t or "").split()).lower()


def seed_results(rows: list[dict[str, Any]], seed_csv: Path) -> list[dict[str, Any]]:
    """relevance_seed.csv(소스 + 제목)로 항목을 찾아 판정과 비교. 시드 제목은 잘려 있을 수 있어 앞부분 일치로 찾는다."""
    out = []
    with seed_csv.open(encoding="utf-8") as f:
        for s in csv.DictReader(f):
            want = _norm_title(s["title"])
            hit = next((r for r in rows if r["source"] == s["source"] and
                        (_norm_title(r["title"]).startswith(want) or want.startswith(_norm_title(r["title"])))), None)
            out.append({**s, "found": hit is not None, "id": hit["id"] if hit else None,
                        "score": hit["score"] if hit else None, "decision": hit["decision"] if hit else None,
                        "correct": (hit["decision"] == s["expected"]) if hit else None})
    return out


def distribution(rows: list[dict[str, Any]]) -> list[tuple[str, int, int]]:
    """0.05 구간별 건수(키워드 통과 / 걸러짐)."""
    if not rows:
        return []
    lo = int(min(r["score"] for r in rows) // BIN)
    hi = int(max(r["score"] for r in rows) // BIN)
    out = []
    for b in range(lo, hi + 1):
        a, z = b * BIN, (b + 1) * BIN
        inside = [r for r in rows if a <= r["score"] < z or (b == hi and r["score"] == z)]
        out.append((f"{a:.2f}~{z:.2f}", sum(r["keyword_status"] == "pass" for r in inside),
                    sum(r["keyword_status"] != "pass" for r in inside)))
    return out


def write_report(db: DB, cfg: FilterConfig, res: FilterResult, out_dir: Path, seed_csv: Path,
                 command: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = res.rows
    with (out_dir / "decisions.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "source", "channel", "title", "keyword_status", "keyword_reason",
                                          "score", "keyword_id", "decision", "reason"])
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: -r["score"]))
    seeds = seed_results(rows, seed_csv)
    found = [s for s in seeds if s["found"]]
    correct = sum(1 for s in found if s["correct"])
    keep_ids = [r["id"] for r in rows if r["decision"] == "keep" and r["channel"] == "text"]
    pairs = similar_pairs(db, res.model, keep_ids, cfg.similar_pairs)
    title = {r["id"]: r for r in rows}
    near = sorted((r for r in rows if not r["keyword_reason"].startswith("excluded:")),
                  key=lambda r: min(abs(r["score"] - cfg.drop_below), abs(r["score"] - cfg.rescue_above)))[:20]
    same = db.conn.execute(
        "SELECT s.item_id, s.canonical_id, s.reason, a.source_id sa, a.title ta, b.source_id sb, b.title tb "
        "FROM item_same_as s JOIN items a ON a.id = s.item_id JOIN items b ON b.id = s.canonical_id "
        f"WHERE s.item_id IN ({','.join('?' * len(rows))}) ORDER BY s.canonical_id",
        [r["id"] for r in rows]).fetchall() if rows else []

    status = "잠정" if cfg.thresholds_status == "provisional" else "확정"
    L = ["# S2 임베딩 필터 검증 산출물", "",
         f"> `{command}`가 만든다. 판정 목록은 `decisions.csv`(점수 내림차순). 임베딩 벡터는 git에 넣지 않는다.", "",
         "## 실행 환경", "", "| 항목 | 값 |", "|---|---|",
         f"| 모델 | `{res.model}` |", f"| 장치 | {res.device} |",
         f"| 라이브러리 | {', '.join(f'{k} {v}' for k, v in library_versions().items())}, 파이썬 {platform.python_version()} |",
         f"| 처리 건수 | {res.n}건(글 {sum(r['channel'] == 'text' for r in rows)}, 영상 {sum(r['channel'] == 'video' for r in rows)}), 새 임베딩 {res.computed} |",
         f"| 걸린 시간 | {res.seconds:.1f}초 |", f"| run_id | `{res.run_id}` |", "",
         f"## 문턱값({status})", "",
         f"- drop_below {cfg.drop_below}, rescue_above {cfg.rescue_above}",
         f"- 근거: {cfg.thresholds_basis or '-'}", "",
         "## 판정 요약", "", "| 이유 | 건수 |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in sorted(res.decisions.items())]
    L += ["", "## 점수 분포 (0.05 구간)", "", "| 구간 | 키워드 통과 | 키워드 걸러짐 |", "|---|---|---|"]
    L += [f"| {b} | {p} | {q} |" for b, p, q in distribution(rows)]
    L += ["", f"## 시드 라벨 결과 (`{seed_csv.name}`, 찾은 {len(found)}/{len(seeds)}건 중 맞음 {correct})", "",
          "| 소스 | 제목 | 기대 | 점수 | 판정 | 맞음 |", "|---|---|---|---|---|---|"]
    for s in seeds:
        mark = "-" if not s["found"] else ("○" if s["correct"] else "×")
        L.append(f"| {s['source']} | {_cell(s['title'][:60])} | {s['expected']} | "
                 f"{s['score'] if s['found'] else '못 찾음'} | {s['decision'] or '-'} | {mark} |")
    L += ["", "- 못 찾은 행은 분모에서 뺀다(S2S3_TASK 7장)", "",
          "## 문턱값 근처 20건 (±0.05 안팎, 사람 확인용)", "",
          "| 확인 | id | 소스 | 제목 | 키워드 | 점수 | 판정 |", "|---|---|---|---|---|---|---|"]
    L += [f"| [ ] | {r['id']} | {r['source']} | {_cell(r['title'][:60])} | {r['keyword_status']} | {r['score']} | "
          f"{r['decision']}({r['reason']}) |" for r in near]
    for label, reason in (("되살린 글(rescued)", "rescued"), ("떨어뜨린 글(low_similarity)", "low_similarity")):
        picked = [r for r in rows if r["reason"] == reason]
        L += ["", f"## {label} {len(picked)}건", "", "| id | 소스 | 제목 | 점수 | 가까운 관심사 |", "|---|---|---|---|---|"]
        L += [f"| {r['id']} | {r['source']} | {_cell(r['title'][:70])} | {r['score']} | {r['keyword_id']} |"
              for r in sorted(picked, key=lambda r: -r["score"])]
    L += ["", f"## 같은 URL 연결 {len(same)}건", "", "| 경유 항목 | 기준 항목 | 공유 URL |", "|---|---|---|"]
    L += [f"| {r['item_id']} {r['sa']}: {_cell((r['ta'] or '')[:40])} | {r['canonical_id']} {r['sb']}: "
          f"{_cell((r['tb'] or '')[:40])} | {_cell(r['reason'].removeprefix('same_url:'))} |" for r in same]
    L += ["", f"## 내용이 비슷한 쌍 상위 {len(pairs)} (keep 글끼리, 합치지 않음. S5 묶기 재료)", "",
          "| 유사도 | A | B |", "|---|---|---|"]
    L += [f"| {s} | {a} {title[a]['source']}: {_cell(title[a]['title'][:45])} | "
          f"{b} {title[b]['source']}: {_cell(title[b]['title'][:45])} |" for s, a, b in pairs]
    L += ["", "## 재현", "", "```", "uv sync --extra embed", command,
          "uv run python -m trendsit filter-fixtures   # eval/fixtures/filter 20건 점수만(리뷰어 CPU용)", "```", ""]
    path = out_dir / "README.md"
    path.write_text("\n".join(L), encoding="utf-8")
    (out_dir / "run.json").write_text(json.dumps(
        {"run_id": res.run_id, "model": res.model, "device": res.device, "n": res.n, "computed": res.computed,
         "seconds": round(res.seconds, 2), "decisions": res.decisions, "seed_correct": correct,
         "seed_found": len(found), "seed_total": len(seeds), "drop_below": cfg.drop_below,
         "rescue_above": cfg.rescue_above, "thresholds_status": cfg.thresholds_status},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path


def make_relevance_labels(rows: list[dict[str, Any]], path: Path, n_each: int = 20) -> int:
    """라벨 40건: 키워드 통과 20, 걸러짐 20. 각 무리 안에서 점수 순으로 고르게(등간격 뽑기). expected는 라벨러가 채운다.

    이미 채운 행(같은 id)은 expected와 labeler(누가 달았나, 사람이 아니면 잠정)를 보존한다.
    """
    old: dict[str, dict[str, str]] = {}
    if path.exists():
        with path.open(encoding="utf-8") as f:
            old = {r["id"]: r for r in csv.DictReader(f)}
    picked = []
    for passed in (True, False):
        group = sorted((r for r in rows if r["channel"] == "text" and (r["keyword_status"] == "pass") == passed
                        and not r["keyword_reason"].startswith("excluded:")), key=lambda r: r["score"])
        if len(group) <= n_each:
            picked += group
        else:
            step = (len(group) - 1) / (n_each - 1)
            picked += [group[round(i * step)] for i in range(n_each)]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "source", "title", "keyword_status", "score", "decision", "expected",
                                          "labeler"])
        w.writeheader()
        for r in picked:
            prev = old.get(str(r["id"]), {})
            w.writerow({"id": r["id"], "source": r["source"], "title": r["title"], "keyword_status": r["keyword_status"],
                        "score": r["score"], "decision": r["decision"], "expected": prev.get("expected", ""),
                        "labeler": prev.get("labeler", "")})
    return len(picked)


def label_metrics(path: Path, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """채운 relevance.csv로 keep 판정의 정밀도·재현율(문턱값 근거). 빈칸은 제외."""
    if not path.exists():
        return None
    by_id = {r["id"]: r for r in rows}
    tp = fp = fn = tn = 0
    used: list[dict[str, str]] = []
    with path.open(encoding="utf-8") as f:
        for lab in csv.DictReader(f):
            exp = (lab.get("expected") or "").strip().lower()
            r = by_id.get(int(lab["id"]))
            if exp not in ("keep", "drop") or r is None:
                continue
            used.append(lab)
            got = r["decision"]
            tp += got == "keep" and exp == "keep"
            fp += got == "keep" and exp == "drop"
            fn += got == "drop" and exp == "keep"
            tn += got == "drop" and exp == "drop"
    n = tp + fp + fn + tn
    if not n:
        return None
    return {"n": n, "precision": round(tp / (tp + fp), 3) if tp + fp else None,
            "recall": round(tp / (tp + fn), 3) if tp + fn else None, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            **labeler_info(used)}
