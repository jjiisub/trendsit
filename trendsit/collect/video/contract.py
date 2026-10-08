"""1차 처리 결과 계약 검사(V12). 스킬 media_analyze_validate.py의 C1~C14 중 TrendsIT에 맞는 것을 옮김.

판독 이후 단계는 이 계약을 믿고 쓴다. 위반은 문장 목록으로 돌려준다(빈 목록 = 통과).
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import ValidationError

from ...core.artifacts_video import MediaResult
from ...core.config_video import FRAME_CAP_MAX

TOL = 1.0  # 구간 경계 여유(초)
EPS = 1e-3


def check(result: MediaResult | dict[str, Any], *, check_files: bool = False) -> list[str]:
    if isinstance(result, dict):
        try:
            result = MediaResult.model_validate(result)
        except ValidationError as e:
            return [f"스키마: {'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in e.errors()]
    r = result
    out: list[str] = []
    lo, hi = r.span.start, r.span.end
    if hi <= lo:
        out.append(f"구간: end({hi}) ≤ start({lo})")
    if hi > r.duration_sec + TOL:
        out.append(f"구간: end({hi})가 영상 길이({r.duration_sec}) 밖")

    # segments: 시간 순서, 겹침 없음, 구간 안
    for i, s in enumerate(r.segments):
        if s.start > s.end + EPS:
            out.append(f"segment {i}: start({s.start}) > end({s.end})")
        if s.end < lo - TOL or s.start > hi + TOL:
            out.append(f"segment {i}: 구간 [{lo}, {hi}] 밖({s.start}~{s.end})")
        if i and s.start < r.segments[i - 1].end - EPS:
            out.append(f"segment {i}: 앞 segment와 겹침({r.segments[i - 1].end} > {s.start})")

    # frames
    if r.mode != "whisper+slides" and r.frames:
        out.append(f"프레임: mode {r.mode}인데 프레임 {len(r.frames)}장")
    if r.frames_error and r.frames:
        out.append("프레임: frames_error가 있는데 프레임이 남아 있음")
    if r.frames and r.frames_meta is None:
        out.append("프레임: frames_meta 없음")
    cap = min(r.frames_meta.cap, FRAME_CAP_MAX) if r.frames_meta else FRAME_CAP_MAX
    if len(r.frames) > cap:
        out.append(f"프레임: {len(r.frames)}장 > 상한 {cap}")
    work = Path(r.work_dir)
    for j, f in enumerate(r.frames):
        if f.t > r.duration_sec + EPS or not lo - TOL <= f.t <= hi + TOL:
            out.append(f"frame {j}: t={f.t}가 구간 [{lo}, {hi}](길이 {r.duration_sec}) 밖")
        if j and f.t < r.frames[j - 1].t - EPS:
            out.append(f"frame {j}: 시각 역순({r.frames[j - 1].t} → {f.t})")
        p = PurePosixPath(f.path)
        if p.is_absolute() or ".." in p.parts or not f.path:
            out.append(f"frame {j}: 경로가 작업 폴더 밖({f.path})")
        elif check_files and not (work / p).is_file():
            out.append(f"frame {j}: 파일 없음({f.path})")
        if f.segment_index is None:
            if f.spoken_text:
                out.append(f"frame {j}: segment_index 없이 spoken_text만 있음")
        elif not 0 <= f.segment_index < len(r.segments):
            if not r.truncated_segments:
                out.append(f"frame {j}: segment_index {f.segment_index} 범위 밖")
        elif f.spoken_text != r.segments[f.segment_index].text:
            out.append(f"frame {j}: spoken_text가 segments[{f.segment_index}].text와 다름")
    return out
