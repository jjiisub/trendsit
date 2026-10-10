"""설정 파일 로딩과 검증. 모델 이름, 제공사, 주소는 여기서 읽은 값만 쓴다."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from .config_brief import BriefConfig
from .config_video import VideoConfig

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
    archive_tz: Literal["kst", "utc"] = "kst"  # day_archive의 날짜 기준. utc면 한국 시간 시작일의 전날부터 읽는다
    pages_per_day: int | None = Field(default=None, ge=1, le=50)  # day_archive에서 날짜당 읽을 페이지 수. 없으면 끝까지(max_pages)
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
    feed: str | None = Field(default=None, pattern=r"^https?://")
    # list_origin: RSS를 쓰지 않고 날짜별 목록(backfill.day_archive)에서 제목, 원문 링크를 모은 뒤 본문은 원문 링크에서(GeekNews)
    fetch: Literal["feed_full", "feed_summary", "feed_title", "list_origin"]
    backfill: Backfill = Backfill(method="rss_only")
    request_interval_s: float | None = Field(default=None, ge=1, le=60)  # 이 소스 도메인의 요청 간격(기본 1초)
    note: str | None = None

    @model_validator(mode="after")
    def _mode(self) -> TextSource:
        if self.fetch == "list_origin":
            if self.feed is not None:
                raise ValueError("list_origin은 RSS(feed)를 쓰지 않음")
            if self.backfill.method != "day_archive":
                raise ValueError("list_origin은 날짜별 목록(day_archive)으로 받음(매일 수집과 백필 모두)")
        elif self.feed is None:
            raise ValueError(f"{self.fetch}에는 feed가 필요함")
        return self


class VideoBackfill(Strict):
    method: Literal["rss_only", "channel_listing"]
    max_videos: int = Field(default=60, ge=1, le=500)
    note: str | None = None


class VideoSource(Strict):
    id: str
    name: str
    channel_id: str = Field(pattern=r"^UC[\w-]{22}$")
    feed: str = Field(pattern=r"^https?://")
    backfill: VideoBackfill = VideoBackfill(method="rss_only")
    note: str | None = None


class Trending(Strict):
    source: Literal["github_trending_page"]
    url: str = Field(pattern=r"^https://github\.com/trending")


class TrackedRepo(Strict):
    repo: str = Field(pattern=r"^[\w.-]+/[\w.-]+$")


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


# ---------- filter.yaml (S2 임베딩 관련성 필터) ----------
class Interest(Strict):
    keyword_id: str = Field(pattern=r"^[a-z0-9-]+$")
    text: str = Field(min_length=10)  # 관심사 설명 1~2문장. 쿼리로 임베딩


class FilterConfig(Strict):
    model: str = Field(min_length=1)  # 임베딩 모델(sentence-transformers 이름)
    instruction: str = Field(min_length=1)  # 쿼리 쪽 지시문(Qwen3-Embedding 모델 카드 방식)
    doc_chars: int = Field(default=1000, gt=0)  # 글 입력 = 제목 + 요약 + 본문 앞 doc_chars자
    drop_below: float = Field(ge=-1, le=1)  # 키워드 통과 + 점수 < drop_below → drop
    rescue_above: float = Field(ge=-1, le=1)  # 키워드 걸러짐(no_keyword) + 점수 ≥ rescue_above → keep
    thresholds_status: Literal["provisional", "confirmed"] = "provisional"  # 라벨로 확정 전에는 잠정
    thresholds_basis: str = ""  # 문턱값 근거 한 줄(리포트와 같이)
    interests: list[Interest] = Field(min_length=1)
    # URL 중복 연결의 기준 항목: 원본에 가까운 쪽. 소스 종류(sources.yaml kind) 순위, source_kind로 소스별 덮어쓰기
    origin_rank: list[str] = ["primary", "blog", "news", "curation"]
    source_kind: dict[str, str] = {}
    similar_pairs: int = Field(default=30, ge=0)  # 리포트에 남길 유사 쌍 수(S5 묶기 재료)
    batch_size: int = Field(default=16, gt=0)

    @model_validator(mode="after")
    def _check(self) -> FilterConfig:
        if self.rescue_above < self.drop_below:
            raise ValueError("rescue_above는 drop_below 이상이어야 함(걸러진 글을 통과 글보다 쉽게 살리지 않게)")
        bad = sorted({k for k in self.source_kind.values() if k not in self.origin_rank})
        if bad:
            raise ValueError(f"source_kind에 origin_rank 밖 종류: {', '.join(bad)}")
        return self


# ---------- deep.yaml (S3 밤 깊게 보기 예산과 상한) ----------
MAX_DEPTH_ALL = 4  # 전체 깊이 상한(코드 상수). deep.yaml의 max_text_depth는 이 아래로만


class DeepConfig(Strict):
    video_minutes: int = Field(ge=0)  # 밤 하나에 처리할 영상 분(skip 제외, 60분 넘는 영상은 처리 구간만)
    slide_videos: int = Field(ge=0)  # whisper+slides 영상 수
    vlm_frames: int = Field(ge=0)  # 슬라이드 판독 프레임 총수
    text_items: int = Field(ge=0)  # 글 분석가 항목 수
    text_tool_calls_per_item: int = Field(ge=1)
    repo_items: int = Field(ge=0)
    repo_tool_calls_per_item: int = Field(ge=1)
    default_text_depth: int = Field(ge=1)
    max_text_depth: int = Field(ge=1, le=MAX_DEPTH_ALL)
    plan_share: float = Field(default=0.8, gt=0, le=1)  # 계획은 예산의 이 비율까지(나머지는 재시도 몫)
    lookback_days: int = Field(default=7, ge=1)  # 계획 입력: day 포함 최근 며칠의 영상·글

    @model_validator(mode="after")
    def _depths(self) -> DeepConfig:
        if self.default_text_depth > self.max_text_depth:
            raise ValueError("default_text_depth가 max_text_depth보다 큼")
        return self


FILES: dict[str, type[BaseModel]] = {
    "models.yaml": ModelsConfig,
    "budget.yaml": BudgetConfig,
    "sources.yaml": SourcesConfig,
    "keywords.yaml": KeywordsConfig,
    "link_kinds.yaml": LinkKindsConfig,
    "filter.yaml": FilterConfig,  # S2
    "deep.yaml": DeepConfig,  # S3
    "video.yaml": VideoConfig,  # S4
    "brief.yaml": BriefConfig,  # S5
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
    """FILES의 설정 파일 전부 검증하고 오류를 모두 모은다."""
    errors: list[ConfigError] = []
    for name, cls in FILES.items():
        path = (config_dir or ROOT / "config") / name
        try:
            cls.model_validate(_read_yaml(path))
        except ConfigError as e:
            errors.append(e)
        except ValidationError as e:
            errors.extend(_errors(name, e))
    if not errors:
        errors += _cross_check(config_dir)
    return errors


def _cross_check(config_dir: Path | None) -> list[ConfigError]:
    """파일 사이 참조: filter.yaml 관심사의 keyword_id는 keywords.yaml에 있어야 한다."""
    kw = {k.id for k in load("keywords.yaml", config_dir).keywords}
    flt = load("filter.yaml", config_dir)
    return [ConfigError("filter.yaml", f"interests[{i}].keyword_id", f"keywords.yaml에 없는 키워드 '{x.keyword_id}'")
            for i, x in enumerate(flt.interests) if x.keyword_id not in kw]


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


# 라벨 파일 labeler 칸: 이 값이 아니면(예: opus-5.5, 리뷰 세션 2차 채점) 그 라벨로 낸 일치율·문턱값은 잠정
HUMAN_LABELERS = {"human", "사람", "user", "사용자"}


def labeler_info(rows: list[dict[str, str]]) -> dict[str, Any]:
    """채운 라벨 행들의 labeler 목록과 잠정 여부."""
    names = sorted({(r.get("labeler") or "").strip() for r in rows} - {""})
    return {"labelers": names, "provisional": any(n.lower() not in HUMAN_LABELERS for n in names)}


SECRET_NAMES = ("OPENROUTER_API_KEY", "GITHUB_TOKEN")


def redact_secrets(data: bytes) -> bytes:
    """녹화 저장 전: 비밀 값(.env, 환경 변수)이 본문에 있으면 [REDACTED]로. 값은 출력하지 않는다."""
    names = set(SECRET_NAMES)
    if SECRET_FILE.exists():
        names |= {line.partition("=")[0].strip() for line in SECRET_FILE.read_text(encoding="utf-8").splitlines()
                  if "=" in line and not line.lstrip().startswith("#")}
    for name in names:
        value = get_secret(name)
        if value and len(value) >= 8:
            data = data.replace(value.encode(), b"[REDACTED]")
    return data


def current_spec(override: str | None = None, default: str = "S0") -> str:
    """--spec, 없으면 환경변수 TRENDSIT_SPEC, 없으면 명령의 기본 스펙."""
    return override or os.environ.get("TRENDSIT_SPEC") or default
