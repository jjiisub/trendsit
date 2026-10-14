"""묶기 리포트(S5_TASK 5.4, COMMON 10장 검증 산출물): reports/S5_brief/cluster_<week>.md + 쌍 CSV.

멈춤 지점에서 리뷰 세션이 이 파일만 보고 문턱값·토픽 수 상한을 정할 수 있어야 한다.
"""

from __future__ import annotations

import csv
import itertools
import re
from collections import Counter
from pathlib import Path
from typing import Any

from ..core.config import ROOT
from ..core.config_brief import BriefConfig
from .aliases import differs_in_version, norm_key
from .cluster import Cluster, ClusterResult
from .evidence import RELEVANCE_RANK
from .weekly import ClusterStage

OUT = ROOT / "reports" / "S5_brief"
LABELS = ROOT / "eval" / "labels"
NEAR_TOP = 20
EDITOR_TOP = 20


def _cell(v: Any, n: int = 70) -> str:
    s = str(v if v is not None else "").replace("|", "／").replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def _combo(c: Cluster) -> str:
    return " + ".join(f"{ch} {n}" for ch, n in c.channels.items())


def histogram(values: list[float], lo: float = 0.0, step: float = 0.05) -> list[tuple[str, int]]:
    bins: Counter[int] = Counter(int((v - lo) // step) for v in values if v >= lo)
    out = []
    for i in range(min(bins, default=0), max(bins, default=-1) + 1):
        a = lo + i * step
        out.append((f"{a:.2f}~{a + step:.2f}", bins.get(i, 0)))
    return out


def suspicious(c: Cluster, res: ClusterResult) -> list[str]:
    """같은 회사 다른 제품, 숫자·버전 다른 이름이 한 묶음에 있으면 표시(이름 표기에서 숫자·크기만 다른 쌍)."""
    names = sorted({n for k in c.members for n in res.members[k].entities if n.strip()})
    out = []
    for a, b in itertools.combinations(names, 2):
        base_a, base_b = re.sub(r"[\d.]+", "", norm_key(a)), re.sub(r"[\d.]+", "", norm_key(b))
        both_numbered = bool(re.search(r"\d", a)) and bool(re.search(r"\d", b))  # 회사 ↔ 제품(Google ↔ Pixel 11)은 제외
        if both_numbered and base_a and (base_a == base_b or base_a.startswith(base_b) or base_b.startswith(base_a)) \
                and differs_in_version(a, b) and min(len(base_a), len(base_b)) >= 3:
            out.append(f"{a} ↔ {b}")
    return out[:6]


def write_cluster_report(stage: ClusterStage, cfg: BriefConfig, note: str = "") -> Path:
    res, ev, table = stage.result, stage.evidence, stage.aliases
    week = res.week
    OUT.mkdir(parents=True, exist_ok=True)
    members = res.members
    cands = res.candidates()
    singles = [c for c in cands if len(c.members) == 1]
    multi = [c for c in cands if len(c.channels) >= 2]
    three = [c for c in cands if len(c.channels) >= 3]
    th = cfg.cluster.thresholds
    n = ev.counts()
    lines = [f"# 묶기 리포트 {week}", "",
             f"> run `{stage.run_id}`. 재현: `uv run python -m trendsit cluster --week {week} --spec S5`. "
             f"문턱값은 임시값(auto {th.auto} / border {th.border}), 멈춤 지점에서 이 리포트로 확정한다.", ""]
    if note:
        lines += [f"> {note}", ""]
    lines += ["## 1. 요약", "",
              "| 항목 | 값 |", "|---|---|",
              f"| 근거 자격 구성원 | 글 {n['text']}, 영상 {n['video']}, 레포 {n['github']} |",
              f"| 제외 | 카드 없는 글 {ev.excluded['no_card']}, digest 없는 영상 {ev.excluded['no_digest']}, "
              f"관련 없는 레포 {ev.excluded['irrelevant_repo']} |",
              f"| 묶음 | {len(res.clusters)}개(토픽 후보 {len(cands)}, 레포만 {len(res.clusters) - len(cands)}) |",
              f"| 2채널 이상 / 3채널 | {len(multi)} / {len(three)} |",
              f"| 1개짜리 묶음 비율(토픽 후보 중) | {len(singles)}/{len(cands)} = "
              f"{(len(singles) / len(cands) if cands else 0):.0%} |",
              f"| decide | 묶기 {res.decide_calls}회 + 별칭 {res.alias_decide_calls}회 / 상한 {cfg.cluster.decide.max_calls_per_week}, "
              f"상한으로 못 부른 후보 {res.capped_decides} |",
              f"| 크기 상한({cfg.cluster.max_cluster_size})으로 막힌 합치기 | {len(res.blocked_size)} |",
              f"| 걸린 시간(초) | {stage.seconds} |", ""]
    combos = Counter(_combo(c).split(" ")[0] if len(c.channels) == 1 else " + ".join(c.channels) for c in cands)
    lines += ["### 채널 조합 분포(토픽 후보)", "", "| 조합 | 묶음 수 |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in combos.most_common()] + [""]

    # 유사도 분포
    same = [p.sim for p in res.pairs if not p.cross]
    cross = [p.sim for p in res.pairs if p.cross]
    lines += ["## 2. 유사도 분포 (문턱값 근거)", "",
              f"전체 쌍 {len(res.pairs)}(같은 채널 {len(same)}, 채널 넘음 {len(cross)}). 0.05 구간별 쌍 수. "
              "글은 본문 임베딩(관련성 필터), 영상은 digest 요약, 레포는 oneliner + description 임베딩이라 채널을 넘는 유사도는 "
              "같은 채널보다 낮게 나오는 경향이 있다.", "",
              "| 구간 | 같은 채널 | 채널 넘음 | 표시 |", "|---|---|---|---|"]
    hs, hc = dict(histogram(same, 0.3)), dict(histogram(cross, 0.3))
    for b in sorted(set(hs) | set(hc)):
        lo = float(b.split("~")[0])
        mark = "auto 이상" if lo >= th.auto else ("border~auto(decide)" if lo >= th.border else "")
        lines.append(f"| {b} | {hs.get(b, 0)} | {hc.get(b, 0)} | {mark} |")
    lines.append("")

    # 묶음 목록
    lines += ["## 3. 묶음 목록 (토픽 후보, 점수 순)", "",
              "점수 = 관련성 먼저(최고 relevance, 그 등급 항목 수) → 채널 수 → 근거 수. 묶인 이유: seed(첫 항목), "
              "embed(같은 채널 auto 이상), decide(판정 same). sim은 묶음 나머지와의 평균 유사도.", ""]
    for c in sorted([x for x in cands if len(x.members) > 1], key=lambda c: -c.score):
        lines += [f"### c{c.id} {_cell(c.label, 60)} ({_combo(c)}, 점수 {c.score})", ""]
        if c.shared.get("names") or c.shared.get("keywords"):
            lines.append(f"- 공유: 이름 {c.shared.get('names') or '-'}, 키워드 {c.shared.get('keywords') or '-'}")
        flag = suspicious(c, res)
        if flag:
            lines.append(f"- **의심**: {', '.join(flag)}")
        lines += ["", "| 구성원 | 채널 | relevance | 제목 | 묶인 이유 | sim |", "|---|---|---|---|---|---|"]
        for k in c.members:
            m = members[k]
            how, s = c.joined[k]
            lines.append(f"| {k} | {m.channel} | {m.relevance} | {_cell(m.title, 60)} | {how} | {s if s is not None else '-'} |")
        lines.append("")
    lines += ["### 1개짜리 토픽 후보", "", "| 묶음 | 구성원 | 채널 | relevance | 제목 | 점수 |", "|---|---|---|---|---|---|"]
    for c in sorted(singles, key=lambda c: -c.score):
        m = members[c.members[0]]
        lines.append(f"| c{c.id} | {m.key} | {m.channel} | {m.relevance} | {_cell(m.title, 60)} | {c.score} |")
    lines.append("")
    repo_only = [c for c in res.clusters if c.repo_only]
    if repo_only:
        lines += ["### 레포만 있는 묶음(토픽 후보 아님, 홈 레포 목록)", ""]
        lines += [f"- c{c.id}: {', '.join(c.members)}" for c in repo_only] + [""]

    # decide 판정
    decided = sorted([p for p in res.pairs if p.decided], key=lambda p: -p.sim)
    lines += ["## 4. decide 판정", "", f"{len(decided)}건. confidence {cfg.cluster.decide.min_confidence} 미만은 묶지 않음.", "",
              "| a | b | 채널 넘음 | sim | 공유 | answer | conf | reason |", "|---|---|---|---|---|---|---|---|"]
    for p in decided:
        share = ", ".join(p.shared_names[:3] + p.shared_kw[:2]) or "-"
        lines.append(f"| {p.a} {_cell(members[p.a].title, 30)} | {p.b} {_cell(members[p.b].title, 30)} | "
                     f"{'예' if p.cross else ''} | {p.sim} | {_cell(share, 40)} | {'same' if p.same else 'diff'} | "
                     f"{p.confidence} | {_cell(p.reason, 80)} |")
    lines.append("")

    # 경계 근처(묶이지 않은 쌍 중 유사도 상위)
    owner = {k: c.id for c in res.clusters for k in c.members}
    near = sorted([p for p in res.pairs if owner[p.a] != owner[p.b]], key=lambda p: -p.sim)[:NEAR_TOP]
    lines += ["## 5. 경계 근처 상위 20쌍 (묶이지 않은 쌍, 묶였어야 할 것 같은지 확인)", "",
              "| a | b | 채널 넘음 | sim | 경로 | 판정 | 공유 |", "|---|---|---|---|---|---|---|"]
    for p in near:
        verdict = (("same" if p.same else "diff") + f" {p.confidence}") if p.decided else "-"
        share = ", ".join(p.shared_names[:3] + p.shared_kw[:2]) or "-"
        lines.append(f"| {p.a} {_cell(members[p.a].title, 35)} | {p.b} {_cell(members[p.b].title, 35)} | "
                     f"{'예' if p.cross else ''} | {p.sim} | {p.route} | {verdict} | {_cell(share, 40)} |")
    lines.append("")

    # border 아래에서 이름을 공유하는 쌍(문턱값을 낮추면 decide로 갈 후보)
    below = sorted([p for p in res.pairs if owner[p.a] != owner[p.b] and p.route == "none" and p.shared_names
                    and th.border - 0.10 <= p.sim < th.border], key=lambda p: -p.sim)[:NEAR_TOP]
    lines += [f"### border 아래({th.border - 0.10:.2f}~{th.border:.2f})에서 이름을 공유하는 쌍 상위 {NEAR_TOP}", "",
              "문턱값을 낮추면 decide로 갈 후보. 같은 대상인데 여기 있으면 border를 낮출 근거다.", "",
              "| a | b | 채널 넘음 | sim | 공유 이름 |", "|---|---|---|---|---|"]
    for p in below:
        lines.append(f"| {p.a} {_cell(members[p.a].title, 35)} | {p.b} {_cell(members[p.b].title, 35)} | "
                     f"{'예' if p.cross else ''} | {p.sim} | {_cell(', '.join(p.shared_names[:4]), 40)} |")
    lines.append("")

    # 의심 병합
    sus = [(c, suspicious(c, res)) for c in cands if len(c.members) > 1]
    sus = [(c, s) for c, s in sus if s]
    lines += ["## 6. 의심 병합 (숫자·버전·크기만 다른 이름이 한 묶음)", ""]
    ok = set(cfg.cluster.reviewed_suspicious)

    def mark(items: list[str]) -> str:
        return ", ".join(f"{x}(확인 완료: 비교 대상으로 언급된 이전 버전)" if x in ok else x for x in items)

    lines += [f"- c{c.id} {_cell(c.label, 50)}: {mark(s)}" for c, s in sus] or ["- 없음"]
    lines.append("")

    # 과거 대조
    past = [c for c in cands if c.past]
    lines += ["## 7. 과거 대조 후보", ""]
    if past:
        lines += ["| 묶음 | 지난 토픽 | 주 | 유사도 |", "|---|---|---|---|"]
        for c in past:
            for p in c.past:
                lines.append(f"| c{c.id} {_cell(c.label, 40)} | {p['topic_id']} {_cell(p['title'], 40)} | {p['week']} | {p['similarity']} |")
    else:
        lines.append("- 지난 토픽 없음(첫 실행): 모든 묶음이 new 후보")
    lines.append("")

    # 별칭 표
    rows = [r for r in table.rows if r.keyword_id is None]
    lines += ["## 8. 별칭 표 (keywords.yaml 별칭 제외)", "",
              f"자동 승인 {sum(r.reason.startswith('표기 차이') for r in rows)}, 후보 {sum(r.status == 'candidate' for r in rows)}, "
              f"decide로 승인 {sum(r.status == 'approved' and 'decide' in r.reason for r in rows)}, "
              f"거절 {sum(r.status == 'rejected' for r in rows)}", "",
              "| 정본 | 별칭 | status | 이유 | 나온 곳 |", "|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (r.status, r.canonical))[:80]:
        lines.append(f"| {_cell(r.canonical, 30)} | {_cell(r.alias, 30)} | {r.status} | {_cell(r.reason, 60)} | "
                     f"{_cell(', '.join(r.evidence[:3]), 40)} |")
    lines.append("")

    # 편집장 입력 후보
    top = sorted(cands, key=lambda c: -c.score)[:EDITOR_TOP]
    high = [c for c in cands if min(RELEVANCE_RANK.get(members[k].relevance, 3) for k in c.members) == 0]
    lines += ["## 9. 편집장 입력 후보와 토픽 수 상한 근거", "",
              f"- 편집장 입력: 점수 상위 {len(top)}개(상한 {cfg.select.max_candidates}). 입력 순서는 cluster_id 고정",
              f"- 관심 주제 후보(relevance high 항목이 있는 묶음): {len(high)}개",
              f"- 2채널 이상 묶음: {len(multi)}개",
              f"- 토픽 수 설정: min {cfg.select.topics.min} / max {cfg.select.topics.max}(멈춤 지점에서 max 10 확정)", ""]
    top_ch = Counter(ch for c in top for ch in c.channels)
    over = [f"{ch} {n}/{len(top)}" for ch, n in top_ch.items() if n > len(top) / 2 and len(top) >= 2]
    lines += [f"- **한 채널이 입력의 절반을 넘음**: {', '.join(over)}" if over else
              f"- 입력 채널 분포: {', '.join(f'{ch} {n}' for ch, n in top_ch.items())}(절반 넘는 채널 없음)"]
    if stage.video_relevance:
        hi = cfg.evidence.video_relevance_high
        lines.append("- 영상 relevance(digest 요약의 관련성 점수, " + f"{hi} 이상 high): " + ", ".join(
            f"{k} {v}" for k, v in sorted(stage.video_relevance.items(), key=lambda x: -x[1])))
    lines += ["",
              "| 순위 | 묶음 | 이름 | 조합 | 점수 |", "|---|---|---|---|---|"]
    for i, c in enumerate(top, 1):
        lines.append(f"| {i} | c{c.id} | {_cell(c.label, 60)} | {_combo(c)} | {c.score} |")
    lines.append("")

    path = OUT / f"cluster_{week}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    with (OUT / f"cluster_pairs_{week}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["a", "b", "cross_channel", "sim", "route", "decided", "answer", "confidence", "same_cluster", "reason"])
        for p in sorted(res.pairs, key=lambda p: -p.sim):
            if p.route == "none" and p.sim < th.border - 0.1:
                continue
            w.writerow([p.a, p.b, int(p.cross), p.sim, p.route, int(p.decided),
                        "" if p.same is None else int(p.same), p.confidence or "", int(owner[p.a] == owner[p.b]), p.reason])
    return path


def _merge_csv(path: Path, key: tuple[str, ...], cols: list[str], rows: list[dict[str, Any]], keep: tuple[str, ...],
               other_week: str | None = None) -> None:
    """라벨 시트를 다시 만들 때 이미 채운 라벨 칸(keep)은 같은 열쇠의 행에 보존하고, 새 rows에 없는 옛 행도
    지우지 않는다(S6-1 5.15-4: 재생성·weekly 재실행이 추적 중인 사람 라벨을 줄이면 안 됨). other_week는 과거
    호출 호환용으로 받되 더는 행을 거르는 데 쓰지 않는다 — 안 지우는 쪽이 늘 더 안전하다."""
    old: dict[tuple[str, ...], dict[str, str]] = {}
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                old[tuple(r.get(k, "") for k in key)] = r
    merged = dict(old)
    for r in rows:
        k = tuple(str(r[k2]) for k2 in key)
        merged[k] = r | {k2: old.get(k, {}).get(k2, "") for k2 in keep}
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in merged.values():
            w.writerow({c: r.get(c, "") for c in cols})


def write_label_sheets(stage: ClusterStage) -> list[Path]:
    """2차 라벨 시트(D1-3, 리뷰 세션이 채움): decide 판정 쌍(eval/labels/decide.csv), 별칭 표(eval/labels/aliases.csv).
    label 칸: same / diff(decide), ok / wrong(별칭). 이미 채운 칸은 보존."""
    res = stage.result
    LABELS.mkdir(parents=True, exist_ok=True)
    keep = ("label", "critique", "labeler")
    dec_cols = ["week", "a", "b", "a_title", "b_title", "cross_channel", "sim", "answer", "confidence", "reason", *keep]
    dec = [{"week": res.week, "a": p.a, "b": p.b, "a_title": res.members[p.a].title[:80], "b_title": res.members[p.b].title[:80],
            "cross_channel": int(p.cross), "sim": p.sim, "answer": "same" if p.same else "diff", "confidence": p.confidence,
            "reason": p.reason} for p in res.pairs if p.decided]
    al_cols = ["canonical", "alias", "status", "reason", "evidence", *keep]
    als = [{"canonical": r.canonical, "alias": r.alias, "status": r.status, "reason": r.reason,
            "evidence": " ".join(r.evidence[:5])} for r in stage.aliases.rows if r.keyword_id is None]
    out = [LABELS / "decide.csv", LABELS / "aliases.csv"]
    _merge_csv(out[0], ("week", "a", "b"), dec_cols, dec, keep, other_week=res.week)
    _merge_csv(out[1], ("canonical", "alias"), al_cols, als, keep)
    return out
