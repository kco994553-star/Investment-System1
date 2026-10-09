# Google 시트 시세 — 승인 배포·공개 CSP 확인 (2026-10-09)

사용자가 PR #73 병합을 승인했다. canonical 병합은
`13e025b0e545fb3da14c15ce065a6a8e4a368eb0`이며
[Pages run 37897789996](https://github.com/kco994553-star/Investment-System1/actions/runs/37897789996)의
build·deploy가 성공했다. 다른 PR은 병합하지 않는다. CSP 수정 및 IA 문서 PR #72는
사용자 병합 승인 대기다.

## 배포된 공개 사이트 확인

[공개 앱](https://kco994553-star.github.io/Investment-System1/)을 새 브라우저 컨텍스트에서
ko/en × 390px/1280px로 열었다. OFF 기본값·OFF 시 Google 호출 없음·설정 화면·
로그인 없는 일괄 붙여넣기·매핑 21개 저장·배치 이력 1개·기기 설정의 백업 제외를
확인했다. 붙여넣기와 설정 검증 값은 합성 데이터이며 브라우저 메모리·임시 기기
저장소에만 두고 컨텍스트를 닫았다. 실제 시세·시트 ID·토큰·보유·금액·수량은
저장소·공개 산출물·로그·검증 파일에 기록하지 않았다.

각 화면에서 사용자 준비 버튼으로 실제 `https://accounts.google.com/gsi/client`를
로드했다(HTTP 200). 실제 `initTokenClient`와 단일 readonly scope로 초기화했다.
반환 클라이언트의 토큰 요청 함수는 감시·차단했고 토큰 요청·revoke·OAuth 요청·
Sheets API·팝업·런타임 오류는 모두 0이었다. 실제 Google 로그인은 하지 않았다.

총 80개 상호작용 검사는 통과했지만 **CSP는 실패**했다. 각 화면 조건에서
`style-src-elem`의 inline 위반 1개, 콘솔 CSP 메시지 1개가 발생했다(총 각 4개).
`securitypolicyviolation.sourceFile`은 Google의 `/gsi/client`이며, 위반은 토큰
클라이언트 초기화 전에 SDK가 inline `<style>`을 생성하는 단계에서 발생했다.
상호작용 PASS를 CSP PASS로 해석하지 않는다.

공개 서버의 16개 파일을 직접 읽고 PR #73의 승인 해시·개인정보 산출물 가드와
대조했다. PASS, violations `{}`. 공개 JSON 3개는 기존 identity/TARGET·WEB
메타데이터 해시와 같으며 실제 시세·환율·시트 ID·접근 토큰이 없다. 배포 직전
실제 업로드 archive 가드도 위 Pages deploy job에서 PASS했다.

## 최소 수정 후보와 근거

[Google 공식 CSP 안내](https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid#content_security_policy)는
`style-src`에 `https://accounts.google.com/gsi/style`을 허용하도록 안내한다.
이번 CSP 변경은 이 정확한 URL 하나뿐이다. 다른 directive·host·scope는 늘리지
않고 `unsafe-inline`, `unsafe-eval`, 고정 nonce, SDK 자체 호스팅을 사용하지 않는다.

현재 SDK는 `googleidentityservice_button_styles` 요소가 없을 때 inline button
스타일을 넣는다. 공식 CSS URL 허용만 추가하거나 marker 없는 CSS 링크를 먼저
로드하면 위반 1개가 그대로 남는 것을 실제 SDK로 재현했다. 따라서 사용자가
준비 버튼을 누를 때만 공식 외부 stylesheet LINK를 이 marker ID로 만들고,
`onload` 완료 뒤 실제 SDK를 로드한다. CSS 실패 시 LINK를 제거하고 SDK 로드를
중단한다. 재시도는 다시 버튼을 눌러야 하며, CSS 대기 중 OFF로 바꾸면 늦은 SDK
요청을 차단한다. 기본 OFF·설정 저장·붙여넣기에는 CSS도 요청하지 않는다.

공식 URL만 허용하는 CSP와 표준 외부 LINK를 사용하지만 **marker ID는 SDK 내부
구현이며 공개 API 계약이 아니다**. 공식 CSS는 SDK의 inline button CSS와 동일하지
않다. 검증 범위는 이 앱의 OAuth token client 초기화이며 Google 렌더링 버튼·
One Tap을 구현하거나 스타일 동등성을 보장하지 않는다. Google SDK가 변경되면
marker 동작·CSP를 다시 확인해야 한다. 이 제약을 숨기기 위해 CSP를 넓히지 않는다.

모의 회귀는 실제 SDK의 marker 없는 inline 스타일 주입을 재현한다. 인증 12개,
공개 빌드 23개, 모의 브라우저 40개가 통과했고 CSP 이벤트는 0이다. CSS 실패·
명시적 재시도·동시 준비·대기 중 OFF도 확인했다. CI·회귀 테스트에서는 Google
CSS·SDK·Sheets API·revoke를 모두 모의 응답으로 처리한다. 실제 공개 런타임
점검은 CI에 추가하지 않는다.

최종 후보의 온라인 점검은 실제 공개 URL에서 `index.html`과
`google-sheet-quotes.js` 두 파일만 검토 중인 후보 바이트로 대체했다. 나머지
공개 파일·Google CSS·SDK는 실제 서버에서 읽었다. ko/en × 390/1280px,
92검사가 통과했다. 공식 CSS·SDK HTTP 200, script load·init 단계의 CSP
이벤트 및 콘솔 CSP 메시지 0, LINK 1개·SDK inline STYLE 0개, 실제 init 호출
1회 및 토큰 요청 감시 1개씩 확인했다. 토큰·콜백·revoke·Sheets·OAuth·팝업
시도는 모두 0이다. 이는 **후보 검증이며 공개 배포 수정 완료를 뜻하지 않는다**.
공개본의 위반 4개는 수정 PR 승인·배포 전까지 그대로다.

최종 소스·공개 해시를 고정한 뒤 전체 Python 855개+subtests345개, Node84개
및 위 모의 브라우저40개가 통과했다. 공개16파일 산출물 가드 PASS, JSON
3개의 해시는 PR #73과 동일하다. native CI는 새 PR의 Checks에서 확인한다.

## 휴대폰에서 이어서 확인할 순서

현재 공개본에서는 [기존 설정 안내](GOOGLE_SHEET_QUOTES_SETUP.md)의 비공개 Quotes
시트를 준비하고 A~C열 일괄 붙여넣기를 사용할 수 있다. CSP 수정 PR 병합·배포
이후 앱 새로고침 → 설정에서 Google 시트 사용 ON → 본인 시트 URL/ID와
`Quotes!A1:C22` 저장 → 로그인 준비 → 읽기 전용 로그인 → 구글 시트에서 불러오기
순으로 확인한다. 실제 계정의 동의·테스트 사용자·Sheets API 활성화·휴대폰
팝업·실제 시트 읽기는 이번 점검에서 확인하지 않았다. 도쿄일렉트론은 계속
수동 입력한다. 시트 ID나 접근 토큰을 GitHub 이슈·댓글·스크린샷에 올리지 않는다.
