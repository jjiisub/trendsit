"""S3 3a 편집장 계획: 입력 조립(세 채널의 깊이 1 결과 + 예산), validate_plan(코드), 규칙 기반 대체 계획, 저장과 보기.

validate_plan은 CollectionPlan.enforce에서 불린다(스키마 검증 뒤, 저장 전). 바꾼 것은 step detail의 enforced와 log에 남는다.
"""

from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from ..collect.text import iso_week
from ..core import config
from ..core.artifacts_text import (
    CollectionPlan,
    PlanBudget,
    PlanInput,
    RepoCandidate,
    RepoQueueItem,
    TextCandidate,
    TextQueueItem,
    VideoCandidate,
    VideoQueueItem,
)
from ..core.config import MAX_DEPTH_ALL, DeepConfig, labeler_info
from ..core.db import DB, now_kst

REPO_CANDIDATES = 20  # 계획 입력에 넣는 레포 후보 수 상한
DESCRIPTION_HEAD = 300


# ---------- 입력 조립 ----------
def window(day: date, cfg: DeepConfig) -> tuple[str, str]:
    return (day - timedelta(days=cfg.lookback_days - 1)).isoformat(), day.isoformat()


def video_candidates(db: DB, day: date, cfg: DeepConfig) -> list[VideoCandidate]:
    lo, hi = window(day, cfg)
    out = []
    for r in db.conn.execute(
            "SELECT i.id, i.title, i.published_at, t.text AS description, v.video_id, v.duration_sec, "
            "v.manual_sub_langs, v.has_auto_sub, v.chapters_json FROM items i JOIN videos v ON v.item_id=i.id "
            "LEFT JOIN item_texts t ON t.item_id=i.id WHERE i.channel='video' AND i.day BETWEEN ? AND ? "
            "AND v.video_id NOT IN (SELECT video_id FROM video_digests) "  # 이미 digest가 있는 영상은 다시 올리지 않음
            "ORDER BY i.published_at DESC, i.id", (lo, hi)):
        if not r["video_id"]:
            continue
        out.append(VideoCandidate(
            video_id=r["video_id"], item_id=r["id"], title=r["title"] or "",
            duration_min=round(r["duration_sec"] / 60, 1) if r["duration_sec"] else None,
            manual_sub_langs=json.loads(r["manual_sub_langs"] or "[]"),
            has_auto_sub=None if r["has_auto_sub"] is None else bool(r["has_auto_sub"]),
            description_head=(r["description"] or "")[:DESCRIPTION_HEAD], published=r["published_at"],
            chapters=len(json.loads(r["chapters_json"] or "[]"))))
    return out


def text_candidates(db: DB, day: date, cfg: DeepConfig) -> list[TextCandidate]:
    """ItemCard v1 중 needs_original=true인 글(아직 v2가 없는 것)."""
    lo, hi = window(day, cfg)
    out = []
    for r in db.conn.execute(
            "SELECT i.id, i.title, i.source_id, c.card_json FROM items i JOIN item_cards c ON c.item_id=i.id "
            "AND c.version=1 WHERE i.day BETWEEN ? AND ? AND i.id NOT IN (SELECT item_id FROM item_cards WHERE version=2) "
            "ORDER BY i.id", (lo, hi)):
        card = json.loads(r["card_json"])
        if not card.get("needs_original"):
            continue
        links = db.conn.execute("SELECT kind FROM links WHERE item_id=? ORDER BY id", (r["id"],)).fetchall()
        kinds = [links[n - 1]["kind"] or "기타" for n in card.get("origin_candidates", []) if 0 < n <= len(links)]
        out.append(TextCandidate(item_id=r["id"], title=r["title"] or "", source=r["source_id"],
                                 relevance=card.get("relevance", "low"),
                                 needs_original_reason=card.get("needs_original_reason", ""),
                                 origin_link_kinds=list(dict.fromkeys(kinds))))
    return out


