# E0 감사 — 2026-10-29

범위: 사용자 직접 승인 E0/E1-A. 기본 브랜치
`claude/investment-system-top500-validation-alrugm`, 시작 HEAD
`282382a76c963e885bfd090d3eec79543bcd90e0`.
START_HERE → DIRECTION_CHANGES → WORKING_RULES → CURRENT_HANDOFF → 기능 명세/현황 →
USER_DECISIONS_PENDING과 실제 코드·GitHub PR/규칙을 대조했다.
공용 문서는 수정하지 않았다. 작업 계획·결정은 [E1A_CONTRACT](E1A_CONTRACT.md).

## 최신 상태·소유권

아래는 이번 세션 GitHub API 재조회 결과다. CURRENT_HANDOFF의 옛 열린 PR 표보다 최신이다.

| PR | 상태 / HEAD | 소유·충돌 경계 |
| --- | --- | --- |
| #417 | Draft/Open `ec9788a6b134a6fd930b5214fef4e18509338052` | 기존 오프라인 연구 엔진, 수정·복제하지 않음 |
| #418 | Draft/Open `ef745b96621b06802c7055eb64da76f64f2800db` | 두 연구 모집단·CPI 기준 가정·보고서 명세, 수정하지 않음 |
| #415 | Merged 10/29 10:27 UTC, merge `6ab756d6` | Main 프론트엔드 QGV, 이미 기준 HEAD에 포함 |
| #419 | Merged 10/29 10:28 UTC, merge `d8553b58` | Main 공용 검색, Universe504 범위 유지 |
| #420 | Merged 10/29 10:29 UTC, merge `282382a7` | Main 시각 양식; 배포 실행하지 않음 |
| #393/#400/#403/#404/#405/#411 | Open | Main 중앙 V 사슬·가드·워크플로·판독기·TARGET 확정, 접근 금지 |
| #392/#361 | Open | 식별 키 이전·기기 시세/분할 경계; 수정하지 않음 |

#400/#403/#404 changed-files API도 확인했다. `providers/iex_hist.py`,
`providers/iex_monthend.py`, `qgv/qgv_official.py`, `public_price_boundary.py`,
`tools/pages_*guard.py`, `tools/qgv_official_*`, `.github/workflows/*`,
`docs/qgv_scoring_standard/*`가 충돌 가능 영역이다. 이번 신규 경로와 겹치지 않는다.
프론트엔드 `product/web_app/`, `product/web_assets/`, root 공용 문서·CI 목록도 제외한다.

AUTONOMY_MODE는 READ_ONLY 그대로다. 이번 이름 붙은 관측 세션의 작업 브랜치 승인만
사용하며 RUN·무인 실행 권한으로 해석하지 않는다(기존 10/8 직접 지시 처리 관례도 확인).
ruleset `24499602`를 재조회했다: active, canonical PR 필수,
`repository-guard` 필수, 승인 수 0, bypass actor 없음, current_user_can_bypass=never.
기술적 리뷰 승인 수와 오너 병합 승인은 별개다. 병합·배포는 이 작업에 포함되지 않는다.

## 실제 기존 경로·재사용 판단

아래 경로는 모두 `implementation/` 기준이다. 가정한 identity.py는 없으며 실제 resolver를 쓴다.

