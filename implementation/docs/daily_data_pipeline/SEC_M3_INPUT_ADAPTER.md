# SEC M3 공급 입력 어댑터 v1

사용자 2026-10-10 지시: #122 연결을 위해 공개 SEC 식별·주식 종류 근거를 먼저 공급한다. Worker·웹·Actions 연결은 코덱1이며 이 PR은 해당 파일을 바꾸지 않는다.

## 파일·계약

- `providers/sec_m3_adapter.py`: `build_sec_m3_input(*, code, companyfacts_body, submissions_body, acquired_at, as_of, synthetic, cover_xml, cover_accession, cover_acquired_at)` → frozen `SecM3Input`.
- code는 정확한 `NASDAQ:SYMBOL`/`NYSE:SYMBOL`. submissions의 ticker·exchange·CIK와 facts CIK를 확인한다. 점/하이픈 alias·CIK 대체·ADR 비율·주식 종류 합산을 추정하지 않는다. TARGET US17은 기존 company_id, 다른 종목은 `sec_<10자리CIK>`; listing/security는 현재 확인 범위의 내부 ID다.
- `ListingSeed`, `SecReceipt`, `ShareBasisReceipt`, `SharesInput`은 #106/#110의 Python 계약을 그대로 사용한다. captured UTC 날짜부터의 현재 식별 근거이며 과거 listing/PIT 최초 발표를 증명하지 않는다.
- 같은 accession·measurement date의 SEC XBRL instance에 있는 CIK context·TradingSymbol·Security12bTitle·EntityCommonStockSharesOutstanding와 shares unit을 결속한다. 단일 ticker/단일 수치만으로 class를 확정하지 않는다. 별도 class/ADR/단위 근거가 없으면 NOT_AVAILABLE; ADR 자동 보정 없음.
- 동일 cover의 무차원 총수량이 companyfacts와 일치하고, 별도 class dimension 수량이 다르며 복수 class 근거가 있을 때만 **SHARE_CLASS_BASIS 표시만** 한다. 기존 수치는 바꾸지 않고 계산을 차단한다. 단순 수량 불일치는 COVER_FACT_MISMATCH, 차이를 입증하지 못한 복수 class는 MULTI_CLASS_AMBIGUOUS다. 과거 filing·다른 measurement date·불명 acceptance·중복/모호 class·취득 이후 cutoff는 제외한다.

cover의 accession·취득시각은 공급자가 제공하는 메타데이터다. 원문 hash는 bytes 동일성을 확인하며 원기관 취득의 진위를 자체 인증하지 않는다. CIK·주식 단위 QName·거래소 dimension을 검증하고, class/context 결속은 같은 context 또는 submissions reportDate와 일치하는 등록 context만 허용한다. 미확인 거래소·ADR·preferred·기타 모호한 종류는 계산을 허용하지 않는다.

## 코덱1 loadInputs 연결

`public_sec_input_json(result)`는 공개 producer 연결이 아닌 **명시적 필드 투영 함수**다. 반환:

```text
identityLookup[Google code] -> ListingSeed
secByListing[listing_id] -> cik, companyfacts_text, submissions_text,
    acquired_at, facts_sha256, submissions_sha256,
    origin_facts_sha256, origin_submissions_sha256, synthetic,
    projection=SEC_PUBLIC_SHARES_ONLY_V1
basisByListing[listing_id] -> ShareBasisReceipt (있을 때)
state, reason_codes
```

JS는 두 `_text`를 **TextEncoder.encode()**해 각각 `companyfacts_body`, `submissions_body` Uint8Array로 옮긴 뒤 기존 `prepareSecShares`에 전달한다. derived bytes의 SHA가 `facts_sha256/submissions_sha256`이며 원문 SHA와 혼동하지 않는다. 기존 원문 bytes는 Python receipt에 그대로 보존한다. JSON 투영에는 CIK·정확한 ticker/exchange·주식 수 두 concept의 val/end/filed/form/accn·recent의 accession/form/filingDate/acceptanceDateTime만 남긴다. 가격 concept·시총·연락처·unknown 필드·원문 전체·XBRL 원문을 내보내지 않는다.

공개 공급은 사용자 승인된 **전체 후보 코드 범위의 정부 식별/주식수**에 한정한다. 기기 ★·선정 종목·N/순위·가격/시총·시트 ID를 Actions/공개 endpoint에 역전송하거나 출력하지 않는다. 현재 함수는 실제 cover 취득/파이프라인·배포를 실행하지 않으며 cover를 확보하지 못한 종목은 basis 미확정으로 남긴다. #126 공급자가 accession별 원문·취득시각·hash를 전달하고 코덱1이 #122 loadInputs를 연결해야 실제 앱 입력이 된다.

## 코드만 있는 정적 자산

[`universe_codes_v1.json`](../../src/investment_system/universe/universe_codes_v1.json)은 사용자가 이번 지시에서 명시적으로 승인한 **504개 code 문자열 배열만**이다. 기존 비공개 Universe의 정확한 A열·거래소 prefix·GOOGL/GOOG·BRK.B·PSKY·ASML을 보존한다. 시트 ID/URL·가격·시총·선정/순위·사용자 ★는 없다. 사용자 후보 목록이며 공식 S&P membership·PIT universe·모든504행의 SEC 가용성을 주장하지 않는다. 코덱1은 이 JSON을 정적 자산으로 복사할 수 있다; 코덱2는 web_assets를 편집하지 않는다.

검증은 합성 XBRL/JSON과 기존 M3 계약으로 수행하며 실제 정부/API/개인 가격 호출 없이 검사한다.
