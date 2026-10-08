"""프레임: 후보(키프레임·장면전환·균등) → 32×32 회색 썸네일 픽셀차로 중복 제거 → 적응형 예산 → 정밀 추출.

스킬 video_frames.py에서 옮김(ffmpeg만 씀, OpenCV·PySceneDetect 없음). 실측 근거는 원본 주석:
- 후보는 썸네일만 받는다. 전 프레임이 키프레임인 인코딩(231초에 6,903개)에서도 몇 MB로 끝난다
- 시각은 showinfo의 실측 pts_time(-copyts로 절대시각). 프레임 번호/fps 산술은 드롭 때 어긋난다
- 중복 제거 문턱 8.0(평균 절대 픽셀차): 같은 장면의 미세 변화는 버리고 달라진 화면은 남기는 경계
"""

from __future__ import annotations

import heapq
import re
import subprocess
from pathlib import Path
from typing import Any

MAX_FRAME_HEIGHT = 1998
THUMB_SIDE = 32
THUMB_BYTES = THUMB_SIDE * THUMB_SIDE
DEDUP_THRESHOLD = 8.0
SCENE_THRESHOLD = 0.3
MIN_SCENE_CANDIDATES = 8  # 이보다 적으면 균등 추출로(강연·화면 녹화는 장면전환이 2~3개뿐)
MIN_KEYFRAME_CANDIDATES = 4
# 중복 제거 생존 비율 → (하한, 상한). 상한은 설정의 frames_cap(최대 20)과 길이 상한 중 작은 값으로 다시 깎인다
DENSITY_BANDS = ((0.2, 8, 12), (0.5, 20, 35), (float("inf"), 40, 70))
MIN_CONTEXT_FRAMES = 8  # 정지 화면 영상도 맥락 확인용으로 최소 이만큼
LENGTH_CAPS = ((180, 40), (600, 60), (1800, 50), (3600, 35), (float("inf"), 25))
CUE_RESERVE_RATIO = 0.30  # 예산의 약 30%는 발화 신호(화면 지시) 프레임 몫
SEEK_COARSE_BACK = 5.0
SEEK_TOLERANCE = 0.5
_SHOWINFO = re.compile(r"n:\s*(\d+)\s+pts:\s*-?\d+\s+pts_time:(-?[\d.]+)")
# 후보 엔진 → 프레임 reason(계약의 네 값). 키프레임은 인코더가 잡은 화면 변화라 scene-change로 묶는다
ENGINE_REASON = {"keyframe": "scene-change", "scene-change": "scene-change", "uniform": "uniform"}


class FrameError(RuntimeError):
    """프레임 단계 실패. 전사 결과는 그대로 둔다(frames_error만)."""


def target_geometry(src_w: int | None, src_h: int | None, res: int) -> tuple[int, int] | None:
    """출력 크기. 업스케일 없음, 세로 1998 상한, 짝수 치수(yuv420p)."""
    if not src_w or not src_h:
        return None
    tw = min(int(res), int(src_w))
    th = max(2, round(int(src_h) * tw / int(src_w)))
    if th > MAX_FRAME_HEIGHT:
        th = MAX_FRAME_HEIGHT
        tw = max(2, round(int(src_w) * th / int(src_h)))
    return max(2, tw - tw % 2), max(2, th - th % 2)


def density_band(ratio: float | None) -> tuple[int, int]:
    if ratio is None:
        return DENSITY_BANDS[1][1], DENSITY_BANDS[1][2]
    for bound, low, high in DENSITY_BANDS:
        if ratio < bound:
            return low, high
    return DENSITY_BANDS[-1][1], DENSITY_BANDS[-1][2]


def length_cap(span: float) -> int:
    return next(cap for bound, cap in LENGTH_CAPS if span <= bound)


def plan_budget(distinct_ratio: float | None, survivors: int, span: float, user_cap: int) -> tuple[int, int]:
    """(cap, target). 생존 수 = 이 영상에 실제로 있는 서로 다른 화면 수라 그것을 존중하고, 하한은 맥락용 8장만.

    밴드 하한을 목표로 강제하면 이미 있는 화면의 중복으로 채워 토큰만 쓴다(스킬 실측: 70초 인터뷰 17장).
    """
    _low, high = density_band(distinct_ratio)
    hard = max(1, min(length_cap(span), user_cap))
    cap = max(1, min(high, hard))
    return cap, min(cap, max(min(MIN_CONTEXT_FRAMES, cap), survivors))


