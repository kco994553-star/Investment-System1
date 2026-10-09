# 비공개 구글 시트 시세 불러오기

개인 참고용입니다. 투자 권유나 자문이 아닙니다.

앱의 수동 시세·환율 입력은 계속 사용할 수 있습니다. 구글 시트 연결은 선택
기능이며 기본 OFF입니다. 사용자가 버튼을 눌렀을 때만 휴대폰 브라우저가
Google에 직접 연결합니다. 서버·중계·GitHub Actions는 시세를 수집하지 않습니다.
로그인 없이 시트 A~C열을 일괄 붙여넣는 방법도 사용할 수 있습니다.

## 1. Google Cloud 설정 확인

다음 항목은 프로젝트 소유자가 Google Cloud Console에서 설정합니다. 이미
설정된 프로젝트는 내용을 확인하면 됩니다. 일반 앱 사용자는 2번부터 진행합니다.

1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트
   `investment-cockpit-511105`를 선택합니다.
2. API 및 서비스 → 라이브러리에서 **Google Sheets API**를 사용 설정합니다.
3. Google Auth Platform → 브랜딩·대상·데이터 액세스에서 OAuth 동의 화면을
   설정합니다. 외부 사용자 앱의 게시 상태가 **테스트**이면, 대상 → 테스트
   사용자에 실제 시트 소유자의 Google 계정을 추가합니다. 테스트 사용자로
   등록된 계정으로 로그인합니다.
4. 데이터 액세스의 요청 범위는
   `https://www.googleapis.com/auth/spreadsheets.readonly` 하나만 둡니다.
   Drive·Gmail 또는 쓰기 범위는 추가하지 않습니다. 이 권한은 계정의
   스프레드시트를 읽을 수 있는 권한이므로, 앱에는 읽으려는 본인의 시트 ID만 입력합니다.
5. 클라이언트 → OAuth 클라이언트에서 유형을 **웹 애플리케이션**으로
   확인하고, 승인된 JavaScript 원본을
   **`https://kco994553-star.github.io`**로 등록합니다. 원본에는
   `/Investment-System1/` 경로를 붙이지 않습니다.
6. 앱 설정 파일의 공개 OAuth 클라이언트 ID는 다음 값입니다.

```text
437589281514-r5hasrua70busongkklplctm8j206k3s.apps.googleusercontent.com
```

이는 공개 식별자입니다. **클라이언트 보안 비밀(client secret)은 사용하지
않으며 저장소·앱·백업에 넣지 않습니다.** 클라이언트 ID 설정이 비어 있는
배포에서는 구글 연결 기능이 숨겨집니다.

## 2. 본인 비공개 시트 만들기

1. 본인 Google 계정에서 새 구글 시트를 만들고 탭 이름을 **`Quotes`**로 정합니다.
2. 공유는 비공개로 유지합니다. 웹에 게시하거나 링크가 있는 모든 사용자에게
   공개하지 않습니다.
3. A1:C1에 `code`, `price`, `tradetime` 머리글을 입력합니다. 아래 표의
   **21개 데이터 행**을 A2:C22에 입력합니다. 표에는 수식만 있으며 실제
   가격·환율은 들어 있지 않습니다.

