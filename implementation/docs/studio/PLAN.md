# Interactive Investment Studio Implementation Plan

**Goal:** 기존 엔진에 연결된 한국어 데모 프론트엔드를 완성한다.
**Architecture:** 로컬 REST 어댑터 + 합성 fixture + 독립 정적 UI. 기존 운영 경로는 수정하지 않는다.
**Tech Stack:** Python 표준 라이브러리, HTML, CSS, JavaScript, Playwright.
**Spec:** [DESIGN.md](DESIGN.md)

## Constraints
- QGV v2 프리셋/결측/가치 함정 관문을 그대로 사용.
- DEMO 지속 표시, TARGET와 가상 ACTUAL 분리, 매크로 참고 표시.
- 공개 빌드·실데이터·개인 저장소·Frozen 계약 변경 없음.

## Review focus
- 납입금이 투자 수익에 포함되지 않으며 양 비교곡선에 동일한 현금 흐름 적용.
- 0과 결측을 구분; 잘못된/비유한 입력 거부.
- 빠른 반복 실행에서 이전 요청이 새 결과를 덮지 않음.
- 모바일 표 내부만 스크롤; 모든 탐색과 검색 키보드 사용 가능.
- 합성 뉴스/성과가 실제 사실/검증으로 오인되지 않음.

## Task 1: Local engine adapter
- [x] `tests/test_studio.py`에 합성 출처·원본 TARGET·v2 점수·기술/매크로·시뮬레이션 납입/결측/입력 검증 테스트를 쓰고 실패 확인.
- [x] `src/investment_system/product/studio.py`에 `studio_snapshot(preset='balanced')`, `simulate(payload)`, `main()` 구현.
- [x] 단위 테스트 실행.

## Task 2: Interactive frontend
- [x] `product/studio_assets/{index.html,studio.css,studio.js}`에 대시보드·모든 모듈·검색·필터·관심·기업 상세·설정·CSV 구현.
- [x] `tools/studio_browser_test.js`로 API 연결, 시뮬레이션 변경, 빈 결과, 반응형, 키보드/에러 상태 검사.

## Task 3: Verification and handoff
- [x] 기존 관련 엔진 회귀 검사 및 브라우저 검사, 데스크톱/모바일 스크린샷.
- [x] README·검증 결과 및 모듈 연결표 기록. 작업 브랜치 commit/push/PR, 배포/병합 없음.
