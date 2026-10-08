"""관문 B 사람 채점표: README 4장(slide_only_facts) 표 갱신 + reports/S4_video/label_summary.md. LLM 호출 없음.

    uv run --extra video python scripts/s4_label_sheets.py reports/S4_video/queue_gateB.json

s4_artifacts.py 뒤에 돈다(그 스크립트가 README 전체를 다시 쓰므로). 4장 표의 모든 행에 썸네일을 붙이고
'쓸 수 없음' 칸을 더한다. 프레임 파일이 없으면 작업 폴더의 영상에서 그 시각을 다시 뽑고, 영상도 없으면 "프레임 없음".
요약 채점표는 eval 픽스처(요약이 실제로 받은 입력)와 eval/labels/video_summary.csv의 출력만 쓴다.
judge 판정·코드 채점 결과는 넣지 않는다(사람 판정이 끌려가지 않게).
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from pathlib import Path

from trendsit.core.artifacts_video import MediaResult, SlideReading, VideoQueueItem
from trendsit.core.config import ROOT
from trendsit.core.db import DB
from trendsit.video import store

OUT = ROOT / "reports/S4_video"
THUMBS = OUT / "thumbs"
THUMB_WIDTH = 640  # 320은 차트 눈금·표 수치가 안 읽힘
FIXTURES = ROOT / "eval/fixtures/video_summary"
LABELS = ROOT / "eval/labels/video_summary.csv"
RUBRIC = ROOT / "eval/rubrics/video_summary.md"
WINDOW = 30
SEC4_START, SEC4_END = "## 4. slide_only_facts 전체", "### 확인 필요(check) 판독"
SEC7_END = "uv run --extra video python scripts/s4_artifacts.py"


def cell(x: object) -> str:
    return str(x).replace("|", "/").replace("\n", " ")


def tc(sec: float) -> str:
    s = int(sec)
    return f"{s // 60}:{s % 60:02d}"


def png(src: Path, dst: Path, at: int | None = None) -> None:
    seek = ["-ss", str(at)] if at is not None else []
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *seek, "-i", str(src), "-frames:v", "1",
                    "-vf", f"scale={THUMB_WIDTH}:-2", "-compression_level", "9", str(dst)], check=True)


def fact_thumb(media: MediaResult, sec: int, stats: dict[str, int]) -> str | None:
    """sec 프레임 썸네일. 프레임 파일 → 작업 폴더 영상에서 다시 뽑기 → None(프레임 없음)."""
    dst = THUMBS / f"{media.video_id}_{sec}.png"
    frame = next((f for f in media.frames if round(f.t) == sec), None)
    src = Path(media.work_dir) / frame.path if frame else None
    if src and src.is_file():
        png(src, dst)
        stats["frame"] += 1
        return f"thumbs/{dst.name}"
    video = next((p for p in sorted(Path(media.work_dir).glob("media.*")) if p.suffix != ".json"), None)
    if video:
        png(video, dst, at=frame.t if frame else sec)
        stats["reextracted"] += 1
        return f"thumbs/{dst.name}"
    stats["missing"] += 1
    return None


def facts_section(rows: list, stats: dict[str, int]) -> list[str]:
    L = [SEC4_START + " (발화에 없고 화면에만 있는 수치)", "",
         "판독 수치 정확도 문턱값: 이 표에서 '화면에 있음' 비율 90% 이상. 문턱값은 '화면에 있음' 칸으로만 계산한다.", "",
         "'쓸 수 없음' 기준: 화면에는 있지만 브리핑 수치가 아님(모델 버전 번호, 데모·터미널 UI 값, 도식 속 예시 값, 슬라이드 번호 등).", "",
         "| 영상 | 초 | 수치 | 단위 | 무엇 | 확신도 | 근거 id | 썸네일 | 화면에 있음 | 쓸 수 없음 |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    THUMBS.mkdir(parents=True, exist_ok=True)
    made: dict[tuple[str, int], str | None] = {}
    n = 0
    for m, d in rows:
        for f in d.slide_only_facts:
            n += 1
            key = (m.video_id, f.sec)
            if key not in made:
                made[key] = fact_thumb(m, f.sec, stats)
            img = made[key]
            L.append(f"| {m.video_id} | [{f.sec}](https://youtu.be/{m.video_id}?t={f.sec}) | {cell(f.value)} | {cell(f.unit)} "
                     f"| {cell(f.fact)} | {f.confidence} | `{f.evidence}` | {f'![]({img})' if img else '프레임 없음'} | [ ] | [ ] |")
    L += ["", f"{n}개. 썸네일 {len(made)}장(폭 {THUMB_WIDTH}px): 프레임 파일에서 {stats['frame']}장, "
          f"영상에서 다시 뽑음 {stats['reextracted']}장, 프레임 없음 {stats['missing']}장.", ""]
    return L


# ---- 요약 채점표 ----

def transcript_lines(text: str) -> list[tuple[int, str]]:
    out = []
    for line in text.splitlines():
        m = re.match(r"\[(\d+)\]\s*(.*)", line)
        if m:
            out.append((int(m.group(1)), m.group(2)))
    return out


def line_md(vid: str, sec: int, text: str) -> str:
    return f"[{tc(sec)}](https://youtu.be/{vid}?t={sec}) {text}"


def window(lines: list[tuple[int, str]], vid: str, sec: int, indent: str) -> list[str]:
    got = [line_md(vid, s, t) for s, t in lines if sec - WINDOW <= s <= sec + WINDOW]
    if not lines:
        return [f"{indent}- (전사 없음: 입력 전사가 빈 문서)"]
    return [f"{indent}- {x}" for x in got] or [f"{indent}- (이 구간 전사 줄 없음)"]


def at_line(lines: list[tuple[int, str]], vid: str, sec: int) -> str:
    cur = [(s, t) for s, t in lines if s <= sec]
    if not lines:
        return "(전사 없음: 입력 전사가 빈 문서)"
    return line_md(vid, *cur[-1]) if cur else "(이 초의 전사 줄 없음)"


def numbers_md(r: SlideReading | None) -> str:
    if r is None or not r.numbers:
        return "없음"
    return ", ".join(f"{n.value}({n.confidence}, {cell(n.what)})" for n in r.numbers)


def readings(db: DB, vid: str) -> dict[int, SlideReading]:
    return {round(r["t"]): SlideReading.model_validate_json(r["reading_json"]) for r in
            db.conn.execute("SELECT t, reading_json FROM video_frames WHERE video_id = ? AND reading_json IS NOT NULL",
                            (vid,))}


def rubric_questions() -> list[str]:
    text = RUBRIC.read_text(encoding="utf-8")
    return [ln for ln in text.splitlines() if re.match(r"\| Q\d \|", ln)]


def summary_sheet(db: DB) -> str:
    rubric = RUBRIC.read_text(encoding="utf-8").splitlines()
    intro = next(ln for ln in rubric if ln.startswith("채점 대상"))
    qs = rubric_questions()
    L = ["# S4 관문 B 요약 채점표 (video_summary, 사람 라벨)", "",
         "> `scripts/s4_label_sheets.py`가 만든다. 입력은 eval 픽스처(요약이 실제로 받은 입력), 출력은 "
         "`eval/labels/video_summary.csv`. judge 판정·코드 채점 결과는 일부러 넣지 않았다.", "",
         f"> {intro}", "",
         "채점: 절 끝의 `[ ]`를 `[x]`로, fail이면 이유를 적는다. 시각 링크는 유튜브 해당 초로 연다.", ""]
    with LABELS.open(encoding="utf-8", newline="") as f:
        label_rows = list(csv.DictReader(f))
    for i, row in enumerate(label_rows, 1):
        rid = row["id"]
        inp = json.loads((FIXTURES / f"{rid}.json").read_text(encoding="utf-8"))["input"]
        out = json.loads(row["output"])
        vid = re.sub(r"^derived_(empty|suspect_hallucination)_", "", rid)
        lines = transcript_lines(inp["transcript"]["text"])
        slides = {s["id"]: s for s in inp["slides"]}
        rd = readings(db, vid)
        L += [f"## {i}. {rid}", "",
              f"- 제목: {inp['title']}", f"- 유튜브: https://youtu.be/{vid}",
              f"- transcript_quality: `{inp['transcript_quality']}`", f"- mode: `{inp['mode']}`",
              f"- 입력: 전사 {len(lines)}줄, 판독 {len(slides)}장" + (" (파생 픽스처: 품질 미달 사본)" if rid.startswith("derived_") else ""),
              "", "| id | 질문 |", "|---|---|", *qs, "", "### key_points", ""]
        for k, kp in enumerate(out.get("key_points", []), 1):
            L.append(f"{k}. **{kp['text']}**")
            for ev in kp.get("evidence", []):
                m = re.match(r"vd:\d+@(\d+)$", ev)
                L.append(f"   - `{ev}`")
                if not m:
                    L.append("     - (id 형식 아님)")
                    continue
                sec = int(m.group(1))
                L.append(f"     - (a) 전사 {tc(max(0, sec - WINDOW))}~{tc(sec + WINDOW)}")
                L += window(lines, vid, sec, "       ")
                s = slides.get(ev)
                if s:
                    r = rd.get(sec)
                    L += [f"     - (b) 판독: 제목 `{cell(s['title'] or '')}`, 수치 {numbers_md(r)}",
                          f"       - ocr_text: {cell(s['text']) or '(빈 문자열)'}"]
                else:
                    L.append("     - (b) 판독: 이 id의 판독 문서 없음")
        if not out.get("key_points"):
            L.append("(key_points 없음)")
        L += ["", "### timeline", ""]
        for t in out.get("timeline", []):
            L.append(f"- **{tc(t['sec'])} {t['label']}**" + (" (slide)" if t.get("slide") else ""))
            L += window(lines, vid, t["sec"], "  ")
        if not out.get("timeline"):
            L.append("(timeline 없음)")
        L += ["", "### summary", ""]
        sents = [x for x in re.split(r"(?<=[.!?])\s+", (out.get("summary") or "").strip()) if x]
        L += [f"{k}. {x}" for k, x in enumerate(sents, 1)] or ["(summary 없음)"]
        L += ["", "### name_pairs", ""]
        for p in out.get("name_pairs", []):
            s = slides.get(f"vd:{inp['item_id']}@{p['sec']}")
            L += [f"- **{p['spoken']} → {p['screen']}** ({tc(p['sec'])})",
                  f"  - 전사: {at_line(lines, vid, p['sec'])}",
                  f"  - 판독 ocr_text: {cell(s['text']) if s else '(이 초의 판독 없음)'}"]
        if not out.get("name_pairs"):
            L.append("(name_pairs 없음)")
        L += ["", "### 채점", "",
              "- Q1 근거 [ ] pass [ ] fail 이유:",
              "- Q2 시각 [ ] pass [ ] fail 이유:",
              "- Q3 지어내지 않음 [ ] pass [ ] fail 이유:", ""]
    return "\n".join(L)


def main(queue_path: str) -> int:
    db = DB(ROOT / "data/trendsit.db")
    items = [VideoQueueItem.model_validate(x) for x in json.loads(Path(queue_path).read_text(encoding="utf-8"))]
    rows = []
    for it in items:
        p = ROOT / "data/media" / it.video_id / "media_result.json"
        d = store.digest(db, it.video_id)
        if p.exists() and d is not None:
            rows.append((MediaResult.model_validate_json(p.read_text(encoding="utf-8")), d))
    if not rows:
        print("처리 결과 없음", file=sys.stderr)
        return 1
    readme = OUT / "README.md"
    text = readme.read_text(encoding="utf-8")
    a, b = text.index(SEC4_START), text.index(SEC4_END)
    stats = {"frame": 0, "reextracted": 0, "missing": 0}
    text = text[:a] + "\n".join(facts_section(rows, stats)) + "\n" + text[b:]
    cmd = f"uv run --extra video python scripts/s4_label_sheets.py {Path(queue_path).as_posix()}"
    if cmd not in text:
        end = text.index("\n", text.index(SEC7_END))
        text = text[:end + 1] + cmd + "\n" + text[end + 1:]
    readme.write_text(text, encoding="utf-8")
    (OUT / "label_summary.md").write_text(summary_sheet(db), encoding="utf-8")
    print(f"README 4장 갱신: 프레임 {stats['frame']}, 다시 뽑음 {stats['reextracted']}, 프레임 없음 {stats['missing']}; "
          f"{(OUT / 'label_summary.md').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