def repo_candidates(ctx: Any, day: date, *, hype: bool = True) -> list[RepoCandidate]:
    """3c 규칙 기반 큐의 후보 + 수치 + 과열 규칙(hype=False면 API를 부르지 않음)."""
    from .repo_agent import hype_check, rule_queue, trending_stats

    week = iso_week(day)
    done = {r[0] for r in ctx.db.conn.execute("SELECT full_name FROM repo_cards WHERE week=?", (week,))}
    out = []
    # 이미 그 주 카드가 있는 레포는 뺀 뒤 앞 REPO_CANDIDATES개(뺀 자리를 다음 후보가 채움)
    for q in [q for q in rule_queue(ctx.db, week, 1000) if q.full_name not in done][:REPO_CANDIDATES]:
        st = trending_stats(ctx.db, week, q.full_name)
        h = None
        if hype:
            r = ctx.db.conn.execute("SELECT readme_head FROM repos WHERE full_name=?", (q.full_name,)).fetchone()
            h = hype_check(ctx, q.full_name, st, r["readme_head"] if r else None)
        out.append(RepoCandidate(
            full_name=q.full_name, rank=st.rank if st else None, forks=st.forks if st else None,
            stars_this_week=st.stars_this_week if st else None,
            stars_total=st.stars_total if st else None, language=st.language if st else None,
            description=st.description if st else None,
            tracked_release=q.reason.removeprefix("추적 레포 릴리스: ") if q.reason.startswith("추적") else None,
            hype_flags=h.flags if h else [], force_check=h.force_check if h else False))
    return out


def budget_of(cfg: DeepConfig) -> PlanBudget:
    """영상 구간·프레임 상한은 실제로 자르는 video.yaml 값(deep.yaml에는 없음)."""
    video = config.load("video.yaml")
    own = {k: getattr(cfg, k) for k in PlanBudget.model_fields if k not in ("video_max_minutes", "frames_per_slide_video")}
    return PlanBudget(**own, video_max_minutes=video.max_span_sec // 60,
                      frames_per_slide_video=video.modes.whisper_slides.frames_cap)


def build_plan_input(ctx: Any, day: date, cfg: DeepConfig, keywords: config.KeywordsConfig, *,
                     hype: bool = True) -> PlanInput:
    return PlanInput(day=day.isoformat(), new_videos=video_candidates(ctx.db, day, cfg),
                     repo_candidates=repo_candidates(ctx, day, hype=hype),
                     text_candidates=text_candidates(ctx.db, day, cfg),
                     keywords=[k.canonical for k in keywords.keywords], budget=budget_of(cfg), recent_topics=[])


# ---------- validate_plan (코드) ----------
def video_minutes(v: VideoQueueItem, cand: VideoCandidate | None, max_minutes: int) -> float:
    """처리할 분. skip은 0. 처리 구간이 없으면 처음부터 최대 max_minutes분."""
    if v.mode == "skip":
        return 0.0
    total = cand.duration_min if cand and cand.duration_min is not None else float(max_minutes)
    start = (v.start_sec or 0) / 60
    end = v.end_sec / 60 if v.end_sec is not None else min(total, start + max_minutes)
    return max(0.0, min(end, total) - start)


def usage(plan: CollectionPlan, inp: PlanInput) -> dict[str, tuple[float, float]]:
    """예산 항목별 (사용, 예산)."""
    b = inp.budget
    vids = {v.video_id: v for v in inp.new_videos}
    slides = sum(1 for v in plan.video_queue if v.mode == "whisper+slides")
    return {"영상 분": (round(sum(video_minutes(v, vids.get(v.video_id), b.video_max_minutes) for v in plan.video_queue), 1),
                      b.video_minutes),
            "슬라이드 영상": (slides, b.slide_videos),
            "판독 프레임": (slides * b.frames_per_slide_video, b.vlm_frames),
            "글 분석": (len(plan.text_queue), b.text_items),
            "레포 분석": (len(plan.repo_queue), b.repo_items)}