| 행 | A: code | B: price 수식 | C: tradetime 수식 |
| --- | --- | --- | --- |
| 2 | NASDAQ:ASML | `=GOOGLEFINANCE(A2,"price")` | `=GOOGLEFINANCE(A2,"tradetime")` |
| 3 | NASDAQ:LRCX | `=GOOGLEFINANCE(A3,"price")` | `=GOOGLEFINANCE(A3,"tradetime")` |
| 4 | NASDAQ:KLAC | `=GOOGLEFINANCE(A4,"price")` | `=GOOGLEFINANCE(A4,"tradetime")` |
| 5 | NASDAQ:NVDA | `=GOOGLEFINANCE(A5,"price")` | `=GOOGLEFINANCE(A5,"tradetime")` |
| 6 | NASDAQ:AMD | `=GOOGLEFINANCE(A6,"price")` | `=GOOGLEFINANCE(A6,"tradetime")` |
| 7 | NASDAQ:AVGO | `=GOOGLEFINANCE(A7,"price")` | `=GOOGLEFINANCE(A7,"tradetime")` |
| 8 | NASDAQ:QCOM | `=GOOGLEFINANCE(A8,"price")` | `=GOOGLEFINANCE(A8,"tradetime")` |
| 9 | NASDAQ:INTC | `=GOOGLEFINANCE(A9,"price")` | `=GOOGLEFINANCE(A9,"tradetime")` |
| 10 | NASDAQ:MSFT | `=GOOGLEFINANCE(A10,"price")` | `=GOOGLEFINANCE(A10,"tradetime")` |
| 11 | NASDAQ:GOOGL | `=GOOGLEFINANCE(A11,"price")` | `=GOOGLEFINANCE(A11,"tradetime")` |
| 12 | NASDAQ:AMZN | `=GOOGLEFINANCE(A12,"price")` | `=GOOGLEFINANCE(A12,"tradetime")` |
| 13 | NYSE:RTX | `=GOOGLEFINANCE(A13,"price")` | `=GOOGLEFINANCE(A13,"tradetime")` |
| 14 | NYSE:SYK | `=GOOGLEFINANCE(A14,"price")` | `=GOOGLEFINANCE(A14,"tradetime")` |
| 15 | NYSE:ETN | `=GOOGLEFINANCE(A15,"price")` | `=GOOGLEFINANCE(A15,"tradetime")` |
| 16 | NYSE:HUBB | `=GOOGLEFINANCE(A16,"price")` | `=GOOGLEFINANCE(A16,"tradetime")` |
| 17 | NYSE:GEV | `=GOOGLEFINANCE(A17,"price")` | `=GOOGLEFINANCE(A17,"tradetime")` |
| 18 | NYSE:ROK | `=GOOGLEFINANCE(A18,"price")` | `=GOOGLEFINANCE(A18,"tradetime")` |
| 19 | TYO:8035 | `=GOOGLEFINANCE(A19,"price")` | `=GOOGLEFINANCE(A19,"tradetime")` |
| 20 | KRX:042700 | `=GOOGLEFINANCE(A20,"price")` | `=GOOGLEFINANCE(A20,"tradetime")` |
| 21 | CURRENCY:USDKRW | `=GOOGLEFINANCE(A21)` | 비워 둠 |
| 22 | CURRENCY:JPYKRW | `=GOOGLEFINANCE(A22)` | 비워 둠 |

환율 수식에는 `"price"` 속성을 넣지 않습니다. 환율의 C열은 비워 둡니다.
USDKRW는 **1 USD당 KRW**, JPYKRW는 **1 JPY당 KRW**이며 100엔 단위가 아닙니다.
주식 통화는 고정 매핑에 따라 미국 17개 USD, 도쿄일렉트론 JPY,
한미반도체 KRW입니다. 종목 코드의 거래소 접두사와 앞자리 0을 유지합니다.

2026-10-09 사용자 실측에서 미국 17개·한미반도체·환율 2개는 정상이고,
**TYO:8035는 GOOGLEFINANCE 미지원으로 `#N/A`**입니다. 도쿄일렉트론 행은
그대로 두고 앱에서 계속 수동 입력합니다. 실제 시트에서는 보통 성공 20개,
도쿄일렉트론 실패 1개가 예상됩니다. 이 관찰은 향후 Google 지원을 보장하지 않습니다.

## 3. 휴대폰 앱에서 설정하고 불러오기

