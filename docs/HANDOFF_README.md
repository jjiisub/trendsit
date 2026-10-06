# TrendsIT 작업 묶음 (Claude Code 전달용)

맥의 Claude Code에 이 폴더를 주고 이렇게 말하면 된다.

> 이 폴더의 README.md를 읽고, docs/03_TASK.md 지시서대로 진행해줘.

## 읽는 순서
1. `docs/01_CONTEXT.md`: 프로젝트 전체 맥락 (프로젝트 루트의 `CLAUDE.md`가 된다)
2. `docs/02_DESIGN.md`: 화면 디자인 명세. `mockups/`의 HTML 8개를 브라우저로 열어 같이 본다
3. `docs/03_TASK.md`: **이번 작업 지시서.** 이 문서의 0번 범위만 수행한다

## 이번 작업 한 줄
예시 데이터(`data/trendsit-example.json`, GeekNews 글 기반 2주치 브리핑 + 소스, 키워드, 실행 기록)로 정적 사이트를 생성하고 `https://trendsit.jiseop.com`에 공개한다.

## 폴더
    README.md
    docs/01_CONTEXT.md   맥락
    docs/02_DESIGN.md    디자인
    docs/03_TASK.md      이번 요구사항과 단계
    data/trendsit-example.json   예시 데이터
    data/make_data.py            예시 데이터 생성 스크립트 (참고)
    mockups/home-mobile.html          홈 모바일
    mockups/topic-mobile.html         토픽 페이지 모바일
    mockups/home-pc.html              홈 PC
    mockups/sources-mobile.html       소스
    mockups/keywords-mobile.html      키워드
    mockups/runs-week-mobile.html     실행 기록 메인 (이번 주차, 메뉴에서 바로 열림)
    mockups/runs-weeks-mobile.html    실행 기록 상위 (주차별)
    mockups/runs-detail-mobile.html   실행 기록 하위 (실행 1건 판단 상세)
