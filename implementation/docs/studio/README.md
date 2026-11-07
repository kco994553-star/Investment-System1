# Investment Studio

GitHub `kco994553-star/Investment-System1`의 기존 백엔드를 사용한 **별도 로컬 데모 프론트엔드**다. 사용자의 2026-10-15 요청에 따라 가격·재무·뉴스·성과 예시를 임의로 채웠으며, 모든 화면에 DEMO를 표시한다.

## 실행

Python 3.11 이상. 추가 Python 패키지가 필요 없다. `implementation/`에서:

```sh
PYTHONPATH=src python -m investment_system.product.studio --port 8765
```

브라우저에서 `http://127.0.0.1:8765`를 연다. 서버는 루프백 주소에만 바인딩한다.

서버 없이 확인할 단일 HTML을 만들려면:

```sh
python tools/build_studio_preview.py --out /tmp/Investment-Studio.html
```

HTML에는 네 QGV 프리셋의 Python 계산 결과와 합성 입력이 포함된다. 내장 JavaScript는 월별 복리·납입 계산을 수행한다. 36개 매개변수 조합의 모든 월별 값을 Python 엔진과 대조한다. 이 스튜디오를 로컬 서버로 실행하면 JavaScript 대체 계산이 아닌 HTTP→Python 엔진 경로를 사용한다. HTML은 로컬 검토용으로, 공개 cockpit 빌드에 포함하지 않는다.

## 화면과 백엔드 연결

| 화면 | 반영한 기존 백엔드·계약 | 데모 범위 |
| --- | --- | --- |
| 오늘 | QGV, 포트폴리오, 시뮬레이션, 기술, 매크로의 독립 결과 | 합성 요약. 공식 통합점수 신설 없음 |
| 포트폴리오 | `PortfolioEngine.official_v11`, 식별자 레지스트리 | 원본 19개 TARGET 비중 그대로, 가상 ACTUAL 별도. 주문 없음 |
| 기업 탐색·상세 | `qgv_v2.score_universe`, 공식 유형·DCF 설정 | 기존 4개 프리셋, 가치 함정 관문, 축 결측·재정규화. 합성 19개 입력 |
| 시뮬레이션 | `SimulationEngine`, `pit_roll_wealth`, `DataStamp` | 합성 경로 재생, 자본금·월납입·기간·현금·시장 환경 조절 |
| 기술 | `TechnicalEngine.evaluate` | 동일 합성 종가 경로로 변동률·기술 상태 계산. 확률·신뢰도 미제공 |
| 매크로 | `MacroEngine.evaluate` v0.1.1 | 성장/물가 합성 입력, 8축 표시. 재정·환율 미제공. 참고만 표시 |
| 뉴스·관계 | RIG 사실/잠재 경로 경계, 13F·공시·리서치 모듈 | 가상 시나리오 카드·연결 경로. 검토된 RIG/기관 보고서/공시는 미연결로 표시 |
| 검증·기록 | 제품 시뮬레이션/백테스트/전진검증/원장의 목적 구분 | 실제 검증·보정·원장 성과를 채우지 않음. 기존 원장 보존 |
| 설정 | 현행 원자료 접힘 규칙·개인 데이터 경계 | 관심 기업 ID만 별도 localStorage 키에 저장. 원자료 기본 접힘 |

범용 검색(`/`로 포커스), 산업 필터, 정렬, 관심 기업, 키보드 기업 상세, 모바일 전체 메뉴, 차트 비교선 토글, CSV 다운로드, 오류 재시도를 제공한다. 390px·1440px를 브라우저로 확인한다.

## 계산 해석

- 월말 납입금은 두 자산곡선에 동일하게 적용한다. 투자 손익은 최종 자산에서 총 납입금을 뺀 값이다.
- 수익률·연환산 수익률·최대 낙폭은 납입 영향을 제외한 단위가치를 사용한다. 연환산 변동성은 월별 표본 표준편차 × √12이며 한 달만 있으면 미제공이다.
- 합성 경로는 시나리오별로 고정된 입력이다. QGV 프로필이나 리더보드 변경으로 투자성과를 만들어내지 않는다.
- 현금 수익률은 0이며 세금·거래비용·환율은 제외한다. 기업의 가상 가격은 모두 USD로 정규화한 예시이며 실제 해외 통화 시세가 아니다.
- 실제 시세/API 키/개인 보유/원장/실시간 피드를 읽지 않는다. 기존 Frozen 계약, 점수식, 가중치, TARGET 원본, 운영 화면, 공개 빌드, 배포 워크플로를 수정하지 않는다.

## 검증

`implementation/`에서:

```sh
PYTHONPATH=src:. python -m pytest -q --tb=short -p no:cacheprovider tests
node tools/studio_preview_runtime_test.js
CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium node tools/studio_browser_test.js
```

브라우저 테스트는 설치된 Playwright와 Chromium을 사용한다. Chromium 위치가 다르면 환경변수를 해당 실행 경로로 바꾼다. 브라우저 스크린샷 기본 저장 위치는 `/tmp/investment-studio-evidence`다.

단일 HTML 검사는 별도 정적 서버로 HTML을 처음 로드한 뒤 브라우저를 오프라인으로 전환해 실행한다:

```sh
python -m http.server 8766 --bind 127.0.0.1 --directory /tmp
CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium node tools/studio_portable_browser_test.js
```

`STUDIO_PREVIEW`로 단일 HTML의 로컬 HTTP 주소를 지정할 수 있다. 이 환경의 Chromium은 `file://` 탐색을 관리자 정책으로 차단하여 HTTP 최초 로드 후 오프라인 검사를 사용한다.

### 2026-10-15 검증 결과

- 전체 Python 테스트: **2,950 passed, 283 subtests passed**.
- 9개 화면 × 390/1440px, 검색·관심 기업·기업 상세·CSV·오류/재시도·지연 응답 중 화면 이동 검사 통과.
- 단일 HTML: 처음 로드 후 오프라인에서 전체 메뉴·키보드 검색·V 결측·원자료 접힘·프로필 변경·현금 100% 계산 검사 통과.
- 단일 HTML 계산: 36개 조합의 모든 월별 자산·비교자산·단위가치와 요약값이 Python과 일치.
- 독립 코드 검토의 두 수정 사항: 지연된 계산 결과가 새로 열린 입력폼과 불일치하던 문제(새 입력 보존 포함), 단일 HTML에서 Python 호출로 잘못 표시하던 출처 문구. 브라우저 회귀 검사로 확인했다.
