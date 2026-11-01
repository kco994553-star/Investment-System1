# 중앙 V(DC-02) 구현 계획 — IEX HIST 수집 → 서버 V 계산 → `qgv-official/1` 게시 → 화면 읽기 (2026-10-24)

상태: **계획 문서.** 코드·워크플로·가드는 바꾸지 않는다. 결정이 필요한 항목은 4절에 모았다.
작성: 2026-10-24 01:10 UTC / 10:10 KST, Claude Code Main. 기준: canonical `d6eaaa8a`(#395 병합).
근거: GSQ-024([결정 기록](../pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md) 510~536행), [설계](CENTRAL_V_PUBLICATION_DESIGN_20261018.md), [D-CV 열린 항목](DCV_OPEN_ITEMS_20261019.md), [IEX HIST 표본](../daily_data_pipeline/IEX_HIST_SAMPLE_20261019.md), 미병합 브랜치 3개(1절).
기능 번호는 명세 v1.0 기준이다: 2.1.5·2.1.6(산출 상태·공식/개인), 2.1.7·6.1.2~6.1.4(TARGET v1), 2.4.4(V 입력 기준), 2.4.5(레이더 V축), 9.2(전진검증).

## 0. 요약

- **이미 만든 것이 많다.** U1~U3 코드(`claude/cv-core-publisher`, PR 없음), U8 월말가 1회 수집(`claude/iex-v4-backfill`, 실행 완료), Actions 실현 가능성 시험(`claude/iex-hist-probe`, PASS)이 있다. 그런데 인수인계·대장에는 "중앙 V 코드 없음"으로만 적혀 있었다. 이 문서가 그 공백을 메운다.
- **남은 것은 U4(워크플로)·U5(가드)·U6(화면 읽기)와 결정 10개다.** U1~U3는 #393 위로 다시 얹고 시험을 고쳐야 한다(지금 #393과 합치면 40개 중 3개 실패).
- **권장 순서:** PR-A(U1~U3 정리) → PR-B(U5 가드, 별도 승인) → PR-C(U4 워크플로) → #393과 같은 배포 창에서 첫 게시 → 전체 샤드 1회 실행 → TARGET v1 숫자 재대조. 화면은 새 프론트엔드의 V 접근자 한 곳(PR-D)에서 바꾼다.
- **#393은 중앙 V 첫 게시와 같은 배포 창에 병합하는 것을 권장한다(결정 D1).** F_k를 쓰는 곳이 중앙 V뿐이라, 먼저 병합하면 원장 구간 분할·숫자 재대조·7일 혼합 기간 비용만 먼저 생긴다.

## 1. 지금 있는 것 (사실, 2026-10-24 01:00 UTC 확인)

> **갱신 2026-10-24 09:55 UTC (PR-A·B·C 작성 뒤, Main).** 아래 표와 "확인된 문제"는 01:00 UTC 기록 그대로 둔다. 바뀐 것:
> - 결정 D1~D10은 소유자가 2026-10-24에 정했다([사용자 결정](../USER_DECISIONS_PENDING.md) 맨 위 절). D5 (b)는 D2 (a)(읽기 전용 토큰)와 충돌해 `D5-UPDATE`로 남았다.
> - U1·U3: PR-A #400(`claude/central-v-core`)에서 #393 위로 정리했다. 실패하던 시험 3개는 #393의 실제 F_k 판독기로 고쳤고, C 파서 한 벌·별칭 표 하나(`iex_hist.SYMBOL_ALIASES`)로 줄였다. 설계 §4를 코드 스키마로 고쳤다.
> - U5: PR-B #403(`claude/central-v-guard-r2`). U4: PR-C #404(`claude/central-v-workflow-r2`). (처음 연 #401·#402는 Gate A 이메일 검사가 옛 중간 커밋을 계속 잡아 같은 트리의 새 브랜치로 바꿨다.) 첫 게시 하루 절차는 [첫 게시 점검표](CENTRAL_V_GO_LIVE_CHECKLIST_20261024.md).
> - U8 저장소 크기는 51,796 B(자산 6개)다. 실행 사실(시간·크기·커버리지, 가격 없음)은 [프로브·U8 사실](CENTRAL_V_PROBE_U8_FACTS_20261024.md)에 있다.
> - 검토에서 첫 게시 전에 소유자가 정할 항목 3개가 나왔다: `CV-LEAK`(사유 묶음이 가격 경계를 다 숨기지 못함), `CV-SPLIT`(주식수 서류 접수 뒤 분할을 못 잡음), `CV-CARRY`(라이브 읽기 실패한 날 게시본 하루 빠짐). 점검표 0절과 사용자 결정 표에 있다.

| 묶음 | 내용 | 상태 | 위치 |
| --- | --- | --- | --- |
| U1 | IEX HIST 어댑터: 색인 읽기, TOPS 1.6 스트림, 길이·MD5 확인, 정규장 마지막 체결가(Last Sale Eligible) | **코드 있음, 미병합** | `claude/cv-core-publisher` `providers/iex_hist.py`, C 파서 `tools/iex_tops/iex_last_trade.c` |
| U2 | `sec-qgv2.json` → 엔진 입력 Python 쌍둥이 | 병합됨(#325) | `qgv/qgv2_inputs.py` |
| U3 | `qgv-official/1` 게시기: 직전 정상본 보존, 전체 Universe 채점, 검증기, JS 대조, 원자적 교체, 상태 파일 | **코드 있음, 미병합** | 같은 브랜치 `qgv/qgv_official.py`, `tools/qgv_official_publish.py`, `tools/qgv_official_js_check.js` |
| U4 | `sec-daily-public-inputs.yml` collect 잡의 V 단계 | 없음 | 요구 사항: 같은 브랜치 `CENTRAL_V_U4_U5_NEEDS_20261023.md` §1 |
| U5 | 가드: 허용 파일명, 파일별 검증기, `rank` 경로 한정 예외, IEX 출처 허용, 신선도 규칙 | 없음 | 같은 문서 §2, 설계 §12 |
| U6 | 화면 판독기(`qgv-official.json` 읽기) | 없음 | 새 프론트엔드 P1 V 접근자가 자리(2절 PR-D) |
| U7 | 공개 규칙(공개 필드·가격 의존 사유 묶음·최신본만) | 설계·결정 있음 | 설계 §4~§7, GSQ-024 |
| U8 | V4 월말가 과거분 1회 수집 → 비공개 저장소 | **실행 완료(2026-10-23)** | run 39945012772, 비공개 저장소 `investment-system1-raw` 릴리스 `iex-v4-monthend-20261023-shard0..5`(62개월·422코드). 저장소 크기는 기록 없음 |
| 실현 가능성 | Actions에서 하루치 TOPS 처리 | **PASS** | run 39935426233: 11.84 GB, 3.2분, 디스크 0, 메모리 33 MB, Universe 502/504 체결(PSKY·WBD 없음) |
| F_k | 주식수 기준 계수(V4 월말가 ÷ F_k) | #393 승인 대기 | `claude/cv-fk-calc-version` |

확인된 문제:
- `cv-core-publisher`는 기준보다 10커밋 뒤다. #393과 합치면 시험 3개가 실패한다. 브랜치 시험이 F_k 판독기를 흉내 내며 #393 검증기가 거부하는 값(`share_basis_factor_reason=None` 등)을 쓰기 때문이다.
- 병합된 설계 §4의 스키마가 코드와 다르다. 설계에는 최상위 `price`·`v_calc_version`이 있고 `attribution`·`rank_row`가 없다. 코드는 `price_source`(키 `price`는 가드의 민감 키), `attribution` 추가, `v_calc_version` 없음(D-CV7 (b))이다.
- C 파서가 두 벌(바이트 동일), 기호 별칭 표가 두 개다. 하나로 합쳐야 한다.
- 프로브·백필 워크플로는 `ubuntu-latest`다. 다시 돌리려면 24.04로 고정해야 한다(#395와 같은 이유).

## 2. PR 순서

모든 PR은 3절 경계를 통과 조건으로 둔다. 워크플로·가드·계산 변경이 들어가는 PR은 소유자 승인 뒤에만 병합한다.

| 순서 | PR | 내용 | 승인 |
| --- | --- | --- | --- |
| 1 | **PR-A** U1~U3 정리 | `cv-core-publisher`를 #393 위로 다시 얹는다(병합 커밋). 시험·픽스처를 #393 검증기에 맞게 고친다. C 파서 한 벌, 별칭 표 하나(`iex_hist.SYMBOL_ALIASES`). 설계 §4를 코드 스키마로 고친다. 프로브·백필 사실(시간·디스크·커버리지·저장소 범위)을 문서에 옮긴다. 워크플로·가드 변경 없음 | 계산 코드 추가라 승인 |
| 2 | **PR-B** U5 가드 | `ALLOWED_NAMES`에 `qgv-official.json`·`qgv-official-status.json`. 파일별 검증기 연결. 민감 키 예외는 `qgv-official.json`의 `rows.<code>.rank` 한 경로만(`price`·`marketcap`·`cash` 등은 그대로 막음). `public_price_boundary`에 IEX 출처 3형태(`iextrading.com/api/1.0/hist`, `www.googleapis.com/…/b/iex/o/…`, `storage.googleapis.com`), 호출자는 게시기 하나. 신선도 규칙(기준일이 라이브보다 이르면 거부, 같은 `publication_id`면 바이트 동일). 워크플로 정적 시험에 `sec-daily-public-inputs.yml` 추가. `AUDIT.md` 추가 절 | GSQ-024: 가드는 **별도 PR·소유자 승인** |
| 3 | **PR-C** U4 워크플로 | collect 잡: 원장 단계 뒤·분류 단계 앞에 V 단계(`continue-on-error`, 종료 코드 0). C 파서 빌드 → 게시기 실행 → 기존 가드. JS 대조용 `actions/setup-node`(버전 고정)를 collect에 추가(결정 D10). Secret은 그 단계 `env`에만. verify 잡에 가격 없는 검증기 시험 추가. `cockpit-pages.yml` 보존 단계에 `--preserve-only` 한 줄(수동 배포 때 게시본 유실 방지). 비공개 점수 이력 업로드(결정 D9) | 워크플로 변경이라 승인 |
| 4 | **PR-D** U6 화면 읽기 | 새 프론트엔드 P1의 V 접근자에서 `qgv-official.json`을 엄격 리더로 읽는다. 유효·같은 calc_version·신선하면 출처 `OFFICIAL_CENTRAL`, 아니면 `DEVICE_TEMPORARY`("임시 V"). 출처 문구(IEX 표시 문구·"IEX 마지막 체결가 기준(공식 종가 아님)")를 화면에 그대로 둔다. 기기 V는 "공식 V 대조" 도구로만 남기고 공식 순위에 섞지 않는다. 옛 화면 판독기는 결정 D8 | 화면 PR |
| 5 | **PR-E** U8 후속 | 월말가 저장소 갱신 방식(결정 D5), 백필 도구가 단일 별칭 표를 import | 결정 뒤 |

> **갱신 2026-10-24 (PR-D 분할, 결정 D8 (b), Main).** 위 4번 PR-D를 둘로 나눈다. 아래 규칙은 Main이 정한 것이고 소유자가 바꿀 수 있다.
> - **PR-D(이번, 옛 화면 작은 판독기, 브랜치 `claude/central-v-reader`, 미병합):** 새 모듈 `web_assets/qgv-official.js`(전역 `QgvOfficial`, `qgv/qgv_official.py` `parse()`·`require_qgv_official()`의 엄격한 JS 쌍둥이, 같은 판정 벡터 `tests/fixtures/qgv_official_vectors_v1.json`). 쓰는 곳은 TARGET v1(2.1.7·6.1.2~6.1.4) 하나다. 다른 옛 화면(리더보드·기업·레이더·V 커버리지)과 R-B 자동 선정은 기기 V 그대로다(알려진 한계, 새 프론트엔드 P2·P3에서 표시를 정리).
> - **PR-D2(다음, 새 프론트엔드):** `web_app/qgv.js`의 `OFFICIAL_READER` 전환. #398 병합 뒤.
> - **사용 규칙(M4):** "규칙으로 초안 만들기"(기기 가격이 없으면 "중앙 V 게시본으로 초안 만들기")와 "TARGET v1 확정 저장"을 누르는 순간, 기존처럼 다시 읽는 `sec-qgv2.json` 옆에서 `qgv-official.json`을 읽는다. 다음이 모두 맞을 때만 공식 V(`OFFICIAL_CENTRAL`)다: ① 읽기와 엄격 검증 통과, ② `times.verified_at` 있음, ③ 게시본 calc_version = 다시 읽은 `sec-qgv2.json` calc_version, ④ `times.price_basis_date` 뒤 **마감된** 뉴욕 거래일이 2일 이하(D-CV6 권장값, 기존 달력 `ForwardValidation.sessionDay`; 기기의 뉴욕 날짜 전날까지의 거래일과, 오늘 거래일은 뉴욕 16:00 마감 뒤부터 셈 — `ForwardValidation`과 같은 마감 기준이며 13:00 조기 폐장 표는 옛 화면에 없음; 미래 기준일은 신선하지 않음; 뉴욕 시각을 모르면 오늘도 셈). 아니면 기기 경로 "임시 V"(GSQ-024)이고, 왜 공식 V를 안 썼는지 한 줄로 보인다: `OFFICIAL_NOT_PUBLISHED`(404)·`OFFICIAL_UNAVAILABLE`·`OFFICIAL_INVALID`·`OFFICIAL_CALC_VERSION_DIFFERS`·`OFFICIAL_STALE`. 입력 as_of 일치는 요구하지 않는다(sic·지표·재무 안전은 지금처럼 다시 읽은 `sec-qgv2.json`). 게시본 행은 기기 경로와 같은 식별 대응으로 읽는다(M6 갱신): Universe 코드는 그 종목 기호가 TARGET 티커인 `TARGET:<id>` 행이 있고 `NOT_AVAILABLE`이 아니면 그 행, 아니면 자기 행(`QgvScores` codeIndex와 같음). 게시본의 `rank_row`(D-CV8, CIK당 한 행)는 쓰지 않는다. 그래서 둘째 주식(GOOG)은 자기 점수, 총점 없는 TARGET 행·다른 calc_version TARGET 행이 대표하는 종목은 기기처럼 총점 없음(`TOTAL_NOT_AVAILABLE`)으로 빠진다. 공식 V 초안은 IEX 출처 문구(게시본 또는 판독기 상수)와 게시본 기록이 함께 있을 때만 점수를 보이고, 없으면 점수·후보를 숨기고 다시 만들라고만 한다. 공식 초안·버전은 게시본 id·가격 기준일·`inputs_as_of`를 남기고, 초안 출처와 확정 순간 출처가 다르거나 게시본 id가 바뀌면 `V_SOURCE_CHANGED`로 초안을 다시 만든다.
> - **선행 조건(어느 V 출처든 같음):** 게시본은 calc_version `qgv2-calc/2026-10-23.1` 이상에서만 나온다. 그래서 확정 버튼은 5절 재대조·재기록 PR이 병합될 때까지 `NUMBER_CHECK_CALC_VERSION_MISMATCH`로, `all_shards=true` 1회 실행 전까지 `CALC_VERSION_MIXED`로 막힌다. 첫 게시 뒤 점검은 [점검표](CENTRAL_V_GO_LIVE_CHECKLIST_20261024.md) 5-1절.

**첫 게시(배포 창 하나로 묶음)**
1. #393, PR-A, PR-B, PR-C를 같은 날 순서대로 병합한다(텍스트 충돌 없음 확인 필요, 가드 파일은 줄이 다름).
2. 소유자가 `SEC daily public inputs`를 `all_shards=true`로 한 번 실행한다(폰 브라우저: 저장소 → Actions → 워크플로 → Run workflow). 504행이 하루에 새 calc_version으로 바뀌어 혼합 기간이 하루로 줄어든다.
3. 실행 기록에서 한 줄 `QGV_OFFICIAL attempt=… published=… rows=… ranked=… supplied=n/m`와 verify·deploy 성공을 확인한다. 가격·URL·키는 출력되지 않는다.
4. 실사이트에서 `qgv-official.json`(점수·순위·사유·커버리지·기준 시각만)과 출처 문구를 확인한다.
5. 5절 재대조를 한다. 전진검증 원장(9.2)은 새 calc_version에서 구간을 한 번만 나눈다(기존 기록은 고치지 않음).

## 3. 원시 가격 비공개 경계 (모든 PR의 통과 조건)

- 가격은 실행기 RAM에만 있다. TOPS 파일은 `curl | gzip | C 파서`로 흘려 읽고 디스크에 쓰지 않는다(프로브 실측 디스크 0).
- 저장소·Pages·Actions 로그·아티팩트·`GITHUB_STEP_SUMMARY`에 가격, 시가총액, EV, 수익률(EBIT·FCF), 배율, 내재 성장률, 기대 차이, DCF 범위, 종목별 가격 시각·해시를 넣지 않는다. 검증기 `FORBIDDEN_KEYS`가 어디서든 거부하고, 가드 민감 키도 그대로 둔다.
- 가격을 거꾸로 추정할 수 있는 사유 코드(`EV_NON_POSITIVE`, `ROOT_NOT_BRACKETED` 등)는 공개본에서 `PRICE_DEPENDENT_NOT_COMPUTABLE` 하나로 묶는다. (2026-10-24 검토: 묶어도 사유가 나오는 요인 칸·V 축 유무·순위로 가격 경계가 드러난다. V 공개 자체에 딸린 한계라 소유자 확인 `CV-LEAK`로 올렸다.)
- 공개는 최신 게시본 1개만이다. 날짜별 점수 이력은 비공개 저장소에만 둔다.
- `publication_id`는 가격 묶음의 HMAC을 넣어 만든다. HMAC 키는 Secret이다. 공개본에는 `publication_id`만 있고, HMAC 원값·종목별 가격 해시 키(`hmac`, `price_hmac`)는 검증기가 거부한다.
- 비공개 저장소에 남는 가격은 U8 월말가(분할 미조정 원가)뿐이다. 일일 가격은 남기지 않는다.
- NA는 0으로 채우지 않는다. F_k가 없으면 그 달을 빼고 사유를 둔다(1.0으로 보지 않음). WBD처럼 IEX 체결이 없는 코드는 `NO_IEX_TRADE`로 NA다(Universe504는 고정 목록이라 그대로 둔다).

## 4. 소유자 결정 목록

| 번호 | 결정 | 선택지 | 권장 |
| --- | --- | --- | --- |
| **D1** | #393(F_k·calc_version 23.1) 병합 시점 | (i) 지금 병합 → 숫자 재대조를 11월 초까지 / (ii) 중앙 V 첫 게시와 같은 배포 창 / (iii) TARGET v1 확정(11-15) 뒤 | **(ii).** F_k의 소비자는 중앙 V뿐이다. (i)은 원장 분할·재대조·혼합 기간 비용을 먼저 치르고, U7 규칙이 바뀌면 두 번째 올림이 생긴다. 중앙 V가 11-08까지 못 나가면 (iii)으로 넘어가고 TARGET v1은 "임시 V"(#391)로 확정 |
| **D2** | Secret | `QGV_OFFICIAL_HMAC_KEY`(새로, 16바이트 이상) + V4 저장소 읽기: (a) 새 읽기 전용 토큰 `RAW_REPO_READ_TOKEN` / (b) 기존 `RAW_REPO_TOKEN`(쓰기 포함)을 이 단계에만 | **(a).** 설계 §3-3("이 단계에 쓰기 토큰 없음")과 맞다. 폰 브라우저에서 GitHub 설정 → 개발자 설정(토큰), 저장소 설정 → Secrets로 만들 수 있다 |
| **D3** | 가격 기준일 | IEX 파일은 T+1(04:24~10:22 UTC 생성)이라 00:37 UTC 무렵 시작하는 정기 실행은 **전 거래일** 가격을 쓴다 | 수용. 게시본에 요청 기준일과 실제 기준일을 따로 싣는다 |
| **D4** | 공급 실패 기준(D-CV5) | V 자격 행 중 가격 확보 95% 미만이면 게시 보류, 직전 정상본 유지 | 95% 수용(표본 99.4%) |
| **D5** | V4 월말가 저장소 갱신 | (a) 분기마다 재백필 / (b) 매월 말일 일일 스트림에서 1건 추가 / (c) 갱신 없음 | (b): 새 수집 없이 같은 스트림을 쓴다. 저장소를 읽지 못하면 게시 전체 보류(현행) 유지 |
| **D6** | 분할 출처(D-CV11) | IEX에는 기업행사가 없다. (a) F_k 근거 재사용 / (b) U8 `split_check` 검증 표 / (c) 연결 안 함 | (a): 이미 SEC 자료로 계산하므로 새 출처가 없다 |
| **D7** | ADR(D-CV10) | 지금은 `ifrs-full` 행만 NA. US-GAAP로 20-F를 내는 발행인 처리 | 20-F 제출 여부로 넓혀 NA(보수적) |
| **D8** | 옛 화면에도 판독기를 둘지 | (a) 새 프론트엔드에만(P3 전환 때 반영) / (b) 옛 화면에도 작은 판독기 | 중앙 V 게시가 P3 전환보다 빠르면 (b), 아니면 (a). GSQ-024 목표("설정 없이 같은 공식 V·종합 순위")는 화면이 있어야 이뤄진다 |
| **D9** | 비공개 점수 이력 위치 | 비공개 저장소 릴리스 태그 `qgv-official-YYYY-MM-DD` | 수용(원장과 같은 방식) |
| **D10** | collect 잡에 Node 설치 | JS 대조(D-CV12)에 필요. 없으면 매번 `VERIFY_FAILED JS_TWIN_UNAVAILABLE` | `actions/setup-node` 버전 고정 추가(PR-C) |

## 5. TARGET v1 숫자 재대조 계획 (#393 병합 시, #386과 같은 방식)

배경: 확정 버튼은 게시 `sec-qgv2.json` 최상위 calc_version과 `number_check.result.calc_version`을 비교한다(`target-v1-builder.js:291-296`). #393 뒤 게시본이 `qgv2-calc/2026-10-23.1`이 되면 값이 같아도 `NUMBER_CHECK_CALC_VERSION_MISMATCH`로 막힌다. F_k는 FCF 수익률을 바꾸지 않는다(기기 경로 `qgv2-inputs.js history()`가 F_k를 버리고, `qgv-v2.js`·`qgv2-inputs.js`·`qgv-scores.js`는 #393에서 바이트 동일). 합성 자료 모의 실행에서도 차이 0이었다. 그래도 같은 calc_version으로 다시 대조하고 기록해야 한다.

0. **지금(승인 불필요):** 재기록 PR 초안을 미리 만든다(숫자·해시 칸은 비움). 대조 스크립트는 저장소에 넣지 않는다(#386과 같음).
1. 2절 "첫 게시" 1~2단계(병합·전체 샤드 실행)가 끝나면 게시 파일의 sha256·as_of·504행·최상위 23.1, 값이 있는 행의 `CALC_VERSION_MIXED` 0을 확인한다.
2. **504행 비교(근거 문서 212·228행 규칙):** 마지막 17.1 게시본과 첫 23.1 게시본에서 companyfacts가 같은 행은 metrics·factors·axes·`v_inputs_v2`(F_k 키 제외)가 같아야 한다. "F_k는 값을 바꾸지 않는다"를 실제 자료로 확인하는 가장 싼 방법이다.
3. **10종목 40칸:** FIX·EME·INCY·RL·DECK·MA·RSG·MNST·CMG·EXPE를 0-2-8절 파일과 비교한다. calc_version 라벨만 바뀌어야 한다. 새 10-Q로 TTM·부채·현금이 바뀐 칸만 원 제출물과 다시 맞춘다.
4. **FCF 수익률 7칸:** 앱 경로(`sec-qgv2.js` → `qgv2-inputs.js fromInputs` → `qgv-v2.js scoreUniverse` → `fcf_yield`)와 독립 구현을 합성 시험 가격 3벌(메모리에서만)로 비교, 허용 5%. 기대: FIX·RL·MA·RSG·MNST·CMG·EXPE 일치, EME·INCY·DECK NA(`DEBT_CASH_NOT_AVAILABLE`). 가격·수익률 숫자는 어디에도 남기지 않는다.
5. 재기록 PR: `target_v1_builder_v0.json` 15행 result를 `{calc_version:'qgv2-calc/2026-10-23.1', passed:true, date:<대조일>, companies:10}`로, `target-v1-config-defaults.js` 같은 내용, 가드 49행 재고정, 시험(`test_target_v1_builder_config.py:34`, `target_v1_builder_node_test.js` 171·175-176·183·554, `target_v1_builder_browser_test.js` 39·57·63·83), 대조 문서 0-2-9절, FUNCTION_STATUS 6.1.2~6.1.4 줄.
   - **#391 병합 뒤에 만든다.** #391이 가드 48·50행을 고치므로 49행을 고치는 PR이 먼저 갈라지면 텍스트 충돌이 난다.
6. 검사: node 시험 2개, pytest 3개, 빌드 후 TARGET 브라우저 시험(390·1280), 방향 검사, 필수 6체크. 승인 뒤 병합.
7. 폰 확인(배포 뒤): TARGET 화면 숫자 검증 줄이 "calc_version qgv2-calc/2026-10-23.1 · <대조일>"이고 막힘 사유에 MISMATCH가 없는지, 저장된 초안이 `DRAFT_BASIS_CHANGED`로 다시 만들어졌는지 본다.

막히는 기간: 전체 샤드 실행을 하면 약 1~2일(재기록 PR 승인까지). 확정 창 11-09~11-15보다 앞서야 하므로 첫 게시는 **11-04 전**이 목표다. 넘기면 D1 (iii)로 바꾼다.

## 6. 일정 (목표, 승인 속도에 따라 바뀜)

| 날짜(UTC) | 일 |
| --- | --- |
| 10-24~10-27 | 결정 D1~D10. PR-A 작성·CI. PR-B·PR-C 작성 |
| 10-28~10-31 | PR-A·PR-B·PR-C 승인. Secret 등록(D2). 배포 창 하루에 #393 포함 병합 → 전체 샤드 실행 → 첫 게시 확인 |
| 11-01~11-04 | 5절 재대조·재기록 PR 승인. PR-D(옛 화면 TARGET v1 작은 판독기) 승인. PR-D2(새 프론트엔드 V 접근자 전환)는 #398 뒤 |
| 11-09~11-15 | TARGET v1 확정 창. 중앙 V가 게시돼 있으면 중앙 V, 아니면 "임시 V" |

## 7. 위험

- IEX 약관: HIST 약관과 웹사이트 약관의 겹침은 서면 확인 없이 진행하기로 했다(GSQ-024). 종료 뒤 보관 규정은 없다.
- 실행기 → GCS 대역폭: 프로브는 하루 1회뿐이다(61 MB/s). 변동성 큰 날 파일이 14.6 GB까지 커진다. 시간 초과 시 직전 정상본 유지.
- 공개 파일 크기: `qgv-official.json` 약 1.06 MiB(한도 2 MiB), #393 뒤 `sec-qgv2.json` 약 1.84 MB(여유 약 8%). Pages 묶음은 약 4.0 → 5.1 MiB(경고 6 MiB, 한도 8 MiB, 추정).
- V 커버리지 상한은 그대로다: 금융 67개는 V 정의 없음(공식 순위 없음), 일반기업 가격 무관 상한 360/434, ASML 통화 기준 미확인, WBD 체결 없음.
- 공휴일·반일 장 동작은 시험이 없다. PR-A에 시험을 더한다. (2026-10-24: PR-A에 더했다. 실제 반일은 2026-11-27에 처음 확인한다.)
