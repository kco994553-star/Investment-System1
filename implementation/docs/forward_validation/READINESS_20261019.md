# 10/19 전진검증 기록 준비 점검 (2026-10-14 작성)

대상: 2026-10-19(월) 미국 장 마감 뒤부터 시작하는 전진검증 기록. 결정 사항(이미 확정): QGV v2를 기본 기록으로, v1은 비교 기록으로 같은 원장의 별도 배열에 남긴다. 준비된 날부터 기록하며 소급하지 않는다.

이 문서는 코드와 테스트만 보고 판단했다. 라이브 Pages와 Actions 로그 앞부분은 이 환경에서 열 수 없었다(Pages 접속은 프록시가 막았고, 10/13 실행 로그는 뒤쪽 5,000줄만 받을 수 있었다). 확인하지 못한 항목은 "확인 불가"로 따로 적었다.

## 1. 준비 상태 요약

| 항목 | 판정 | 조건 |
|---|---|---|
| (a) v2 원장 행 (`forward_validation/v2`) | CONDITIONAL | 10/19 22:17 UTC 일일 실행에서 원장 단계 앞의 필수 단계가 모두 성공해야 한다. 같은 실행의 `sec-qgv2.json`이 같은 미국 동부 날짜에 만들어지고, Pages에 이전 원장 사본이 있어야 한다. 공개 원장에 남으려면 검증 단계가 통과하고 배포까지 끝나야 한다. |
| (b) v1 비교 행 (`forward_validation/v1`) | CONDITIONAL | (a)와 같은 실행 조건이다. 입력은 같은 실행의 `sec-qg-factors.json`(TARGET SEC 단계)이다. 요인이 축 비중의 50%에 못 미치는 축은 NA(null)로 기록되며, 이것은 기록을 막지 않는다. |
| (c) 세트 A 가상 장부 (TARGET v0) | CONDITIONAL | (a)의 10/19 v2 행이 `RECORDED`이고, 한 기업 이상에서 Q·G가 둘 다 숫자여야 한다. 그날이 세트 A의 시작일(readyDate)이 된다. 기기 쪽 준비(비공개 가격 Worker ON·승인 주소·구글 로그인·시트 연결)를 마치고 기록 모드에서 사용자가 직접 기록을 눌러야 한다. 시간 제한은 없다. |
| (d) 기기 V 기록 (v2 V 이력) | CONDITIONAL | 정해진 시간 안에 기기에서 실행해야 한다. 10/19 기록은 Pages 배포 뒤부터 미국 동부 자정 전까지만 가능하다. 한국 시각으로 10/20(화) 약 08:00~12:59다. 같은 세션의 `sec-qgv2.json`, Worker 종가(10/19 SPY 봉), 구글 로그인이 필요하다. 시간을 놓치면 그날 V는 기록되지 않고 나중에 소급되지도 않는다. |
| (e) 일일 워크플로의 공개 입력 생성 | CONDITIONAL | #243 병합으로 10/10~10/13 실패 원인은 고쳐졌다. 그러나 v2 원장 코드(schema 2)는 아직 실제 Actions에서 한 번도 돌지 않았다. 10/14~10/16 정기 실행 중 한 번 이상이 배포까지 성공하는지 확인해야 한다. 10/19 당일에는 검증 단계도 통과해야 한다. #240은 10/19 기록의 필수 조건은 아니다. |

코드 결함으로 기록이 막히는 항목(NO)은 없다. 다섯 항목 모두 운영 조건(실행 성공, 배포, 기기 조작 시간)에 달려 있다.

## 2. 항목별 의존성과 막는 요인

### (a) v2 원장 행

- 생성: `implementation/tools/forward_validation_ledger.py` → `validation/forward_ledger.py::build_v2_record`.
- 입력(같은 실행 `--out` 폴더):
  - `sec-qgv2.json`: TARGET 행은 `public_screens_pipeline.py --live`가 staged로 만들고, `sec_universe_shares.py --live`가 Universe 행과 합쳐 백분위를 다시 계산한다. 이때 `as_of`는 그 단계의 실행 시각이다.
  - `actual-catalog.json`: 오프라인 빌드, TARGET v0 비중.
  - 선택 입력 `dart-financials.json`: 한미반도체 참고용, `DART_API_KEY`가 있을 때만 생긴다.
