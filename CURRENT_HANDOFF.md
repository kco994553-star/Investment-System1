# Claude Code 인수인계 — 2026-10-10

메인 개발을 Claude Code로 이전한다. 코덱1은 새 기능 착수를 중단하고 진행 중 변경을 원격 WIP로 보존했다. **코덱2 최종 인수인계 #154의 필수6체크 SUCCESS·실패0을 확인하여 병합한 뒤, 코덱1의 최신 운영·WIP 결과를 이 파일에 통합했다.** 이 문서 PR #155가 이번 최종 인수인계본이며 이후 변경이 있으면 최신 상태를 보존해 갱신한다.

## 읽기 순서와 운영 경계

1. [WORKING_RULES.md](WORKING_RULES.md): 1인용 혼합 운영 규칙.
2. 이 파일: 실제 완료·미완료·의존·운영 상태.
3. [ROADMAP_2026Q4.md](implementation/docs/ROADMAP_2026Q4.md): 범위·연구 및 후속 정책. 작성 당시 OPEN/배포 대기 표는 아래 최신 상태로 대체한다.
4. [DESIGN_CANVAS_SCREENS_v1.md](implementation/docs/cockpit_ia/DESIGN_CANVAS_SCREENS_v1.md): #149로 병합된 S01~S16 정본, 390px/1440px. 추가 4화면 명세 대기는 해소됐다.

최신 사용자 승인: **승인 필요 표시 없는 PR은 실행된 필수 체크 전부 성공·실패0이면 자체 병합 가능**. Worker 변경·workflow 변경 등 별도 승인 필요 항목은 사용자 승인 범위를 확인한다. WORKING_RULES의 과거 #95 승인 대기 문구는 이후 병합·배포 승인과 결과로 대체됐다. 26E 결정 기록 변경·미승인 가중치/새 방법론은 별도 승인 대상이다. 미완성 WIP는 체크 통과만으로 완료로 간주하지 않는다. force push·ruleset·AUTONOMY_MODE 변경·임의 PR 닫기·브랜치 삭제 금지.

테스트·CI·필요한 브라우저 검사·계산 정확성·Frozen/원본 TARGET 불변·개인정보 가드는 유지한다. 작은 변경의 gate/receipt/fingerprint/GSQ 행정 기록과 대량 증거 파일은 만들지 않는다. A-G1~G3는 1인용 범위 해당 없음으로 종료됐다. 기술·매크로를 QGV 원점수에 혼합하지 않고 새 방법론·가중치·미정 기본값을 만들지 않는다. 산업(SIC)·테마·유형, MODEL·TARGET·ACTUAL을 분리한다. 결측은 NOT_AVAILABLE/—이며 0·합성값으로 대체하지 않는다. 주문 기능 없음.

가격·가격 파생값·M3 선정/순위는 기기 RAM 전용이다. 토큰·시트 ID·Worker 주소·가격은 새 통합 백업에 넣지 않는다. 관심/그룹·프로필 등 승인된 개인 설정은 기기 저장 및 백업에 포함한다. 공개 JSON/Pages에는 허용된 비가격 자료만 넣고 raw SEC 임시 파일·벡터 테스트 가격을 배포하지 않는다. 기존 수동 입력/legacy 백업과 새 RAM 산출물의 경계를 유지한다.

## canonical·배포 상태

