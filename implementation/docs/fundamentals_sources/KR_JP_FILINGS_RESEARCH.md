# 한국·일본 보유 종목 재무 공시 데이터 출처 조사

조회일: **2026-10-09 (UTC)**. 대상은 한미반도체 **KRX 042700 → DART OpenAPI**, Tokyo Electron **TSE 8035 → 금융청 EDINET API v2**다. 공식 웹페이지·FAQ·PDF와 저장소 코드를 읽은 문서 조사이며, 가입·키 발급·인증 API 호출·구현·데이터 공개는 수행하지 않았다.

## 판정과 추천

판정 기준은 “정당한 이용자가 API로 자동 취득하여 숫자 중심의 가공 JSON을 공개할 수 있는가”다. API 제공, 공개 재이용 조건, 현재 저장소의 지원 여부를 구분한다.

| 확인 항목 | DART / 한미반도체 | EDINET / Tokyo Electron |
| --- | --- | --- |
| 종합 판정 | **조건부 가능** | **조건부 가능** |
| 무료 여부 | **원칙적으로 무료**, 약관 제11조에 명시 | 비용 없는 공개 API로 판단. 공식 무료 열람 안내는 있으나 **현행 v2의 명시적 무료 보장 조항은 미확인** |
| 키 발급 조건 | 개인/기업 가입·약관 동의·이메일 등. 개인 즉시, 기업 승인 및 사업자등록증·IP 등록 | 이메일 확인·비밀번호·전화 MFA·이름/전화번호·규약 동의 후 키 발급 |
| 호출 한도 | 개인 전체 API 합산 **20,000건/일**. 기업 예외와 과도 접속 제한은 아래 참조 | **공개된 확정 수치 한도 미확인**. FAQ 권장 주기 1분에 1회 이하, 대량 요청 제한·429 대응 필요 |
| 재무제표 | JSON/XML 계정 데이터, 연결/별도 구분, 2015년 이후 | 공시 목록 JSON + 문서 ZIP/PDF; XBRL 또는 XBRL→CSV에서 수치 추출 |
| XBRL·주석 | XBRL ZIP·공시 원문 XML. 주석 웹 조회/TSV도 있으나 주석 전용 OpenAPI는 미확인 | XBRL/Inline XBRL·text block·첨부 문서. CSV는 긴 주석 전문을 보장하지 않음 |
| GitHub Actions 자동 취득 | 키 소유자의 비공개 실행 및 한도 준수 조건. **제3자 키 이용 금지**·기업 IP 조건에 유의 | 서버 측 API 취득은 약관이 안내하는 경로. 저빈도 요청·키 비공개·오류 확인 조건 |
| 공개 가공 JSON | 공식 FAQ가 공개·활용을 허용. 공익·타인 권리 보호, 재가공 책임 조건 | PDL1.0 및 EDINET 출처·가공자 표시, 제3자 권리와 별도 taxonomy 조건 |
| 기존 SEC 형태 연결 | 공통 입력 계약 재사용 가능, DART 전용 변환 필요 | 공통 입력 계약 재사용 가능, EDINET 전용 문서/회계 변환 필요 |
| 현재 실제 지원 | 미구현; 이번 조사에서 지원 상태를 변경하지 않음 | 미구현; 이번 조사에서 지원 상태를 변경하지 않음 |

**추천 1개: 후속 작업의 첫 대상은 한미반도체의 DART 숫자 재무제표 JSON으로 한정한다.** 전체 재무제표 API의 계정·기간·연결 구분을 이용하면 EDINET의 ZIP/Inline XBRL 파싱보다 초기 변환 부담이 작고, 공식 FAQ에 공개·재가공 근거도 있다. 출처와 접수번호를 붙인 주요 수치부터 검증하고 주석은 원문 링크로 연결하는 범위가 적절하다. 이는 구현 제안이며, 키 신청이나 후속 구현의 실행 승인이 아니다.

## 1. DART OpenAPI

### 회사 식별, 무료 및 키