def validate_plan(plan: CollectionPlan, inp: PlanInput) -> CollectionPlan:
    """없는 id 제거, 깊이 자르기, 예산 합계를 넘는 꼬리를 우선순위 뒤에서부터 잘라 냄, 80%를 넘으면 attention."""
    b = inp.budget
    notes: list[str] = []
    out = plan

    # 1) 없는 id, 중복
    def keep_known(items: list[Any], key: str, known: set[Any], label: str) -> list[Any]:
        seen, kept = set(), []
        for x in items:
            k = getattr(x, key)
            if k not in known:
                notes.append(f"없는 {label} {k} 제거")
            elif k in seen:
                notes.append(f"중복 {label} {k} 제거")
            else:
                seen.add(k)
                kept.append(x)
        return kept

    tq = keep_known(out.text_queue, "item_id", {t.item_id for t in inp.text_candidates}, "글")
    vq = keep_known(out.video_queue, "video_id", {v.video_id for v in inp.new_videos}, "영상")
    rq = keep_known(out.repo_queue, "full_name", {r.full_name for r in inp.repo_candidates}, "레포")

    # 2) 깊이: max_text_depth와 전체 상한 4로
    cap = min(b.max_text_depth, MAX_DEPTH_ALL)
    clipped = []
    for t in tq:
        if t.max_depth > cap:
            notes.append(f"글 {t.item_id} 깊이 {t.max_depth}→{cap}")
            t = t.model_copy(update={"max_depth": cap})
        clipped.append(t)
    tq = clipped

    # 3) 예산 꼬리 자르기(우선순위 뒤에서부터)
    vids = {v.video_id: v for v in inp.new_videos}
    kept_v: list[VideoQueueItem] = []
    minutes = slides = 0.0
    for v in vq:
        m = video_minutes(v, vids.get(v.video_id), b.video_max_minutes)
        s = 1 if v.mode == "whisper+slides" else 0
        if minutes + m > b.video_minutes or slides + s > b.slide_videos or (slides + s) * b.frames_per_slide_video > b.vlm_frames:
            notes.append(f"영상 {v.video_id}({v.mode}, {m:.0f}분) 예산 초과로 잘림")
            continue
        minutes, slides = minutes + m, slides + s
        kept_v.append(v)
    if len(tq) > b.text_items:
        notes += [f"글 {t.item_id} 예산 초과로 잘림" for t in tq[b.text_items:]]
        tq = tq[:b.text_items]
    if len(rq) > b.repo_items:
        notes += [f"레포 {r.full_name} 예산 초과로 잘림" for r in rq[b.repo_items:]]
        rq = rq[:b.repo_items]

    for field_name, value, rule in (("text_queue", tq, "validate_plan: 글 큐"), ("video_queue", kept_v, "validate_plan: 영상 큐"),
                                    ("repo_queue", rq, "validate_plan: 레포 큐")):
        out = out.fix(field_name, value, rule)
    over = [f"{k} {u:g}/{t:g}" for k, (u, t) in usage(out, inp).items() if t and u > t * b.plan_share]
    if notes:
        out = out.fix("log", f"{out.log} / 잘림·정리: {'; '.join(notes)}"[:500], "validate_plan: 잘라 낸 항목 기록")
    if over and not out.attention:
        out = out.fix("attention", True, f"계획이 예산의 {b.plan_share:.0%}를 넘음({', '.join(over)})")
    return out


# ---------- 규칙 기반 대체 계획 ----------
def fallback_plan(inp: PlanInput, reason: str) -> CollectionPlan:
    """수동 자막 → captions, 없으면 whisper, slides 0편, 레포는 이번 주 별 상위, 글은 relevance high만 기본 깊이."""
    videos = [VideoQueueItem(reason="규칙: 수동 자막 있음" if v.manual_sub_langs else "규칙: 수동 자막 없음, 로컬 전사",
                             video_id=v.video_id, mode="captions" if v.manual_sub_langs else "whisper")
              for v in inp.new_videos]
    repos = sorted(inp.repo_candidates, key=lambda r: -(r.stars_this_week or 0))
    repo_q = [RepoQueueItem(reason=f"규칙: 이번 주 별 {r.stars_this_week}", full_name=r.full_name, max_depth=2)
              for r in repos]
    text_q = [TextQueueItem(reason="규칙: relevance high, 기본 깊이", item_id=t.item_id,
                            max_depth=inp.budget.default_text_depth)
              for t in inp.text_candidates if t.relevance == "high"]
    plan = CollectionPlan(text_queue=text_q, video_queue=videos, repo_queue=repo_q,
                          log=f"규칙 기반 대체 계획({reason})", attention=True)
    return validate_plan(plan, inp)


# ---------- 저장, 보기 ----------
def save_plan(db: DB, day: str, plan: CollectionPlan, source: str, run_id: str | None) -> int:
    with db.conn:
        cur = db.conn.execute("INSERT INTO plans(day, run_id, source, plan_json, created_at) VALUES (?,?,?,?,?)",
                              (day, run_id, source, json.dumps(plan.model_dump(), ensure_ascii=False), now_kst()))
    return int(cur.lastrowid)


def latest_plan(db: DB, day: str) -> dict[str, Any] | None:
    r = db.conn.execute("SELECT plan_json, source, run_id FROM plans WHERE day=? ORDER BY id DESC LIMIT 1", (day,)).fetchone()
    return None if r is None else {**json.loads(r["plan_json"]), "_source": r["source"], "_run_id": r["run_id"]}