- 저장소: `kco994553-star/Investment-System1`.
- canonical: `claude/investment-system-top500-validation-alrugm`.
- **이 인수인계 PR 직전 원격 HEAD: `f5d13be8f3e22fb9b5dae3f93bea6b5bdc29831c`** (#154까지). 문서 PR 병합 후 HEAD는 GitHub canonical에서 확인한다.
- Pages: https://kco994553-star.github.io/Investment-System1/ . 마지막 확인된 실제 배포는 **SEC run 38042681260**, deployment 6979119251, **2026-10-10 09:52:34 UTC**, SHA `f8b55ce509853606b5fde0a3c7d4389ab4201ea8`(#144), SUCCESS. #142 PWA와 #144 공개 JSON 연결 포함. **#148 프로필과 그 이후 canonical은 아직 이 배포에 포함되지 않는다.** PR의 deploy SKIPPED를 배포 성공으로 세지 않는다. 이번 정리에서 추가 배포는 실행하지 않았다.
- Worker: `private-investment-history.kco994553.workers.dev`. 마지막 실제 수동 배포 **38034132303, 2026-10-10 07:21:11 UTC, SUCCESS**. #124 Tiingo/KRX 예비 경로 포함, KRX는 1개월 비상용. 이전 Actions 익명 검사: Origin 없음 `403 ORIGIN_FORBIDDEN`, 앱 Origin·토큰 없음 `403 AUTH_FORBIDDEN`. 이번 환경의 직접 GET 재점검은 `HTTP 0 CHECK_FAILED`로 응답을 검증하지 못했다. 이것을 Worker 중단/정상 증거로 바꾸지 않는다. 재배포하지 않았다.
- SEC 매일: `.github/workflows/sec-daily-public-inputs.yml`, **매일 22:17 UTC**, 수동 workflow_dispatch도 가능. 현재 실제 범위는 **US TARGET 17개**. #145의 504 코드/분할 수집 모듈은 병합됐으나 workflow 확장은 미연결; 500회사 커버리지로 표시하지 않는다.

마지막 수동 SEC 실행 38042681260은 수집·공개 경계 build·Pages 배포 모두 SUCCESS. 출력은 다음과 같고 SEC_FAILURE 줄은 없었다.

```text
SEC_EXCLUDED company_index=8 code=VALUE_INVALID count=1
SEC_PUBLIC_BUILD_OK failed_companies=0
PUBLIC_SCREENS_OK files=5
```

## 이미 병합된 연결과 남은 경계

| 범위 | 최신 완료 | 미완료/주의 |
| --- | --- | --- |
| 로그인·통합 시트 | #131 로그인·#132 CSP 필수 CI 수정, #133 첫 설정/자동 생성/Picker. Quotes·Trades·Universe 이름 기반, 기존 로그인 재사용, 요청 scope는 drive.file와 email | 시트 ID는 기기 설정에만. 본인 휴대폰 실제 연결 성공을 코드/CI 성공으로 대신하지 않는다. |
| 기기·기술 | #116 백업, #117 Research JS, #119 캔들/MA/AVG, #120 Trades B/S, #142 PWA | Research 표시 전용, warm-up 부족 선 숨김. PWA는 승인 정적 셸만 캐시; 인증/가격/개인 데이터 캐시 금지. |
| SEC consumer | #139 schema /3 및 /1·/2 하위 호환, 제외 사유 수·주식 종류 주의 표시. #140 고급 접기·빈 붙여넣기 안내 | 주식 종류 자동 합산/보정 없음. |
| 공개 표시 JSON | 엔진 #141, 앱/Pages/SEC 연결 #144. `public-screens.js`, `public_screens_pipeline.py`, `preserve_public_screens.py` | 5개 파일: macro-screen.json, sec-13f-changes.json, sec-filing-windows.json, sec-qg-factors.json, company-types-pricefree.json. 매크로/13F 실제 입력 없음→NA. Q/G는 제공 요소만, V 공개 금지; 실적은 제출 패턴의 예상 시기·확정일 아님. 기존 정본 값을 합성 채우지 않는다. |
| 엔진 기반 | #123 실적 패턴, #125 V 요소, #127 전략 재계산, #128 Macro 8×6, #129 13F, #134 SEC 식별/Universe 코드, #135 유형 설정, #136 테마, #143 DCF, #145 SEC 분할, #146 JS 사양/36벡터, #149 디자인 정본 모두 병합 | #135 미병합 의존은 해소됨. 매크로 실제 국면 mapping·테마 정규화·DCF 금융 기본값은 미정. 자료가 있어도 근거 없는 산출 금지. |
| 프로필 골격 | #148 공식 복사·초안 비중·합100 확인·기기 저장·통합 백업 /2(기존 /1 호환), 유형 커스텀 골격 | 실제 PREVIEW 재계산·리더보드 순위 변화·유형 config 연결은 미완료. 공식 축내부 비중과 유형 Q/G/V 부모 비중을 혼동하지 않는다. |

## 열린 PR과 의존 관계

아래 현재 작업은 **모두 원격 push된 draft WIP**다. PR 본문에 완료/남은 것/다음 단계를 적었다. 새 기능은 더 시작하지 않았다.

| PR | 완료/상태 | 남은 의존·다음 단계 |
| --- | --- | --- |
| [#153](https://github.com/kco994553-star/Investment-System1/pull/153) | 코덱2의 #104 채택 이전 과거 매크로 로컬 스냅샷 보존 | 현 canonical #104/#128 대비 차이 검토용. 그대로 병합하지 않는다. 최신 통합 테스트 미실행. |
| [#150](https://github.com/kco994553-star/Investment-System1/pull/150) | DCF/역DCF/V/전략/M3/SEC 어댑터 JS 라이브러리. #146 벡터 중 **31/36** 브라우저 대조 PASS, 입력 불변·RAM 경계. profile-defaults 요소 순서·번역 누락 수정 포함 | 기업 유형 JS **5벡터 미완료**, `TYPE_JS_PORT_PENDING`은 이 PR의 미완료다. #135는 이미 병합. 전체 suite 및 실제 화면/가격 입력 연결 필요. |
| [#151](https://github.com/kco994553-star/Investment-System1/pull/151) | 승인 identity 19개 기반 ★/그룹/검색/정렬/관심 화면/리더보드 필터. Node·390/1440px 브라우저 PASS | 최신 canonical과 **merge conflict** 있음: app/index/asset guard 등을 통합하고 프로필/차트 보존. 새 locale 및 전체 suite/필수 CI 확인. 전체 500개 디렉터리/순위 아님. |
| [#152](https://github.com/kco994553-star/Investment-System1/pull/152) | #136 참고 메타데이터·14개 제안 바스켓, 종목 상위2·쏠림 위치 NA. 참조/guard/390·1440px PASS | 바스켓 승인·소속도 정규화·공식 노출 입력 대기. 수치 쏠림/경고 구현 없음; 임계값 발명 금지. |
| [#147](https://github.com/kco994553-star/Investment-System1/pull/147) | 기존 12화면 반응형·색상·빈 상태·하단 메뉴 테스트 PASS, 필수6체크 SUCCESS | #149의 16화면 정본으로 전체 구조/번호 배지/QGV 탐색/활성 막대/S05/S14 등 정합 필요. 명세 자체 대기는 해소됨. |
| [#122](https://github.com/kco994553-star/Investment-System1/pull/122) | 기존 M3 JS/기기 보기 prototype | #150 라이브러리 완료 후 통합 시트 Universe 탭·SEC 식별/basis·loadInputs·앱 리더보드 연결. N=20, 10% 경계, SHARE_CLASS_BASIS는 표시만. 부분 cover는 전체 cover로 추론하지 않는다. |

기존 장기 PR은 이 인수인계에서 수정·닫기·병합하지 않았다. 과거 gate 문구가 최신 혼합 운영을 되돌리는 근거가 아니다. 실제 원격 PR base 및 본문을 확인하고 새 장기 대기열과 중복 여부를 판단한다.

| PR | 현재 열린 범위 | 기존 의존/주의 |
| --- | --- | --- |
| #71 | Chart public reference (일반 OPEN, WIP 아님) | 과거 TARGET/locale/공개 경계 변경과 현 canonical의 중복 검토 필요, 자동 재개/병합하지 않음 |
| #43 | draft GitHub write-path 문서 | 과거 문서 지침의 현 WORKING_RULES와 중복 검토 |
| #31 | draft Track C CDR-012 | 과거 stacked Track C 및 합성 검증 범위, 현 forward/Holdout 결정과 분리 |
| #29 | draft Web producer 계약/E2E | producer/P01 공개 경계와 현 앱 구현 중복 검토 |
| #19 | draft QGV invalidation binding | 표시 활성화 미포함, 기존 binding/원점수 계약 검토 |
| #18 | draft US equity session | PR base가 #15 기술 model branch; calendar vintage/close basis |
| #17 | draft P01 publication | 기존 #9 infrastructure stack와 명시적 research display 승인 의존 |
| #16 | draft SEC 8-K disclosure | 8-K 공개 제출 경계; 일반 뉴스 제공 아님 |
| #15 | draft technical REAL model | #11 위 stack, 모델 입력/공개 권한 미완료 |
| #14 | draft leaderboard REAL producer | 기존 P01/Track C 및 공개 권한, within-tie 정책 미완료; 현재 개인 M3와 별개 |
| #13 | draft RIG news | 공급자 활성화·유사도/영향 정책 미정 |
| #12 | draft Macro REAL producer | 과거 provisional series/exposure/mapping 미정; 현재 정부 #128과 중복 검토 |
| #11 | draft technical real producer | 가격 시계열/return 변환·모델 입력 미완료 |
| #10 | draft QGV REAL producer | rubric 실입력·PIT/공개 경계 미완료; 현재 Q/G 후보와 구분 |
| #7 | draft entity metadata | #6 위 stack였던 Frozen Top500 검색 metadata, 현재 504 code-only와 별개 |
| #4 | draft Track C | C8~C10 정책 승인/연구 범위 의존; 기존 Holdout 사용 금지 |

코덱2의 최종 결과/대응표 문서 PR #154는 필수6체크 성공·실패0 확인 후 병합했다. [19종목 결과·500회사 커버리지](implementation/docs/company_types/QUEUE_RESULTS_AND_COVERAGE.md), [8축 대응표 제안](implementation/docs/macro_data_rights/EIGHT_AXIS_MAPPING_PROPOSAL.md), ROADMAP 및 Python/JS 계약 갱신을 보존한다. 해당 결과표의 raw blobs 0건·19종목 NA는 **코덱2 로컬 환경의 원문 부재**에 대한 판정이며, 위 Actions에서 취득·배포한 US17 재무/QG 요소 성공과 구분한다. 504 listing 코드와 500 issuer coverage도 다르다.

## 의존 대기·사용자 결정

- **SIC 매핑 확인**: 제안 SIC→업종군 대응표 승인 전 경기민감/경기방어 소속도 NA. 테마로 업종을 대체하지 않는다.
- **DCF 기본값**: 할인율·말기 성장률·cash-flow/통화·주당/ADR/split basis 확인 대기. 할인율 10%·영구성장 2%는 코덱2 문서의 미채택 제안이며 앱 기본값이 아니다. explicit years 5 외 미확정 값은 null/confirmed=false; 계산 임의 기본값 금지.
- **매크로 8축 대응표**: exact series/단위/SA/PIT·GDP/CPI→기존 축 대응 및 6칸 의미 확인 대기. 정부 입력만, FRED/ALFRED 금지. 실제 국면/확률 합성 금지.
- **DART 키 등록 예정**: 사용자의 등록 예정 안내는 10/11 18시 이후(원 공지 시간대 미명시)다. 등록 완료 알림 전 키 존재 확인·API·adapter 착수 금지. 이후 엔진 어댑터가 병합되면 한미반도체 재무 연결.
- **테마**: #136 바스켓 승인·정규화 입력 대기. 포트폴리오 쏠림 수치/임계는 새로 만들지 않는다.
- **13F·Macro 실제 취득 입력**: 화면/공개 serializer는 있으나 공급 입력 미연결. 투자자 ★는 기기 저장이고 추천 목록을 합성하지 않는다. 13F는 보고 수량 변화이며 실제 매매/현재 보유 확정이 아니다.
- **검증/연구**: 기존 Holdout UNCONFIRMED, v2 근거 제외·사용 금지. forward 시작 시점은 사용자 결정 전 선택하지 않는다.

## 다음 할 일 — 사용자 장기 대기열 순서 유지

기존 A1~C12를 그대로 보존한다. 의존이 막히면 다음으로 넘어가고 해소되면 돌아온다. Claude Code가 작업 재개 시 현재 WIP 통합과 검증 회귀를 먼저 확인한다.

1. **A1 PWA**: #142 코드/정적 셸 검증 완료·#144 배포 포함. 실기기 설치/오프라인 운영 확인은 별도.
2. **A2 16화면 정합**: #147 이어서 #149 디자인 정본 적용, 빈 상태/NOT_AVAILABLE/390·1440px/하단5메뉴.
3. **A3 유형 커스텀·프로필 골격**: #148 병합, 실제 함수/type_config 연결은 B9. locale 누락 회귀는 아래 #150 수정 참조.
4. **A4 테마**: #152 이어서 승인된 #136 입력 연결, 실제 쏠림·종목 상위2는 의존 대기.
5. **A5 ★·그룹**: #151 canonical 충돌 해소·전체 검증 후 연결 완료.
6. **B6 공개 JSON**: #144 기본 연결 완료. 실제 정부/13F 입력, #135 이후 price-free 유형 갱신 및 최신 앱 재배포 필요.
7. **B7 JS 이식**: #150 유형 5개를 포함한 **36벡터 전부 대조** 및 전체 검증. 가격은 RAM-only.
8. **B8 M3**: #122 통합 Universe 읽기·SEC 식별/basis·N20·10% 경계 연결, 리더보드 ‘내 기기 기준’/‘내 프로필 기준’.
9. **B9 유형·전략**: #148 골격과 #150 함수를 공식 type_config/재계산에 연결, PREVIEW/원 QGV 보존·기기 저장/백업.
10. **B10 13F·실적·매크로**: #144 reader 유지, 실제 입력/투자자 ★ 저장, ‘확정일 아님’, 8축×6칸 NA 처리.
11. **C11 운영 상태 UI**: 마지막 성공 시각·실패 회사 수·STALE 표시 미착수. 공개 가능한 운영 메타데이터 계약 필요.
12. **C12 DART**: 등록 알림+엔진 어댑터 병합 이후만 착수.

SEC 504 분할 workflow 연결은 기존 운영 확장 후속이며 #145 모듈을 실제 연결하기 전 현재 17개 범위를 유지한다. 새 작업 착수/수집 범위 확대/별도 승인 필요 변경은 최신 사용자 승인을 확인한다.

## 재개할 때 확인할 검증·로컬 보존

- #150 최종 로컬: 공개 build/가격 경계 guard, 기존 Node 검사, engine_reference_browser_test.js **31벡터**, 프로필/Cockpit/차트 브라우저 PASS. 새 유형 5개와 전체 suite는 미완료. #150/#152 최종 필수6체크 SUCCESS·실패0을 확인했으나 미완성이므로 WIP를 유지했다. #151은 canonical 충돌로 원격 체크가 실행되지 않았다.
- 기존 #148 브랜치 full Python: **1 failed, 2045 passed, 360 subtests passed**. 실패는 `test_web_state_presentation.py::test_every_ui_string_has_ko_and_en_entries`의 `기업 유형 커스텀` locale 누락. 최신 canonical 관련 검사에서도 1 failed·12 passed를 확인했다. #150 locale.js에 수정이 있고 관련 13개 검사는 PASS이나 **이 수정은 아직 canonical에 병합되지 않았다**. 필수 CI 성공을 전체 suite 성공으로 표현하지 않는다.
- 테스트: `cd implementation && PYTHONPATH=src python -m pytest -q`. RAM 이식 Node: `node implementation/tools/engine_preview_node_test.js`. 기존 Pages workflow의 build/asset guard 및 각 browser 테스트를 함께 유지한다. 벡터 fixture는 배포하지 않는다.
- 최종 필수 체크 이름: repository-guard, ingest-and-gate, build, validate, guard, presentation. 모두 최종 PR head에서 SUCCESS이고 실행 체크 실패0인지 확인한다. deploy SKIPPED는 배포 아님.
- 이번 WIP push 후 모든 로컬 브랜치에 같은 이름의 origin 원격 브랜치가 있고 **로컬 전용 커밋 0건·로컬 전용 브랜치 0건·작업 트리 미커밋 변경 0건**을 확인했다. 이 문서 PR push/병합 후 다시 확인한다. 다른 기기/코덱2 환경의 미push 작업은 이 환경에서 보증하지 않는다.

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
