"""역할 입력의 이미지(S4 이미지 입력, 공통 코어). 메시지·캐시 키·실행 기록에는 경로와 바이트 해시만 두고,
전송 직전에만 data URI로 바꾼다(llm_calls와 캐시에 이미지 원본이 쌓이지 않게).

자리표시 부분: {"type": "image_url", "image_url": {"url": "image:sha256=<hex>", "path": "<파일>"}}
"""

from __future__ import annotations

import base64
import copy
import hashlib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

SCHEME = "image:sha256="
# 예상 비용 계산용 장당 입력 토큰. 실측(qwen3.8-27b, DeepInfra, 2026-10-08, 같은 프레임·같은 문구):
# 기본 해상도 1024px 약 540(요청 626토큰), 768px 약 300(386토큰). 관문 B 판독 1장 평균 입력 약 3,030토큰
# (시스템 프롬프트 포함). 상한 쪽으로 넉넉하게
IMAGE_TOKENS_EST = 1500
MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


class ImageError(Exception):
    pass


class ImageFile(BaseModel):
    """역할 입력의 이미지 칸. 메시지 조립이 자료 블록 바로 뒤에 이미지 부분으로 붙인다."""

    model_config = ConfigDict(extra="forbid")
    path: str


def digest(path: Path | str) -> str:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError as e:
        raise ImageError(f"이미지를 읽지 못함: {path} ({e})") from e


def image_part(img: ImageFile) -> dict[str, Any]:
    return {"type": "image_url", "image_url": {"url": SCHEME + digest(img.path), "path": img.path}}


def _parts(body: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for m in body.get("messages") or []:
        if isinstance(m.get("content"), list):
            out += [p for p in m["content"] if isinstance(p, dict) and p.get("type") == "image_url"]
    return out


def count(body: dict[str, Any]) -> int:
    return sum(1 for p in _parts(body) if str(p["image_url"].get("url", "")).startswith(SCHEME))


def without_paths(messages: Any) -> Any:
    """캐시 키용: 경로를 뺀 메시지(같은 바이트면 다른 폴더에 있어도 같은 키)."""
    if not isinstance(messages, list) or not any(isinstance(m.get("content"), list) for m in messages):
        return messages
    out = copy.deepcopy(messages)
    for m in out:
        for p in m.get("content") if isinstance(m.get("content"), list) else []:
            if isinstance(p, dict) and p.get("type") == "image_url":
                p["image_url"].pop("path", None)
    return out


def materialize(body: dict[str, Any]) -> dict[str, Any]:
    """전송용 사본: 자리표시를 data URI로. 파일이 바뀌었으면(해시 불일치) 보내지 않는다."""
    if not count(body):
        return body
    wire = copy.deepcopy(body)
    for p in _parts(wire):
        ref = p["image_url"]
        url = str(ref.get("url", ""))
        if not url.startswith(SCHEME):
            continue
        path = Path(ref.pop("path", ""))
        data = path.read_bytes() if path.is_file() else None
        if data is None or hashlib.sha256(data).hexdigest() != url.removeprefix(SCHEME):
            raise ImageError(f"이미지 파일이 없거나 기록된 해시와 다름: {path}")
        ref["url"] = f"data:{MIME.get(path.suffix.lower(), 'image/jpeg')};base64,{base64.b64encode(data).decode()}"
    return wire