def parse_times(stderr: bytes) -> list[float]:
    found = sorted((int(m.group(1)), float(m.group(2))) for m in _SHOWINFO.finditer(stderr.decode(errors="replace")))
    return [t for _n, t in found]


def mean_abs_diff(a: bytes, b: bytes) -> float:
    return sum(abs(x - y) for x, y in zip(a, b, strict=True)) / len(a)


def dedup_indices(thumbs: list[bytes], threshold: float = DEDUP_THRESHOLD) -> list[int]:
    """직전에 남긴 프레임과의 평균 픽셀차가 문턱 미만이면 버린다."""
    if not thumbs:
        return []
    keep, last = [0], thumbs[0]
    for i in range(1, len(thumbs)):
        if mean_abs_diff(thumbs[i], last) >= threshold:
            keep.append(i)
            last = thumbs[i]
    return keep


def uniform_reduce(n: int, target: int) -> list[int]:
    """n개에서 target개를 고르게. 처음과 끝은 항상 남긴다."""
    if target <= 0 or n <= 0:
        return []
    if target >= n:
        return list(range(n))
    if target == 1:
        return [0]
    step = (n - 1) / (target - 1)
    return [round(i * step) for i in range(target)]


def gap_fill_times(existing: list[float], count: int, lo: float, hi: float, min_gap: float = 1.0) -> list[float]:
    """가장 큰 시간 간격을 반복해서 이등분."""
    if count <= 0 or hi <= lo:
        return []
    pts = sorted({round(t, 3) for t in existing if lo <= t <= hi} | {lo, hi})
    heap = [(-(b - a), a, b) for a, b in zip(pts, pts[1:], strict=False)]
    heapq.heapify(heap)
    out: list[float] = []
    while heap and len(out) < count:
        _neg, a, b = heapq.heappop(heap)
        if b - a < 2 * min_gap:
            continue
        mid = (a + b) / 2
        out.append(mid)
        heapq.heappush(heap, (-(mid - a), a, mid))
        heapq.heappush(heap, (-(b - mid), mid, b))
    return sorted(out)


def _ffmpeg(cmd: list[str], timeout: float) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=timeout)
    except FileNotFoundError as e:
        raise FrameError("ffmpeg 없음 (brew install ffmpeg)") from e
    except subprocess.TimeoutExpired as e:
        raise FrameError(f"ffmpeg 시간 초과({timeout:.0f}초)") from e


