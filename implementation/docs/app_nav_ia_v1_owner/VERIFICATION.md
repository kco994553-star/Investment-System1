# Cockpit IA v1 메뉴 재배치 검증

기준 canonical: `c8b9debecaeaebf392672c74f5bfd50b20217227` (#72 병합). 작업 브랜치: `codex/app-nav-ia-v1`. 병합은 사용자 승인 대기다.

## 변경 범위

하단 메뉴는 오늘 / QGV / 기술 / 매크로 / 검증 5개로 바뀐다. 1024px 이상에서는 동일 메뉴와 QGV 하위 4그룹을 좌측 사이드바로 표시한다. 기존 화면·해시는 유지하고 QGV 하위 화면 및 리서치에 상위 이동 링크를 추가한다.

QGV 허브는 기존 화면으로 연결하며 별도 상세 화면이 없는 전략 프로필·모델 포트폴리오·관심 기업·13F는 링크 없이 준비 중으로 표시한다. 기술은 기존 운영 결과·차트의 연결 상태, 매크로는 공식 8축과 각 축의 Level / Direction / Momentum / Surprise / Stress / Confidence를 표시한다. 실데이터가 없어 NOT_AVAILABLE을 유지하고 차트·숫자·종합 점수를 만들지 않는다. 매크로 v0.1.1 확정 / v0.1.4 후보는 기존 `versions.py` 기록의 표시이며 승격이 아니다. 검증 허브는 기존 리서치와 준비 중인 백테스트·전진검증·Track Record를 표시한다.

## 검증 결과

- Python 전체: 856 passed / 345 subtests passed. 기존 번역 검사기는 JSON 사전을 줄바꿈과 무관하게 읽도록 보완했으며 번역 누락 검사 조건은 유지했다.
- 기존 Node: 84 passed. 기존 Pages·기기 보유·수동 시세·Google 모의 브라우저: 222 passed.
- 신규 탐색 브라우저: ko/en × 390/1280px, 741 checks passed. 5탭 클릭, 허브 카드, 기존 해시·북마크·뒤로 가기·부모 이동, aria-current, 언어, 44px 터치 영역, 가로 넘침, 신규 미제공 상태를 확인했다.
- 신규 브라우저 외부 요청·쓰기 요청·실패 응답·런타임 오류·CSP 이벤트·CSP 콘솔 경고: 모두 0. Google 회귀 검증은 모의 응답만 사용했다.
- 공개 산출물 16개 가드 PASS. 변경은 app.js / index.html / locale.js / style.css 4개이며 다른 12개와 공개 JSON 3개는 기준과 byte-identical이다. 검토된 4개 자산 해시만 갱신했고 가드 규칙은 유지했다.
- CSP, script 태그, stylesheet 태그는 기준과 동일하다. 기존 app 함수 48개 중 수정은 renderRoute뿐이며 함수 삭제는 없다. Home·설정·기기 저장·가격 계산·Google 인증 코드와 투자 기준은 유지했다.
- repository/privacy guard PASS, AUTONOMY_MODE READ_ONLY. force push·ruleset 변경·canonical 병합은 없다.

신규 브라우저의 연구 iframe → 설정 이동은 네트워크 유휴를 기다리는 대신 실제 목적 화면과 활성 메뉴의 렌더 상태를 기다린다. 새 테스트는 같은 상위 탭에 속한 다른 화면이 남아 있어도 준비 완료로 판정하지 않는다.

## 스크린샷

모든 캡처는 빈 기기 저장소와 입력되지 않은 폼을 확인한 뒤 저장했다. 공개 Pages 폴더에는 포함되지 않는다. 신규 4화면 × 언어·폭 조합의 16개 캡처는 CI verification artifact에도 남는다.

| 언어 | 모바일 390px | 사이드바 1280px |
|---|---|---|
| ko | [QGV 390](evidence/ia-qgv-ko-KR-390.png) | [QGV 1280](evidence/ia-qgv-ko-KR-1280.png) |
| en | [QGV 390](evidence/ia-qgv-en-US-390.png) | [QGV 1280](evidence/ia-qgv-en-US-1280.png) |

## OPEN

이번 메뉴 재배치 범위의 미구현 항목은 없다. 기술·매크로 실데이터와 검증 성과 기록은 기존 미연결 상태이며 이번 PR에서 연결하지 않는다. 공개 사이트 확인·배포는 사용자 승인 병합 이후 작업이다.
