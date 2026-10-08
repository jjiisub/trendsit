"""mlx-whisper 로컬 전사 + 다지점 언어 감지 + 전사 품질 판정(V5). 스킬 transcribe.py에서 옮김.

품질 판정은 거짓 양성을 줄이는 쪽: 신호 여러 개가 함께 성립할 때만 suspect_hallucination.
정상 영상을 막는 것이 환각을 한 번 통과시키는 것보다 나쁘다(스킬 실측 근거).
"""

from __future__ import annotations

import re
import statistics
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

MODEL_REPOS = {
    "tiny": "mlx-community/whisper-tiny-mlx",
    "base": "mlx-community/whisper-base-mlx",
    "small": "mlx-community/whisper-small-mlx",
    "medium": "mlx-community/whisper-medium-mlx",
    "large-v3": "mlx-community/whisper-large-v3-mlx",
    "large-v3-turbo": "mlx-community/whisper-large-v3-turbo",
}

# 언어 감지: whisper는 앞 30초만 보고 언어를 정한다. 오프닝 음악에 낚이지 않게 세 지점 다수결
LANG_PROBE_POINTS = (0.2, 0.5, 0.8)
LANG_PROBE_WINDOW = 30.0
LANG_MIN_DURATION = 60.0

# 품질 판정 문턱(스킬 실측값 그대로)
EMPTY_CHAR_THRESHOLD = 10
REPEAT_RATIO_HIGH = 0.5
UNIQUE_TOKEN_FEW = 40
WINDOW_UNIFORM_HIGH = 0.5
NO_SPEECH_RATIO_HIGH = 0.6
AVG_LOGPROB_LOW = -0.8
SILENCE_RATIO_HIGH = 0.4
COMPRESSION_RATIO_HIGH = 2.2
WHISPER_WINDOW_SEC = 28.0  # 30초 창 그대로 나온 segment(환각 흔적)
SILENCE_NOISE_DB = -35
SILENCE_MIN_DUR = 1.0


class TranscribeError(RuntimeError):
    pass


def to_wav(media: Path, wav: Path, start: float | None, end: float | None) -> Path:
    """16kHz 모노 WAV. 구간이 있으면 잘라 낸다(시각은 time_offset으로 되돌림)."""
    cmd = ["ffmpeg", "-y", "-nostdin", "-loglevel", "error"]
    if start:
        cmd += ["-ss", f"{start:.3f}"]
    if end is not None:
        cmd += ["-to", f"{end:.3f}"]
    cmd += ["-i", str(media), "-vn", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)]
    proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if proc.returncode != 0 or not wav.is_file():
        raise TranscribeError(f"ffmpeg 오디오 변환 실패: {proc.stderr.decode(errors='replace')[-400:]}")
    return wav


def silence_ratio(wav: Path, duration: float) -> float | None:
    if duration <= 0:
        return None
    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-i", str(wav), "-af",
           f"silencedetect=noise={SILENCE_NOISE_DB}dB:d={SILENCE_MIN_DUR}", "-f", "null", "-"]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=300)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    total = sum(float(x) for x in re.findall(r"silence_duration:\s*([\d.]+)", proc.stderr.decode(errors="replace")))
    return round(min(1.0, total / duration), 4)


