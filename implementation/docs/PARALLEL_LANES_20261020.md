# 병렬 작업 영역 — QGV · 기술적 분석 · 매크로 (2026-10-20)

근거: 사용자 결정 2026-10-20 "기술적 분석·매크로 병렬 구현". 원문 요지는 [USER_DECISIONS_PENDING](USER_DECISIONS_PENDING.md) "결정됨 — 2026-10-20"에 있다.
관리: Main(Claude Code). 이 표는 영역이 바뀔 때마다 Main이 고친다.

## 0. 바뀐 것과 바뀌지 않은 것

- **바뀐 것:** 기술적 분석의 "TARGET 확정 + 정기 실행 7회 성공 후 착수" 조건은 더 이상 구현을 막지 않는다. 구현·시험·미리보기는 지금 한다.
- **그대로인 것:**
  - 공식 판정 활성화와 투자 의사결정 사용 조건은 따로 남는다.
  - TARGET 확정과 운영 결함 수정이 먼저다.
  - M-RULE C는 가설이다. 매크로 게이트 재가동은 결과 보고 뒤 사용자 승인 대상이다.
  - 가격·가격 파생값·개인 자료는 저장소·Pages·Actions 로그에 넣지 않는다. 주문·매매 기능은 만들지 않는다.
- 한 영역의 대기는 다른 영역의 중단 사유가 아니다.

## 1. 영역 표

| 영역 | 담당 | 브랜치 | 주로 고치는 파일 | 공통 의존성 |
|---|---|---|---|---|
| A. QGV·공통 V·리더보드·포트폴리오 선정 | Main | 대기열 PR별 브랜치(#347 · #346 · #341 · #340 · #344 등) | `qgv-scores.js`, `leaderboard-screen.js`, `portfolio-screen.js`, `playbook-*` | 가격 접근(`price-store.js`·`private-history.js`), 데이터 계약 |
| B1. 기술적 분석 엔진 | 작업자 B1 | `claude/ta-bars-core` → `claude/ta-patterns-v1`(쌓음) | 새 `chart-bars.js`, 패턴 규칙·피벗·상태 기계·공식 탐지 이력, Python 참조 `technical/` | `chart-indicators.js`(ATR14 재사용), `private-history/1` 응답 형식 |
| B2. 기술적 분석 차트 화면 | 작업자 B2 | `claude/ta-renderer` | Lightweight Charts 5.2.1 벤더링·고지, 렌더러 어댑터, `technical-chart.js`(SVG 대체 유지), 설정 패널 | B1의 `ChartBars`(주봉), Pages 가드 고정 |
| C1. 매크로 순환 화면 | 작업자 C1 | `claude/macro-cycle-ring` | 새 순환 링 모듈·css, 링 브라우저 시험 | 국면 모델 초안(#339), `macro-lights.js` 참고 모드 |
| C2. 매크로 근거 지표 | 작업자 C2 | `claude/macro-evidence`(코드) + 워크플로 PR(승인 필요) | 근거 지표 수집기, 공개 `macro-evidence` 계약, 관측 그래프·근거 세로선 | 기존 `--macro-v0` 수집기, FRED·원기관 권리 기록 |

## 2. 공통 파일 — 통합 순서는 Main이 정한다

- `app.js`, `index.html`, `ia-screens.js`, `style.css`: 작업자는 최소 연결 지점만 넣고 PR 본문에 적는다.
- 데이터 계약(`FRONTEND_DATA_CONTRACT.md`)과 가격 접근 모듈(`price-store.js`, `private-history.js`): 바꿀 때는 Main이 순서를 잡는다.
- `implementation/tools/ci_browser_tests.txt`, Pages 가드 고정값 충돌, `CURRENT_HANDOFF.md`, 이 문서, `USER_DECISIONS_PENDING.md`: Main만 고친다.
- 가드 고정값은 저장소 도구로 다시 만든다. 가드를 약하게 만들지 않는다.

## 3. 중복 금지

- 주봉 묶기는 B1의 `chart-bars.js` 하나만 쓴다. B2는 직접 만들지 않는다.
- ATR·이동평균 등 지표는 기존 `chart-indicators.js`를 쓴다.
- 매크로 수집은 기존 `--macro-v0` 경로를 넓힌다. 이미 받는 계열을 다시 받는 수집기를 만들지 않는다.
- 순환 링(C1)과 관측 그래프·근거 세로선(C2)은 나눠 만든다. C2가 자료 접근 함수를 내고 C1이 거기에 붙는다.

## 4. 공통 데이터 — 기능별로 따로 판단

- 공통 V용 가격 확보가 끝나야 차트를 시작할 수 있는 것은 아니다.
- 기술적 분석: 실제 가격은 기기에서만 비공개 Worker로 받는다(RAM). 저장소·시험은 합성 봉만 쓴다. 합성 미리보기는 "합성 자료 · 미리보기 · 실데이터 검증 아님"으로 표시한다.
- 가격 기준 연속성: Worker가 분할 이벤트를 아직 주지 않는다. 그래서 지금은 모든 창이 `PRICE_BASIS_CONTINUITY_UNCONFIRMED`(판정 불가)다. Worker 분할 이벤트(P1-W)는 Worker 배포라 별도 승인 대상이다.
- 매크로: 공개 공식 통계는 Pages에 게시할 수 있다. 시장 가격 기반 계열은 기존 B-PRICE 경계대로 기기 전용이다. 권리가 불분명한 계열은 탐색 전용 또는 NOT_AVAILABLE로 두고 결정 항목으로 올린다.

## 5. 승인 경계

| 종류 | 처리 |
|---|---|
| 문서·시험·화면 PR, 이번 결정으로 승인된 기술적 분석·매크로 구현 PR | 필수 6체크 통과 후 Main이 바로 병합. 공식 판정·게이트는 켜지 않음 |
| 계산·워크플로·경계·결정 PR | 사용자 승인 뒤 병합 (예: C2 워크플로 PR, Worker 분할 이벤트) |
| 새 방법론·공급원 권리·유료 계약 | 구현하지 않고 결정 항목으로 분리 |
