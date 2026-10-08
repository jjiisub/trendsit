"""S4 검증 산출물(COMMON 10장, S4_TASK 9장): reports/S4_video/README.md + 썸네일. 맥에서 관문 B 실행 뒤.

    uv run python scripts/s4_artifacts.py reports/S4_video/queue_gateB.json

리뷰어가 API 키, 맥, 원본 영상 없이 파일만 보고 판단할 수 있게: 실행 환경, 전사 발췌, 썸네일과 판독·발화,
slide_only_facts 전체(사람 확인 칸), 포착률 확인 칸, 표기 쌍, whisper vs whisper+slides 비교, 재현 명령.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from trendsit.core.artifacts_video import FRAME_PRIORITY, MediaResult, VideoQueueItem
from trendsit.core.config import ROOT
from trendsit.core.db import DB
from trendsit.video import store

OUT = ROOT / "reports/S4_video"
THUMBS = OUT / "thumbs"
THUMB_WIDTH = 320
PER_VIDEO = 5
EXCERPT_SEC = 120


def cell(x: object) -> str:
    return str(x).replace("|", "/").replace("\n", " ")


def tc(sec: float) -> str:
    s = int(sec)
    return f"{s // 60}:{s % 60:02d}"


def thumb(media: MediaResult, frame_path: str, sec: int) -> str | None:
    src = Path(media.work_dir) / frame_path
    if not src.is_file():
        return None
    THUMBS.mkdir(parents=True, exist_ok=True)
    dst = THUMBS / f"{media.video_id}_{sec}.png"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vf", f"scale={THUMB_WIDTH}:-2",
                    "-compression_level", "9", str(dst)], check=True)
    return f"thumbs/{dst.name}"


def main(queue_path: str) -> int:
    db = DB(ROOT / "data/trendsit.db")
    items = [VideoQueueItem.model_validate(x) for x in json.loads(Path(queue_path).read_text(encoding="utf-8"))]
    rows = []
    for it in items:
        p = ROOT / "data/media" / it.video_id / "media_result.json"
        d = store.digest(db, it.video_id)
        if p.exists() and d is not None:
            rows.append((it, MediaResult.model_validate_json(p.read_text(encoding="utf-8")), d))
    if not rows:
        print("처리 결과 없음", file=sys.stderr)
        return 1
    env = rows[0][1].env
    L = ["# S4 검증 산출물: 영상 분석가 관문 B", "",
         "> `scripts/s4_artifacts.py`가 만든다. 사람 확인 칸(`[ ]`)은 리뷰 때 `[x]`로 표시한다. 원본 영상·오디오·전체 프레임은 커밋하지 않는다.", "",
         "## 1. 실행 환경", "",
         f"- 장치: `{env.device}`(맥 M1 Max, mlx Metal), 전사 모델 mlx-whisper `{env.whisper_model}`",
         "- 버전: " + ", ".join(f"{k} {v}" for k, v in env.versions.items()),
         "- 판독·요약 모델: `generate`(config/models.yaml), 설정 `config/video.yaml`", "",
         "| 영상 | 제목 | 길이 | mode | 처리 구간 | 받기(초) | 전사(초) | 프레임 1차(초) | 후보 → 중복 제거 → 선택 | 판독 | 전사 품질 | segment |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for _it, m, d in rows:
        t, fm = m.env.timings_sec, m.frames_meta
        frames = f"{fm.candidates} → {fm.deduped} → {fm.selected}" if fm else "-"
        L.append(f"| [{m.video_id}](https://youtu.be/{m.video_id}) | {cell(m.title[:40])} | {tc(m.duration_sec)} | {m.mode} "
                 f"| {tc(m.span.start)}~{tc(m.span.end)} | {t.get('download', 0):.0f} | {t.get('transcribe', 0):.0f} "
                 f"| {t.get('frames_pass1', 0):.0f} | {frames} | {d.frames_read}/{d.frames_total} | {m.transcript_quality} "
                 f"| {len(m.segments)} |")
    L += ["", "받기 0초는 작업 폴더의 받은 파일을 다시 쓴 것(픽스처 저장 때 받음). 전사 시간에는 모델 적재가 들어 있다.", ""]

    L += ["## 2. 전사 발췌(앞 2분)와 품질 판정", ""]
    for _it, m, _d in rows:
        sig = {k: v for k, v in m.quality_signals.items() if k != "language_votes"}
        votes = ", ".join(f"{v['at']}s→{v['lang']}" for v in m.quality_signals.get("language_votes", []))
        L += [f"### {m.video_id} ({m.language}, {m.transcript_quality})", "",
              f"- 근거 수치: `{json.dumps(sig, ensure_ascii=False)}`", f"- 언어 감지(3지점): {votes or '-'}",
              f"- 경고: {cell('; '.join(m.warnings)) or '없음'}", "", "```"]
        L += [f"[{tc(s.start)}] {s.text}" for s in m.segments if s.start < m.span.start + EXCERPT_SEC]
        L += ["```", ""]

    L += ["## 3. 프레임 썸네일, 판독, 발화 (영상당 최대 5장)", "",
          "썸네일은 판독 수치가 있는 프레임 → 판독 우선순위 순으로 고른다. 포착률 확인: 썸네일에 보이는 수치 중 판독이 놓친 것이 있으면 `[x]`.", ""]
    captures = []
    frame_thumb: dict[tuple[str, int], str] = {}
    for _it, m, d in rows:
        if m.mode != "whisper+slides":
            continue
        readings = {s.sec: s for s in d.slides}
        chosen = sorted(m.frames, key=lambda f: (0 if readings.get(round(f.t)) and readings[round(f.t)].numbers else 1,
                                                  FRAME_PRIORITY[f.reason], f.t))[:PER_VIDEO]
        L += [f"### {m.video_id}", "", "| 썸네일 | 시각·이유 | 발화(spoken_text) | 판독 | 놓친 수치 있음 |", "|---|---|---|---|---|"]
        for f in sorted(chosen, key=lambda f: f.t):
            sec = round(f.t)
            img = thumb(m, f.path, sec)
            if img:
                frame_thumb[(m.video_id, sec)] = img
            r = readings.get(sec)
            read = (f"{r.frame_kind}, 제목 `{cell(r.title)}`, 수치 " + ", ".join(f"{n.value}({n.confidence}, {cell(n.what)})"
                                                                         for n in r.numbers)
                    if r else "판독 없음")
            L.append(f"| ![]({img}) | [{tc(f.t)}](https://youtu.be/{m.video_id}?t={sec}) {f.reason} "
                     f"| {cell(f.spoken_text[:120])} | {read} | [ ] |")
            captures.append((m.video_id, sec))
        L.append("")

    L += ["## 4. slide_only_facts 전체 (발화에 없고 화면에만 있는 수치)", "",
          "판독 수치 정확도 문턱값: 이 표에서 '화면에 있음' 비율 90% 이상. 썸네일이 없는 행은 시각 링크로 확인.", "",
          "| 영상 | 초 | 수치 | 단위 | 무엇 | 확신도 | 근거 id | 썸네일 | 화면에 있음 |", "|---|---|---|---|---|---|---|---|---|"]
    n_facts = 0
    for _it, m, d in rows:
        for f in d.slide_only_facts:
            n_facts += 1
            img = frame_thumb.get((m.video_id, f.sec))
            L.append(f"| {m.video_id} | [{f.sec}](https://youtu.be/{m.video_id}?t={f.sec}) | {cell(f.value)} | {cell(f.unit)} "
                     f"| {cell(f.fact)} | {f.confidence} | `{f.evidence}` | {f'[보기]({img})' if img else '-'} | [ ] |")
    L += ["", f"{n_facts}개", ""]
    checks = [(m.video_id, c) for _it, m, d in rows for c in d.check_numbers]
    L += ["### 확인 필요(check) 판독", "", "| 영상 | 초 | 보이는 값 | 무엇 |", "|---|---|---|---|"]
    L += [f"| {v} | {c.sec} | {cell(c.value)} | {cell(c.what)} |" for v, c in checks] or ["| - | - | - | - |"]
    L.append("")

    L += ["## 5. 표기 쌍(별칭 후보, V7)", "", "keywords.yaml 반영은 설계 세션이 정한다.", "",
          "| 영상 | 초 | 전사 표기 | 화면 표기 |", "|---|---|---|---|"]
    pairs = [(m.video_id, p) for _it, m, d in rows for p in d.name_pairs]
    L += [f"| {v} | {p.sec} | {cell(p.spoken)} | {cell(p.screen)} |" for v, p in pairs] or ["| - | - | - | - |"]
    L.append("")

    L += ["## 6. whisper만 vs whisper+slides", "", "같은 전사로 요약만 다시(슬라이드가 더한 것만 차이). `scripts/s4_compare.py`.", ""]
    for cmp_path in sorted(OUT.glob("compare_*.json")):
        c = json.loads(cmp_path.read_text(encoding="utf-8"))
        vid = cmp_path.stem.removeprefix("compare_")
        L += [f"### {vid}", "", "| | whisper | whisper+slides |", "|---|---|---|",
              f"| 포인트 수 | {len(c['whisper']['key_points'])} | {len(c['whisper+slides']['key_points'])} |",
              f"| 슬라이드 전용 수치 | - | {len(c['whisper+slides']['slide_only_facts'])} |",
              f"| 표기 쌍 | {len(c['whisper']['name_pairs'])} | {len(c['whisper+slides']['name_pairs'])} |", "",
              "| whisper 포인트 | whisper+slides 포인트 |", "|---|---|"]
        a, b = c["whisper"]["key_points"], c["whisper+slides"]["key_points"]
        for i in range(max(len(a), len(b))):
            L.append(f"| {cell(a[i]['text']) if i < len(a) else ''} | {cell(b[i]['text']) if i < len(b) else ''} |")
        L.append("")

    L += ["## 7. 재현 명령", "", "```bash",
          "uv sync --extra video",
          "TRENDSIT_SPEC=S4 uv run python -m trendsit collect --source techbridge --since 2026-09-01",
          f"TRENDSIT_SPEC=S4 uv run --extra video python -m trendsit video run --queue {Path(queue_path).as_posix()}",
          "TRENDSIT_SPEC=S4 uv run --extra video python scripts/s4_compare.py xRZHLI5SPWo -TeOEuplMrQ",
          f"uv run --extra video python scripts/s4_eval_fixtures.py {Path(queue_path).as_posix()}",
          "TRENDSIT_SPEC=S4 uv run python -m trendsit eval video_summary",
          f"uv run --extra video python scripts/s4_artifacts.py {Path(queue_path).as_posix()}", "```", ""]
    (OUT / "README.md").write_text("\n".join(L), encoding="utf-8")
    size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"{OUT.relative_to(ROOT)}/README.md, 썸네일 {len(list(THUMBS.glob('*.png')))}장, 전체 {size / 1024:.0f}KB")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