def video_queue_json(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """CONTRACTS 1장 형식(S4 video run --queue 입력): video_id, mode, start_sec, end_sec, reason."""
    return [{k: v[k] for k in ("video_id", "mode", "start_sec", "end_sec", "reason")} for v in plan["video_queue"]]


def write_plan_report(inp: PlanInput, plan: CollectionPlan, source: str, path: Path, command: str) -> Path:
    """검증 산출물(reports/S3_plan.md): 영상별 길이·자막·mode·reason, 글·레포 큐, 예산 사용, 잘린 항목."""
    vq = {v.video_id: v for v in plan.video_queue}
    L = [f"# S3 편집장 계획 검증 산출물 ({inp.day}, {source})", "", f"> `{command}`가 만든다.", "",
         "## 예산 사용(계획 / 예산)", "", "| 항목 | 계획 | 예산 | 비율 |", "|---|---|---|---|"]
    for k, (u, t) in usage(plan, inp).items():
        L.append(f"| {k} | {u:g} | {t:g} | {u / t:.0%} |" if t else f"| {k} | {u:g} | 0 | - |")
    L += ["", f"## 영상 {len(inp.new_videos)}편 (사람 확인: mode에 동의하면 체크)", "",
          "| 동의 | video_id | 제목 | 길이(분) | 수동 자막 | 자동 자막 | 챕터 | mode | reason |", "|---|---|---|---|---|---|---|---|---|"]
    for v in inp.new_videos:
        q = vq.get(v.video_id)
        L.append(f"| [ ] | {v.video_id} | {v.title[:50].replace('|', '/')} | {v.duration_min} | "
                 f"{', '.join(v.manual_sub_langs) or '없음'} | {v.has_auto_sub} | {v.chapters} | "
                 f"{q.mode if q else '(큐에 없음)'} | {(q.reason if q else '-').replace('|', '/')} |")
    L += ["", "## 글 큐", "", "| item_id | 깊이 | reason |", "|---|---|---|"]
    L += [f"| {t.item_id} | {t.max_depth} | {t.reason} |" for t in plan.text_queue]
    L += ["", "## 레포 큐", "", "| 레포 | 깊이 | reason |", "|---|---|---|"]
    L += [f"| {r.full_name} | {r.max_depth} | {r.reason} |" for r in plan.repo_queue]
    L += ["", "## log와 enforce(잘림·정리)", "", f"- log: {plan.log}", f"- attention: {plan.attention}"]
    L += [f"- {e['field']}: {e['rule']}" for e in plan.enforced]
    L.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L), encoding="utf-8")
    return path


def make_mode_labels(inp: PlanInput, plan: dict[str, Any], path: Path) -> int:
    """editor_plan 라벨: 영상마다 mode 동의/비동의(agree 칸, y/n). 채운 값은 같은 video_id·mode면 보존."""
    old: dict[tuple[str, str], dict[str, str]] = {}
    if path.exists():
        with path.open(encoding="utf-8") as f:
            old = {(r["video_id"], r["mode"]): r for r in csv.DictReader(f)}
    vq = {v["video_id"]: v for v in plan["video_queue"]}
    cols = ["video_id", "title", "duration_min", "manual_sub_langs", "has_auto_sub", "mode", "reason", "agree", "note",
            "labeler"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for v in inp.new_videos:
            q = vq.get(v.video_id, {"mode": "(큐에 없음)", "reason": ""})
            prev = old.get((v.video_id, q["mode"]), {})
            w.writerow({"video_id": v.video_id, "title": v.title, "duration_min": v.duration_min,
                        "manual_sub_langs": " ".join(v.manual_sub_langs), "has_auto_sub": v.has_auto_sub,
                        "mode": q["mode"], "reason": q["reason"], "agree": prev.get("agree", ""), "note": prev.get("note", ""),
                        "labeler": prev.get("labeler", "")})
    return len(inp.new_videos)


def mode_agreement(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if (r.get("agree") or "").strip()]
    yes = sum(1 for r in rows if r["agree"].strip().lower() in ("y", "yes", "o", "1", "동의", "pass", "true"))
    return {"n": len(rows), "agree": yes, "rate": round(yes / len(rows), 3) if rows else None, **labeler_info(rows)}