def detect_language(wav: Path, model_repo: str) -> tuple[str | None, list[dict[str, Any]], list[str]]:
    """세 지점(20/50/80%) 30초씩 언어 감지 → 다수결(동수면 확률 합). 실패하면 whisper 기본 감지에 맡김."""
    try:
        import mlx.core as mx  # type: ignore[import-not-found]
        from mlx_whisper.audio import (  # type: ignore[import-not-found]
            N_FRAMES,
            SAMPLE_RATE,
            load_audio,
            log_mel_spectrogram,
            pad_or_trim,
        )
        from mlx_whisper.transcribe import ModelHolder  # type: ignore[import-not-found]

        model = ModelHolder.get_model(model_repo, mx.float16)
        audio = load_audio(str(wav))
    except Exception:  # noqa: BLE001 - 감지 실패는 전사를 막지 않는다
        return None, [], []
    n, win = len(audio), int(LANG_PROBE_WINDOW * SAMPLE_RATE)
    votes = []
    for frac in LANG_PROBE_POINTS:
        offset = max(0, min(int(frac * n), max(0, n - win)))
        chunk = audio[offset:offset + win]
        if len(chunk) < SAMPLE_RATE:
            continue
        try:
            mel = pad_or_trim(log_mel_spectrogram(chunk, n_mels=model.dims.n_mels), N_FRAMES, axis=-2)
            _tokens, probs = model.detect_language(mel.astype(mx.float16))
            dist = probs[0] if isinstance(probs, list) else probs
            lang = max(dist, key=dist.get)
            votes.append({"at": round(offset / SAMPLE_RATE, 1), "lang": lang, "prob": round(float(dist[lang]), 4)})
        except Exception:  # noqa: BLE001
            continue
    if not votes:
        return None, [], []
    tally: dict[str, list[float]] = {}
    for v in votes:
        tally.setdefault(v["lang"], []).append(v["prob"])
    best = max(tally, key=lambda k: (len(tally[k]), sum(tally[k])))
    warnings = []
    if len(tally) > 1:
        detail = ", ".join(f"{v['at']}s→{v['lang']}({v['prob']:.2f})" for v in votes)
        warnings.append(f"언어 감지가 지점마다 다름({detail}) → 다수결 {best}")
    return best, votes, warnings


def normalize_segments(raw: list[dict[str, Any]], offset: float, lo: float, hi: float
                       ) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """계약(V12)을 전사 단계에서 지킨다: 시간 순서, 겹침 없음, 구간 안.

    mlx-whisper는 start > end를 내기도 하고(실측 665개 중 1건), 30초 창 때문에 오디오 끝을 넘기도 한다.
    오디오 끝에서 글자 없는 segment나 깨진 문자(U+FFFD)가 줄줄이 나오기도 해서(실측 7분 영상 끝에 31건) 지운다.
    """
    items, fixed, dropped, blank = [], 0, 0, 0
    for seg in raw:
        try:
            s, e = float(seg["start"]) + offset, float(seg["end"]) + offset
        except (KeyError, TypeError, ValueError):
            continue
        if s > e:
            fixed += 1
            e = s
        if s > hi + 0.5 or e < lo - 0.5:
            dropped += 1
            continue
        s, e = min(max(s, lo), hi), min(max(e, lo), hi)
        text = (seg.get("text") or "").replace("\ufffd", "").strip()
        if not text:
            blank += 1
            continue
        item = {"start": s, "end": e, "text": text}
        for k in ("no_speech_prob", "avg_logprob", "compression_ratio"):
            if isinstance(seg.get(k), int | float):
                item[k] = float(seg[k])
        items.append(item)
    items.sort(key=lambda x: (x["start"], x["end"]))
    overlapped = 0
    for prev, cur in zip(items, items[1:], strict=False):
        if cur["start"] < prev["end"]:
            overlapped += 1
            cur["start"] = prev["end"]
            cur["end"] = max(cur["end"], cur["start"])
    return items, {"reversed": fixed, "out_of_span": dropped, "overlapped": overlapped, "blank": blank}


_TOKEN = re.compile(r"[\w가-힣]+", re.UNICODE)


def quality_signals(segments: list[dict[str, Any]], silence: float | None) -> dict[str, Any]:
    text = " ".join(s["text"] for s in segments if s["text"])
    norm = [t for t in (re.sub(r"\s+", " ", s["text"]).strip().lower() for s in segments) if t]
    tokens = _TOKEN.findall(text.lower())
    n = len(segments)

    def mean(key: str) -> float | None:
        vals = [s[key] for s in segments if key in s]
        return round(statistics.fmean(vals), 4) if vals else None

    no_speech = [s["no_speech_prob"] for s in segments if "no_speech_prob" in s]
    return {
        "segments": n,
        "chars": len(re.sub(r"\s", "", text)),
        "repeat_ratio": round(1 - len(set(norm)) / len(norm), 4) if norm else 0.0,
        "unique_tokens": len(set(tokens)),
        "window_uniform_ratio": round(sum(1 for s in segments if s["end"] - s["start"] >= WHISPER_WINDOW_SEC) / n, 4)
        if n else 0.0,
        "silence_ratio": silence,
        "no_speech_ratio": round(sum(1 for p in no_speech if p > NO_SPEECH_RATIO_HIGH) / len(no_speech), 4)
        if no_speech else None,
        "mean_avg_logprob": mean("avg_logprob"),
        "mean_compression_ratio": mean("compression_ratio"),
    }


