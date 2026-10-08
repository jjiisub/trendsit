"""video.yaml 읽기와 검사. 오류는 check-config와 같은 형식(파일, 경로, 이유)."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from ...core import config
from ...core.config_video import VideoConfig

FILE = "video.yaml"


def load_video_config(config_dir: Path | None = None) -> VideoConfig:
    data = config._read_yaml((config_dir or config.ROOT / "config") / FILE)
    try:
        return VideoConfig.model_validate(data)
    except ValidationError as e:
        raise config._errors(FILE, e)[0] from e


def check_video_config(config_dir: Path | None = None) -> list[config.ConfigError]:
    """오류를 모두 모은다(빈 목록 = 통과)."""
    try:
        data = config._read_yaml((config_dir or config.ROOT / "config") / FILE)
    except config.ConfigError as e:
        return [e]
    try:
        VideoConfig.model_validate(data)
    except ValidationError as e:
        return config._errors(FILE, e)
    return []
