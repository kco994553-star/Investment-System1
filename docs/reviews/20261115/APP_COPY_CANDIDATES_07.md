# APP 화면 글 후보 부록 (계속)

정적 후보·잠정 분류이며 실제 노출 확정/삭제 명령이 아니다. [주요 조사](APP_SCREEN_COPY.md)를 먼저 읽는다.

| ID | 문구(제목) | 위치 | 종류 | 처리 |
| --- | --- | --- | --- | --- |
| plv1.cross.012 | 가장 약한 Evidence와 Horizon 충돌 찾기 | [implementation/src/investment_system/product/web_app/screen-prompts-live.js:595](https://github.com/kco994553-star/Investment-System1/blob/4a3141b8fa1593e68552390c7ad4b1ea16b89d2f/implementation/src/investment_system/product/web_app/screen-prompts-live.js#L595) | 판단·조작에 필요 | 눌렀을 때 |
| plv1.cross.013 | Investment System 판단·Thesis·Source Red Team | [implementation/src/investment_system/product/web_app/screen-prompts-live.js:596](https://github.com/kco994553-star/Investment-System1/blob/4a3141b8fa1593e68552390c7ad4b1ea16b89d2f/implementation/src/investment_system/product/web_app/screen-prompts-live.js#L596) | 판단·조작에 필요 | 눌렀을 때 |
| plv1.cross.014 | 빠진 변수와 다음 Research 질문 찾기 | [implementation/src/investment_system/product/web_app/screen-prompts-live.js:597](https://github.com/kco994553-star/Investment-System1/blob/4a3141b8fa1593e68552390c7ad4b1ea16b89d2f/implementation/src/investment_system/product/web_app/screen-prompts-live.js#L597) | 판단·조작에 필요 | 눌렀을 때 |
| plv1.cross.015 | 이전 cutoff 이후 Delta Evidence 찾기 | [implementation/src/investment_system/product/web_app/screen-prompts-live.js:598](https://github.com/kco994553-star/Investment-System1/blob/4a3141b8fa1593e68552390c7ad4b1ea16b89d2f/implementation/src/investment_system/product/web_app/screen-prompts-live.js#L598) | 판단·조작에 필요 | 눌렀을 때 |
| plv1.cross.016 | 시장과 시스템 판단 차이의 원인 찾기 | [implementation/src/investment_system/product/web_app/screen-prompts-live.js:599](https://github.com/kco994553-star/Investment-System1/blob/4a3141b8fa1593e68552390c7ad4b1ea16b89d2f/implementation/src/investment_system/product/web_app/screen-prompts-live.js#L599) | 판단·조작에 필요 | 눌렀을 때 |

## 프롬프트 개인화 화면 추가 후보(500~529행)

| 문구 | 위치 | 종류 | 처리 | 근거 |
| --- | --- | --- | --- | --- |
| ① 이 기기(브라우저)에 저장된 값 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:503 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 즐겨찾기 · 가중치 · 노트 · 내 위치 · 프롬프트 사본 · 다른 기기와는 공유 안 됨 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:503 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 프롬프트 ★ · 내 사본 · 이 브라우저에 저장 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:503 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| ② 저장된 값이 없으면 개발자 기본값 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:504 | 방어용 설명 | 삭제 | 조작·결과 구분에 필요한 정보는 별도 짧은 라벨로 보존 |
| 공식 가중치 · 기본 프롬프트 · 기본 화면 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:504 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 프롬프트는 저장된 사본이 없으면 이것 · 공식 원문 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:504 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 기업 화면 (0. 기업 검색에서 고른 기업) | implementation/src/investment_system/product/web_app/screen-prompts-live.js:505 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 선택 기업 (빈 기업 칸만 · 가격 없음) | implementation/src/investment_system/product/web_app/screen-prompts-live.js:505 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 연결됨 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:505 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 5.2 투자 일일보고서 · 보고 불가 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:506 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 사유 코드 · 최소 누락 입력 · 기준 거래일 (금액 · 수량 없음) | implementation/src/investment_system/product/web_app/screen-prompts-live.js:506 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 준비 중 · 포트폴리오 화면 연결 전 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:506 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 5.3 모의투자 일일보고서 · 보고 불가 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:507 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 세트 이름 · 가상 장부 · 실제 자금 아님 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:507 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 준비 중 · 포트폴리오 화면 연결 전 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:507 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 세부: 플레이북 기록 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:508 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 상황 · 판정 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:508 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 준비 중 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:508 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 주간 보고 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:509 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 결정 대기 (WEEKLY-REPORT) | implementation/src/investment_system/product/web_app/screen-prompts-live.js:509 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 뉴스 · 연구 프롬프트 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:510 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 카탈로그에 없음 (PROMPT-DOMAIN) | implementation/src/investment_system/product/web_app/screen-prompts-live.js:510 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 개인화 — 어떤 값을 보여 줄까? | implementation/src/investment_system/product/web_app/screen-prompts-live.js:512 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 앱 전체 설정에 같은 순서 적용이 목표 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:512 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 지금 상태 · 이 브라우저에 저장한 내 사본이 있으면 그것을, 없으면 개발자 기본값(공식 원문 PLV1)을 보여 줍니다 · ★와 내 사본은 이 브라우저에만 저장됩니다 · 개인 자료는 이 기기 밖으로 나가지 않습니다 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:514 | 방어용 설명 | 삭제 | 조작·결과 구분에 필요한 정보는 별도 짧은 라벨로 보존 |
| 다른 화면에서 열기 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:515 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 기능 7.1.5 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:515 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 맥락만 채워서 같은 채우기를 엶 · 맨 위에 돌아가는 링크 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:516 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 화면별로 넘기는 것과 연결 상태 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:517 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 화면 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:518 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 넘기는 것 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:518 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 상태 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:518 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 연결됨 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:520 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 보고 불가 프롬프트 틀은 옛 화면(5.2) 안에 따로 있습니다 · 라이브러리로 합치려면 새 카탈로그 판과 소유자 승인이 필요합니다 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:521 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 다른 화면은 주소 #/prompts/<프롬프트 번호>/<돌아갈 메뉴>로 이 채우기를 엽니다 · 선택 기업은 화면을 옮겨도 이 기기 메모리에 남고 빈 칸만 채웁니다 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:522 | 판단·조작에 필요 | 눌렀을 때 | 기본 화면 설명 한 문장; 방법·한계 상세는 펼침 |
| 1. QGV에서 연 모습 보기 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:523 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 기업 외부 Evidence 확장 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 신규 투자 종합 검토 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 실적 발표 Delta 분석 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| Technical 검증 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| Macro 환경 검증 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 투자 Thesis Red Team | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 보유 종목 재점검 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 숨겨진 위험 찾기 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 새로운 종목 발굴 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 시스템 Red Team | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 후보 탐색 범위 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 어떤 종목 집합에서 조사 후보를 찾을지 정합니다. 국가·시장·선정 기준·기준일을 명확히 씁니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: 미국 시총 상위 500개 종목 · 기준일 2026-10-09 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 직접 정한 조사 범위 또는 이미 확인한 Universe 목록에서 가져옵니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 최대 후보 수 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 출력할 Research Candidate 수의 상한입니다. 양의 정수로 입력하며 부족한 후보를 억지로 채우지 않습니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: 10 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 한 번에 검토할 수 있는 최대 후보 수를 직접 정합니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 정보 기준일 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 이 시점까지 공개·이용 가능했던 정보만 사용합니다. 미래 날짜는 허용되지 않습니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: 2026-10-09 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 이번 분석에 사용할 정보 기준일을 직접 정합니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 기존 시스템 후보 목록 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 기존 QGV 리더보드 후보와 비교하여 중복·빠진 후보를 조사합니다. 새 공식 후보 목록이나 점수를 입력하는 필드가 아닙니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: 기존 후보·판단 근거·기준일 또는 자료 미제공 표시 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 리더보드 화면에 실제 QGV_LEADERBOARD 결과가 있을 때만 복사합니다. 없으면 미제공을 명시하고 확인된 빈 목록과 구분합니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 조사할 산업 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 후보 탐색이나 거시 영향 분석의 대상 산업입니다. 전략 테마와 산업 분류를 혼동하지 않습니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: 반도체 장비 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 확인한 산업 분류 또는 직접 정한 조사 범위에서 가져옵니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 공급망 조사 산업·테마 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 원재료부터 최종 수요까지 Value Chain을 살펴볼 산업 또는 테마입니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: AI 반도체 공급망 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 공급망 탐색의 대상 산업·테마를 직접 정합니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 조사할 테마 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 직접 수혜뿐 아니라 2·3차 수혜 경로를 조사할 투자 테마입니다. 산업 분류를 바꾸지 않습니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: AI 데이터센터 전력 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 탐색하려는 테마를 직접 정하고 근거와 범위를 함께 씁니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 탐색 출발 회사 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 경쟁 생태계·공급업체·고객사에서 다른 후보를 찾기 위한 출발 회사입니다. 새 후보 자체와 구분합니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: NVIDIA | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 조사를 시작할 회사의 확인된 이름을 직접 고릅니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 출발 회사 종목 코드 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 탐색 출발 회사를 식별하는 종목 코드입니다. 분석 대상 종목 코드와 역할이 다릅니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: NVDA | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 출발 회사의 공식 상장 정보에서 확인합니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 기존 기술 스크리닝 요약 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 여러 종목의 기존 기술 상태 변화에서 새 Research Candidate를 조사할 입력입니다. 개별 종목 차트 기간과 구분합니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: 기존 스크리닝 종목·상태 변화·기준일·근거 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 기술 화면에 실제 여러 종목의 스크리닝 결과·저장된 요약이 있을 때만 복사합니다. 없으면 미제공을 명시합니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 후보 탐색의 거시 변화 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 직접·2차 수혜 후보를 찾을 거시 변화입니다. 기존 거시 판단 요약과 구분해 변화 자체를 씁니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: 금리 인하에 따른 직접·2차 수혜 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 확인한 거시 Evidence 또는 검토할 가설에서 가져오고 사실·가정을 구분합니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 기존 거시 판단 요약 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 거시 변화의 직접·2차 수혜 후보를 조사할 기존 Macro 판단·근거 요약입니다. 새 국면 판단을 만들지 않습니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: 기존 거시 판단·변화·근거·기준일 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 매크로 화면에 실제 MACRO Snapshot·저장된 거시 판단이 있을 때만 복사합니다. 없으면 미제공을 명시합니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 기존 통합 판단 요약 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 기존 QGV·기술·거시 판단의 충돌·누락·새 근거를 검토합니다. 원본 결과를 다시 계산하거나 새 통합점수를 만들지 않습니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: 기존 각 시스템 판단·근거·기준 시점 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 오늘 화면에 실제 기존 통합 판단이 있을 때만 복사합니다. 없으면 미제공을 명시하며 개별 결과를 새 통합 판단으로 합성하지 않습니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 기존 분석 범위·누락 요약 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 시스템이 다룬 종목·항목과 빠진 범위를 비교하여 놓친 Research Candidate를 찾습니다. 완료율을 새로 계산하지 않습니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: 확인된 분석 범위·누락 항목·기준일 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 오늘·검증 화면에 기존 통합 판단의 실제 분석 범위·누락 기록이 있을 때만 복사합니다. 없으면 미제공을 명시하며 개별 QGV 범위를 통합 기록으로 바꾸지 않습니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 눌렀을 때 | 기본 화면 설명 한 문장; 방법·한계 상세는 펼침 |
| 분석할 회사 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 이번 분석의 대상 회사 이름입니다. 종목 코드와 같은 회사를 가리켜야 합니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: NVIDIA | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 회사 공시·공식 홈페이지 또는 확인한 기업 정보에서 가져옵니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 종목 코드 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 이번에 분석할 종목의 코드를 입력합니다. 같은 코드의 다른 거래소 종목과 구분합니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: NVDA | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 기업의 공식 상장 정보 또는 확인한 종목 식별 정보에서 가져옵니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 기존 QGV 요약 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 기존 QGV 판단·근거를 재계산 없이 읽기 위한 선택 입력입니다. 비우면 NOT_PROVIDED이며 독자 점수를 만들지 않습니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: 기존 QGV 판단·근거·기준 시점 또는 빈칸 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 종목 화면의 QGV 카드에 실제 판단·근거가 있을 때만 복사합니다. 없으면 비워 NOT_PROVIDED로 표시할 수 있습니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 실적 검토 기간 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 기대치·전년·전분기와 비교할 실적의 회계연도·분기입니다. 회사의 회계 기간을 확인합니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: FY2026 Q3 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 해당 회사의 실적 발표 자료·공시에서 확인합니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 역 DCF 검토 가정 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 기존 역 DCF가 요구하는 성장·마진·재투자·할인율 등의 가정을 현실 근거와 비교합니다. 새 계산 결과를 만드는 필드가 아닙니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: 기존 성장·마진·재투자·할인율 가정과 기준·출처 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 출처 표기 | 눌렀을 때 | 짧은 출처/상세 버튼으로 진입; 원문·근거를 삭제하지 않음 |
| 기존 가치평가·역 DCF 분석에서 확인한 가정을 가져옵니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 고객 근거 조사 범위 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 수요·만족도·이탈을 조사할 고객군·제품·기간·자료 유형의 범위입니다. 고객 반응이 확인됐다는 결과가 아닙니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: 클라우드 3사 실적 발언·개발자 커뮤니티 · 제품과 조사 기간 추가 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 조사할 고객 범위와 자료 유형을 직접 정합니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 자료 입력 방식 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| SYSTEM_CONTEXT는 기존 시스템 결과를 받아 재계산하지 않습니다. STANDALONE도 질문만으로 충분하지 않으며 기술·거시 실제 PIT 원자료가 없으면 INSUFFICIENT_DATA로 종료합니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 눌렀을 때 | 기본 화면 설명 한 문장; 방법·한계 상세는 펼침 |
| SYSTEM_CONTEXT 또는 STANDALONE을 선택 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 사용자가 직접 선택합니다. 선택만으로 Snapshot이나 원자료를 자동으로 가져오지 않습니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 가격·차트 분석 기간 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 기술적 분석에 제공할 가격·거래량 자료의 기간입니다. 정보 기준일까지의 실제 자료와 맞춥니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: 최근 1년 · 2025-10-09~2026-10-09 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 보유한 차트·OHLCV 자료 또는 기존 TechnicalSnapshot의 기간에서 확인합니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 기술 분석 입력 자료 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| SYSTEM_CONTEXT는 기존 기술 Snapshot·계산 결과를 재계산 없이 사용합니다. STANDALONE은 실제 PIT OHLCV·조정 기준·시간대·기업행사·출처가 필요하며 없으면 INSUFFICIENT_DATA입니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 출처 표기 | 눌렀을 때 | 짧은 출처/상세 버튼으로 진입; 원문·근거를 삭제하지 않음 |
| 예: 기존 기술 Snapshot 또는 기준·시점·출처를 포함한 실제 OHLCV | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 출처 표기 | 눌렀을 때 | 짧은 출처/상세 버튼으로 진입; 원문·근거를 삭제하지 않음 |
| 기술 화면에 실제 TECHNICAL 결과가 있을 때만 복사하거나 STANDALONE용 실제 시점별 원자료를 제공합니다. 없으면 미제공을 명시합니다. 준비 화면은 자동 데이터 연결이 아닙니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 눌렀을 때 | 기본 화면 설명 한 문장; 방법·한계 상세는 펼침 |
| 비교 지수·경쟁사 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 상대강도·가격 반응을 비교할 지수나 기업과 근거 자료입니다. 기간·통화·기업행사 기준을 맞춥니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: S&P 500 / AMD / AVGO · 비교 기간과 자료 출처도 추가 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 출처 표기 | 눌렀을 때 | 짧은 출처/상세 버튼으로 진입; 원문·근거를 삭제하지 않음 |
| 확인한 지수·Peer 목록과 같은 기준의 실제 가격 자료에서 가져옵니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 시간순 뉴스·이벤트 근거 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 가격 움직임과 비교할 실적·정책 등 사건의 실제 근거입니다. 공개 시점·이용 가능 시점·원문을 함께 씁니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 가상 예: 2026-08-27 실적 발표; 2026-09-10 수출 규제 발표 · 원문과 공개 시각 추가 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 확인한 공시·공식 발표·뉴스 원문에서 가져오고 사실과 해석을 구분합니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 옵션·포지셔닝 자료 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| IV·Skew·Open Interest 등 실제 보유 자료와 출처를 씁니다. 필수 입력이며 자료가 없으면 그 사실을 명시하고 결론을 만들지 않습니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 출처 표기 | 눌렀을 때 | 짧은 출처/상세 버튼으로 진입; 원문·근거를 삭제하지 않음 |
| 예: NOT_AVAILABLE · 옵션 자료 없음 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 보유한 확인된 옵션 자료에서 가져옵니다. Dealer/Flow 추정은 사실과 구분합니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 거시 분석 시장 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 거시 변화와 전달 경로를 조사할 국가·시장 범위입니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: 미국 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 이번 거시 질문의 대상 시장을 직접 정합니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 거시 판단 기간 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 거시 시나리오·영향을 검토할 기간입니다. 과거 가격 자료의 기간인 period와 구분합니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: 향후 3~12개월 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 거시 질문과 사용할 기존 Macro 자료의 평가 기간을 확인합니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 거시 분석 입력 자료 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| SYSTEM_CONTEXT는 기존 거시 Snapshot·State·Regime을 덮어쓰지 않습니다. STANDALONE은 시장·기간에 맞는 실제 PIT 발표·빈티지·시장 내재 자료와 출처가 필요하며 없으면 INSUFFICIENT_DATA입니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 출처 표기 | 눌렀을 때 | 짧은 출처/상세 버튼으로 진입; 원문·근거를 삭제하지 않음 |
| 예: 기존 거시 Snapshot 또는 시점·빈티지·출처가 있는 실제 자료 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 출처 표기 | 눌렀을 때 | 짧은 출처/상세 버튼으로 진입; 원문·근거를 삭제하지 않음 |
| 매크로 화면에 실제 MACRO 결과가 있을 때만 복사하거나 STANDALONE용 확인된 원자료를 제공합니다. 없으면 미제공을 명시합니다. 8축 준비 표시가 데이터 제공 완료를 뜻하지 않습니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 눌렀을 때 | 기본 화면 설명 한 문장; 방법·한계 상세는 펼침 |
| 시장 금리경로 가정 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 시장에 내재한 금리경로 중 검증할 가정입니다. 기준 시점·기간·근거와 이를 틀리게 할 조건을 함께 씁니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: 향후 금리 인하를 예상하는 시장 가정 · 기준일과 근거 추가 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 확인한 시장 내재 자료·기존 분석에서 가져옵니다. 미래 금리경로를 사실처럼 만들지 않습니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 거시 시나리오 가정 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 연착륙·침체 등 반박할 기존 시나리오의 전제입니다. 근거 없는 확률을 새로 넣지 않습니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: 연착륙 가정: 성장 둔화·물가 완화 · 전제와 반대 근거 추가 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 검토할 기존 Macro 시나리오에서 복사하고 관측 사실과 가정을 구분합니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 이전 분석 기준일 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 이전 분석 이후 새로 공개된 정보를 비교할 시작 기준일입니다. 이번 정보 기준일보다 앞서야 합니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: 2026-07-01 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 비교할 이전 분석·Snapshot의 기준일에서 확인합니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 검토할 정책 변화 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 행동 변화·대체·공급 반응 같은 2차 효과를 조사할 정책입니다. 발표·시행 시점과 근거를 씁니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 예: 반도체 수출 규제 강화 · 발표/시행일과 출처 추가 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 출처 표기 | 눌렀을 때 | 짧은 출처/상세 버튼으로 진입; 원문·근거를 삭제하지 않음 |
| 정책 당국의 원문·공식 발표 등 확인한 자료에서 가져옵니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 판단 원본 참조 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 판단·조작에 필요 | 유지 | 제목·값·상태·조작/접근성 문구; 합쳐지는 단편은 렌더링 때 재검토 |
| 통합 판단이 참조한 기존 Snapshot의 ID·기준일·출처 등입니다. 검증되지 않은 ID나 연결을 만들지 않습니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 출처 표기 | 눌렀을 때 | 짧은 출처/상세 버튼으로 진입; 원문·근거를 삭제하지 않음 |
| 예: 기존 Snapshot ID·기준일·출처·버전 | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 출처 표기 | 눌렀을 때 | 짧은 출처/상세 버튼으로 진입; 원문·근거를 삭제하지 않음 |
| 기존 통합 판단이 실제 참조한 각 화면 데이터의 Snapshot ID·기준일·출처를 확인해 복사합니다. 없으면 미제공을 명시하며 임의 ID나 통합 참조를 만들지 않습니다. | implementation/src/investment_system/product/web_app/screen-prompts-live.js:529 | 출처 표기 | 눌렀을 때 | 짧은 출처/상세 버튼으로 진입; 원문·근거를 삭제하지 않음 |
