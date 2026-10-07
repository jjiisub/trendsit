"""역할 입력, 출력 스키마. 역할 md의 input/output 이름으로 찾는다."""

from __future__ import annotations

from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field


class RoleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


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
    readme_head: str = ""


class RepoOneliner(RoleOutput):
    oneliner: str = Field(max_length=60, description="무엇을 하는 레포인지 한 문장. 명사형, 60자 이내, README 근거로만")

    @classmethod
    def fallback(cls, reason: str, inp: RepoOnelinerInput) -> Self:
        text = (inp.description or inp.full_name)[:60]
        return cls(oneliner=text, log=f"{inp.full_name}: 설명 문구로 대체 ({reason})", attention=True)


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
    task_input: dict[str, Any]
    output: dict[str, Any]


class CriterionScore(BaseModel):
    model_config = ConfigDict(extra="forbid")
    criterion: str = Field(description="채점표의 항목 이름 그대로")
    reason: str = Field(description="점수 근거 한두 문장. 입력의 어느 부분과 비교했는지")
    score: int = Field(ge=1, le=5, description="1~5")


class JudgeResult(RoleOutput):
    scores: list[CriterionScore]


INPUTS: dict[str, type[RoleInput]] = {
    c.__name__: c for c in (RepoOnelinerInput, LookupInput, JudgeInput)
}
OUTPUTS: dict[str, type[RoleOutput]] = {
    c.__name__: c for c in (RepoOneliner, LookupAnswer, JudgeResult)
}