1. [앱](https://kco994553-star.github.io/Investment-System1/)의 계정 화면에서
   구글 시트 선택 기능을 켭니다.
2. 스프레드시트 **ID 또는 본인 시트 URL**을 입력합니다. URL을 붙여넣으면
   앱이 ID를 추출합니다. 이 값을 GitHub 이슈·PR·공개 문서에 붙이지 않습니다.
3. 범위에 기본값 **`Quotes!A1:C22`**를 입력하고 설정을 저장합니다.
4. **구글 로그인 준비**를 눌러 로그인 도구를 불러옵니다. 이어서
   **구글 로그인 · 읽기 전용**을 직접 눌러 팝업을 열고, 시트를 소유한
   테스트 사용자 계정으로 로그인해 스프레드시트 읽기 전용 권한을 허용합니다.
5. **구글 시트에서 불러오기**를 누릅니다. 성공 수와 실패 종목명, 모르는 코드
   경고를 확인합니다. 불러오기는 이 버튼을 누를 때만 실행됩니다.
6. 도쿄일렉트론 등 실패한 행은 기존 수동 입력을 유지하거나 직접 보완합니다.
   필요하면 **구글 연결 해제**를 누릅니다. 메모리 토큰을 즉시 삭제하고
   Google 권한 철회를 요청합니다.

ID와 범위는 해당 기기에만 저장하고 **백업에서 제외**합니다. 접근 토큰은
**메모리에만** 유지하며 IndexedDB·localStorage·백업에 저장하지 않습니다.
로그인은 약 1시간 후 만료되며 다시 **구글 로그인 · 읽기 전용**을 눌러야 합니다. 새로고침으로도
메모리 토큰이 사라질 수 있습니다. 만료·취소·조회 실패는 기존 시세를 지우지 않습니다.
기기 백업을 복원하면 구글 시트 설정은 다시 입력합니다.

## 4. 로그인 없이 일괄 붙여넣기

본인 시트에서 A1:C22 또는 A2:C22를 복사해 앱의 **일괄 붙여넣기** 입력란에
넣고 적용합니다. 탭 구분 또는 쉼표 구분 텍스트를 사용합니다. 같은 코드
매핑과 값 검증을 적용하며, 알려지지 않은 코드는 경고 후 무시합니다.
이 방법은 Google 로그인이나 시트 연결을 켜지 않아도 사용할 수 있습니다.

숫자가 아닌 가격·빈칸·`#N/A`·0 이하 값은 `NOT_AVAILABLE` 실패로 보고하며
기존 저장값을 덮어쓰거나 지우지 않습니다. 성공한 값은 기기 시세 저장소에
새 기록으로 추가하고 변경 이력에는 한 번의 입력 작업으로 기록합니다.
최근 변경 이력 10건을 화면에 표시하고 기기에는 최대 1,000건을 보관합니다.
저장 한도에 도달하면 새 입력을 저장하지 않고 기존 값과 이력을 유지합니다.

## 시각과 사용 한계

- 출처는 **`GOOGLEFINANCE · 최대 20분 지연 · 정보용`**으로 표시합니다.
  정보가 지연·누락될 수 있으므로 체결가나 실시간 시세로 취급하지 않습니다.
- Sheets API는 `UNFORMATTED_VALUE`와 `SERIAL_NUMBER`로 읽습니다. 주식 C열은
  거래소 현지 시각으로 해석하며 미국은 `America/New_York`, KRX는
  `Asia/Seoul`을 사용합니다. 시간대가 없는 값을 휴대폰 시간대로 추측하지 않습니다.
- 시각 해석에 실패하거나 C열이 없으면 불러온 시각을 사용하고 **시각 미확인**을
  표시합니다. 예시 시트의 환율 C열은 비어 있으므로 불러온 시각과 **환율 시각 미확인**을 표시합니다.
  이는 실제 환율 기준 시각을 확인했다는 의미가 아닙니다.
- 일괄 붙여넣기의 시각 문자열을 해석할 수 없어도 시각 미확인을 표시합니다.
  Google 시트 로캘·서식에 따라 문자열이 달라질 수 있습니다.
- 기존 **7일 신선도 규칙**을 유지합니다. 기준 시각과 불러온 시각은 서로 다릅니다.
- GOOGLEFINANCE는 전문가용으로 사용할 수 없으며, 정보 제공 목적으로만
  사용합니다. 과거 시세는 Sheets API를 통해 가져올 수 없습니다.
  [Google 공식 GOOGLEFINANCE 안내](https://support.google.com/docs/answer/3093281)를 확인합니다.
- 테스트 모드·테스트 사용자·승인된 원본·Sheets API 설정과 브라우저 팝업
  허용 여부에 따라 로그인 또는 조회가 실패할 수 있습니다. 앱 테스트는 모두
  모의 응답을 사용하며 실제 사용자 계정의 OAuth·시트 접근 성공은 사용자가
  본인 기기에서 확인해야 합니다.
- Alpha Vantage는 검토 기록만 유지하고 OFF입니다. 한국투자증권·중계 서버는
  DEFERRED입니다. 매수·매도·주문·이체 기능은 없습니다.
