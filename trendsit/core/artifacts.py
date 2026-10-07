"""역할 입력, 출력 스키마. 역할 md의 input/output 이름으로 찾는다."""

from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .textclean import clean_markdown


class RoleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


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

    @classmethod
    def fallback(cls, reason: str, inp: Any) -> Self:
        """상한 도달, 실패 시 대체 출력. 역할마다 정의."""
        raise NotImplementedError(f"{cls.__name__}에 대체 출력이 없음")


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
