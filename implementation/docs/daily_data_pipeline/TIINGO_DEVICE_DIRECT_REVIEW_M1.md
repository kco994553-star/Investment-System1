# Tiingo 사용자 키·기기 직접 일봉 표시 조사

조회일: **2026-10-09 UTC**. 범위는 사용자 각자의 Tiingo 계정·본인 키로
휴대폰 브라우저가 미국 17종목 일봉을 직접 받고, 영구 저장 없이 본인에게만
표시하는 방식이다. 공식 문서와 무인증 OPTIONS 2회만 확인했다. 계정 조회,
키 발급·Secret 값 조회, 가격 GET, 응답 본문, 실제 차트·연동 코드는 없다.

**판정: Developer Program 요건을 지키는 개인 직접 조회·일시 처리는 조건부
후보이나, 현재 사전 요청에서 CORS 허용 헤더가 없어 브라우저 직접 조회는
UNCONFIRMED다. 이번 결과는 구현·CSP 확장·공급자 채택 승인이 아니다.**

## 프로그램과 사용자 자격

공식 Developer Program은 각 사용자가 자신의 계정·API Token을 제공하고 앱이
Tiingo 데이터를 재배포하지 않는 통합을 설명한다. 요건에 맞는 사용 방식에는
별도 허가가 필요 없다고 안내한다. 프로그램 등록을 위한 앱 소개·연락처
이메일 안내는 통합 목록·메일링·마케팅 절차와 함께 제시된다. 이 설명을 모든
앱·플랜의 무조건 승인이나 별도 계약·추가 약관의 면제로 해석하지 않는다.
이번에는 연락하거나 등록하지 않았다.
[Developer Program](https://www.tiingo.com/documentation/appendix/developers),
[일반 API 안내의 라이선스 구분](https://www.tiingo.com/documentation/)

사용자별 본인 토큰으로 인증하며 Tiingo 비밀번호·로그인 폼을 앱에서 받거나
자동 계정 등록하지 않는다. 공급자 출처를 명확히 표시하고 사용자 API 이용
메타데이터를 수집·기록·판매하지 않는다. 문서의 제한적인 지원 분석 예외도
명시적 opt-in 조건이 있어 기본 추적 근거가 아니다. 공유 앱 키, GitHub
Secret을 기기로 전달하는 방식, 서버·중계·Actions 가격 수집은 이 범위에서
계속 금지한다. 기존 앱의 가격 공급자 OFF 상태도 변경하지 않는다.

## 영구 저장 없는 표시의 경계

공식 약관 최종 변경 표시는 **2026-10-06**이다. §1.6(a)는 무료 Starter와
무료·유료 Trial에서 원자료와 파생물을 휘발성 메모리/비영구 캐시의 일시 처리로
제한한다. 해당 처리·작업 완료 즉시 삭제하고, 어떤 경우에도 프로세스·작업·
사용자 세션이 끝나기 전 삭제해야 한다. 단순히 ‘탭을 닫을 때 삭제’로만
설계하면 처리 완료 후 잔존 금지를 충족한다고 볼 수 없다.
[약관 §1.6(a)](https://app.tiingo.com/tos/)

개인 기기의 IndexedDB·localStorage·파일·백업·로그·큐·영구 브라우저 캐시와
가격 또는 파생 결과 내보내기는 금지 대상으로 취급한다. 표시 과정에 남는
차트 값·계산 결과도 원자료와 함께 삭제 경계를 확인해야 한다. 영구 데이터가
없는 단순 화면이라는 설명만으로 이런 조건을 충족했다고 판단하지 않는다.
공개 차트 파일·JSON을 생성하거나 반환값을 공개 스냅샷에 합치는 방식은
Developer Program의 개인 직접 조회와 다른 재배포다.

개정 약관은 신규 이용자와 기존 이용자의 적용 시점이 다르며, 기존 이용자는
게시/이메일 통지 후 30일 조건과 추가 약관 우선 조항을 확인해야 한다.
실제 계정 플랜·추가 계약·통지일은 미확인이다. 최신 공개 조건을 이 설계의
기준으로 삼지만 그 계정의 현재 적용 조건을 확정하지 않는다.
[약관 변경·추가 약관 안내](https://app.tiingo.com/tos/)

## 무료 한도와 17종목 범위

| 공개 개인 요금제 | Starter | Power |
| --- | --- | --- |
| 월 구독료 | $0 | $30 |
| 월 unique symbols | 500 | 전체 카탈로그 한도 |
| 요청 한도 | 50/시간, 1,000/일 | 10,000/시간, 100,000/일 |
| 월 대역폭 | 1GB | 40GB |
| 라이선스 | Internal Use Only | Internal Use Only |

17종목당 일봉 1요청은 최소 17요청으로 Starter의 공개 시간·일·심볼 한도
안이다. 메타데이터 확인·백필·재시도와 대역폭을 합산해야 하며 실제 계정
잔여 한도는 확인하지 않았다. 오래된 블로그의 무료 한도를 재사용하지 않는다.
[현재 가격표](https://www.tiingo.com/pricing),
[한도 초기화 안내](https://www.tiingo.com/documentation/general/overview)

PR #78 승인 문서의 기존 공개 목록 조사에는 미국 17개
`ASML, LRCX, KLAC, NVDA, AMD, AVGO, QCOM, INTC, MSFT, GOOGL, AMZN,
RTX, SYK, ETN, HUBB, GEV, ROK`가 존재한다. 큰 지원목록은 재다운로드하지
않았다. 공식 EOD 문서는 지원목록에 **예약 심볼도 포함**한다고 경고하므로
17/17 목록 존재를 실제 계정 접근 성공·완전한 일봉 이력으로 간주하지 않는다.
TSE 8035·KRX 042700을 미국 대체 종목으로 바꾸지 않으며 이 조사 대상에도
포함하지 않는다.
[공식 EOD 문서](https://www.tiingo.com/documentation/end-of-day),
[기존 조사 커밋](https://github.com/kco994553-star/Investment-System1/blob/9c2eb172778e7cc8b781dc53267a0f02757097c6/implementation/docs/daily_data_pipeline/PRICE_RIGHTS_OPTIONS.md)

## CORS: 사전 요청만 확인

공식 문서에서 이 앱 Origin의 브라우저 CORS 보장은 찾지 못했다. 공개 Origin
`https://kco994553-star.github.io`에서 향후 `GET`과 `Authorization` 헤더를
쓸 때의 사전 요청을 무인증 **OPTIONS 2회**로 확인했다. 자동 리다이렉트,
쿠키·토큰·본문 읽기·실제 GET 없이 아래 상태와 세 허용 헤더만 기록했다.

| 2026-10-09 UTC | 공식 API 경로 | HTTP | Allow-Origin / Allow-Methods / Allow-Headers |
| --- | --- | --- | --- |
| 10:19:55 | `https://api.tiingo.com/tiingo/daily/nvda/prices` | 200 | 모두 없음 |
| 10:20:15 | `https://api.tiingo.com/tiingo/daily/nvda/prices/` | 200 | 모두 없음 |

검사한 응답은 `GET + Authorization` 사전 요청을 허용한다는 증거가 아니다.
환경에서 관측한 두 경로의 결과를 전체 계정·모든 엔드포인트의 불가능 판정으로
확장하지 않고 **CORS UNCONFIRMED**로 남긴다. 사전 요청이 성공하더라도
인증 GET의 성공·그 응답의 CORS·상품 접근권을 보증하지는 않는다. 서버나
프록시로 우회하지 않는다. 기존 CSP는 별도 승인이 없는 한 유지한다.
[공식 EOD 경로](https://www.tiingo.com/documentation/end-of-day),
[공식 헤더 인증 설명](https://www.tiingo.com/documentation/general/connecting)
