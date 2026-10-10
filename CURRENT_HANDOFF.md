# 현재 인수인계 — 2026-10-10 (Claude Code 메인 개발)

메인 개발은 Claude Code가 맡는다(이전 코덱1·코덱2 역할 통합). 사용량이 떨어지면 이 파일만 보고 코덱스가 이어받을 수 있게 단위가 끝날 때마다 갱신한다. 이전 판(#155)의 상세 이력은 Git에 있다.

## 읽기 순서와 운영 경계

1. [WORKING_RULES.md](WORKING_RULES.md): 1인용 혼합 운영 규칙.
2. 이 파일: 실제 완료·미완료·의존·운영 상태.
3. [ROADMAP_2026Q4.md](implementation/docs/ROADMAP_2026Q4.md): 범위·연구 및 후속 정책. 진행 상태는 이 파일이 우선한다.
4. [DESIGN_CANVAS_SCREENS_v1.md](implementation/docs/cockpit_ia/DESIGN_CANVAS_SCREENS_v1.md): S01~S16 화면 정본.
5. 26E 결정 기록: [GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md](implementation/docs/pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md) GSQ-005~017.

병합 규칙(2026-10-10 사용자 지시): PR 단위로 push하고 **실행된 필수 체크 전부 성공·실패 0이면 자체 병합**. 단 **인증·배포·Worker·워크플로·공개 데이터 경계·26E 결정 기록 변경은 사용자 승인 후 병합**. force push·ruleset·AUTONOMY_MODE 변경(READ_ONLY 유지) 금지, 새 방법론·가중치·TARGET 임의 변경과 Holdout 사용 금지, 공개 저장소·Pages·Actions 로그에 가격·가격 파생값·개인 데이터 금지, Secret 값 출력 금지, 매수·매도·주문·이체 기능 금지, 결측은 NOT_AVAILABLE(0 대체 금지).

구조 원칙: 가격 불필요 공개 데이터는 Actions에서 Python으로 계산해 공개 JSON, 가격 필요 계산은 기기 JS(RAM 전용)로 하고 Python은 대조용 참조.

## canonical·배포 상태

- 저장소 `kco994553-star/Investment-System1`, canonical `claude/investment-system-top500-validation-alrugm`. 최신 HEAD는 GitHub에서 확인(이 문서 PR 직전 병합: #150 #151 #147 #122 #157 #158 #159 #160).
- Pages: https://kco994553-star.github.io/Investment-System1/ . 마지막 실제 배포는 여전히 **SEC run 38042681260(2026-10-10 09:52 UTC, #144 기준)**. #148 이후 병합분(프로필·엔진 이식·★·A2·B9·B10·C11)은 **아직 배포되지 않았다.** 배포(cockpit-pages workflow_dispatch 또는 SEC 일일 실행)는 사용자 승인 대상이며 이번 작업에서 실행하지 않았다. 다음 SEC 일일 실행(22:17 UTC)이 canonical을 빌드·배포하면 포함된다.
- Worker: 마지막 수동 배포 38034132303(07:21 UTC) 그대로. 변경·재배포 없음.
- SEC 매일: US TARGET 17개 범위 그대로. #145 504 분할 모듈은 workflow 미연결.

## 이번 세션 완료 (모두 필수 6체크 SUCCESS·실패 0 확인 후 병합)

| PR | 내용 |
| --- | --- |
| #150 | JS 엔진 이식 완료: DCF·역DCF·V·전략·M3·SEC 어댑터 + **기업 유형 JS**. #146 Python 참조 **36/36 대조 PASS**(Node·브라우저). locale `기업 유형 커스텀` 누락 해소 |
| #151 | ★·그룹·관심 기업 화면(S15)·리더보드 관심 필터. identity 기업 화면 제목은 티커(M2 계약) |
| #147 | 정본 색상·좁은 화면 줄바꿈, 12화면 390/1440 반응형 검사 |
| #122 | M3 '내 기기 기준' Universe 읽기·설정(시트 ID 기기 저장·백업 제외). SEC 주식수 입력 미연결 → `NOT_AVAILABLE · SEC_INPUTS_NOT_CONNECTED` |
| #157 | **A2** S01~S16 구조 정합: 흐름 번호 배지·QGV 소분류·S01 통합 판단/시스템/데이터 기준·S02 허브 4그룹+범례·**S14 모델 포트폴리오 신설(MODEL —)**·S08/S09/S10 배지·탭 |
| #158 | **B9** 전략 프로필 PREVIEW 재계산(공개 Q/G 요소, 공식 vs 내 프로필 Q·G·순위 변화, V NA) + **기업 유형 커스텀 편집기**(공식 type_config 내장 사본, 검증·기기 저장·백업) |
| #159 | **B10** 13F 읽기 경고·투자자별/종목별/겹침(NA)·투자자 ★(기기 전용) + 실적 '다음 예상 시기·확정일 아님'·S15 이번 주 실적 |
| #160 | **C11** 데이터 운영 상태 카드(설정): SEC 공개 입력 마지막 성공·실패 회사 수, 5개 화면 JSON 상태·STALE(각 파일 stale_after 기준) |

## 열린 PR

| PR | 상태 | 다음 단계 |
| --- | --- | --- |
| [#156](https://github.com/kco994553-star/Investment-System1/pull/156) | **[승인 필요] 워크플로 변경** draft. cockpit-pages·SEC 일일이 `implementation/tools/ci_node_tests.txt`·`ci_browser_tests.txt` manifest로 테스트 실행 + 전체 `pytest tests/` 단계 추가 | 사용자 승인 후 병합. 병합 후 이번 세션 새 테스트(design_responsive, design_canvas, profile_preview, thirteenf_filings, ops_status_node/browser, private_subset node/browser)를 manifest에 추가하는 작은 PR. 지금은 로컬에서만 실행·통과 확인 |
| [#152](https://github.com/kco994553-star/Investment-System1/pull/152) | draft. 테마 참고 메타데이터(14 바스켓 제안·ETF 티커)를 새 공개 파일로 표시 | 바스켓 승인 + 새 공개 파일(공개 데이터 경계) 승인 필요. 승인 후 canonical 병합·충돌 해소 |
| [#153](https://github.com/kco994553-star/Investment-System1/pull/153) | 과거 매크로 스냅샷 보존용 | 병합하지 않음 |
| #4~#71 | 과거 장기 draft·일반 PR | 수정·닫기·병합하지 않음(이전 판 표 참고) |

## 사용자 결정·조치 대기

1. **#156 워크플로 PR 병합 승인.**
2. **배포 승인**: #148 이후 앱 변경을 Pages에 배포(cockpit-pages workflow_dispatch). 또는 다음 SEC 일일 실행에 맡김.
3. **M3 SEC 주식수 공급 경로**(B8): (a) Actions가 Universe 코드별 SEC 주식수·basis(가격 없음)를 공개 JSON으로 제공(권장, 공개 데이터 경계 + 504 workflow 확장) 또는 (b) Worker SEC 중계(Worker 변경). 참고: 현재 공개 `sec-public-inputs.json`에 US17 reported_shares가 이미 있으나 M3 어댑터는 원본 body+SHA 검증을 요구한다.
4. **유형 지표 공개**(B9): `company-types-pricefree.json`에 가격 불필요 지표(revenue_cagr_3y·roic) 원값을 추가해야 기기에서 커스텀 유형 램프로 기업별 미리보기가 가능. 공개 데이터 경계 변경.
5. 기존 대기: SIC→업종군 매핑 확인, DCF 기본값, 매크로 8축 대응표, 테마 바스켓 승인(#152), 13F 추적 기관 집합, forward 시작 시점, **DART 등록 알림(10/11 18시 이후, 알림 전 착수 금지)**.

## 다음 할 일 — 장기 대기열(막히면 건너뛰고 의존 해소 시 복귀)

1. A1 PWA: 코드 완료. 실기기 설치 확인은 사용자.
2. A2 16화면: **완료(#157)**. 후속은 실데이터 연결 시 각 카드 채우기.
3. A3 프로필 골격: **완료(#148·#158)**.
4. A4 테마: #152 승인 대기.
5. A5 ★·그룹: **완료(#151)**.
6. B6 공개 JSON: 코드 연결 완료. 실제 정부/13F 입력·최신 앱 재배포는 사용자 결정(위 2·5).
7. B7 JS 이식: **완료(#150, 36/36)**.
8. B8 M3: 기기 읽기 완료(#122). SEC 주식수 공급 결정 대기(위 3).
9. B9 유형·전략: **완료(#158)**. 기업별 유형 미리보기는 위 4 대기.
10. B10 13F·실적·매크로: **완료(#159)**. 투자자 ★ 백업 포함은 후속(백업 schema 변경 필요).
11. C11 운영 상태 UI: **완료(#160)**.
12. C12 DART: 등록 알림 후 착수.

기타 후속: #156 병합 후 manifest에 새 테스트 등록. 레거시 브라우저 테스트 9종(app_nav_ia, device_actual, google_sheet_storage, manual_quotes, prompt_field_guide, web_mvp, web_research_guard, web_state_presentation, global_language_search)은 CI 미등록이며 현재 UI와 불일치로 실패 — 갱신 또는 정리 필요(삭제는 승인 후).

## 검증 방법

- 필수 체크: repository-guard, ingest-and-gate, build, validate, guard, presentation. deploy SKIPPED는 배포 아님.
- 전체 Python: `cd implementation && PYTHONPATH=src python3.12 -m pytest -q tests` → 2071 PASS(py3.12). Python 3.13에서는 3건(strategy_preview·sec_13f·scoring_standard의 3.13 특이 동작) 실패, `experiments/chart-contract` 9건은 고정 기준선 부재로 실패 — 둘 다 이번 변경과 무관.
- 로컬 Playwright는 CI와 같은 **playwright@1.58.2**를 써야 한다(1.56에서는 PWA 오프라인 테스트가 거짓 실패).
- 공개 산출물 해시는 `implementation/tools/pages_artifact_guard.py` APPROVED_SHA256에 고정. 웹 자산을 바꾸면 해시·`files_scanned`·`test_pages_cockpit_build.py` 파일 목록을 함께 갱신한다.

## 비밀값·외부 서비스 — 이름과 저장 위치만

| 서비스 | 상태 | 필요한 이름 | 저장 위치 |
| --- | --- | --- | --- |
| Cloudflare Worker | 위 실제 deploy SUCCESS, 본인 가격 경로 | ALLOWED_EMAIL, GOOGLE_CLIENT_ID, TIINGO_API_KEY, KRX_API_KEY | Worker: ALLOWED_EMAIL/TIINGO_API_KEY/KRX_API_KEY Secret, GOOGLE_CLIENT_ID Text; 값 기록 금지 |
| Worker 배포 Actions | 마지막 수동 deploy SUCCESS | CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID | GitHub Actions Secrets, 값/계정 ID 출력 금지 |
| Google OAuth/Drive/Picker/Sheets | API/scope/리퍼러 제한 키 설정 완료 사용자 통지; 첫 설정 코드 병합 | Google OAuth client ID, Picker browser key/app ID | 공개 제한된 앱 설정은 app-config.js, OAuth token RAM, 생성/선택 시트 ID 기기 설정만·백업 제외 |
| BEA | 공급 입력 모듈만, 실제 Macro 입력 미연결 | BEA_USERID | GitHub Actions Secret, 값 출력 금지 |
| SEC EDGAR | US17 manual SUCCESS·daily 등록 | SEC_USER_AGENT | GitHub Actions Secret, 값/이메일 출력 금지 |
| DART | 등록 완료 알림 대기 | DART_API_KEY | GitHub Actions Secret 예정, 알림 전 확인/호출 금지 |
| EDINET | 장기 후순위·등록/착수 미승인 | Subscription-Key | 미등록/미운영으로 취급, 값 기록 금지 |

원본 재무 자료는 수집 임시 경로에서 처리하고 공개 가능 결과만 Pages에 보존한다. 개인 보유·거래·관심·그룹·프로필은 기기 전용이다. 어떤 비밀값도 이 문서·PR 본문·로그에 넣지 않는다.
