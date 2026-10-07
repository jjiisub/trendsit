"""설정 파일 로딩과 검증. 모델 이름, 제공사, 주소는 여기서 읽은 값만 쓴다."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_ALIASES = ("generate", "judge", "compare", "smoke")
SECRET_FILE = Path.home() / ".config" / "trendsit" / ".env"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------- models.yaml ----------
class ProviderPref(BaseModel):
    # OpenRouter provider 객체. 알려진 칸만 형식 검사하고 나머지는 그대로 전달
    model_config = ConfigDict(extra="allow")
    order: list[str] | None = None
    allow_fallbacks: bool | None = None
    require_parameters: bool | None = None
    quantizations: list[str] | None = None


class ReasoningSpec(Strict):
    effort: Literal["minimal", "low", "medium", "high"] | None = None
    max_tokens: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _one_of(self) -> ReasoningSpec:
        if (self.effort is None) == (self.max_tokens is None):
            raise ValueError("effort와 max_tokens 중 하나만 지정 (OpenRouter 제약)")
        return self


class ModelSpec(Strict):
    id: str = Field(min_length=1)
    provider: ProviderPref | None = None
    # YAML의 off는 False로 읽힌다. False/None = 추론 끔
    reasoning: ReasoningSpec | Literal[False] | None = None
    base_url: str | None = None  # 없으면 default_base_url. Ollama 전환 시 모델별로 지정
    api_key_env: str = "OPENROUTER_API_KEY"

    @field_validator("reasoning", mode="before")
    @classmethod
    def _off(cls, v: Any) -> Any:
        if isinstance(v, str) and v.lower() == "off":
            return False
        return v


class ModelsConfig(Strict):
    default_base_url: str
    models: dict[str, ModelSpec]

    @model_validator(mode="after")
    def _required(self) -> ModelsConfig:
        missing = [a for a in REQUIRED_ALIASES if a not in self.models]
        if missing:
            raise ValueError(f"필수 별칭 없음: {', '.join(missing)}")
        return self

    def base_url(self, alias: str) -> str:
        return self.models[alias].base_url or self.default_base_url


# ---------- budget.yaml ----------
class BudgetConfig(Strict):
    phase: str
    phase_total_usd: float = Field(ge=0)
    specs: dict[str, Annotated[float, Field(ge=0)]]  # 음수면 경로 specs.S0로 짚음


# ---------- sources.yaml ----------
class Backfill(Strict):
    method: Literal["rss_only", "list_pages", "day_archive"]
    url_template: str | None = Field(default=None, pattern=r"^https?://")
    page_template: str | None = Field(default=None, pattern=r"^https?://")  # list_pages의 2페이지부터
    max_pages: int = Field(default=50, ge=1, le=200)
    note: str | None = None

    @model_validator(mode="after")
    def _template(self) -> Backfill:
        if self.method == "rss_only":
            return self
        if not self.url_template:
            raise ValueError(f"{self.method}에는 url_template이 필요함")
        if self.method == "day_archive" and not any(k in self.url_template for k in ("{date}", "{d}")):
            raise ValueError("day_archive의 url_template에는 날짜 자리({date} 또는 {yyyy}/{Mon}/{d})가 필요함")
        return self


class TextSource(Strict):
    id: str
    name: str
    kind: Literal["primary", "curation", "news"]
    lang: str
    feed: str = Field(pattern=r"^https?://")
    fetch: Literal["feed_full", "feed_summary", "feed_title"]
    backfill: Backfill = Backfill(method="rss_only")
    note: str | None = None


class VideoBackfill(Strict):
    method: Literal["rss_only", "channel_listing"]
    max_videos: int = Field(default=60, ge=1, le=500)
    note: str | None = None


class VideoSource(Strict):
    id: str
    name: str
    lang: str
    channel_handle: str
    channel_id: str = Field(pattern=r"^UC[\w-]{22}$")
    feed: str = Field(pattern=r"^https?://")
    backfill: VideoBackfill = VideoBackfill(method="rss_only")
    note: str | None = None


class Trending(Strict):
    source: Literal["github_trending_page"]
    url: str = Field(pattern=r"^https://github\.com/trending")
    top_n: int = Field(gt=0)


class TrackedRepo(Strict):
    repo: str = Field(pattern=r"^[\w.-]+/[\w.-]+$")
    why: str


class GithubConfig(Strict):
    trending: Trending
    tracked: list[TrackedRepo]


class SourcesConfig(Strict):
    text: list[TextSource]
    video: list[VideoSource]
    github: GithubConfig

    @model_validator(mode="after")
    def _unique(self) -> SourcesConfig:
        ids = [s.id for s in self.text] + [s.id for s in self.video]
        dup = {i for i in ids if ids.count(i) > 1}
        if dup:
            raise ValueError(f"소스 id 중복: {', '.join(sorted(dup))}")
        return self


# ---------- link_kinds.yaml ----------
class KindRule(Strict):
    domains: list[str] = []
    paths: list[str] = []  # 참고용(예: arxiv /abs/). 판별은 도메인으로
    path_contains: list[str] = []  # 도메인이 달라도 경로에 이 문자열이 있으면 이 종류


class LinkKindsConfig(Strict):
    kinds: dict[str, KindRule]
    default: str

    @model_validator(mode="after")
    def _kinds(self) -> LinkKindsConfig:
        if not self.kinds:
            raise ValueError("kinds가 비어 있음")
        return self


# ---------- keywords.yaml ----------
class Keyword(Strict):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    canonical: str = Field(min_length=1)
    aliases: list[str] = Field(min_length=1)
    note: str | None = None

    @field_validator("aliases")
    @classmethod
    def _non_empty(cls, v: list[str]) -> list[str]:
        if any(not a.strip() for a in v):
            raise ValueError("빈 별칭이 있음")
        return v


class KeywordsConfig(Strict):
    keywords: list[Keyword]
    exclude: list[str] = []

    @model_validator(mode="after")
    def _unique(self) -> KeywordsConfig:
        ids = [k.id for k in self.keywords]
        dup = {i for i in ids if ids.count(i) > 1}
        if dup:
            raise ValueError(f"키워드 id 중복: {', '.join(sorted(dup))}")
        return self


FILES: dict[str, type[BaseModel]] = {
    "models.yaml": ModelsConfig,
    "budget.yaml": BudgetConfig,
    "sources.yaml": SourcesConfig,
    "keywords.yaml": KeywordsConfig,
    "link_kinds.yaml": LinkKindsConfig,
}


class ConfigError(Exception):
    def __init__(self, file: str, path: str, reason: str):
        self.file, self.path, self.reason = file, path, reason
        super().__init__(f"{file}: {path or '(최상위)'}: {reason}")


def loc_to_path(loc: tuple[Any, ...]) -> str:
    """pydantic loc → keywords[3].aliases 형태."""
    out = ""
    for part in loc:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            out += f".{part}" if out else str(part)
    return out


def _errors(file: str, err: ValidationError) -> list[ConfigError]:
    result = []
    for e in err.errors():
        # 유니언, 검증 함수 표시(function-after[...], literal[False] 등)는 경로에서 뺀다
        loc = tuple(p for p in e["loc"] if not (isinstance(p, str) and ("[" in p or p.startswith("function-"))))
        msg = e["msg"].removeprefix("Value error, ")
        result.append(ConfigError(file, loc_to_path(loc), msg))
    return result


def _read_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise ConfigError(path.name, "", "파일 없음") from e
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        where = f"{mark.line + 1}행" if mark else ""
        raise ConfigError(path.name, where, f"YAML 형식 오류: {getattr(e, 'problem', e)}") from e


def load(name: str, config_dir: Path | None = None) -> Any:
    """설정 파일 하나를 읽어 검증한 모델을 돌려준다. 틀리면 ConfigError(첫 오류)."""
    path = (config_dir or ROOT / "config") / name
    data = _read_yaml(path)
    try:
        return FILES[name].model_validate(data)
    except ValidationError as e:
        raise _errors(name, e)[0] from e


def check_all(config_dir: Path | None = None) -> list[ConfigError]:
    """네 파일 전부 검증하고 오류를 모두 모은다."""
    errors: list[ConfigError] = []
    for name, cls in FILES.items():
        path = (config_dir or ROOT / "config") / name
        try:
            cls.model_validate(_read_yaml(path))
        except ConfigError as e:
            errors.append(e)
        except ValidationError as e:
            errors.extend(_errors(name, e))
    return errors


def get_secret(name: str) -> str | None:
    """환경 변수 → ~/.config/trendsit/.env 순서로 찾는다. 값은 출력하지 않는다."""
    if os.environ.get(name):
        return os.environ[name]
    if SECRET_FILE.exists():
        for line in SECRET_FILE.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() == name and value.strip():
                return value.strip().strip("'\"")
    return None


def current_spec(override: str | None = None) -> str:
    return override or os.environ.get("TRENDSIT_SPEC") or "S0"