class FrameEngine:
    """pass1()(전사와 동시) → add_times(발화 신호) → topup() → result()."""

    def __init__(self, media: Path, frames_dir: Path, duration: float, *, width: int | None, height: int | None,
                 tier: str, cap: int, res: int, lo: float, hi: float):
        if tier not in ("auto", "full"):
            raise ValueError(f"프레임 tier: {tier!r}")
        if hi <= lo:
            raise FrameError(f"처리 구간이 비어 있음(start={lo}, end={hi})")
        self.media, self.dir = media, frames_dir
        self.duration, self.tier, self.res, self.user_cap = float(duration), tier, int(res), int(cap)
        self.lo, self.hi = max(0.0, lo), min(float(duration), hi)
        self.range_mode = self.lo > 0 or self.hi < self.duration
        self.geom = target_geometry(width, height, self.res)
        self.frames: list[dict[str, Any]] = []
        self.warnings: list[str] = []
        self._seq = 0
        self._reserve: list[float] = []
        self.engine = ""
        self.candidates = self.deduped = 0
        self.distinct_ratio: float | None = None
        self.fallback = False
        self.cap = self.target = 0

    # ---------- 1차 ----------
    def pass1(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        engine = "keyframe" if self.tier == "auto" else "scene-change"
        times, thumbs = self._survey(engine)
        if len(times) < (MIN_KEYFRAME_CANDIDATES if engine == "keyframe" else MIN_SCENE_CANDIDATES):
            self.fallback, engine = True, "uniform"
            times, thumbs = self._survey(engine)
        self.engine, self.candidates = engine, len(times)
        if not times:
            raise FrameError("프레임 후보 0개(영상 스트림 확인)")
        keep = list(range(len(times)))
        if thumbs is not None:
            keep = dedup_indices(thumbs)
            self.deduped = len(keep)
            self.distinct_ratio = round(len(keep) / len(times), 4)
        else:
            self.deduped = len(times)
            self.warnings.append("썸네일을 읽지 못해 중복 제거 없이 진행")
        self.cap, self.target = plan_budget(self.distinct_ratio, len(keep), self.hi - self.lo, self.user_cap)
        first_target = min(self.cap, max(1, round(self.target * (1 - CUE_RESERVE_RATIO))))
        chosen = [keep[i] for i in uniform_reduce(len(keep), first_target)]
        self._reserve = [times[i] for i in keep if i not in set(chosen)]
        reason = ENGINE_REASON[engine]
        for rank, i in enumerate(chosen):
            path = self._next_path("frame")
            try:
                actual = self.extract_single(times[i], path)
            except FrameError:
                path.unlink(missing_ok=True)
                continue
            self.frames.append({"t": round(actual, 3), "path": path, "pinned": False,
                                "reason": "first-frame" if rank == 0 and i == 0 else reason})
        if not self.frames:
            raise FrameError("고른 프레임을 하나도 추출하지 못함")
        self._sort()

    def _survey(self, engine: str) -> tuple[list[float], list[bytes] | None]:
        thumb = self.dir / "thumbs.gray"
        thumb.unlink(missing_ok=True)
        pre, input_opts = "", []
        if engine == "keyframe":
            input_opts += ["-skip_frame", "nokey"]
        elif engine == "scene-change":
            pre = f"select='eq(n\\,0)+gt(scene\\,{SCENE_THRESHOLD})',"
        else:
            want = min(240, max(24, int((self.hi - self.lo) / 2) or 24))
            pre = f"fps=1/{max(0.2, (self.hi - self.lo) / want):.6f},"
        if self.range_mode:
            input_opts += ["-ss", f"{self.lo:.3f}", "-to", f"{self.hi:.3f}", "-copyts"]
        fc = f"[0:v]{pre}scale={THUMB_SIDE}:{THUMB_SIDE}:flags=neighbor,format=gray,showinfo[thumb]"
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "info", "-nostdin", "-y", *input_opts, "-i", str(self.media),
               "-an", "-filter_complex", fc, "-map", "[thumb]", "-fps_mode", "passthrough", "-f", "rawvideo",
               "-pix_fmt", "gray", str(thumb)]
        proc = _ffmpeg(cmd, max(180.0, (self.hi - self.lo) * 4))
        times = parse_times(proc.stderr)
        if proc.returncode != 0 and not times:
            raise FrameError(f"후보 검출 실패(exit {proc.returncode}): {proc.stderr.decode(errors='replace')[-300:]}")
        thumbs = None
        try:
            blob = thumb.read_bytes()
            if len(blob) // THUMB_BYTES == len(times) and times:
                thumbs = [blob[i * THUMB_BYTES:(i + 1) * THUMB_BYTES] for i in range(len(times))]
        except OSError:
            pass
        thumb.unlink(missing_ok=True)
        kept_t, kept_h = [], []
        for i, t in enumerate(times):  # 필터가 구간 경계를 조금 넘길 수 있다
            if self.lo - 0.05 <= t <= self.hi + 0.05:
                kept_t.append(min(max(t, self.lo), self.hi))
                if thumbs is not None:
                    kept_h.append(thumbs[i])
        return kept_t, (kept_h if thumbs is not None else None)

    # ---------- 추가 ----------
    def bump_for_low_quality(self) -> bool:
        """전사를 믿을 수 없으면 정보가 화면에만 있을 가능성이 크다 → 예산을 상한까지."""
        new_cap = max(self.cap, min(self.user_cap, length_cap(self.hi - self.lo)))
        if new_cap > self.cap or self.target < new_cap:
            self.cap = self.target = new_cap
            return True
        return False

    def add_times(self, entries: list[tuple[float, str]]) -> int:
        """발화 신호 시각의 프레임(고정). 구간 밖, 예산 초과, 0.25초 안에 이미 있는 시각은 건너뜀."""
        added = 0
        for t, reason in entries:
            if len(self.frames) >= self.cap:
                break
            if not self.lo - 1e-6 <= t <= self.hi + 1e-6:
                continue
            t = min(max(t, self.lo), self.hi)
            if any(abs(t - f["t"]) < 0.25 for f in self.frames):
                continue
            path = self._next_path("cue")
            try:
                actual = self.extract_single(t, path)
            except FrameError:
                path.unlink(missing_ok=True)
                continue
            self.frames.append({"t": round(actual, 3), "path": path, "reason": reason, "pinned": True})
            added += 1
        self._sort()
        return added

    def topup(self) -> int:
        """남은 예산: 중복 제거를 통과했지만 1차에서 빠진 후보 먼저, 모자라면 시간 간격 이등분."""
        want = max(0, self.target - len(self.frames))
        if want <= 0:
            return 0
        pool = [t for t in self._reserve if all(abs(t - f["t"]) >= 1.0 for f in self.frames)]
        times = [pool[i] for i in uniform_reduce(len(pool), min(want, len(pool)))]
        if want > len(times):
            times += gap_fill_times([f["t"] for f in self.frames] + times, want - len(times), self.lo, self.hi)
        before = len(self.frames)
        for t in sorted(times):
            path = self._next_path("frame")
            try:
                actual = self.extract_single(t, path)
            except FrameError:
                path.unlink(missing_ok=True)
                continue
            self.frames.append({"t": round(actual, 3), "path": path, "reason": "uniform", "pinned": False})
        self._sort()
        return len(self.frames) - before

    def extract_single(self, t: float, out: Path) -> float:
        """1단: 입력 seek + -copyts(실측상 프레임 정확). 오차가 0.5초를 넘으면 2단: 되감아 select 필터."""
        actual = self._seek(t, out, coarse=t, select_from=None)
        if actual is not None and abs(actual - t) <= SEEK_TOLERANCE:
            return actual
        actual2 = self._seek(t, out, coarse=max(0.0, t - SEEK_COARSE_BACK), select_from=t)
        if actual2 is not None:
            return actual2
        if actual is not None:
            return actual
        raise FrameError(f"{t:.2f}초 프레임 추출 실패")

    def _seek(self, t: float, out: Path, coarse: float, select_from: float | None) -> float | None:
        pre = "" if select_from is None else f"select='gte(t\\,{select_from:.3f})',"
        scale = f"scale=w={self.res}:h=-2" if self.geom is None else f"scale={self.geom[0]}:{self.geom[1]}:flags=bicubic"
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "info", "-nostdin", "-y", "-ss", f"{coarse:.3f}", "-copyts",
               "-i", str(self.media), "-an", "-vf", f"{pre}{scale},showinfo", "-frames:v", "1", "-q:v", "3",
               "-f", "image2", str(out)]
        try:
            proc = _ffmpeg(cmd, 120.0)
        except FrameError:
            return None
        if proc.returncode != 0 or not out.is_file():
            return None
        times = parse_times(proc.stderr)
        return times[0] if times else None

    # ---------- 마무리 ----------
    def _next_path(self, prefix: str) -> Path:
        self._seq += 1
        return self.dir / f"{prefix}_{self._seq:04d}.jpg"

    def _sort(self) -> None:
        self.frames.sort(key=lambda f: (f["t"], str(f["path"])))

    def result(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        self._sort()
        frames = [{"t": round(min(max(f["t"], 0.0), self.duration), 3), "path": f["path"], "reason": f["reason"]}
                  for f in self.frames]
        meta = {"tier": self.tier, "engine": self.engine, "candidates": self.candidates, "deduped": self.deduped,
                "distinct_ratio": self.distinct_ratio, "selected": len(frames),
                "cue_selected": sum(1 for f in self.frames if f["pinned"]), "cap": self.cap,
                "resolution": self.geom[0] if self.geom else self.res, "fallback": self.fallback}
        return frames, meta

    def discard(self) -> None:
        for f in self.frames:
            Path(f["path"]).unlink(missing_ok=True)
        self.frames = []