- 기록 조건:
  - 실행 시각이 미국 동부 기준으로 그 거래일 16:00 이후여야 한다(22:17 UTC는 EDT 18:17, EST 17:17).
  - `sec-qgv2.json`의 `as_of`가 같은 동부 날짜여야 한다. 아니면 `SEC_QGV2_NOT_SAME_SESSION`, 즉 NA다.
  - TARGET 축 점수가 나오려면 Universe 동업종 표본이 8개 이상이어야 한다. 현재 Pages 사본은 224/504 코드다(`QGV_V2_QUALITY_PARTIAL_20261013.md`).
- 이전 원장 읽기: 라이브 Pages `forward-validation-ledger.json`.
  - 시작일 이후에 404를 받으면 exit 1이 되어 그날 작업 전체가 실패한다.
  - 10/13 수동 실행(run 9, 성공·배포)에 원장 단계가 들어 있었으므로 schema 1 `NOT_STARTED` 사본이 있을 것으로 판단한다. **확인 불가.** 오너가 Pages URL을 열어 확인해야 한다.
  - schema 1 사본은 다음 실행에서 schema 2로 올라간다. 이 경로는 리허설 7번에서 확인했다.
- 막는 요인:
  1. 원장 단계 앞에 continue-on-error가 아닌 단계가 7개 있다: 오프라인 회귀, 빌드, TARGET SEC+매크로, 분류, 도메인/로고, 13F, Universe. 이 중 하나라도 실패하면 그날 원장은 NA 기록조차 생기지 않는다(§4 F1).
  2. 원장 단계 뒤의 검증(node·브라우저)이 실패하면 배포되지 않는다. 그러면 다음 날 실행이 이전 Pages 사본을 읽으므로, 그날 행은 공개 원장에서 영구히 빠진다(소급 없음, §4 F2). `RAW_REPO_TOKEN`이 있으면 비공개 저장소 release에는 남는다. 토큰 설정 여부는 확인하지 못했다.

### (b) v1 비교 행

- 생성: `build_record`. 입력은 같은 실행의 `sec-qg-factors.json`(`public_screens_pipeline.emit`, `as_of`는 그 단계 시각)과 `actual-catalog.json`이다.
- v1 Q·G는 QGV standard v1 가중치에 결측 재정규화 규칙(축 비중 50% 미만이면 NA)을 적용한다. 한미반도체·도쿄일렉트론은 SEC 입력이 없어 NA다.
- 막는 요인: (a)와 같다. 두 버전은 같은 실행에서 같이 기록되거나 같이 빠진다. v1과 v2 중 하나만 생기는 경로는 없다.

### (c) 세트 A 가상 장부

- 계산: 기기 `virtual-trading-runner.js::assemble`.
  - schema 2 원장이면 v2 행만 스냅샷으로 쓴다(`snapshot_basis: 'v2'`).
  - 세션 시작일은 첫 v2 `RECORDED` 행 가운데 Q·G가 둘 다 숫자인 기업이 하나라도 있는 날이다(readyDate). 엔진 시작일은 `virtual-trading.js` 설정의 `start_date: 2026-10-19`다.
- 저장: 사용자의 구글 시트 `VirtualA`/`VirtualMeta` 탭(`virtual-ledger-sheets.js`). 사용자가 누를 때만 추가로 기록한다.
  - 기록 범위는 `recordableThrough`가 정한다: 원장 스냅샷 최신일과 가격 최신 세션 중 앞선 날까지다.
  - 기록이 하루 늦어도 빠진 세션을 결정적으로 이어서 붙인다. 시간 제한은 없다.
- 체결은 `NEXT_SESSION_CLOSE` 규칙을 따른다. 10/19 판단은 10/20 종가로 체결된다.
- 막는 요인:
  - (a)의 10/19 v2 행이 NA이면 세트 A는 다음 준비된 날부터 시작한다.
  - 기기 쪽: Worker 기능 OFF, 미승인 주소, 로그인 없음, 시트 미연결이면 `INPUTS_NOT_READY`/`SHEET_NOT_READY`.
- 리허설 6번: 리허설 원장을 기기 검증기(`forward-validation.js validate`)와 `snapshotsFromLedger`에 넣어 확인했다. 스냅샷 날짜는 `2026-10-19, 2026-10-20`이고 readyDate는 `2026-10-19`다.

### (d) 기기 V 기록 (v2)

