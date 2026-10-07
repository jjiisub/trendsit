# 저장소 규칙

## 커밋
- 한 줄: `<종류>(s<n>): <무엇을>`. 종류는 feat / fix / docs / test / refactor / chore
  - 예: `feat(s1): GeekNews 목록 페이지 백필`
- 여러 단계 스펙은 단계 이름을 본문 첫 줄에(예: `1a S0 보완`)
- 비밀(`.env`, 키), `data/`의 실행 산출물(DB, 캐시)은 커밋하지 않는다

## 브랜치와 PR
- 스펙마다 `s<n>-<짧은이름>` 브랜치 → PR → 설계 세션 리뷰 → 사용자 병합
- PR 설명은 `.github/pull_request_template.md` 양식. CI(ruff + pytest)가 초록이어야 리뷰
- 스펙 완료 기준은 `scripts/verify_s<n>.sh`(관문 A) 전부 PASS + 관문 B 문턱값(`docs/handoff/COMMON.md` 2장)

## 코드
- ruff(`pyproject.toml`: E, F, W, I, B, UP, 줄 길이 검사는 끔), pytest. 테스트는 네트워크와 비밀 없이 돈다(LLM은 모의 전송, HTTP는 저장한 응답)
- 모델 이름과 제공사는 `config/models.yaml`에만. 반드시 지켜질 것(스키마, 상한, 예산, 보안)은 코드, 모델이 알아야 할 것은 `roles/*.md`
- 역할 md는 `docs/reference/prompt_guide.md` 형식. `check-config`가 검사
- 문체: 요약, 개요는 "~다", 포인트, 화면 문구, 로그는 명사형(`skills/style_ko.md`)
