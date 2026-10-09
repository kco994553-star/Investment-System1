# Google Sheet Quotes — scoped Decision Register

이 파일은 2026-10-09 구글 시트 시세 입력 작업의 append-only 결정 기록입니다.
기존 항목의 바이트를 수정·삭제하지 않고 후속 결정만 끝에 추가합니다. 기준
브랜치 `claude/investment-system-top500-validation-alrugm`의 PR #70 병합 후
`011b756`에는 Global `COORDINATION_DECISION_REGISTER.md`가 없습니다.
Global 기록은 별도 `integration/global-handoff-v1` 브랜치에 있으므로, 이 PR은
그 브랜치를 변경하거나 Global 기록의 일부를 새 원본처럼 만들지 않습니다.
이 파일은 Global 기록을 대체하거나 새 CDR 번호를 부여하지 않습니다.

## GSQ-001 — 사용자 결정 및 구현 승인 (2026-10-09)

아래는 사용자의 이번 결정 원문입니다.

> - 26E 보완: 시세·환율 자동 입력 경로로 **사용자 본인의 비공개 구글 시트(GOOGLEFINANCE)를 휴대폰 앱이 읽기 전용으로 직접 읽는 방식**을 채택한다.
> - Alpha Vantage는 OFF 유지(검토 기록만), 한국투자증권·중계 서버는 DEFERRED 유지.
> - 수동 입력은 그대로 유지한다. 구글 시트는 선택 기능이며 기본 OFF.
> - Decision Register에 append-only로 기록한다.

구현 기준과 승인 경계 원문:

> - 기준 브랜치: `claude/investment-system-top500-validation-alrugm` (PR #70 병합 이후 `011b756` 이상)
> - 작업 브랜치: `codex/google-sheet-quotes-20261009`, PR 1개. 병합은 사용자 승인.

항상 적용되는 금지 원문:

> - 승인된 PR 외 canonical 병합·force push·ruleset 변경·AUTONOMY_MODE 변경 금지
> - 공개 저장소·공개 JSON·Pages 산출물에 시세 값, 스프레드시트 ID, 접근 토큰, 금액·수량 기록 금지
> - 서버·중계·GitHub Actions로 시세 수집 금지 (구글 → 사용자 휴대폰 직접만)
> - 매수·매도·주문·이체 기능 금지, 투자 방법론·TARGET 변경 금지
> - CI·테스트에서 실제 구글 호출 금지 (모의 응답만)

마지막 사용자 실행 지시: **“진행해”**. 이는 아래 범위의 구현·테스트·PR 작성
승인입니다. canonical 병합 및 공개 배포 승인을 뜻하지 않습니다.

| 항목 | 이번 결정 |
| --- | --- |
| 인증 | Google Identity Services token client; 사용자가 버튼을 누를 때만 팝업; scope는 `https://www.googleapis.com/auth/spreadsheets.readonly` 하나 |
| 공개 설정 | 사용자 제공 웹 OAuth 클라이언트 ID 사용; client secret 사용·저장 금지; ID 설정이 비면 연결 기능 숨김 |
| 토큰 | 메모리만; 저장소·백업 제외; 만료 시 재연결; 연결 해제는 메모리 즉시 삭제 후 revoke 요청 |
| 시트 설정 | 본인 비공개 ID/URL과 범위 `Quotes!A1:C22`; 기기만 저장, 백업 제외 |
| 실행 | “구글 시트에서 불러오기” 버튼으로만 Sheets API GET; 백그라운드·자동 주기 없음 |
| 고정 매핑 | 사용자 지정 미국 17개 USD, TYO:8035 JPY, KRX:042700 KRW, USDKRW 및 JPYKRW; 추측 매핑 금지 |
| 오류 | 숫자 아님·`#N/A`·빈칸·0 이하 → 해당 행 `NOT_AVAILABLE`; 기존 저장값 보존; 모르는 코드 무시·경고 |
| 시간 | SERIAL_NUMBER를 거래소 현지 시각으로 해석; 해석 실패 시 불러온 시각과 시각 미확인; FX C열 없음은 환율 시각 미확인 |
| 저장 | 기존 기기 시세 저장소의 새 기록; 출처 `GOOGLEFINANCE · 최대 20분 지연 · 정보용`; 기존 7일 신선도 유지; 결과 요약 및 변경 이력 1건 |
| 붙여넣기 | A~C열 탭/쉼표 텍스트, 로그인 없이 동일 매핑·검증·저장 |
| CSP | GIS client script, Sheets·oauth2 connect, accounts frame만 최소 추가; 그 외 확장 없음 |
| 개인정보 가드 | Google 시트 URL/문맥 ID 및 ya29. 토큰 패턴 추가; 공개 클라이언트 ID·소스 매핑·해시 허용 |
| 검증 | 실제 Google 호출 없는 단위/브라우저 모의 테스트; 390px·1280px, ko/en; 공개 산출물·백업 비밀값 없음; 전체 CI |

사용자 실측 기록(2026-10-09): 미국 17개·KRX:042700·환율 2개 정상,
TYO:8035 및 다른 표기 5종 `#N/A`. 도쿄일렉트론은 수동 입력을 유지하며
실패 응답으로 기존 수동값을 덮어쓰지 않습니다. 실제 시세·ID·토큰은 기록하지 않습니다.

구현 선택으로 외부 provider·서버·중계·투자 방법론·TARGET 또는 운영 모드를
추가로 승인하지 않습니다. `AUTONOMY_MODE`는 기존 `READ_ONLY`를 유지합니다.
새 PR의 병합은 사용자 승인을 기다립니다.


## GSQ-002 — 구현·검증 영수증 (2026-10-09)

GSQ-001 원문은 보존하고 이 영수증만 끝에 추가합니다. 지정 기준 `011b756`에서
작업 브랜치 `codex/google-sheet-quotes-20261009`에 구현했습니다. 기본 OFF,
기기 직접 읽기, 로그인 없는 붙여넣기, 실패값 보존, 메모리 토큰, 기기 설정
백업 제외, 고정 코드·시간대 검증 및 1회 불러오기당 기기 이력 1건을 적용했습니다.

로컬 전체 Python 855개 + subtests345개, Node80개, 브라우저214검사와 독립
브라우저36검사가 통과했습니다. 공개16파일의 디렉터리·raw-tar 가드가 통과했고
세 공개JSON 해시는 기준과 같습니다. 독립 검토의 중요한 보안 가드 발견사항은
동적 모의 재현 테스트로 수정했습니다. [검증과 남은 한계](GOOGLE_SHEET_QUOTES_VERIFICATION.md)
및 [사용자 설정 순서](GOOGLE_SHEET_QUOTES_SETUP.md)를 함께 기록합니다.

PR1개 작성만 승인된 상태이며 canonical 병합·공개 배포는 진행하지 않습니다.
실제 Google 계정/OAuth/CSP·시트 성공은 사용자 기기에서 확인할 항목이며,
CI는 전부 모의 응답만 사용합니다. native CI 결과는 PR Checks에 기록합니다.


## GSQ-003 — 계정 번호 포함 URL 호환성 (2026-10-09)

표준 `/spreadsheets/d/…` 외에 Google의 `/spreadsheets/u/0/d/…` 형태도
ID로 추출하도록 보완했습니다. HTTPS·정확한 Google 호스트·자격 증명/포트
제한·고정 API 경로는 동일합니다. 계정 번호0/2 회귀 재현은 RED→GREEN이며
인증8개, 네 화면 조합의 모의 브라우저32검사 및 전체Python855+subtests345가
다시 통과했습니다. 독립 검토의 추가 잘못된 URL7개도 모두 거부했습니다.
개인정보·공개16파일 가드가 통과했으며 동일 PR #73에 후속 커밋으로 반영합니다.
canonical 병합·배포는 여전히 사용자 승인 대기입니다.


## GSQ-004 — PR #73 병합 승인 및 공개 CSP 최소 수정 범위 (2026-10-09)

기존 GSQ-001~003 원문은 보존하고 최신 사용자 승인만 끝에 추가한다.

> #73 병합을 승인합니다. PR #73을 canonical에 병합하고 GitHub Pages 배포가 성공하는지 확인.
> 다른 PR 병합 금지. force push·ruleset 변경·AUTONOMY_MODE 변경 금지.
> 공개 사이트 실제 확인(실제 구글 로그인은 하지 않음). CSP 위반이 있으면 구글 공식 권장 범위 안에서만 최소 수정하여 별도 PR로 올리고 병합은 대기.
> Cockpit IA v1 공식화 + 차트 목록 보강(문서 전용 PR)을 이어서 진행. 병합은 사용자 승인 대기.

승인된 PR #73만 canonical `13e025b0e545fb3da14c15ce065a6a8e4a368eb0`에
병합했다. Pages run `37897789996`의 build·deploy가 성공했다. 공개 16파일
승인 산출물·개인정보 가드 PASS, 실제 시세·시트 ID·접근 토큰 공개 없음.

ko/en × 390/1280px 실제 공개 런타임 80검사에서 OFF·설정·붙여넣기·실제 GIS
로드·실제 token-client 초기화는 통과했으나 SDK inline style CSP 위반은 각
화면 1개였다. 실제 로그인·토큰 요청·Sheets 호출은 하지 않았다. 수정은 별도
브랜치 `codex/google-sheet-csp-20261009`에서 exact Google 공식 CSS URL의
`style-src` 허용과 준비 버튼에서 외부 CSS 선로드만 다룬다. SDK 내부 marker
의존성과 token-client 전용 검증 한계는 [공개 점검 기록](GOOGLE_SHEET_QUOTES_PUBLIC_CHECK_20261009.md)에
명시한다. CSP 수정 PR과 기존 IA 문서 PR #72는 사용자 병합 승인을 기다린다.
투자 방법론·TARGET·공급처 상태·READ_ONLY·scope·메모리 토큰·기기 직접 읽기·
수동 입력 유지·백업 제외 경계는 변경하지 않는다.


## GSQ-005 — 26E 가격 경로 결정 및 SEC M1 구현 승인 (2026-10-09)

GSQ-001~004의 바이트는 보존하고 최신 사용자 결정만 끝에 추가한다. 이 항목은
26E의 가격 권리 후속 결정 기록이며 Global CDR을 대체하거나 새 번호를 부여하지 않는다.

사용자 결정 원문(범위 관련 발췌):

> #78 병합을 승인합니다(문서 전용). 병합 후 CI·Pages 정상 확인.
>
> - 가격 옵션: 지금은 유료 재배포 계약 보류. 공개 종목군은 기존 Frozen 유지.
>   D4 차트는 옵션 1(사용자 본인 키로 기기 직접 조회, 저장 없이 표시) 방향으로 후속 검토.
>   유료 계약은 M2 진입 시 재판단.
> - 다음 작업: 제안한 첫 구현 PR "SEC 일일 입력의 PIT 시각·정정 lineage 및 보존 receipt 보완"(M1)을 진행.
>   작은 issuer 범위(TARGET 미국 17종목 이내), 기존 provider 재사용, 가격 수집·QGV 재점수·예약 워크플로·
>   Pages 자동 공개는 포함하지 말 것. 병합은 승인 대기.
> - 별도 확인(문서 1~2쪽, 같은 PR 또는 별도 docs PR): Tiingo 개발자 프로그램의 "사용자 본인 키·기기 직접 조회" 조건으로
>   미국 17종목 일봉 차트를 저장 없이 표시하는 것이 허용되는지, CORS 가능 여부, 무료 한도.
> 다른 PR 병합·force push·ruleset·AUTONOMY_MODE 변경 금지. Secret 값 출력 금지.

| 항목 | 현재 결정과 승인 경계 |
| --- | --- |
| 유료 재배포 | DEFERRED. M2 진입 시 사용자가 재판단한다. #78의 선택지 비교·당시 추천은 역사 기록으로 보존한다. |
| 공개 종목군 | 기존 `2024-12-31` FROZEN_SNAPSHOT 유지. 현재 가격·새 시총·종목군 재선정 없음. |
| D4 차트 | 옵션 1을 후속 검토한다. 각 사용자 본인 키·기기 직접 조회·저장 없는 표시 방향이며 공급자 채택·구현 승인으로 확대하지 않는다. |
| 기존 시세 기능 | 구글 시트 기본 OFF·수동 입력 유지. 기존 구글 시트 기기 저장 규칙을 D4의 무저장 검토 결정으로 변경하지 않는다. Alpha Vantage OFF, 한국투자증권·중계 DEFERRED 유지. |
| SEC M1 | 기존 SEC parser·raw store를 재사용하는 입력 PIT 시각·정정 lineage·보존 receipt만 구현. 명시적으로 선택한 미국 TARGET 17개 안의 소수 issuer로 제한한다. |
| M1 제외 | 가격 수집·QGV 재점수·예약 workflow·Pages 자동 공개·Holdout 선택/사용·투자 방법론/가중치/TARGET 변경 없음. |
| Tiingo | 공식 문서 및 소량 메타데이터로 개인 키·휘발성 표시 권리, CORS, 무료 한도만 조사한다. 계정/키 발급·유료 가입·실제 가격 수집·서버 우회·CSP 확장 승인 아님. |
| 운영·병합 | `AUTONOMY_MODE=READ_ONLY` 유지. 승인된 #78만 병합하고 M1 PR은 사용자 병합 승인 대기. |

승인된 문서 PR [#78](https://github.com/kco994553-star/Investment-System1/pull/78)은
canonical `c31b9556ad584d2132268f77bb98445416c7bca6`에 병합했다.
[Pages run 37917223708](https://github.com/kco994553-star/Investment-System1/actions/runs/37917223708)의
build·deploy가 모두 성공했다. 공개 16파일은 이전 승인 산출물과 동일하고
공개 개인정보·승인 파일 가드도 통과했다.

M1 구현의 실제 경계는 [SEC 입력 계약](../daily_data_pipeline/SEC_M1_INPUT_OWNER.md),
Tiingo 판정은 [기기 직접 조회 조사](../daily_data_pipeline/TIINGO_DEVICE_DIRECT_REVIEW_M1.md)에
기록한다. 이 기록은 입력 보존을 LIVE 데이터·전체 PIT 검증·공개 배포 허가로
승격하지 않는다.