| 실제 경로 | 발견한 기능 | 이번 사용 / Main 후속 |
| --- | --- | --- |
| `src/investment_system/universe/resolve.py` | cik10/company_id_for, 날짜별 alias, 현재 map을 과거 종료 구간에 소급하지 않는 resolver | 엄격한 ASCII CIK 검사 뒤 **company_id_for 직접 호출**; 역사 alias는 E1-B 식별 증거로 재사용 |
| `src/investment_system/contracts/universe.py` | 발행사 중심 UniverseMember/UniverseSnapshot, dirty-set DataEvent | 공개 계약 비교만; 증권·상장 사건 필드가 없어 교체/확장하지 않음 |
| `src/investment_system/universe/engine.py`, `events.py`, `recon.py` | 기존 PIT roster, QGV dirty set, 일일 대조 | 공식 계산과 결합돼 있어 변경하지 않음; E1-B에서 별도 카탈로그 diff를 입력으로 연결할 수 있음 |
| `src/investment_system/universe/sources.py` | 역사 구성 CSV·PIT shares, 시총 top-N 연구 | 기존 경로 보존. 현재 504와 다른 옛 연구 정책을 새 카탈로그 정책으로 사용하지 않음 |
| `src/investment_system/providers/sec_universe_collection.py` | UniverseRegistry/UniverseIssuer, CIK 충돌 차단, 7샤드, PSKY issuer-pinned alias | **504에 고정된 registry이므로 확장에 직접 호출 금지**; pacing client·실패코드 설계 재사용 후보 |
| `src/investment_system/providers/sec_collection.py` | 32 MiB 제한·중복 JSON 키 거절·고정 오류·429/5xx retry·0.2초 간격 | E1-B 어댑터에서 재사용할 bounded transport. 이번 호출 없음 |
| `src/investment_system/universe/sec_universe_shares.py` | 504 코드/7샤드, 상장종료·CIK 충돌 철회, 이전 관측 보존 | 운영 변경 금지. 새 카탈로그를 여기에 넣지 않음 |
| `src/investment_system/universe/universe_codes_v1.json`, `universe_codes.py` | 고정 504 코드·공개 목록 검증 | 불변 회귀시험에서 재사용; 카탈로그 연결·쓰기 없음 |
| `src/investment_system/universe/private_subset.py` | 실제 존재. ListingSeed에 issuer/security/listing ID, 비공개 M3·단위/주식종류 검사 | 원가격·Sheet 경계와 결합돼 있어 가져오지 않음. E2에서 ID·기준 대사 설계 재사용, 계산 복제 없음 |
| `src/investment_system/universe/share_class_groups.py` | 경제적 동일 종류주 그룹, 비상장 종류 합산 정책 | 카탈로그 수와 회사 시총 합산은 별개. E2 승인 전 이 정책을 전체시장에 일반화하지 않음 |
| `src/investment_system/providers/sec_cover_shares.py`, `sec_m3_adapter.py` | 표지 종류·주식수 증거 | E2 후보, 실제 주식수 계산·수집 없음 |
| `src/investment_system/providers/sec_submissions.py`, `sec_vintage.py`, `sec_filing_timing.py` | accession·접수/공개 시각, filing vintage, 관측 시각의 한계 | PIT 의미 재사용. 관측 시각을 역사 최초 공개로 바꾸지 않음 |
| `src/investment_system/universe/sec_qgv2.py` | 504 단면 Q·G 재계산, calc_version·NA·이전 관측 검증 | 수정·호출·점수 산출 없음 |
| `src/investment_system/validation/file_store.py`, `forward_ledger.py` | 원장·불변 결정 저장/후속 성과 | 새 카탈로그 저장소로 복제하지 않음. E1-A는 파일 I/O 자체가 없음 |
| `tools/sec_universe_shares.py`, `tools/public_screens_pipeline.py`, `tools/pages_artifact_guard.py` | 운영 수집·게시·Pages 허용 경계 | 변경 없음; 추가 카탈로그 파일을 자동 게시하지 않음 |

#417 브랜치는 읽기 전용으로 fetch해서 `research/qgv_backtest/pit_adapter.py`,
`runner.py`, `reporting.py`, `tools/qgv_backtest_research.py`를 확인했다.
membership 입력 `cik, security_id, start, end(exclusive), known_at`가 카탈로그 소비 계약의
기존 연결점이다. 이번 원장을 그 엔진에 강제 연결하지 않으며, Main이 권리·당시
available_at 증거가 있는 interval만 이 모양으로 어댑트해야 한다. 거래일 단위 변환 시
UTC 날짜를 무조건 잘라 사용하지 말고 미국 거래 세션 경계를 확인해야 한다.
#418의 U-BOOK200/U-SPX-HIST·2009 CPI-U 연평균 $200m은 그대로 **사전 등록 연구 가정**이다.

## 운영 영향 기준선

Universe504 = S&P 500 구성에서 출발해 고정한 504코드 목록이다. 지수 추종·시총 재선정이 아니다.
현행 `sec-qgv2.json`/`sec-universe-shares.json`은 기존 생산자가 계속 소유한다.
코드에 있는 가격 요청 경계(기기에서 클릭할 때), 7샤드·뉴욕 관측일,
원장·TARGET v0/v1·calc_version·공식 V 첫 게시 승인 조건을 바꾸지 않는다.

기준 HEAD와 비교해 기존 tracked 파일 수정/삭제가 **0개**인지 최종 인계에서 검증한다.
추가로 504 파일·QGV·원장 바이트와 기존 관련 시험을 직접 검사한다.
이는 로컬 소스 불변 검증이며 공개 사이트·실환경 최신 데이터 검증을 의미하지 않는다.

공급원·비용·권리는 [SOURCE_RIGHTS](SOURCE_RIGHTS.md), E1-B/E2 연결 조건은
[E1B_E2_PLAN](E1B_E2_PLAN.md), 실제 시험 결과와 Main 요청은 [HANDOFF](HANDOFF.md)에 둔다.
