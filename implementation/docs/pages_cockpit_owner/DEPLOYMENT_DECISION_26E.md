# 26E — 사용자 결정 기록 (2026-10-09)

## 현재 결정: 수동 시세·환율과 KRW 표시

**26E 결정 = ① 시세·환율 수동 입력 + KRW 기준 표시 (사용자 선택, 2026-10-09).**

시세·환율 구현 lane은 기존 WAIT에서 **수동 입력 범위만 READY**로 전환한다.
READY는 이 범위의 후속 구현을 검토할 수 있다는 뜻이며, 이번 문서 전용 PR에서
구현·검증·배포가 완료됐다는 뜻이 아니다. 자동 수집, 공개 JSON(②), 실시간 API(③)는
채택하지 않았다. 사용자 API 키의 기기 직접 조회도 [후속 공식 문서 조사](DEVICE_DIRECT_QUOTES_RESEARCH.md)만
허용하며, 별도 사용자 선택 전에는 도입하지 않는다.

### 결정 영수증과 보호 경계

| 항목 | 기록 |
| --- | --- |
| 결정 권한 | 사용자 「Cockpit IA v1 공식화 + 차트 목록 보강 + 26E 결정 (문서 전용 PR)」 작업 5-1, 2026-10-09. 사용자 선택을 기록하며 watcher의 자동 승인으로 대체하지 않는다. |
| 선택·대안 | ① 앱 수동 입력 + KRW 표시 선택. ② 일일 공개 JSON, ③ 실시간 API는 미채택. 기기 직접 API는 조사 후보일 뿐이다. |
| 설계 정합성 | [Cockpit IA v1](../frontend_ia_v1/COCKPIT_IA_v1.md)의 S03/S11 및 TARGET≠ACTUAL·결측≠0 원칙. 원통화 식별과 시세 시각·환율 기준일을 보존한다. TARGET·점수·가중치·방법론·Holdout은 변경하지 않는다. |
| 보호 경계 | 읽기 전용. 입력값·보유수량·금액·계좌·키는 공개 저장소/공개 JSON/서버로 보내지 않는다. 주문·이체 기능, 키 발급·가입·외부 API 호출 코드는 범위 밖이다. |
| 이번 PR 검증 | 문서만 변경, 기존 값·계산 코드·데이터·워크플로 무변경, 경로 및 개인정보/repository-guard 검증. 후속 구현 검증 완료나 gate 수 증가로 해석하지 않는다. |
| semantic_delta | 선택 미수신 WAIT → 사용자 선택 수신, 수동 입력 lane만 READY; 표시 기준 KRW 확정. 시장 데이터 자동 연동·공개 재배포 권한·거래 권한은 확대하지 않는다. |

### SSoT §8 · §26D 범위 영향

