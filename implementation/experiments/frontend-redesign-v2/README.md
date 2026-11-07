# 투자시스템 프론트엔드 v2 시안

현재 공개 데이터와 기존 투자시스템의 기능 범위를 바탕으로 만든 독립형 UI 시안입니다. 운영 사이트 파일과 배포 설정은 변경하지 않습니다.

## 열기

`index.html`을 브라우저에서 열거나, 다음 명령으로 생성한 단일 HTML을 엽니다. 외부 스크립트·폰트·이미지 요청은 없으며 출처 링크는 사용자가 선택할 때만 열립니다.

```bash
python implementation/experiments/frontend-redesign-v2/package_preview.py /tmp/Investment_System_Frontend_v2.html
```

오늘 / 기업 탐색 / 내 투자 / 시장·뉴스 / 성과·기록을 중심으로 기업 상세, 관심기업, 설정을 연결했습니다. 검색·필터·정렬·3기업 비교·관심기업·메모·한영 전환·테마 전환을 제공합니다. 저장은 시안 전용 localStorage 키를 사용합니다.

## 데이터와 범위

`data.js`는 2026-10-17 확인한 공개 게시본의 고정 스냅샷입니다. 출처별 시점과 SHA-256은 설정에서 확인할 수 있습니다. 자동 갱신하지 않습니다. TARGET v0는 기준 포트폴리오이며 실제 개인 보유가 아닙니다. 가격·실제 보유·수익률·V·총점은 연결되지 않았고 임의의 값으로 대체하지 않았습니다.

Q/G는 같은 계산 버전과 유효한 수집 시각을 확인하며 결측·버전 불일치·만료를 구분합니다. 공개 Universe 504개와 TARGET 19종목의 관측 표본을 구분합니다. 캡처한 시점을 기준으로 최신성을 판정하는 설계 미리보기이며 운영 투자 판단용 실시간 화면이 아닙니다.

## 검증

```bash
node --test implementation/experiments/frontend-redesign-v2/model.test.cjs implementation/experiments/frontend-redesign-v2/render.test.cjs
node --check implementation/experiments/frontend-redesign-v2/app.js
```

17개 검사 통과: 자료 상태, 0점, 정렬, 검색, 3개 비교 제한, 한영 출력, HTML escape, URL scheme, 별도 저장 키, 결측 날짜, 한글 IME, 페이지 범위. 출력 검사는 Node VM의 단순 DOM 대역을 사용하며 실제 브라우저 검사가 아닙니다.

독립 코드 리뷰에서 발견한 결측 날짜의 1970년 표시, 한글 검색 조합 중 입력 요소 교체, 표의 자료 상태 구분을 수정했습니다. 실제 브라우저와 390/1440px 레이아웃·키보드·모바일 조작 검사는 아직 수행하지 못했습니다.

운영 통합은 `docs/superpowers/specs/2026-10-17-frontend-redesign.md`의 순서를 따릅니다. 기존 계산 엔진·개인 기기 데이터·가격 입력을 연결하고 브라우저 검증 후, 저장소의 사용자 승인 범위에서 병합과 배포를 진행합니다.
