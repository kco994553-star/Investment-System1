# Cockpit IA v1 · Design Source

기준일: 2026-10-09 · 요구사항 상태: `REQUIREMENT_IDENTIFIED_NOT_REAUDITED`

## 1. 디자인 기준과 접근 경계

현재 디자인 SSoT는 Claude의 owner-private canvas **「투자시스템 Cockpit 시안」**이다. 화면 기준은 S01~S12의 12개 화면이며, 저장소의 화면·탐색 요구사항은 [COCKPIT_IA_v1.md](COCKPIT_IA_v1.md)에 기록한다. canvas 접근·공유·수정은 owner가 관리한다. 이 문서는 private canvas 내용을 재접속·재감사했다고 주장하지 않는다.

비공개 URL·접근 토큰·개인 계좌·잔고·키·로그인 정보는 저장소에 기록하지 않는다. private URL을 이 문서·주석·예시·handoff에 복사하거나 공개 링크로 바꾸지 않는다. 저장소에 추가한 IA 문서는 요구사항 기록이며 canvas 접근 권한을 대신하지 않는다.

MagicPath는 과거 차트 SAMPLE·컴포넌트 시안·검토 기록의 역사적 출처다. 이후 Cockpit 디자인의 SSoT가 아니며 이 문서는 MagicPath 재연결·재작업·유료 사용 또는 비공개 자료 업로드를 승인하지 않는다. 과거 MagicPath/Figma/차트 검토 기록은 삭제하지 않고 당시 근거로 보존한다.

## 2. 기준별 소유권

| 기준 | 위치·역할 | 경계 |
|---|---|---|
| 디자인 SSoT | Claude owner-private canvas 「투자시스템 Cockpit 시안」 | owner 관리, private URL 미기록 |
| 화면·탐색 기준 | `implementation/docs/frontend_ia_v1/COCKPIT_IA_v1.md` | docs-only 제안, 사용자 PR 병합 승인 필요 |
| Macro 8축의 기존 기록 | `Macro System · Latest Consolidated Record v0.1.4 Candidate.md` §15 | 본문의 8축·6상태 확인; 엔진·운영 승격 아님 |
| 기존 renderer·검증 스택 | `implementation/experiments/chart-contract-v0.1/package.json`·`README.md` | Lightweight Charts 5.2.1, native SVG, Noto Sans KR, Playwright 1.58.2 유지; 새 의존성 없음 |
| 과거 IA·독립 검토 | IA 본문 §5의 실제 경로 목록 | Markdown 안내 1줄 외 원문 보존, 실제 legacy DOCX 변경 없음 |
| 계산·원본 계약·데이터 | 기존 각 owner의 계약·snapshot·판단 | canvas 또는 IA로 원점수·가중치·PIT·권한 변경 금지 |

## 3. 2026-10-09 사용자 결정

| 결정 | 문서에 보존한 내용 | 이번 범위에서 하지 않는 일 |
|---|---|---|
| 매크로 축 | Growth / Inflation / Liquidity / Monetary Policy / Credit / Labor / Fiscal / FX의 기존 8축. 각 축 Level / Direction / Momentum / Surprise / Stress / Confidence 보존 | 새 단일 Macro Score, 모델 방법론 변경·추가축·엔진 승격 |
| 디자인 정합성 | 사용자 보고: 시안의 8축 수정 완료. 임금은 Labor 하위, 생산성은 Growth 하위, 주식시장은 국면 참고 패널 | 임금/생산성/주식시장을 독립 축으로 추가; private canvas 직접 재감사·앱 구현 완료 주장 |
| 추가 축 | 필요하면 별도 방법론 버전으로 검토 | 화면 시안만으로 자동 채택 |
| 26E | ① 앱 시세·환율 수동 입력 + KRW 기준 표시 | 기능·환율 계산·feed 구현. 다른 ②/③ 대안 채택 |

### 기존 기술 스택과 색상 토큰

Lightweight Charts **5.2.1**, native SVG, Noto Sans KR, Playwright **1.58.2**를 유지한다.
아래는 사용자가 지정한 디자인 토큰 기록이며 앱 CSS를 변경하지 않는다.

| 토큰 | 값 |
| --- | --- |
| bg | #F4F4EF |
| surface | #FFFFFF |
| border | #E2E2DA |
| text | #17201D |
| muted | #5E6863 |
| primary | #1E4D43 |
| primary-soft | #E3EEEA |
| warn / warn-bg | #7A4600 / #FBEAD2 |
| info / info-bg | #1D4A80 / #DDE8F6 |
| placeholder | #8A938F |

## 4. 아직 없는 상세 시안

S02의 전략프로필·모델포트폴리오·관심기업·13F 상세 화면은 `OPEN`이고 세부 시안은 `NOT_AVAILABLE`이다. 해당 기능의 목적·진입점을 유지하되 12개 화면에 상세 설계가 완비됐다고 주장하지 않는다. S03 요약 8칸/12열, S06 필터 8개/9열, S07 영향 6항목, S10 지표 6개의 정확한 세부 배치는 근거 재감사 전 임의로 확정하지 않는다.

## 5. 후속 변경·검증 절차

사용자가 이 docs-only PR을 검토·병합한 뒤 후속 구현은 별도 요청·별도 PR에서 다룬다. 디자인 변경은 owner의 canvas 기준과 IA 요구사항을 함께 대조하고, 기존 원문에만 있는 요구는 IA 부록의 「이관 확인 필요」를 해소한다. 누락 항목을 묵시적으로 삭제하거나 새 완료율·수치·상태를 채우지 않는다.

후속 구현 검증은 모바일 390px·PC 1440px에서 탐색·원본 데이터·상태·접근성·빈 상태를 별도 확인한다. READ_ONLY·TARGET≠ACTUAL·결측≠0·확률≠신뢰도·Research≠Model·Backtest≠Forward·Macro Context≠QGV Base를 유지한다. 문서 작성·canvas 화면·기존 과거 테스트 기록은 실제 구현 완료, 브라우저 PASS, 운영 배포 또는 투자 유효성의 증거가 아니다.
