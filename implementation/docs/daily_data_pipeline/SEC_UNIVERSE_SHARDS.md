# Universe504 — 명시적 SEC 범위·일 단위 분할 수집

US17 기존 collect는 그대로 제한한다. `providers/sec_universe_collection.py`의 별도 UniverseSecClient는 승인된 코드 자산504개와 **공급된 공식 SEC company_tickers_exchange.json의 cik/ticker/exchange**를 결합한 registry만 허용한다. 공식 원기관 파일 URL은 https://www.sec.gov/files/company_tickers_exchange.json 이며 원문 취득·출처 확인은 caller가 한다. SHA는 공급 bytes 결합이며 원기관 인증 증명이 아니다. SEC 이름은 출력하지 않는다. Nasdaq/NYSE를 명시 매핑하고 BRK.B/BRK-B처럼 점→하이픈의 주식 종류 표기 alias만 허용한다. 다른 거래소/불일치/CIK 충돌은 미확인으로 남긴다. alias는 주식수·가격 basis 변환이 아니다.

같은 CIK의 GOOG/GOOGL 등은 한 번만 companyfacts+submissions를 취득한다. listing504개와 회사500개를 동일 분모로 취급하지 않는다. 모든 회사의 종류별 주식 basis가 확인됐다는 뜻도 아니다. #134 SEC M3 cover 확인·#110 SHARE_CLASS_BASIS 표시만/자동보정 금지를 그대로 적용한다.

## 코덱1 실행 연결

```sh
python implementation/tools/sec_universe_collect.py \
  --sec-ticker-exchange-json /private-workspace/sec-ticker-exchange.json \
  --shard-count 7 --shard-index 0 \
  --output-dir /private-workspace/sec-universe-raw --allow-live
```

7/0은 호출 예시이며 자동 채택한 주기/시작일이 아니다. caller가 shard_count를 고정하고 매일 index를0..count−1 순환한다. SHA256(CIK) mod count로 모든 issuer를 정확히 한 파티션에 배치하며 투자 순위·시총·모델 방법론을 만들지 않는다. registry 또는 count 변경 시 전체 사이클을 다시 커버할 운영 정책은 코덱1이 정한다. 키는 환경 `SEC_USER_AGENT` 이름만 참조한다. import/테스트에 환경값 조회나 요청은 없다.

요청은 단일 client의 기존 lock·0.2초 최소 간격(5회/초)·최대5회 재시도·Retry-After 상한60초·32MiB·redirect 거부·CIK 확인을 공유한다. SEC 한도10회/초는 다른 Actions/Worker를 포함하므로 운영자가 작업 겹침을 조정해야 한다. 동시504개 호출·새 워크플로·실제 대량 실행은 하지 않았다.

회사별 성공 bytes는 caller sink에만 전달한다. fetch/parse/sink 실패는 다음 회사로 계속하고 값 없는 고정 코드+회사 순번과 성공/실패/미확인 코드 수만 출력한다. 하나 이상 성공이면exit0, 시도한 회사가 전부 실패면exit1·이전 manifest 보존, 해당 shard에 회사가 없으면빈 manifest/exit0다. 현재 shard에 없는 과거 회사 파일/다른 파티션의 manifest는 통합하지 않는다. 최신성·전체 커버리지는 운영측이 취득시각으로 따로 검증한다.

출력은 **로컬 raw workspace 전용**이다. companyfacts에는 다양한 원본 개념이 있으므로 raw JSON/manifest를 Pages·공개 artifact로 복사하면 안 된다. 공개 표시에는 #141의 strict 가격 없는 projection/guard를 사용한다. 여기서는 QG 점수나 M3 순위·가격·share-class confirmation을 생성하지 않는다. 기기 ★/시트 ID/시세는 입력도 없다.

## 검증·미확인 범위

합성 SEC metadata/transport로504code 경계·거래소/BRK.B alias·CIK 충돌·동일회사 중복 방지·파티션의 배타적 전체 커버·invalid schedule·요청 속도·403·부분/전부 실패·sink 오류·고정 코드 마스킹을 검증한다. 실제504code의 CIK 확인율과 회사 수, 실제 daily 성공률은 공식 metadata와 실제 취득이 공급되기 전 NOT_AVAILABLE다. SEC_USER_AGENT 미설정 실행 환경에서 실데이터 수집을 가장하지 않는다.