근거는 Global `integration/global-handoff-v1` exact HEAD
`1f8229154f1e6e298509654db974c65ee726e0ab`의
[Autonomous Execution & Decision Authority SSoT v1.1](https://github.com/kco994553-star/Investment-System1/blob/1f8229154f1e6e298509654db974c65ee726e0ab/implementation/docs/coordination/policies/Investment-System1_Autonomous_Execution_Decision_Authority_SSoT_v1_1.md)
§8 및 §26D다. Global 정책·STATE·AUTONOMY_MODE 자체는 이 PR에서 수정하지 않는다.

| 범위 | 영향과 후속 검증 경계 |
| --- | --- |
| §8 위험 비례 검증 | 이번 변경은 문서 및 요구 목록의 기록이다. 후속 수동 입력 구현은 실제 변경의 위험에 맞춰 재분류·검증해야 하며, 금액성 변환·대사·개인정보 경계에 필요한 검증을 이 문서로 면제하지 않는다. CI PASS가 독립검증·방법론 승인·거버넌스 수락을 대신하지 않는다. |
| §26D rollback | 문서 오류는 승인된 정정/revert PR로 되돌린다. 공개 Git 이력·기존 증거를 삭제하거나 force push하지 않는다. 이후 구현 rollback은 별도 검토하며 사용자 기기 입력값을 자동 삭제하지 않는다. |
| 미채택 lane | 자동 수집/②/③ 및 기기 직접 API는 이번 READY에 포함하지 않는다. 무료 여부·CORS·조회 전용 키·가격 제공·개인 표시 조건을 조사해도 구현 승인이 되지 않는다. |

관련 기록: [선택안과 현재 결정](QUOTES_FX_OPTIONS_26E.md),
[FX 조사와 현재 선택](FX_RESEARCH_26E.md), [기기 직접 API 조사](DEVICE_DIRECT_QUOTES_RESEARCH.md).

## 과거 배포 준비 기록 (보존; 현재 26E 선택 대기가 아님)

아래는 배포 준비 당시의 질문·관측 기록이다. 사용자는 별도 Main 지시(2026-10-09)에서
Pages Source 변경 완료와 배포 PR 병합 승인을 알렸다. 아래 준비 시점의 None/404/WAIT는
현 시점 설정·배포 결과를 주장하지 않는다. 이 문서 전용 PR은 실제 공개 배포 검증을 수행하지 않는다.

결정 질문: 이 배포 PR의 병합을 승인하고 Pages Source를 GitHub Actions로 직접 변경하시겠습니까?

현재 Pages Source None은 사용자가2026-10-09 확인했습니다. 준비 시점의
has_pages=false, Pages API404, 예정 공개 주소404도 기록했습니다.
예정 주소: https://kco994553-star.github.io/Investment-System1/
공개 주소 검증은 실제 배포 이후에 수행하며 현재 NOT_RUN입니다.

| 선택지 | 영향·비용 | 되돌리기 |
| --- | --- | --- |
| Source 변경 완료 후 PR 병합 승인 (권장) | 사용자 설정 후 정상 병합의 push가 검증·웹 폴더 업로드·Pages 배포를 실행합니다. 공개 저장소 표준 Actions/Pages 범위로 유료 서비스는 추가하지 않습니다. | 코드 문제는 revert PR. 이미 게시된 사이트는 이후 승인된 재배포 또는 사용자 Pages 비활성화까지 남을 수 있습니다. |
| PR 보류·Source None 유지 | 검증된 PR과 스크린샷을 보존하며 공개 사이트는 생기지 않습니다. | 이후 설정·병합 승인 가능. |

사용자 설정 위치: [Settings → Pages](https://github.com/kco994553-star/Investment-System1/settings/pages)
→ Build and deployment → Source → GitHub Actions.
설정 완료 여부와 PR 병합 승인을 함께 알려주시면 됩니다. 에이전트는 Pages 설정을 변경하지 않습니다.

권장 근거: 사용자가 명시한 중간 확인·개인 사용 목적, SSoT8 비례 검증과26D rollback 경계.
PR에서는 deployment job을 실행하지 않습니다. 실제 배포는 기준 브랜치에서만 가능하고,
업로드 직전11개 산출물 검사와 실제 uploaded tar의 배포 직전 재검사를 통과해야 합니다.
보유 데이터·채워진 금액성 필드·비밀 값·local/ 및 예상 밖 파일은 fail closed입니다.
실제 보유 데이터가 없는 새 브라우저의390px·1280px ko/en 스크린샷4개를 첨부합니다.
기존 서비스워커/PWA manifest는 없으며 루트 scope나 보유 캐시를 추가하지 않습니다.

WAIT lane: 배포 PR 병합과 Pages 공개 배포. 설정 변경은 사용자 작업입니다.
계속 진행: READ_ONLY 보고·증거 보존, 별도 시세/기준통화 선택지 정리.
시세·환율 수집 구현은 이번 결정 범위에 포함되지 않고 계속 WAIT입니다.
기한: 없음. 무응답을 승인으로 해석하지 않습니다.