- 기록: `virtual-trading-v-history.js::captureV2` → 키 `investment.web.v2.virtual-trading-v-scores`.
  - 같은 날짜·기업 값은 덮어쓰지 않는다.
  - 마지막 기록일보다 이른 날짜는 거절한다(`DATE_BEFORE_LAST_RECORDED`).
  - 가격은 저장하지 않는다.
- 조건(`completedToday`):
  - 기록일 = 실행 결과의 최근 완료 SPY 세션.
  - `sec-qgv2.json` `as_of`의 동부 날짜 = 기록일.
  - 관측 시각(기기 현재 시각)의 동부 날짜 = 기록일, 그리고 16:00 이후.
- 시간 창: 그 거래일 Pages 배포가 끝난 뒤(10/13 실행 기준 약 22:57 UTC 종료)부터 동부 자정 전까지다. 한국 시각으로 10/20 약 08:00~12:59이고, 11/2(EST) 이후 거래일은 다음 날 약 08:00~13:59다. 창을 놓치면 `V2_SAME_SESSION_INPUTS_REQUIRED`로 기록되지 않는다.
- V 기울기는 같은 구성의 20거래일 전 값이 필요하다. 그래서 첫 20거래일(약 11/16까지)은 NA다.
- 막는 요인: 배포 지연·실패(그날 `sec-qgv2.json`이 Pages에 없음), 사용자가 시간 창에 기기를 실행하지 않음, Worker·로그인 미준비. 코드 쪽 막힘은 없다(`virtual_trading_v_history_node_test.js` 통과).

### (e) 일일 워크플로

- 원장에 필요한 공개 입력 4개는 모두 같은 build 작업 안에서 원장 단계보다 먼저 만들어진다: `actual-catalog.json`, `sec-qg-factors.json`, `sec-qgv2.json`, 그리고 선택 입력 `dart-financials.json`.
- 기기에 필요한 공개 입력도 같은 배포에 들어간다: `forward-validation-ledger.json`, `sec-qgv2.json`, 분류 파일.
- Universe504는 하루 한 샤드다(UTC 날짜 서수 mod 7). 10/19는 샤드 1, 10/20은 샤드 2다. 이전 샤드 값은 Pages 사본에서 이어받는다. Universe SEC 요청이 전부 실패해도 이전 사본이 있으면 exit 0이고, TARGET v2 Q·G는 계속 나온다(리허설 7번).
- 최근 이력:
  - 10/10~10/13 정기 실행은 실패했다. 10/13의 원인은 `dart_disclosures_browser_test.js` 실패였고 #243으로 고쳐졌다.
  - 10/13 09:45 UTC 수동 실행(run 9)은 성공했다. 다만 그 시점 코드에는 v2 원장(schema 2)이 아직 없었다.
- #240(수집/검증/배포 분리): 검증 실패 때 수집 결과(아티팩트)와 원장 raw release는 보존한다. 하지만 공개 원장에서 그날이 빠지는 문제(F2)는 #240으로도 해결되지 않는다. 10/19 기록의 필수 조건은 아니다.

## 3. 리허설 (queue 2-2)

`implementation/tests/test_forward_validation_rehearsal_1019.py` (합성 자료와 가짜 전송만 사용, 네트워크 없음, 약 80초)

```
cd implementation && PYTHONPATH=src python3 -m pytest -q tests/test_forward_validation_rehearsal_1019.py
```

방법:
- 일일 워크플로의 순서대로 저장소 도구 진입점을 그대로 호출한다: 빌드 → TARGET SEC → DART → Universe 샤드 → DART v2 투영 → 원장. 각 단계 뒤에 `pages_artifact_guard.scan_artifact`를 실행한다.
- 가짜 전송:
  - SEC TARGET은 `sec_qgv2_reference.synthetic_sec` 기반 합성 companyfacts다.
  - Universe는 `test_sec_universe_shares.transport_for`다.
  - DART는 `test_dart_qgv2_history.SixAnnualDart`다.
