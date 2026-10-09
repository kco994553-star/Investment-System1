# 26E — 배포 PR 병합 및 사용자 Pages Source 변경

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
