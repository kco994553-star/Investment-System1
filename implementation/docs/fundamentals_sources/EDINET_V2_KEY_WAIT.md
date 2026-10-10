# EDINET v2 키 요구 확인 — 사용자 결정 대기

2026-10-10 저장소 근거 확인. 사용자 연속 대기열9번의 **키 필요 여부**를 확인했으며, 필요하면 보고 후 대기한다는 지시에 따라 adapter 구현은 시작하지 않는다. 기존 [KR/JP 공식 조사](KR_JP_FILINGS_RESEARCH.md#2-edinet-api-v2)의2026-10-09 공식 조회 근거를 사용했으며 이번에는 가입·키 발급·키 존재 확인·인증/API·실제 데이터 취득을 하지 않았다.

## 판정

**KEY_REQUIRED / WAITING_USER_DECISION**. 금융청 EDINET API v2는 제출 목록과 문서 취득에 `Subscription-Key`가 필요하다. 이 문자열은 공식 credential parameter 이름이며 실제 값은 저장소/PR/로그/대화에 기록하지 않는다.

| 용도 | 키 값을 제외한 공식 endpoint |
| --- | --- |
| 제출 목록 | `https://api.edinet-fsa.go.jp/api/v2/documents.json`, public parameters date/type |
| 문서 취득 | `https://api.edinet-fsa.go.jp/api/v2/documents/{docID}`, public parameter type |

Tokyo Electron identity는 `E02652`·증권코드`80350`·TSE8035다. 키 등록이 확인돼도 SEC companyfacts 형식으로 주입하지 않고, 별도 제출 목록→문서→XBRL/CSV context·회계·연결/별도·통화/단위·정정/철회·취득시각 adapter가 필요하다.

## 공식 근거와 후속 조건

- [API v2 사양서](https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/download/ESE140206.pdf),2026년6월판/개정2.9: 등록·MFA/키와 v2 호출 계약. [공식 등록 진입점](https://api.edinet-fsa.go.jp/api/auth/index.aspx?mode=1). 사용자 본인이 등록·약관 수락·비공개 설정을 수행한다.
- [공식 API FAQ](https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/WZEK0090_001.html) Q6: 목록 조회1분1회 이하 권장; 사양서의429 대기·간격 조정. 권장 간격을 무제한/확정 최대 한도로 주장하지 않는다.
- 숫자 재사용의 PDL1.0·EDINET 출처·가공 사실 표시와 제3자 권리/주석·taxonomy 구분은 기존 조사 조건을 따른다. 현행 서비스에 요금표는 없지만 영구 무료 보장 조항은 미확인이며 민간 EDINET DB와 혼동하지 않는다.

사용자에게 필요한 것은 **비공개 키 등록 완료 알림과 adapter 착수 결정**이다. 실제 키 값을 전달받지 않는다. 설정 이름은 후속 구현에서 확정하며 이번 문서가 새 Secret/워크플로·계정·자동 수집을 생성하지 않는다.

## DART 유지

대기열10번은 **사용자가10/11 18시 이후 DART_API_KEY 등록을 알린 뒤** 시작한다. 현재 해당 알림이 없으며 DART 코드·키 존재 확인·인증/API는 착수하지 않았다. 시간 경과를 등록 알림이나 승인으로 간주하지 않는다. 원 지시의 시간대는 명시되지 않았으므로 임의로 설정하지 않는다.

이것은 기존 승인 조건의 상태 기록이며26E 사용자 결정 변경·새 GSQ·receipt·fingerprint가 아니다.
