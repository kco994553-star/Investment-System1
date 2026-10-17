# 투자 시스템 프론트엔드 v2 (읽기 전용)

디자인 캔버스 S01~S17의 흐름(오늘 / 1 QGV / 2 기술 / 3 매크로 / 4 검증)을 따르는 새 화면이다. 기존 코크핏(`src/investment_system/product/web_assets/`)과 CI·배포는 바꾸지 않는다.

## 무엇을 보여 주나

| 화면 | 주소 | 내용 |
| --- | --- | --- |
| 오늘 | `#/` | 산출 현황(Q·G n/504), 시스템 4단계 상태, 주의할 것(켜진 경고등·2주 안 예상 실적), 최근 7일 공시·뉴스, TARGET v0 19종목, 데이터 기준 |
| QGV · 종목 찾기 | `#/qgv` | 504+19종목 리더보드: 검색·범위·정렬·프로필(균형/우량/성장/가치)·가치 함정 관문, 50개씩 |
| QGV · TARGET 구성 | `#/qgv/target` | 테마별 목표 비중과 종목 (ACTUAL은 기기 전용이라 기존 코크핏으로 연결) |
| QGV · 공시·뉴스 | `#/qgv/market` | TARGET 기업의 최근 30일 SEC·DART 공시와 뉴스 |
| 기업 | `#/company/<id>` | QGV·Q·G·V, 요인 15개(비중·점수·사유), 분류 3축, 다음 실적 예상 시기, 90일 공시·뉴스 |
| 기술 | `#/technical` | 준비 상태만 (차트는 착수 조건+별도 승인 대기, 공개 자료에 가격 없음) |
| 매크로 | `#/macro` | 경고등 v1 다섯 개(공개 3 + 기기 가격 필요 2), 상태·판정 규칙 |
| 검증 | `#/validation` | 전진검증 원장 상태와 일별 Q·G 기록(본 기록/준비 기록) |
| 설정 | `#/settings` | 데이터 출처별 상태·기준 시각, 범위 안내, 원자료 보기(개발자용, 기본 접힘) |

## 지키는 규칙

- 공개 자료만 읽는다. 가격·보유·계좌·시트 설정을 읽지 않고, 아무것도 저장·전송하지 않는다(localStorage도 쓰지 않음).
- 점수·경고등·원장은 기존 엔진과 검증기를 그대로 불러 쓴다(`index.html`의 `../*.js`: QgvScores, QgvV2, Qgv2Inputs/SecQgv2, MacroLights, PublicScreens, ClassificationScreens, SecDisclosures, NewsSignals, DartDisclosures, ForwardValidation, DeviceWatchlist). 새 계산 방법·가중치는 없다.
- QGV v2만 표시한다. 가격이 없으므로 V는 계산하지 않고 QGV는 엔진 규칙대로 Q·G로만 계산된다(반영 비중 50% 이상일 때만).
- 결측은 `—`와 사유로 표시하고 0으로 채우지 않는다. 사용자 화면에는 결과만, 원자료는 설정 > 원자료 보기에만 둔다.
- 매수·매도·주문 기능이 없다. 순서는 이 화면의 정렬이며 공식 순위가 아니다.

## 로컬 실행

앱은 공개 JSON과 엔진 스크립트를 자기 위치의 한 단계 위(`../`)에서 읽는다(`<meta name="data-base">`). 개발 서버가 앱을 `/app/`에, 공개 자료 폴더를 `/`에 둔다.

```bash
# 합성 테스트 자료로 (오프라인 코크핏 빌드 + 기존 테스트 fixture, 실제 시장 자료 아님)
node implementation/frontend/tools/fixture_public_dir.js /tmp/is-public --ledger active
python3 implementation/frontend/tools/dev_server.py --data /tmp/is-public
# http://127.0.0.1:8994/app/

# 실제 게시 자료로: 게시된 Pages의 파일들을 한 폴더에 내려받아 --data로 지정
```

## 검사

```bash
node --test implementation/frontend/tests/model.test.mjs          # 뷰 모델 10개 (기존 엔진·fixture 사용)
NODE_PATH=<playwright가 있는 node_modules> implementation/frontend/tools/run_browser_test.sh   # 390·1440px, 정상·자료 없음
```

## 배포 (미연결, 승인 필요)

지금은 Pages에 올라가지 않는다. 올리려면 `tools/pages_artifact_guard.py`가 하위 폴더(`app/`)와 새 파일 해시를 허용하도록 바꾸고, `cockpit-pages.yml`이 이 폴더를 산출물에 복사하며, 위 두 검사를 CI 목록에 넣어야 한다. 병합·배포는 사용자 승인 범위에서 한다.
