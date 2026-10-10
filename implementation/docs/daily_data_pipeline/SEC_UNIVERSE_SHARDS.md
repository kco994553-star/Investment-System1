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
