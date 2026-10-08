"""역할 입력, 출력 스키마. 역할 md의 input/output 이름으로 찾는다."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

from .textclean import clean_markdown

if TYPE_CHECKING:
    from .context import Ctx


def _plain(v: Any) -> Any:
    """기록용으로 pydantic 값을 JSON으로 바꿀 수 있는 값으로."""
    if isinstance(v, BaseModel):
        return v.model_dump()
    if isinstance(v, list):
        return [_plain(x) for x in v]
    return v


class RoleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # 도구 에이전트의 입력별 상한(코드가 지킴). 기본은 역할 md 설정 그대로
    def tool_names(self, names: list[str]) -> list[str]:
        """이 입력에서 허용할 도구(예: 레포 분석가 max_depth 1이면 일부만)."""
        return names

    def depth_limit(self, default: int | None) -> int | None:
        """이 입력의 문서 깊이 상한(예: 편집장 계획의 항목별 max_depth)."""
        return default

    def tool_call_limit(self, default: int | None) -> int | None:
        """이 입력의 도구 호출 상한(예: deep.yaml의 항목당 상한). 역할 md 값보다 늘리지는 않는다."""
        return default

    def depth_seed(self) -> list[tuple[str, list[str]]]:
        """이미 읽은 시작 문서(깊이 1)와 그 문서의 링크. 예: 글 분석가의 원래 글(본문은 1차 요약 때 읽음)."""
        return []


class Document(BaseModel):
    """문서형 자료. user 메시지에서 <document id source title url> 태그로 들어간다. id는 근거 id(rp:, it:, vd:)."""

    model_config = ConfigDict(extra="forbid")
    id: str
    source: str
    text: str
    title: str | None = None
    url: str | None = None


class RoleOutput(BaseModel):
    """모든 역할 출력의 공통 부모. log, attention은 실행 기록 화면의 원천."""

    model_config = ConfigDict(extra="forbid")
    log: str = Field(description="한 줄 기록. 명사형, 화면 문구 규칙")
    attention: bool = Field(default=False, description="사람이 확인해야 하면 true")

    # enforce가 바꾼 칸 기록과 enforce 전 원래 출력(평가가 모델 품질을 원래 출력으로 재도록)
    _enforced: list[dict[str, Any]] = PrivateAttr(default_factory=list)
    _raw: dict[str, Any] | None = PrivateAttr(default=None)

    @classmethod
    def fallback(cls, reason: str, inp: Any) -> Self:
        """상한 도달, 실패 시 대체 출력. 역할마다 정의."""
        raise NotImplementedError(f"{cls.__name__}에 대체 출력이 없음")

    def enforce(self, inp: Any, ctx: Ctx | None) -> Self:
        """코드 규칙(반드시 지켜져야 하는 것). 스키마 검증 뒤, 저장 전에 run_role/run_agent가 부른다(S1 리뷰 M2).

        기본은 그대로 반환. 역할이 덮어쓸 때는 칸을 직접 바꾸지 않고 fix()로 바꿔 기록이 남게 한다.
        """
        return self

    def fix(self, field: str, value: Any, rule: str) -> Self:
        """칸 하나를 바꾼 사본. 값이 같으면 그대로. 바꾼 내용은 enforced에 {field, before, after, rule}로 쌓인다."""
        before = getattr(self, field)
        if before == value:
            return self
        new = self.model_copy(update={field: value})
        change = {"field": field, "before": _plain(before), "after": _plain(value), "rule": rule}
        new._enforced = [*self._enforced, change]
        new._raw = self._raw
        return new

    @property
    def enforced(self) -> list[dict[str, Any]]:
        return list(self._enforced)

    def raw_dump(self) -> dict[str, Any]:
        """enforce 전 원래 출력. enforce가 바꾼 것이 없으면 지금 출력과 같다."""
        return dict(self._raw) if self._raw is not None else self.model_dump()


def apply_enforce(out: RoleOutput, inp: Any, ctx: Ctx | None) -> RoleOutput:
    """원래 출력을 보관한 뒤 역할의 enforce를 적용한다."""
    raw = out.model_dump()
    fixed = out.enforce(inp, ctx)
    if fixed.enforced:
        fixed._raw = raw
    return fixed


README_THIN_CHARS = 200  # 정리한 README 본문이 이보다 짧으면 사람 확인(attention). S1 리뷰 M2


# ---------- repo_oneliner ----------
class RepoOnelinerInput(RoleInput):
    full_name: str
    description: str | None = None
    topics: list[str] = []
    readme_head: Document  # 픽스처와 CLI 입력은 README 원문 문자열. 아래에서 기호를 걷어 내고 rp:{full_name} 문서로

    @model_validator(mode="before")
    @classmethod
    def _readme_as_document(cls, data: Any) -> Any:
        """README 원문의 마크다운·HTML 기호를 걷어 낸 본문을 모델에 준다(설계 결정 S1 Q3)."""
        if isinstance(data, dict) and not isinstance(data.get("readme_head"), dict | Document):
            data = {**data, "readme_head": Document(id=f"rp:{data.get('full_name', '')}", source="GitHub README",
                                                    text=clean_markdown(data.get("readme_head") or ""))}
        return data


class RepoOneliner(RoleOutput):
    basis: str = Field(max_length=120, description="README 본문이나 description에서 근거가 된 구절을 그대로 옮김. 근거가 없으면 빈 문자열")
    oneliner: str = Field(max_length=60, description="무엇을 하는 레포인지 한 문장. 명사형 60자 이내. 근거가 없으면 빈 문자열")

    @classmethod
    def fallback(cls, reason: str, inp: RepoOnelinerInput) -> Self:
        text = (inp.description or inp.full_name)[:60]
        return cls(basis="", oneliner=text, log=f"{inp.full_name}: 설명 문구로 대체 ({reason})", attention=True)

    def enforce(self, inp: RepoOnelinerInput, ctx: Ctx | None) -> Self:
        """정리한 README 본문이 README_THIN_CHARS자 미만이면 근거가 얇으므로 attention 고정(S1 리뷰 M2)."""
        if len(inp.readme_head.text.strip()) < README_THIN_CHARS:
            return self.fix("attention", True, f"README 본문 {README_THIN_CHARS}자 미만")
        return self


# ---------- lookup_agent (테스트용) ----------
class LookupInput(RoleInput):
    question: str


class LookupAnswer(RoleOutput):
    doc_id: str | None = Field(description="조건을 처음 만족한 문서 id. 허용 깊이 안에서 못 찾으면 null")

    @classmethod
    def fallback(cls, reason: str, inp: LookupInput) -> Self:
        return cls(doc_id=None, log=f"답 없이 종료: {reason}", attention=True)


# ---------- 평가 채점자 ----------
class JudgeInput(RoleInput):
    """채점 대상 역할의 입력(근거 문서 + 짧은 칸)과 그 출력. 역할과 무관한 형태."""

    source_documents: list[Document]
    source_fields: dict[str, Any]
    output: dict[str, Any]


class QuestionVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(description="채점표의 질문 id 그대로(예: Q1)")
    critique: str = Field(description="한 줄 비평. 근거 문서의 어느 부분과 비교했는지")
    verdict: Literal["pass", "fail"]


class CriterionScore(BaseModel):
    model_config = ConfigDict(extra="forbid")
    criterion: str = Field(description="보고용 점수표의 항목 이름 그대로")
    reason: str = Field(description="점수 근거 한 줄")
    score: int = Field(ge=1, le=5, description="1~5")


class JudgeResult(RoleOutput):
    verdicts: list[QuestionVerdict]  # 통과 기준
    scores: list[CriterionScore]  # 보고용


INPUTS: dict[str, type[RoleInput]] = {
    c.__name__: c for c in (RepoOnelinerInput, LookupInput, JudgeInput)
}
OUTPUTS: dict[str, type[RoleOutput]] = {
    c.__name__: c for c in (RepoOneliner, LookupAnswer, JudgeResult)
}


# ---------- 스펙별 스키마 모듈 합치기(COMMON 9장) ----------
# 스펙마다 자기 파일에 입력·출력 스키마를 두고 INPUTS, OUTPUTS 튜플을 내놓는다. 여기에는 합치는 줄만.
# 아직 없는 모듈은 건너뛴다(병행 브랜치가 먼저 병합되는 경우). 같은 이름이 다른 클래스로 들어오면 오류.
# 스키마 모듈은 무거운 선택 의존성(numpy, torch 등)을 import하지 않는다. 안 그러면 그 묶음이 없는 환경에서 모든 명령이 멈춘다.
def register_schemas(module: str, inputs: tuple[type[RoleInput], ...], outputs: tuple[type[RoleOutput], ...]) -> None:
    """스펙별 모듈이 끝에서 부른다. 같은 이름이 다른 클래스로 들어오면 오류."""
    for table, classes in ((INPUTS, inputs), (OUTPUTS, outputs)):
        for c in classes:
            if table.get(c.__name__, c) is not c:
                raise ValueError(f"스키마 이름 '{c.__name__}'이 {module}과 다른 모듈에서 겹침")
            table[c.__name__] = c


def _merge(module: str) -> None:
    """모듈을 읽어 등록되게 한다. 그 모듈이 지금 읽히는 중(순환)이면 끝에서 스스로 register_schemas를 부른다."""
    import importlib
    import sys

    name = f"{__package__}.{module}"
    if name in sys.modules and not hasattr(sys.modules[name], "INPUTS"):
        return  # 읽히는 중: 모듈 끝의 register_schemas가 등록
    try:
        mod = importlib.import_module(name)
    except ModuleNotFoundError as e:
        if e.name == name:
            return
        raise
    register_schemas(module, tuple(getattr(mod, "INPUTS", ())), tuple(getattr(mod, "OUTPUTS", ())))


_merge("artifacts_text")  # S2~S3
_merge("artifacts_repo")  # S2~S3
_merge("artifacts_video")  # S4
