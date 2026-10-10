# SEC13F supplied 정보표와 분기 보고 수량 변화

사용자 대기열8번. `providers/sec_13f.py`는 supplied 정보표 XML과 별도로 확인한 cover/header metadata를 순수 함수로 처리한다. 실제 SEC 수집·워크플로·공개 serializer·가격/개인 목록 저장을 연결하지 않는다. 투자자는 **사용자 선택 CIK 목록**으로만 허용하며 기본 추적 기관은 없다. 투자자 CIK를 TARGET 기업 issuer CIK 목록으로 제한하거나 서로 혼동하지 않는다.

## 입력·단위·완전성

`parse_information_table(payload, metadata, *, selected_manager_ciks=(), as_of=...)`의 XML 자체에는 manager·보고분기·amendment 관계가 없어 supplied cover/header 결속을 별도로 확인해야 한다. manager CIK/accession, 정확한 달력 분기말·제출일·aware 취득시각, 명시적 value basis, 보고 유형, 정정 유형, 비공개 보유 생략 여부, 전체 entry count/완전성과 정정 계보 해결 근거가 필요하다.

금액 단위는 `USD_DOLLARS`/`USD_THOUSANDS`를 보존한다.2023-01-03 이후 **제출되는** 보고/과거분기 amendment에는 새 dollar 양식이 적용된다. 보고분기 연도로 단위를 추정하거나 모든 rawvalue에1000을 곱하지 않는다. 변화 계산은 금액이 아닌 **정수 보고 수량**이며 현재가격·매매가·가격 변화 계산을 하지 않는다.

정보표 schema의 full9자리 CUSIP, class, SH/PRN, Put/Call, investment discretion, otherManager 귀속을 보존한다. FIGI는 CUSIP 대체물이 아니다. 동일한 exact bucket의 여러 행만 보고 수량을 합산하며 원 행은 보존한다. 서로 다른 주식 종류·옵션·수량 단위·귀속을 합치거나 ticker/split 변환하지 않는다. otherManager 행번호는 filing마다 달라질 수 있어 확인된 cover의 manager identity로 결속되어야 비교할 수 있다.

## 비교·표시

`compare_quarters(previous, current)`는 같은 사용자 선택 manager의 **연속 달력분기**만 비교한다. 두 입력의 취득/as_of·cover 결속·전체 표·비공개 생략 없음·정정 계보가 확인되어야 한다. 서로 다른 분기·기관, NOTICE/COMBINATION, NEW_HOLDINGS 단독, 미확인 완전성/비공개 여부, count/value 합 불일치, 잘못된 행은 NOT_AVAILABLE이며 누락을0/EXIT로 만들지 않는다. RESTATEMENT는 완전한 대체본·해결된 계보일 때만 허용하고 원본에 다시 더하지 않는다.

두 입력은 동일한 실제 UTC cutoff로 선택된 취득본이어야 한다. 이전 표를 현재 cutoff로 다시 파싱하더라도 실제 취득시각은 보존한다. 전체 entry count나 cover/정정/비공개 확인이 부족하면 형식상 유효한 행은 PARTIAL/RAM로 보존할 수 있지만 비교는 NOT_AVAILABLE다. 잘못된 XML 행은 전체 capture를 무효화하며 임의로 건너뛰지 않는다.

변화는 NEW/ADD/REDUCE/EXIT의 **공개 보고 수량 변화**다. NEW는 새로 보고된 항목, EXIT는 공개 보고에서 소멸/수량0이며 **실제 신규매수·전량매도 확정이 아니다**. SEC는 소액 보유의 생략을 허용하며 기업행위·비공개 해제·표현/귀속 변경도 실제 매매와 다를 수 있다. 금액만 변하면 ADD/REDUCE를 만들지 않는다. 같은 CUSIP의 class/share basis/귀속이 비교 불가능하게 바뀌면 임의 alias나 신규/EXIT 대신 미제공이다.

결과 role은 `REPORTED_QUANTITY_ONLY`, split 보정은 하지 않는다. 개인 선택 manager·정보표와 결과는 repr에서 숨긴 불변 RAM 값이며 Model/TSV/QGV·현재 보유·실제 거래 추론·공개 producer에 연결하지 않는다. 분기는 호출자가 공급하며 에이전트가 Holdout/전진검증 시작 기간을 선택하지 않는다.

## 공식 근거·검증

공식 schema·설명만 조사했으며 실제 manager filing/보유는 받지 않았다.

- [13F XML v2.0(September2026) 공식 사양](https://www.sec.gov/files/edgar/filer-information/specifications/edgar-form-13f-xml-technical-specification-2-0.zip): `http://www.sec.gov/edgar/document/thirteenf/informationtable`, informationTable/infoTable, 필수 issuer/class/CUSIP/value/shrsOrPrnAmt/discretion/voting 필드와 선택 FIGI/Put/Call/otherManager.
- [SEC13F FAQ](https://www.sec.gov/rules-regulations/staff-guidance/frequently-asked-questions-about-form-13f): Q36/Q62 금액 단위·새 양식, Q58b/c RESTATEMENT·추가 항목 amendment 구분.
- [Form13F](https://www.sec.gov/files/form13f.pdf): Special Instructions5/9 NOTICE·소액 생략, Confidential Treatment Instruction4 비공개 해제의 NEW HOLDINGS amendment.

합성 XML로 namespace/필수·중복 필드/DTD·entity/NUL/CUSIP·class/options/SH·PRN/단위·정수/entry 완전성/연속분기·같은 기관/정정·비공개·귀속/0·신규·추가·축소·소멸/금액만 변화/불변성·저장·네트워크 없음 경계를 검증한다. 실제 투자자 목록·가격·Holdout을 사용하지 않는다.

공식 XSD의 infoTable 기본 minOccurs=1이므로 빈 XML 표는 무효이며 전체 보유의 실제 청산을 추론하지 않는다. root의 `xsi:schemaLocation`은 허용하되 힌트를 무시하며 외부 schema를 요청하지 않는다. otherManager는 사양의 단일/쉼표 reference(cover 번호1~999)와 raw100자 경계를 확인한다. 같은 CUSIP에서 bucket 집합이 바뀌면 전체 비교를 보수적으로 미제공하며 자동 alias·주식/옵션/귀속 변환은 하지 않는다.
