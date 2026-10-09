# Tiingo 개인별 키 기기 직접 조회 검토

조회일: 2026-10-09. 대상은 미국 17종목 일봉을 이용자 자신의 기기에서 조회·표시하는 방식이다.
실제 계정 플랜·계약·적용 약관은 사용자가 확인한다. 인증 GET, 키 조회·발급, 가입·연락, 프런트엔드 구현은 조사에 포함하지 않았다.

판정: 사용자별 키 통합은 공식 프로그램에 부합할 수 있지만, 브라우저 직접 호출의 CORS 성공과 구체적인 표시 라이선스 정합성은 미확인이다. 구현·실행 가능을 확정하지 않는다.

## 사용자별 키와 공용 키의 구분

[Developer Program 공식 문서](https://www.tiingo.com/documentation/appendix/developers)는 이용자가 자신의 Tiingo 계정과 API 키를 제공하는 소프트웨어 통합을 설명한다.

- “Each user must have their own API token.”
- “You do not need permission if your use case qualifies”

프로그램 요건을 충족하는 통합에는 별도 허가가 필요 없다고 명시하며, Tiingo 출처 표시와 이용자·개발자의 약관 준수를 요구한다.
이용자별 API 사용 메타데이터 추적은 제한되며, 허용된 지원·디버깅 목적의 추적에도 명시적 사전 동의와 철회가 필요하다.
기존 저장소의 한 공용 키로 여러 이용자에게 데이터를 제공하는 방식은 이 사용자별 키 모델에 해당하지 않는다.
공유 OHLCV JSON이나 공개 API 프록시는 사용자별 키 프로그램만으로 허용되지 않으며, 별도 재배포 권리가 필요하다.
[연결 문서](https://www.tiingo.com/documentation/general/connecting)는 Authorization 헤더의 Token 인증을 지원한다. 키를 정적 사이트에 삽입하는 근거는 아니다.

## 공개 Starter 한도

[현재 가격표](https://www.tiingo.com/pricing): $0/월, 월 500종목, 시간 50회, 일 1,000회, 월 1GB. 과거의 월 50종목 설명을 현재 한도로 사용하지 않는다.
종목당 일봉 요청 한 번이라는 가정에서 US17 조회는 17회이며, 같은 시간에 전체 조회를 세 번 하면 51회로 시간 한도를 초과한다.
다른 요청·재시도·대역폭도 계정 한도에 포함된다. 실제 계정의 플랜과 권한은 공개 가격표나 기존 키 존재로 추론하지 않는다.

## 휘발성 처리와 표시의 조건

[최신 공개 TOS](https://app.tiingo.com/tos/)의 변경 표시는 2026-10-06이다. 기존 이용자에게는 게시·통지 후 30일 적용 조항이 있어 실제 적용 시점은 미확인이다.
§1.6(a)는 Starter/Trial 데이터와 파생 결과를 “volatile memory” 또는 비영구 임시 캐시에서 필요한 계산·작업 동안만 처리하도록 한다.
작업 완료 즉시, 늦어도 작업·세션 종료 전에 삭제해야 한다. 파일·DB·로그·백업·브라우저 영구 저장에 축적하는 설계는 이 조건에 맞지 않는다.
자기 키로 가져온 데이터를 조회·표시 작업 동안 메모리에만 두는 구상은 영구 저장과 구분되지만, 세션이라는 이유로 불필요한 보관까지 허용되지는 않는다.
§1.6(c)는 원본을 대체하거나 복원할 수 있는 파생물을 제한하고, 원시 데이터를 표시·전달하는 “dashboards, charts” 등을 금지 예시에 포함한다.
이 조항만으로 모든 개인의 일시적 원시 차트를 확정적으로 금지한다고 단정하지 않는다. 해당 표시 방식과 Developer Program·계정 계약의 정합성은 별도 확인이 필요하다.

## 익명 CORS 확인 결과

공식 Connecting·Developer Program 문서에서 브라우저 CORS 지원 보장을 찾지 못했다.
2026-10-09 키 없이 EOD prices 경로에 OPTIONS를 보냈다. Origin은 https://example.github.io, http://localhost:8000, https://app.tiingo.com을 사용했다.

| 항목 | 관측 |
| --- | --- |
| 경로 | https://api.tiingo.com/tiingo/daily/aapl/prices 및 끝에 /를 붙인 경로 |
| 요청 메서드 | OPTIONS; Access-Control-Request-Method: GET |
| 요청 헤더 지정 | authorization,content-type 또는 authorization |
| HTTP 상태 | 확인한 응답 모두 200 |
| Vary | Origin |
| Content-Type | text/html; charset=utf-8 |
| 추가 확인 응답 | Content-Length: 0; 리다이렉트·challenge 표식 없음 |
| CORS 허용 헤더 | Access-Control-Allow-Origin, Access-Control-Allow-Headers, Access-Control-Allow-Methods 모두 없음 |

HTTP 200만으로 CORS가 허용된 것은 아니다. 관측된 응답은 Authorization 헤더를 사용하는 브라우저 preflight 통과를 뒷받침하지 않는다.
실제 배포 Origin과 인증 GET·브라우저 런타임은 검증하지 않았다. no-cors 모드는 읽을 수 있는 JSON 응답을 보장하는 해결책이 아니다.
따라서 기기 직접 조회는 사용자별 키·휘발성 처리·표시 권리·CORS가 모두 충족되는 조건부 선택이며, 현재 결과를 실행 성공 약속으로 사용하면 안 된다.
