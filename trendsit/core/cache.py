"""응답 캐시. 같은 모델, 제공사, 메시지, 설정, 스키마, 도구면 저장된 응답을 재사용(0원)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .images import without_paths

# 캐시 키에 들어가는 요청 칸. usage 같은 회계용 칸은 응답 내용에 영향이 없어 뺀다
KEY_FIELDS = ("model", "provider", "messages", "response_format", "tools", "tool_choice",
              "max_tokens", "temperature", "reasoning")


def cache_key(body: dict[str, Any]) -> str:
    material = {k: body.get(k) for k in KEY_FIELDS}
    material["messages"] = without_paths(material["messages"])  # 이미지는 경로가 아니라 바이트 해시로
    raw = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class Cache:
    def __init__(self, directory: Path):
        self.dir = directory

    def _path(self, key: str) -> Path:
        return self.dir / key[:2] / f"{key}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        path = self._path(key)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def put(self, key: str, response: dict[str, Any]) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(response, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