## 공개 주식수 파일 `sec-universe-shares.json` (사용자 결정 2026-10-11, M3 주식수 (a))

- 생성: `tools/sec_universe_shares.py --live --out <Pages 폴더>`(Actions, `SEC_USER_AGENT` 이름만 참조). shard = UTC 날짜 ordinal mod `shard_count`. 공식 `company_tickers_exchange.json` → 504 registry → 당일 shard의 companyfacts·submissions + 같은 filing의 cover XBRL(`<primary>_htm.xml`).
- 병합: 실행 전 Pages의 직전 파일을 검증해 읽고(404면 새로 시작, 형식 불일치면 폐기), 이번 shard 행만 교체한다. 새 행에 주식수가 없으면 기존 값을 지우지 않는다. 각 행은 자기 `acquired_at`을 유지하고 stale 창을 넘으면 `STALE`. 직전 파일 네트워크 실패 시 아무것도 쓰지 않고 exit1.
- 설정: `universe/sec_universe_shares_config_v0.json` — shard_count 7, stale 14일. **DEFAULT_V0_UNCALIBRATED**(v0 기본값, 보정 아님). 기기 화면은 "v0 기본값 · UNCALIBRATED"로 표시한다.
- basis(표지 기준, `sec_m3_adapter` cover parse 재사용): 한 class·symbol 일치 → `SINGLE_CLASS_CONFIRMED`; 표지에 복수 class가 있고 이 listing의 class 값이 하나로 확정 → `SHARE_CLASS_BASIS`(공개 파일은 표지 class 값만, 보정 없음; 기기에서 `share_class_groups/v0` 묶음만 합산해 순위, 나머지는 순위 제외); 그 외 → `BASIS_UNCONFIRMED`(companyfacts 수치는 보이되 검증 안 됨). 결측은 null, 0 대체 없음.
- 공개 필드: cik·listing_id·company_id·shares·measurement_date·accn·form·filed·acquired_at·concept·share_class_basis·basis_evidence(cover accn, class member 이름·개수)·source_sha256(companyfacts/submissions/cover)·state·reason_codes. 가격·시총·순위·선정·시트 ID 없음. 검증: Python `require_universe_shares`(Pages guard), JS `SecUniverseShares.validate`.
- 원본: `RAW_REPO_TOKEN`이 있으면 shard 원본(tar.gz+sha256)을 비공개 `investment-system1-raw` 릴리스 `sec-universe-raw-YYYY-MM-DD-shardN`에 올린다. 없으면 `RAW_UPLOAD_NOT_CONFIGURED`. 토큰 값은 출력하지 않는다.
- UI 전용 배포(cockpit-pages)는 `tools/sec_universe_shares.py --preserve-only --out <폴더>`로 직전 파일을 보존한다.
- 기기: `private-subset-view.js`가 이 파일을 읽어(`sec-universe-shares.js`) `PrivateSubset.preparePublicShares`로 기존 M3 비교(N=20, 10% 포함 경계)에 넣는다. 가격·R·순위는 RAM 전용. JS==Python 대조: `tests/fixtures/m3_public_shares_reference_v1.json`.
- 경제적 동일 종류 합산(사용자 결정 2026-10-11): 기기 설정 `share_class_groups/v0`(V0_UNCALIBRATED)에 있는 Alphabet(GOOGL+GOOG)·Fox(FOXA+FOX)·News Corp(NWSA+NWS)만 종류별 `SHARE_CLASS_BASIS` 표지 주식수 × 종류별 시트 가격을 합산해 회사 1개로 순위에 넣는다. 모든 종류가 LIVE·가격 있음이어야 하며 아니면 사유와 함께 제외(부분 합·0 대체 없음). 그 밖의 `SHARE_CLASS_BASIS`/`BASIS_UNCONFIRMED`는 계속 제외. 공개 파일 형식은 그대로. 상세: [M3_SHARE_CLASS_GROUPS_V0.md](M3_SHARE_CLASS_GROUPS_V0.md).