한미반도체의 DART 고유번호는 **`00161383`**, 종목코드는 **`042700`**, 결산월은 12월이다. [DART 기업개황](https://dart.fss.or.kr/dsae001/selectPopup.ax?selectKey=00161383)과 아래 보고서 원문에서 확인했다. [회사별 정기공시 검색](https://dart.fss.or.kr/navi/searchNavi.do?naviCode=A002&naviCrpCik=00161383&naviCrpNm=%ED%95%9C%EB%AF%B8%EB%B0%98%EB%8F%84%EC%B2%B4)은 탐색 경로다. 고유번호는 주식 종목코드와 다르며, 후속 운영 시 `corpCode.xml` 공식 목록으로 대조해야 한다.

조회한 [2026년 반기보고서 원문](https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260814003665)은 접수번호 `20260814003665`, 제출일 2026-08-14, 사업기간 2026-01-01~2026-06-30이다. 연결/별도 주석 목차와 3개월·누적 손익이 존재한다. 이는 키 없는 웹 원문 확인이며 API 응답 검증은 아니다.

[이용약관](https://opendart.fss.or.kr/intro/terms.do) 제11조①의 원문 발췌:

> “금융감독원이 제공하는 서비스는 원칙적으로 무료입니다.”

같은 조항은 일부 서비스 유료화 시 사전 통지를 규정하므로 영구 무료 보장으로 해석하지 않는다. 약관 페이지 부칙은 2020-01-21 시행으로 표시된다.

약관 제7조·제8조 및 [키 발급 FAQ, nttId=31](https://opendart.fss.or.kr/cop/bbs/selectArticleDetail.do?bbsId=B0000000000000000002&nttId=31)에 따르면 개인/기업 신청 구분, 이메일, 비밀번호, 사용환경·용도·확인 URL 등이 필요하다. 기업 신청에는 회사명·사업자번호·담당자 연락처·홈페이지·요청 시스템 IP·사업자등록증 등이 포함된다. 개인회원은 계정 신청 완료 후 즉시, 기업회원은 담당자 승인 후 발급하며 1~2영업일이 걸릴 수 있다. API에는 40자리 `crtfc_key`가 필요하다. 약관 제19조⑤는 ID·인증키를 2개 이상 발급받을 수 없다고 규정한다.

### 호출 한도와 조회일의 가용성

[이용한도 FAQ, nttId=29](https://opendart.fss.or.kr/cop/bbs/selectArticleDetail.do?bbsId=B0000000000000000002&nttId=29)의 현재 본문 기준:

- 개인: 서비스별이 아닌 **전체 API 합산 일 20,000건**.
- 기업: 사업자등록증·IP 등록 조건. 공시검색·기업개황 2종은 일일 한도 없음; 나머지 서비스는 합산 일 20,000건.
- 일일 한도 이내라도 **분당 1,000회 이상**의 과도한 접속은 이용 제한 가능. 이것을 안전한 허용 속도로 간주하면 안 된다.
- 개발가이드의 상태 코드 `020`은 요청 제한 초과, `012`는 접근 불가 IP, `800`은 점검을 뜻한다. 약관 제10조는 한도 변경·과도 접속 제한을 허용한다.

FAQ 일반 한도와 별개로 개발가이드 `020` 설명은 인증키별 한도가 다르게 설정될 수 있다고 안내한다. 실제 운영에서는 발급받은 키의 한도를 다시 확인해야 한다.

[홈페이지 점검 공지](https://opendart.fss.or.kr/)는 **2026-10-08 20:00~2026-10-11 18:00** 일부 서비스 중지를 안내한다(사이트 표기 시각, 시간대 미명시). 키 신청/관리, 단일회사 재무제표 웹 조회·XBRL/일괄 다운로드, API 공시 원문·고유번호·XBRL 등이 대상이다. 나머지 서비스는 이용 가능하다고 안내한다. 따라서 오늘의 일부 기능 중단을 API 미지원으로 판정하지 않으며, 재개 시각은 공지상의 예정이다. 이번 조사는 키를 사용하지 않았으므로 다른 인증 API도 실제 성공을 검증한 것이 아니다.

### 제공 항목과 제약

| 목적 | 공식 경로·포맷 | 연결 시 의미 |
| --- | --- | --- |
| 공시 인덱스 | `GET /api/list.json` 또는 `.xml`; [가이드](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001) | `corp_code`, 보고서명, `rcept_no`, `rcept_dt` 등. `last_reprt_at`으로 최종/전체 범위를 선택; 과거 시점 조사에는 정정 보고서도 보존 |
| 고유번호 목록 | `GET /api/corpCode.xml`, ZIP 내부 XML; [가이드](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019018) | 8자리 고유번호와 종목코드 매핑. 키 필요 |
| 주요 계정 | `fnlttSinglAcnt.json/.xml`, `fnlttMultiAcnt.json/.xml`; [재무정보 API 목록](https://opendart.fss.or.kr/guide/main.do?apiGrpCd=DS003) | 일부 주요 계정만 제공하며 전체 계정/주석과 구분 |
| 전체 재무제표 | `GET /api/fnlttSinglAcntAll.json` 또는 `.xml`; [가이드](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019020) | `bsns_year`, `reprt_code`, `fs_div` 필요. BS/IS/CIS/CF/SCE, 계정 ID/명·상세, 당기/전기 금액·누적금액·통화·접수번호 |
| 재무제표 XBRL | `GET /api/fnlttXbrl.xml`, **실제 응답은 ZIP 바이너리**; [가이드](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019019) | `rcept_no`·`reprt_code`로 제출본 지정. 확장자 `.xml`만 보고 XML 파서로 읽으면 안 됨 |
| 공시 원문 | `GET /api/document.xml`, ZIP 내부 XML; [가이드](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019003) | 재무제표·주석의 보고서 원문을 확인하는 보완 경로; 숫자 계정 API와 별도 |
| 주석 | [주요 주석 웹 조회](https://opendart.fss.or.kr/disclosureinfo/fnltt/singlnote/main.do), [주석 일괄다운로드](https://opendart.fss.or.kr/disclosureinfo/fnltt/xbrlnote/main.do) | IFRS XBRL 작성기로 제출한 주석을 TSV로 제공. 오늘 DS003 목록에 주석 전용 JSON/XML API는 확인되지 않음 |

전체 재무제표 API는 **2015년 이후** 정보를 제공한다. 보고서 코드는 1분기 `11013`, 반기 `11012`, 3분기 `11014`, 사업보고서 `11011`; `fs_div=CFS`는 연결, `OFS`는 별도다. 표준계정 ID가 없는 항목도 있어 계정명만으로 무조건 통합하면 안 된다. 분기 단독 금액과 누적 금액을 구분하고, 통화·원 단위/스케일을 확인해야 한다.

**주석 지원은 제출본마다 확인해야 한다.** 숫자 전체 재무제표 API가 모든 주석을 구조화해 주는 것은 아니다. XBRL ZIP의 주석/text block 포함 여부, 원문 XML, 웹 TSV 경로를 구분해야 하며, 한미반도체의 주석 전체가 특정 API에서 항상 제공된다는 사실은 이번 조사에서 검증하지 않았다. 웹 다운로드 기능의 존재를 자동 수집용 API 계약으로 간주하지 않는다.

주요 주석 웹 조회는 공식 메뉴의 존재를 확인했으나 직접 화면은 조회일에 “서비스 일시 중지 안내”를 반환했다. 주석 일괄다운로드 페이지의 TSV 제공 안내는 직접 열람했다.

### 자동 수집과 공개 JSON 재배포 조건

[이용약관](https://opendart.fss.or.kr/intro/terms.do) 제19조② 원문:

> “회원은 ID 및 비밀번호, 인증키를 제3자에게 이용하게 해서는 안 됩니다.”

제16조는 API 서비스·프로그램의 저작권을 금융감독원에 두고, 미규정 저작권 문제는 저작권법·공공데이터법을 따르게 한다. **키 이용 제한과 취득한 데이터의 재이용은 별개의 문제**다.

같은 약관 제16조④의 원문:

> “약관에 명시되지 않은 저작권과 관련된 사항은 저작권법 및 공공데이터법에 따릅니다.”

[상업적 이용 FAQ, nttId=26](https://opendart.fss.or.kr/cop/bbs/selectArticleDetail.do?bbsId=B0000000000000000002&nttId=26)의 원문:

> “공익이나 타인의 권리를 침해하지 않는 선에서 데이터의 공개 및 활용은 제한되지 않습니다.”

FAQ는 OpenDART 정보를 공공데이터법상 공공데이터로 설명하며, 서비스에 대한 별도 심사·승인을 하지 않고 재배포·재가공의 책임은 이용자가 부담한다고 안내한다. 이는 **권리 조건을 지킨 가공 JSON 공개가 가능하다는 근거**이며, 모든 주석·사진·제3자 표현을 무제한 복제할 수 있다는 보장은 아니다. FAQ 게시일은 2020-01-18이지만 본문은 조회일에 다시 읽었다. FAQ 상세는 일반 GET에서 오류가 있어 공식 목록의 상세보기 방식인 읽기 목적 POST(`bbsId`, `nttId`)로 확인했다. 재현하려면 [공식 FAQ 목록](https://opendart.fss.or.kr/cop/bbs/selectArticleList.do?bbsId=B0000000000000000002)에서 해당 제목을 클릭한다.

후속 Actions 운영은 다음 조건을 전제로 **조건부 가능**으로 판단한다. GitHub Actions라는 실행 플랫폼을 명시적으로 허용하는 조항은 확인되지 않았다.

1. 정당한 키 소유자가 관리하는 서버 측 실행에서만 키를 사용하고, 공개 JSON·로그·요청 URL·캐시/아티팩트에 키를 포함하지 않는다. Secrets 사용은 운영 방안이며 제19조 준수 자체를 보증하지 않는다. 호스팅 실행의 위탁 사용이 제3자 이용에 해당하는지는 별도 해석 여지가 남는다.
2. 기업 키의 등록 IP 조건은 GitHub 호스팅 러너의 IP와 충돌할 수 있다. 실제 허용 IP 정책은 이번 조사에서 인증 검증하지 않았으므로 기업 키의 호스팅 러너 호환성을 확정하지 않는다.
3. 일일 합산 한도·과도 접속 제한을 지키고, 공시 인덱스 확인 후 변경된 제출본만 취득하며 오류를 빈 재무제표나 0으로 공개하지 않는다.
4. 공개 JSON에는 수치·기간·통화·연결/별도·접수번호·원문 URL·조회일·가공 주체를 붙인다. 출처·가공자 표시는 추적 가능성을 위한 권고이며, FAQ에 명시된 별도 표시 의무라고 단정하지 않는다. 주석 원문 전문 복제는 권리 확인을 별도로 거친다.

## 2. EDINET API v2

### 회사 식별, 비용 및 키

[공식 EDINET 코드 목록](https://disclosure2dl.edinet-fsa.go.jp/searchdocument/codelist/Edinetcode.zip)의 **2026-10-09 현재** CSV에서 東京エレクトロン株式会社는 **`edinetCode=E02652`**, 증권코드 **`80350`**(TSE 8035와 구분), 결산일 **3월 31일**, 연결재무제표 제출 대상으로 확인된다. [실제 제63기 유가증권보고서](https://disclosure2dl.edinet-fsa.go.jp/searchdocument/pdf/S100YEOO.pdf)는 2026-06-22 제출, 사업기간 2025-04-01~2026-03-31이며 [회사 IR](https://www.tel.co.jp/ir/library/fs/)과 대조했다.

비용은 **현재 비용 없는 공개 서비스로 판단하되, 현행 v2의 무료 보장 조항은 미확인**으로 남긴다. 금융청 [2019년 사업 설명자료](https://www.fsa.go.jp/common/budget/kourituka/03_h31/process/03_r01_08.pdf)는 무료 열람과 API 취득을 안내한다. 현재 공식 [API v2 사양서](https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/download/ESE140206.pdf)·이용규약에는 결제·카드 등록·요금표가 없지만, 이것만으로 영구 무료를 확정할 수는 없다. 구 API 규약 `ESE140191.pdf`는 조회일 HTTP 404였으므로 검색 인덱스의 무료 문구를 현행 약관으로 인용하지 않는다. 민간 **EDINET DB**의 가격·100회/일 한도를 금융청 API 조건과 혼동하지 않는다.

사용 기준 문서는 **2026년 6월판, 개정 이력 2.9의 API v2 사양서**다. 아래 PDF 쪽수는 표지부터 센 물리 쪽수가 아닌 문서에 인쇄된 쪽수다. p13~22의 계정/키 발급 절차는 이메일·CAPTCHA·이메일 코드 확인, 비밀번호, 전화번호를 이용한 SMS 또는 자동음성 MFA, 이름·연락처 및 규약 동의를 요구한다. 회사/소속은 선택 항목이다. 등록 URL은 [공식 키 등록 진입점](https://api.edinet-fsa.go.jp/api/auth/index.aspx?mode=1)이다. p13은 최초 키의 지속 이용을 안내하며, 재발급하면 이전 키는 무효가 된다. 정기 만료 주기는 확인되지 않았지만 **2년 이상 이용 실적이 없는 키는 자동 삭제되며, 이용 재개 시 계정을 다시 만들어야 한다**(p29). 계정 등록과 키 발급을 실제 수행하지 않았다.

### 호출 한도와 데이터

[공식 API FAQ](https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/WZEK0090_001.html)의 API Q6은 목록 조회를 **1분에 1회 또는 더 낮은 빈도**로 권장한다. 확정된 일/분/초당 최대 요청 수는 현행 약관·FAQ·사양서에서 찾지 못했다. 권장 주기를 허용량 보장이나 무제한으로 해석하지 않는다. API 사양서 p83은 `429 Too Many Requests` 시 충분히 기다린 후 재시도하고 취득 간격을 조정하도록 설명한다. 이 규정은 2026년 5월 개정 이력 2.8에 추가됐다.

| 목적 | 공식 v2 경로·포맷 | 제공 범위와 해석 |
| --- | --- | --- |
| 제출 목록 | `GET https://api.edinet-fsa.go.jp/api/v2/documents.json?date=YYYY-MM-DD&type=2` + `Subscription-Key` | 날짜별 메타데이터/목록 JSON. `docID`, `edinetCode`, `secCode`, `docTypeCode`, `submitDateTime`, `periodStart/End`, `parentDocID`, XBRL/CSV 플래그 등 |
| 문서 취득 | `GET https://api.edinet-fsa.go.jp/api/v2/documents/{docID}?type=…` + `Subscription-Key` | `type=1`: XBRL 포함 제출本文·감사보고서 ZIP, `2`: PDF, `3`: 첨부 ZIP, `4`: 영문 ZIP, `5`: XBRL→CSV ZIP. 문서별 제공 플래그 확인 필요 |
| 재무제표 | 제출 문서의 XBRL/Inline XBRL 또는 `type=5` CSV | SEC companyfacts 같은 회사별 정규화 재무 수치 JSON API는 없음. 회계 기준·연결/별도·context·단위 선택이 필요 |
| 주석 | XBRL text block 및 제출 HTML/문서 | 태깅된 주석과 서술을 포함하나 모든 항목의 숫자 태깅은 보장되지 않음. 긴 주석은 원문 확인 |
| 조회 기간 | API 사양서 p5·p40 | 일반 기업 유가증권·반기·분기 보고서는 법정/연장 기간 합계 **10년**. 목록 날짜도 최근 재무국 영업일 기준 10년 미경과 범위. 문서 유형별 차이가 있어 무기한 이력 아카이브는 아님 |

API는 제출일 목록에서 `E02652`를 선택한 뒤 해당 문서를 내려받는 방식이다. 당일 목록은 JST 08:30 이후 원칙적으로 분 단위로 갱신되고 과거 목록도 교체될 수 있으므로, 동일 날짜의 목록을 영구 불변으로 가정하지 않는다. 정정·취하·불개시·열람기간 만료 상태를 구분해야 한다.

법정기간과 연장기간을 합산한 **10년 열람 기간**은 반기보고서는 2024-04-01 이후, 분기보고서는 2015-04-01 이후 제출 문서에 적용된다. 연장기간 자체는 유가증권/반기보고서 5년, 분기보고서 7년이다. 문서 유형별 전환 조건을 무시해 모든 과거 문서를 동일하게 10년 조회할 수 있다고 단정하지 않는다.

[XBRL→CSV 공식 가이드](https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/download/ESE140133.pdf) p17~19에 따르면 CSV는 UTF-16LE·탭 구분이고, **값이 30,000자를 넘으면 앞 30,000자까지만 출력**한다(p18). 따라서 `type=5`만으로 주석 전문 보존을 주장할 수 없다. 문서 취득은 HTTP 200만으로 성공 판정하지 말고 `Content-Type`·오류 본문·ZIP 유효성을 확인해야 한다(API 사양서 p78~84).

### 자동 수집과 공개 JSON 재배포 약관

[EDINET 현행 이용규약](https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/WZEK0030.html)은 **2025-04-25 개정/효력 발생**으로 표시된다. 원문에서 다음 핵심 구절을 확인했다.

| 조항 | 원문 발췌 | 의미 |
| --- | --- | --- |
| II 2.2 | “本ウェブサイトのコンテンツを機械的に取得するには、API機能を利用してください” | 기계적 취득은 API 이용 안내. API로 얻을 수 있는 콘텐츠를 웹 스크레이핑하는 방식은 금지 |
| I 1.1ア | “本コンテンツを利用する際は出典を記載してください。” | 콘텐츠 이용 시 출처 표시 |
| I 1.1イ | “編集・加工等を行ったこと及びその主体を記載してください。” | 가공 여부와 가공 주체 표시; 금융청이 만든 미가공 정보인 것처럼 공개하면 안 됨 |
| III 3.2ア② | “短時間における大量のアクセス” | 단시간 대량 접속 등 API 운영을 방해하는 행위 금지. 무통보 정지 가능 |

규약 I는 [**PDL1.0**](https://www.digital.go.jp/resources/open_data/public_data_license_v1.0)에 따른 이용을 허용한다. PDL1.0 §1 원문 발췌는 “複製、公衆送信、翻訳・変形等の翻案等、自由に利用できます”이며 상업적 이용도 허용한다. 숫자 데이터·단순 표/그래프는 저작권 보호 대상이 아니라고 설명한다. §1.2는 제출기업 등 **제3자의 권리를 일괄 허락하지 않으며**, 권리 대상 부분은 이용자가 확인/처리해야 한다. 공개됐다는 이유만으로 보고서 표현·주석 전문·사진 등의 권리 처리가 끝났다고 보지 않는다.

**EDINET taxonomy는 PDL 대상에서 제외**된다(EDINET I 1.4). [별도 지식재산 조건](https://www.fsa.go.jp/search/EDINET_Taxonomy_Legal_Statement.html)은 무단 개변·수정·번역을 금지하며, taxonomy 자체의 재배포는 Legal Statement 동봉과 지정 저작권 표시를 조건으로 허용한다. 이용에는 해당 Statement의 조건 수락 및 XBRL International(XII)의 지식재산 정책 준수도 요구된다. 공시 수치를 자체 JSON 필드로 매핑하는 일과 taxonomy 파일을 수정·배포하는 일을 구분해야 한다.

따라서 GitHub Actions에서 API로 취득한 **숫자 중심 가공 JSON 공개는 조건부 가능**이다. 실행 플랫폼에 대한 명시 허가 조항은 없으나 약관이 안내하는 프로그램/API 취득 경로와 부합한다는 판단이다. API의 브라우저 교차 도메인 호출 제한(CORS) 때문에 서버 측 실행이 적절하다. 현행 EDINET 규약에서 DART와 동일한 키 제3자 이용 금지 문구는 확인하지 못했다. 키를 비공개 Secrets로 관리하는 것은 운영 권고이며 확인되지 않은 약관 문구로 주장하지 않는다.

공개 결과에는 **EDINET 출처/문서 URL, PDL1.0 URL, 가공 사실·주체**를 표시하고, `docID`, 사업기간, 제출시각, 통화·단위·연결 구분, 조회일, 가공 방법을 함께 남긴다. 제3자 권리 대상 콘텐츠와 taxonomy 원본을 일반 수치 JSON에 일괄 포함하지 않는다. API 조회는 증분·저빈도로 운영하고 429/서비스 중지에 대응해야 한다.

## 3. 기존 SEC 연결 구조와의 호환성

검토 기준: 저장소 기본 브랜치 `claude/investment-system-top500-validation-alrugm`, 커밋 **`771a3bf67a330e72349591b4879891e03340d7c1`**. 이번 문서는 해당 기준에서 독립한 `docs/kr-jp-filings-research` 브랜치의 문서 1개 변경이다.

| 현재 파일/함수 | 실제 역할 | KR/JP 재사용 경계 |
| --- | --- | --- |
| [sec_companyfacts.py](../../src/investment_system/providers/sec_companyfacts.py): `try_fetch_companyfacts()`, `facts_to_raw()` | 공개 SEC JSON 취득, concept/단위/기간 선택, `RawFundamentals` 변환 | fetch와 변환을 분리하는 구조는 참고 가능. JSON 모양·CIK·USD/EUR·SEC concept 매핑은 직접 재사용 불가 |
| [sec_submissions.py](../../src/investment_system/providers/sec_submissions.py): `parse_filings()`, `latest_annual()` | SEC form/filingDate/accession 인덱스 | DART 접수번호/보고서 코드, EDINET docID/docTypeCode·정정 관계로 별도 변환 필요 |
| [sec_vintage.py](../../src/investment_system/providers/sec_vintage.py): `resolve_vintages()`, `select_latest()` | `filed <= as_of`, 기간별 정정본 선택 | 시점 당시 이용 가능 보고서 선택 원칙 재사용. `10-K/10-Q`·SEC fy/fp/accn 구조와 기간 필터는 그대로 적용 불가 |
| [sec_accn_reconcile.py](../../src/investment_system/providers/sec_accn_reconcile.py), [sec_cover_shares.py](../../src/investment_system/providers/sec_cover_shares.py) | accession 대조, SEC cover 주식수/종류 처리 | `rcept_no`/`docID` 대조와 KR/JP 주식수·분할/자기주식 의미 검증을 별도 설계해야 함 |
| [contracts/raw.py](../../src/investment_system/contracts/raw.py): `RawFundamentals`; [contracts/models.py](../../src/investment_system/contracts/models.py): `DataStamp` | 주요 수치·출처·공개/이용/관측시각·기간·통화·품질 계약 | 통화 `KRW`/`JPY`, 기간, 결측값을 명시한 입력 계약 재사용 가능. 주석 저장 계약은 없음 |
| [qgv/raw_map.py](../../src/investment_system/qgv/raw_map.py): `map_raw()` | `RawFundamentals`를 공통 분석 입력으로 변환 | 계약 이후 재사용 가능하나 회계 taxonomy/통화/기간을 자동 통일하는 변환기는 아님 |
| [ingestion/raw_store.py](../../src/investment_system/ingestion/raw_store.py), [ingestion/manifest.py](../../src/investment_system/ingestion/manifest.py) | 원본 bytes/JSON·content type·해시·시점/출처 manifest 저장 | 원본 취득 증거 보존 구조는 참고 가능. SEC 이름/CIK에 묶인 기존 재생 경로는 별도 KR/JP 로더 필요 |

[us_sec.py](../../src/investment_system/providers/us_sec.py)의 `parse_us_company()`는 companyfacts 취득→`facts_to_raw()` 변환 경로이며 **submissions 인덱스 잠금/대조를 필수로 실행하지 않는다**. 따라서 이미 완성된 공통 `fetch→index→vintage→raw` 파이프라인에 API URL만 바꾸면 된다고 설명하면 부정확하다. 기존 코드의 재사용 가능한 계약에 지역별 수집·검증·변환을 붙이는 것이 가능하다는 판정이다.

후속 설계에서 필요한 연결 단계:

1. **식별:** `hanmi ↔ KRX:042700 ↔ DART:00161383`, `tokyo_electron ↔ TSE:8035 ↔ EDINET:E02652/80350`를 별도 filing identity로 대조한다. [markets/us.py](../../src/investment_system/markets/us.py)는 두 회사를 `KR_DEFERRED`/`C-08_NON_US`로 제외하고 있으므로 CIK 보유 US 종목처럼 주입하지 않는다.
2. **제출본 선택:** 공시 인덱스·접수번호/docID·정정 관계를 보존하고 `as_of` 이전 공개본만 선택한다. DART 접수일에 없는 정확한 시각을 임의로 UTC 00:00으로 만들지 말고 KST/JST를 UTC로 일관되게 변환한다. 관측시각과 실제 공개시각을 구분한다.
3. **회계 변환:** 연결/별도, 연간/분기/누적, 보고 통화·배율, 기본/희석 EPS, 현금흐름 부호·FCF 산식을 일치시킨다. 한미반도체 12월 결산과 Tokyo Electron 3월 결산을 같은 달력연도·같은 기간으로 취급하지 않는다. 다른 기간·통화의 지표를 섞지 않는다.
4. **계약 출력:** 검증된 수치만 `RawFundamentals`로 전달하고 결측은 `None`으로 유지한다. 공통 `map_raw()`는 `period_quality`/`reporting_currency`/품질 플래그를 검사해 회계 의미를 보정하지 않으므로 변환 단계에서 충족해야 한다. 입력별 제출본·concept·context provenance는 별도 manifest로 보존한다. [pipeline.py](../../src/investment_system/qgv/pipeline.py)의 `analyze_raw()`는 PIT 가용성 검사를 직접 하지 않으므로 [pit/resolver.py](../../src/investment_system/pit/resolver.py)의 `require_available()` 또는 시점 검사 제공자를 거쳐 전달해야 한다.
5. **공개 출력:** 소유자의 수집 작업과 공개 숫자 JSON을 분리하고 출처·가공 표시를 적용한다. 전체 주석/XML/ZIP의 공개 배포, 다른 회계 지표나 제품 노출은 이 조사만으로 승인된 것으로 보지 않는다.

실제 키·응답이 없는 상태에서 계정 매핑 완전성, 한미반도체 주석 XBRL 범위, Tokyo Electron 모든 기간의 CSV/XBRL 가용성, 정정 전 이력 복원·PIT 완전성을 주장할 수 없다. 새 어댑터·공개 JSON·workflow·`web_assets`는 이 PR에 추가하지 않는다.

## 4. 조회·검증 기록과 PR 범위

- 본문의 인용 근거는 **2026-10-09**에 공식 출처를 조회했다. FAQ는 목록/상세보기, PDF는 직접 다운로드·텍스트/필요한 화면 확인, 회사 코드는 공식 목록/기업개황을 이용했다. 본문에서 미확인·추론·과거 근거를 각각 표시했다.
- DART 공식 이용약관·상업적 이용 FAQ와 EDINET 현행 규약·PDL1.0을 대조했다. 금융청 API와 민간 EDINET DB, API 사용권과 취득 콘텐츠 재배포권을 구분했다.
- 키 신청·가입·인증 API 성공 확인을 하지 않았다. 따라서 무료/한도·제공 필드는 공식 문서 기준 조사이며 운영 시험 결과가 아니다.
- 저장소 변경은 `implementation/docs/fundamentals_sources/KR_JP_FILINGS_RESEARCH.md` **1개 추가**에 한정한다. 다른 PR에 의존하는 커밋·구현 코드·`web_assets`·ruleset·`AUTONOMY_MODE` 변경과 force push를 포함하지 않는다. PR은 생성 후 병합 대기한다.