- 라이브 Pages는 메모리 사이트로 흉내 냈다. 시작 상태는 10/13 배포와 같은 schema 1 `NOT_STARTED` 원장과 이전 샤드의 합성 Universe v2 표본 27개다. 각 날의 배포가 사이트를 통째로 바꾸므로, 다음 날 실행은 실제와 같은 `fetch_previous` 경로로 전날 원장을 읽는다.
- 모의 실행일: 10/16(금, 시작 전 거래일), 10/17(토), 10/19(월, 첫 거래일), 10/20(화). 시각은 22:20(TARGET), 22:24(DART), 22:28(Universe), 22:45(원장) UTC다.
- 10/16과 10/17은 요청된 날짜지만 둘 다 기록이 생기면 안 되는 날이다(시작 전 거래일과 토요일). 그래서 실제 추가와 이어 쓰기를 확인하려고 10/19와 10/20까지 이어 실행했다.

결과(8개 테스트 모두 통과):

| 확인 | 결과 |
|---|---|
| 전날 원장을 읽어 이어 쓰기 | 10/16은 10/13 schema 1 사본을 읽고 schema 2 `NOT_STARTED`(0행)를 쓴다. 10/17은 10/16 사본, 10/19는 10/17 사본, 10/20은 10/19 사본을 읽는다(바이트 일치 확인). |
| 행 추가 | 10/19: v2·v1 각 1행 `RECORDED`. 10/20: 각 2행이며, 10/19 행은 바이트 그대로 유지된다. V 포함 버전은 빈 배열(`V_REQUIRES_DEVICE_PRICES`)이다. |
| 소급 없음 | 10/16(완료된 거래일이지만 시작 전)은 그날에도 그 뒤에도 기록되지 않는다. 배포가 보류된 10/19는 10/20 공개 원장에서 빈칸으로 남고 다시 채워지지 않는다. |
| NA를 0으로 채우지 않음 | score가 null인 것과 coverage `BLOCKED`는 항상 같이 간다. NOT_AVAILABLE 기업의 값은 모두 null이다. v1 값은 같은 실행의 `sec-qg-factors.json`을 `company_axes`로 다시 계산한 값과 같고, v2 값은 같은 실행의 `sec-qgv2.json` TARGET 축 점수와 정확히 같다(null은 null로 남는다). 한미반도체 v1은 NA이고, v2는 DART 참고값(reference_only)이다. 도쿄일렉트론은 두 버전 모두 NA다. |
| 가격·개인 정보 없음 | 날짜마다 6단계 모두 가드가 PASS다. 공개 파일 전체와 출력 로그에서 User-Agent, 가짜 DART 키, 합성 companyfacts에 일부러 넣은 가격 값(StockPrice)이 나오지 않는다. 원장 키 중 price·close·return·holding·quantity·market이 들어간 것은 `price_free` 하나뿐이다. |
| 결정성 | 같은 합성 입력으로 다시 실행하면 원장과 원장 입력(`sec-qg-factors.json`, `sec-qgv2.json`, `actual-catalog.json`, `dart-financials.json`), 출력 로그가 바이트 단위로 같다. 다른 것은 오프라인 빌드의 NOT_AVAILABLE 자리표시 파일 3개(`company-classification.json`, `news-signals.json`, `sec-disclosures.json`)의 빌드 시각 `as_of`뿐이다. 실제 실행에서는 원장 입력이 아닌 뒤 단계가 이 파일들을 다시 쓴다. |
| 기기 읽기 | 리허설 원장이 JS 검증기를 통과한다. `snapshotsFromLedger`는 v2 행 2일을, readyDate 규칙은 2026-10-19를 낸다. |
| 장애 경로 | 10/19에 Universe SEC 요청이 전부 거절되어도(`COLLECTION_NOT_RUN ... previous_kept`) v1·v2 모두 `RECORDED`다. schema 1 사본을 10/19에 처음 읽어도 정상으로 올라간다. |

## 4. 발견 사항

코드 결함은 찾지 못했다. 원장 생성, 검증, 이어 쓰기 경로는 리허설에서 모두 기대대로 동작했다. 아래는 운영 위험과 문서 오류다. 워크플로와 계산 변경은 오너 승인이 필요하므로 이 PR에서는 고치지 않았다.

