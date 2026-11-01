# 시작 문서 — 모든 AI 세션은 이것부터 읽는다

이 저장소는 사용자 한 명이 폰으로 지휘하는 투자시스템 웹이다. 문서가 많고 방향이 여러 번 바뀌었다. **아래 순서대로만 읽고, 여기와 다른 옛 문서는 따르지 않는다.**

## 1. 읽는 순서

1. **이 파일**
2. [docs/SPEC/DIRECTION_CHANGES.md](docs/SPEC/DIRECTION_CHANGES.md) — 바뀐 방향과 금지 표현. **가장 자주 틀리는 곳이다.**
3. [WORKING_RULES.md](WORKING_RULES.md) — 작업 규칙
4. [CURRENT_HANDOFF.md](CURRENT_HANDOFF.md) — 지금 상태(기준 HEAD·게시·열린 PR·다음 할 일)
5. [docs/SPEC/FUNCTION_HIERARCHY_v1.0.md](docs/SPEC/FUNCTION_HIERARCHY_v1.0.md) — 제품 기능 명세 원문(수정 금지)
6. [docs/SPEC/FUNCTION_STATUS.md](docs/SPEC/FUNCTION_STATUS.md) — 명세 번호별 현황과 메뉴 번호 대응표. **화면마다 공개 층과 비공개 층(로그인 오너 전용 KIS·Lab 비공개)의 경계는 [1-3절 "공개 + 비공개 2층 구조"](docs/SPEC/FUNCTION_STATUS.md#1-3-공개--비공개-2층-구조-2026-10-31-오너-dc-36) 표를 따른다(DC-36). 공개 화면은 비공개 자료 없이 완전히 동작해야 한다**
7. [implementation/docs/USER_DECISIONS_PENDING.md](implementation/docs/USER_DECISIONS_PENDING.md) — 결정 원문과 남은 결정

루트의 2026-09 문서와 `SUPERSEDED` 머리말이 붙은 문서는 **기록 보존용**이다. 현재 상태 판단에 쓰지 않는다.

## 2. 절대 틀리면 안 되는 것 (상세는 DIRECTION_CHANGES)

- **Universe504** = S&P 500 구성에서 출발해 **고정한** 504코드 목록이다. 시가총액 상위 504가 아니고, S&P 500 지수를 따라가지도 않는다(DC-01).
- **공식 V** = 서버가 IEX HIST로 계산해 공개하는 점수·순위(2026-10-23 결정, 2026-10-29 첫 게시, 정밀값 공개 허용 GSQ-025). 원시 가격은 공개하지 않는다. **기기 V는 폐지됐다(DC-31, 2026-10-31, #435·#439 병합)**: 화면은 중앙 V만 보이고, 중앙 V가 없거나 늦으면 마지막 중앙 V를 갱신 시각·STALE과 함께 보인다(기기 값으로 채우지 않음). TARGET v1 빌더만 11/16 PR까지 옛 V 출처를 유지한다.
- 화면 점수는 **QGV v2만**(DC-03).
- **TARGET v0(카탈로그 19, `actual-catalog.json`)은 QGV와 전혀 무관하다.** 사용자가 QGV 없이 고른 목록이다(DC-04). QGV 화면·점수·순위·후보·공개 데이터의 "TARGET"에 v0을 쓰지 않는다. 공개 TARGET은 **확정된 TARGET v1만**이다(DC-24, 사용자 2026-10-27: "이유를 계속 잊는 것 같다").
- 기능 번호는 **명세 v1.0의 1~9**만 쓴다. 메뉴 번호(0 검색, 1 QGV…)로 보고하지 않는다(DC-08).
- 새 프론트엔드는 **시안(같은 아티팩트) 배치대로 새로 작성** 중이다. 무채색 미니멀 지시는 대체됐다(DC-07). 시각 양식은 **혼잡스 영상 기준(DC-25, [VISUAL_STYLE](implementation/docs/frontend_v2/VISUAL_STYLE.md))**: 흰 바탕 선화, 제목 Jua·본문 기기 고딕, 그림자 없음. 색은 6가지에 뜻 하나씩, 메뉴별 색 없음(DC-26).
- 역할(**DC-42, 2026-11-01 — 역할 확대**, DC-40의 "Main 엔진·입력 / Codex 실행·대사" 분담을 대체): **Main(Claude Code)**은 기능 계층 1~9의 모든 프론트엔드·UI/UX·차트·화면 연결(9 Lab 화면 포함), 인증·권한·Secret·워크플로·운영 인프라·공용 가드, 결정 기록·DC 번호·최종 통합, 승인 범위의 병합·배포. **Codex**는 계산·데이터·연구 구현(수집·변환 로직, PIT·증권 신원·입력 연결, 백테스트·전진검증 계산·결과 산출, 책 조사·규칙표·연구 문서, Notion). 명시적으로 인수한 공통 계산 모듈은 Codex가 직접 고친다. 별도 구현 담당은 없다. 이전 분담(DC-35·DC-40) 원문은 DIRECTION_CHANGES에만 남고 현행 규칙이 아니다.

## 3. 매 작업 규칙

- 사용자가 방향을 바꾸면 **같은 PR에서** DIRECTION_CHANGES에 한 줄을 더한다. 결정만 하고 코드가 아직 옛 방향이면 "구현 상태"에 그렇게 적는다.
- 기능을 병합하면 FUNCTION_STATUS의 해당 번호 줄을 같은 PR에서 고친다.
- 금지 표현 검사: `python implementation/tools/spec_direction_guard.py`(CI 전체 시험 `test_spec_direction_guard.py`에 포함).
- 원시 가격·개인 자료·토큰·이메일은 저장소·Pages·로그에 넣지 않는다. 병합·배포는 사용자 승인 범위에서만 한다.
- 사용자는 폰만 쓴다. 사용자에게 시키는 절차는 폰 브라우저에서 할 수 있어야 한다. 보고는 한국어로 묶어서 한다.

## 4. 파일 담당표 (2026-11-01, DC-42 — 역할 확대. DC-40 표를 대체)

개발 흐름은 둘이다: Main(Claude Code) · Codex. 인계 기록: [#437 인계 3](https://github.com/kco994553-star/Investment-System1/pull/437#issuecomment-6557255668)(PR·가지·전체 SHA·파일·명령·입력 위치·알려진 결손).

| 담당 | 파일 | 할 수 있는 것 |
| --- | --- | --- |
| **Main** | **프론트엔드·UI/UX·차트·화면 연결 전부**: `implementation/src/investment_system/product/web_app/` 전부(화면 파일 `screen-*.js`, Lab 화면 포함), 옛 화면 `web_assets/`, 화면 시험(`implementation/tools/*_browser_test.js`·`*_node_test.js`). **운영 인프라**: `.github/workflows/` 전부, `implementation/worker/`, `private_area/`, Secret·권한·실행 기반. **공용 가드·CI 목록**: `spec_direction_guard.py`·`autonomy_gate_a_guard.py`·Pages 가드·`public_price_boundary.py`·`ci_*_tests.txt`. **정본·결정 기록**: START_HERE·WORKING_RULES·CURRENT_HANDOFF·`docs/SPEC`·USER_DECISIONS_PENDING·결정 문서. **화면 입력 계약**: lab-backtest-v1, 연구 인계 계약, 기업 목록 공통 접근 계약. **Codex가 아직 인수하지 않은 운영 계산·자료 모듈**(`qgv/`·`providers/`·`validation/`·`universe/`·`pit/`·`ingestion/` 등. 인수는 모듈별로 4.1절에 적는다. 그 전까지 운영 유지·장애 복구는 Main, 예: #456) | 바꾸고 병합한다(병합·배포는 오너 승인 범위에서). 독립 화면은 하위 에이전트로 병렬 구현할 수 있다 |
| **Codex** | **연구·계산·자료 구현**(수집·변환, PIT·증권 신원, 백테스트·전진검증 계산, 책 조사·규칙표): `implementation/src/investment_system/research/` 전부(`exp_deciles/` 엔진, `exp_deciles/adapters/` 입력 어댑터, `pit_filings.py`), `implementation/tools/exp_stock_indicator_deciles.py`, `implementation/tests/research/` 전부, `implementation/tests/test_research_pit_filings.py`. **1회용 수집·변환·진단 도구**: `implementation/tools/measure_once/` 중 `sec_once_collect.py`·`sec_once_ticker_mismatch.py`·`fv3_pit_ticker_measure.py`·`alpaca_sample_once.py`와 그 시험 `implementation/tests/test_{sec_once_collect,sec_once_ticker_mismatch,fv3_pit_ticker_measure,alpaca_sample_once}.py`. **연구·수집 문서**: `implementation/docs/lab/EXP_STOCK_INDICATOR_DECILES_V1.md`·`SEC_ONCE_COLLECTION_PLAN_20261101.md`·`ALPACA_SAMPLE_PLAN_20261101.md`. 기존 연구 가지(`research/*`), 책 원문 조사·규칙표(#443), Notion | 계산·자료·연구 코드와 문서 PR까지. 병합·워크플로·Secret·공용 가드·DC 번호 부여·결정 기록 직접 수정은 안 한다. 결과 원본 경로는 제안하고 Main이 확인한다 |

### 4.1 공통 파일의 수정 담당 (파일별)

| 파일 | 수정 담당 | 규칙 |
| --- | --- | --- |
| `implementation/tests/test_alpaca_sample_once.py`·`test_sec_once_collect.py` | Codex | 안의 워크플로 모양 시험 함수 하나(`test_workflow_runs_once_with_the_secrets_in_a_job_that_never_ran_pip`·`test_workflow_runs_only_on_the_run_branch_push_with_one_secret_per_step`)만 Main이 고친다. 워크플로를 바꾸는 같은 PR에서 고치고 PR 댓글로 알린다 |
| `.github/workflows/alpaca-sample-once.yml`·`sec-once-collect.yml` | Main | 도구 실행 명령·인자가 바뀌면 Codex가 PR 댓글로 요청한다 |
| `implementation/docs/lab/SEC_ONCE_COLLECTION_PLAN_20261101.md`·`ALPACA_SAMPLE_PLAN_20261101.md` | Codex | 워크플로·Secret·공개 로그 범위 문장은 Main이 정한 값을 따른다. 실행 승인 질문은 Main이 USER_DECISIONS_PENDING에 적는다 |
| `implementation/docs/lab/EXP_STOCK_INDICATOR_DECILES_V1.md` | Codex | #457 안의 Main 변경(1절 정정·5~10절)은 그대로 둔다. 인계 뒤 오너 결정이 이 문서를 바꿔야 하면 Main이 결정 기록에 적고 Codex가 고친다 |
| `implementation/src/investment_system/qgv/playbook_v1.json`의 `target_v1.grades`(배분 설정, AUD-01) | Codex | 승인된 6% 규칙 반영은 Codex. 같은 PR에서 생성 사본 `web_assets/playbook-config-defaults.js`가 바뀌면 그 파일과 Pages 가드 고정값(`pages_artifact_guard.py`)·화면 시험은 Main이 맡는다. 나머지 키(매크로 관문 등)는 인수 기록 전까지 Main |
| `ci_*_tests.txt`(CI 시험 목록) | Main | Codex가 PR 본문에 추가할 시험을 적으면 Main이 넣는다 |
| 운영 모듈 인수 기록 | Main | Codex가 #437 또는 자기 PR에 모듈 인수를 적으면 Main이 이 표에 줄을 더한다. 인수 전에는 Main이 유지한다 |

- **넘긴 파일은 Main이 병행 수정하지 않는다.** Main은 Codex 소유 연구 코드·결과 원본·동결 결과를 고치거나 숫자를 다시 계산하지 않는다. Codex 문서도 직접 고치지 않고, 바꿀 곳은 PR 댓글로 남긴다.
- **화면 연결:** 화면에 필요한 스키마·상태값·예시 데이터는 Codex가 PR로 내고, Main은 그것으로 화면을 만든다. 비공개 연구 결과는 공개 화면에 자동 게시하지 않는다. 실자료 백테스트·회원 DB 완성은 공개 웹의 선행 조건이 아니다.
- **다른 흐름(Codex)의 PR이 DC 번호·`DIRECTION_CHANGES`·`USER_DECISIONS_PENDING` 같은 결정 기록을 직접 바꾸면, Main이 번호를 다시 매겨 자기 PR에 반영한다**(그 PR의 해당 변경은 병합하지 않는다).
- 외부 개발 책임자(별도 화면 세션 등)는 늘리지 않는다. DC-32의 "화면 세션(Frontend)"은 시행 전에 대체됐다.
- Codex PR 병합 조건: canonical과 동기화, 필수 CI 6개 녹색, **담당 파일만 바뀜**(Main이 파일 목록으로 확인), 오너 승인. 병합은 Main이 한다.
- 이 역할 변경은 병합·배포·SEC/Alpaca 실행·결제·권한 확대 승인이 아니다.

이전 담당표(DC-40·DC-35)는 현행 규칙이 아니다. 원문은 [DIRECTION_CHANGES](docs/SPEC/DIRECTION_CHANGES.md) DC-35·DC-40 줄과 git 이력에 있다.