def judge_quality(sig: dict[str, Any]) -> tuple[str, list[str]]:
    """ok / suspect_hallucination / empty와 근거. 반복형과 무발화형 두 무리 중 하나가 성립할 때만 suspect."""
    if sig["segments"] == 0 or sig["chars"] < EMPTY_CHAR_THRESHOLD:
        return "empty", [f"전사 글자 수 {sig['chars']} < {EMPTY_CHAR_THRESHOLD}"]
    reasons = []
    repeat = (sig["repeat_ratio"] >= REPEAT_RATIO_HIGH and sig["unique_tokens"] <= UNIQUE_TOKEN_FEW
              and sig["window_uniform_ratio"] >= WINDOW_UNIFORM_HIGH)
    if repeat:
        reasons.append(f"같은 문구 반복률 {sig['repeat_ratio']:.0%}, 고유 어휘 {sig['unique_tokens']}개, "
                       f"30초 등간격 segment {sig['window_uniform_ratio']:.0%}")
    nospeech = False
    if sig["no_speech_ratio"] is not None and sig["mean_avg_logprob"] is not None:
        corroborating = ((sig["silence_ratio"] is not None and sig["silence_ratio"] >= SILENCE_RATIO_HIGH)
                         or sig["window_uniform_ratio"] >= WINDOW_UNIFORM_HIGH or sig["repeat_ratio"] >= 0.3
                         or (sig["mean_compression_ratio"] or 0) >= COMPRESSION_RATIO_HIGH)
        nospeech = (sig["no_speech_ratio"] >= NO_SPEECH_RATIO_HIGH and sig["mean_avg_logprob"] <= AVG_LOGPROB_LOW
                    and corroborating)
        if nospeech:
            reasons.append(f"무발화 segment {sig['no_speech_ratio']:.0%}, 평균 로그확률 {sig['mean_avg_logprob']:.2f}")
    return ("suspect_hallucination", reasons) if (repeat or nospeech) else ("ok", [])


WhisperFn = Callable[..., dict[str, Any]]


def _mlx_transcribe(wav: str, **kwargs: Any) -> dict[str, Any]:
    import mlx_whisper  # type: ignore[import-not-found]

    return mlx_whisper.transcribe(wav, **kwargs)


def transcribe(wav: Path, *, model: str, lo: float, hi: float, lang: str | None = None,
               whisper: WhisperFn = _mlx_transcribe, detect: Callable[..., Any] = detect_language,
               silence: Callable[[Path, float], float | None] = silence_ratio) -> dict[str, Any]:
    """전사 → 정규화 → 품질 판정. 시각은 절대시각(구간 시작 lo를 더함)."""
    repo = MODEL_REPOS[model]
    span = hi - lo
    warnings: list[str] = []
    votes: list[dict[str, Any]] = []
    if lang is None and span >= LANG_MIN_DURATION:
        lang, votes, w = detect(wav, repo)
        warnings += w
    kwargs: dict[str, Any] = {"path_or_hf_repo": repo, "verbose": None}
    if lang:
        kwargs["language"] = lang
    result = whisper(str(wav), **kwargs)
    segments, fixes = normalize_segments(result.get("segments") or [], lo, lo, hi)
    if fixes["reversed"]:
        warnings.append(f"시간이 거꾸로인 segment {fixes['reversed']}건 보정")
    if fixes["out_of_span"]:
        warnings.append(f"구간 밖 segment {fixes['out_of_span']}건 제외")
    if fixes["blank"]:
        warnings.append(f"글자 없는 segment {fixes['blank']}건 제외")
    if fixes["overlapped"]:
        warnings.append(f"앞 segment와 겹친 segment {fixes['overlapped']}건 시작 시각 보정")
    sig = quality_signals(segments, silence(wav, span))
    quality, reasons = judge_quality(sig)
    if quality != "ok":
        warnings.append(f"전사 품질 {quality}: {' / '.join(reasons)}")
    return {"language": result.get("language") or lang or "unknown",
            "segments": [{"start": round(s["start"], 3), "end": round(s["end"], 3), "text": s["text"]}
                         for s in segments],
            "transcript_quality": quality, "quality_signals": sig | {"language_votes": votes},
            "warnings": warnings}