- **F1 (운영 위험, 미수정, 결정 필요)**: 원장 단계는 원장과 무관한 단계 뒤에 있다. 분류(SIC·10-K·N-PORT), 도메인/로고, 13F가 그렇고, TARGET 단계 안의 매크로 수집도 마찬가지다. 이 단계들은 continue-on-error가 아니므로 하나만 실패해도 그날 원장이 통째로 빠진다. 입력 결측 때 남기도록 설계된 NA 기록조차 생기지 않는다. 대안은 둘이다: 원장 입력 단계(TARGET, Universe, DART)와 원장 단계를 앞으로 옮기거나, 원장과 무관한 단계를 continue-on-error로 바꾼다. #240과 같은 파일을 바꾸므로 #240과 함께 결정하는 것이 좋다.
- **F2 (운영 위험, 이미 알려짐)**: 검증 실패로 배포가 보류되면 다음 날 실행이 이전 Pages 사본에서 이어 쓰므로, 그날 행이 공개 원장에서 영구히 빠진다. 리허설 7번에서 재현했다. 막으려면 이전 원장을 비공개 raw release(`forward-ledger-YYYY-MM-DD`)에서 읽는 변경이 필요하다(#240 본문의 확인 사항과 같음).
- **F3 (문서 오류 수정 + 용량 결정 필요)**: v1·v2를 함께 기록하므로 원장은 거래일당 약 8.2KB씩 늘어난다(합성 리허설 측정: 10/19 8,945B → 10/20 17,182B). 생성기 한도 2MB(`MAX_BYTES`)에는 약 250거래일 뒤, 즉 **2027년 10월 전후**에 닿는다. 닿는 날부터 원장 단계가 exit 1로 실패하고 그날 일일 작업 전체가 멈춘다. `FORWARD_VALIDATION_V1.md` §7의 "기록 1건 약 4KB, 연 약 1MB, 약 2028년"은 v1만 기록하던 때의 값이라 실제보다 작다. 같은 PR의 별도 커밋에서 문서만 고쳤다. 분할 방식 결정 기한은 2027-09 이전이다.
- **F4 (주의)**: cockpit-pages 수동 배포(workflow_dispatch)를 일일 실행 시간대(약 22:17~23:15 UTC = 한국 07:17~08:15)에 하면 위험하다. 그날 원장이 들어가기 전의 Pages 사본을 복원해 덮어쓸 수 있고, 그러면 그날 행이 공개 원장에서 빠진다(F2와 같은 결과). 그 시간대에는 수동 배포를 하지 않는다.
- **F5 (참고)**: v2 점수는 `sec-qgv2.json` 값을 반올림 없이 그대로 기록한다(예: 12.884615384615385). v1은 소수 4자리로 반올림한다. 결정성과 검증에는 문제가 없고 표시 형식만 다르다.

## 5. 당일 확인 순서

- 10/14~10/16 각 실행(한국 다음 날 아침): 아래를 확인한다.
  - `FORWARD_LEDGER status=NOT_STARTED records=0 appended=0 ... v2_records=0 v2_record=NONE`
  - deploy 작업 success
  - Pages의 `forward-validation-ledger.json`이 `schema_version: 2`, `status: NOT_STARTED`
  - 실패하면 `CI_TEST_FAILED`/`DAILY_VERIFY_FAILED` 토큰을 확인한다.
- 10/19 실행(한국 10/20 07:17 시작): 아래를 확인한다.
  - `SEC_QGV2_TARGET staged companies=17 ...`
  - `SEC_QGV2 shard=1/7 ... target_q_scored=N` (N ≥ 1)
  - `FORWARD_LEDGER status=ACTIVE records=1 appended=1 record=RECORDED session=2026-10-19 v2_records=1 v2_record=RECORDED`
  - `RAW_UPLOADED tag=forward-ledger-2026-10-19` 또는 `RAW_UPLOAD_NOT_CONFIGURED`
  - deploy success
- 10/20 한국 08:00~12:59: 기기에서 기록 모드로 가상매매를 실행해 v2 V를 기록한다(S17 표시가 `RECORDED`인지 확인). 세트 A 장부는 시트 연결 뒤 같은 화면에서 기록하며, 나중에 해도 된다.
- 10/19 행이 `NOT_AVAILABLE`로 기록되면 이유 코드(`SEC_QGV2_NOT_SAME_SESSION` 등)를 확인한다. 소급 기록은 하지 않고 다음 거래일 기록을 기다린다.

## 6. 범위 밖

- 실제 Actions 실행과 라이브 Pages 상태: 이 환경에서 접근할 수 없었다.
- #240의 병합 여부와 F1·F2 대안: 오너 결정이 필요하다.
- 새 node·브라우저 테스트는 없으므로 CI 목록에 등록할 것도 없다. 새 pytest는 cockpit-pages의 전체 pytest(`tests` 전체)에서 실행된다.
