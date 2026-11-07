# AI 작업 탐색 안내

이 파일은 검색 범위를 안내한다. 권한·제품 규칙·완료 판정은
[START_HERE.md](START_HERE.md)와 연결된 현재 승인 문서를 따른다.
필수 읽기 순서를 줄이거나 담당 범위를 변경하지 않는다.

## 시작과 검색

1. START_HERE.md가 지정한 문서를 순서대로 확인한다.
2. 작업의 기능 번호·변경 대상·관련 승인 명세를 정한 뒤 해당 경로부터 검색한다.
3. 파일명 탐색은 `rg --files <관련 경로>`, 내용 탐색은
   `rg -n '검색어' <관련 경로>`로 범위를 지정한다.
4. 처음부터 전체 트리·모든 문서·큰 JSON 본문을 출력하지 않는다.
   목록·개수·관련 행을 먼저 확인하고 필요한 파일만 읽는다.
5. 자료가 없으면 검색 범위를 넓힌다. 제한된 검색에서 안 나왔다는 이유로
   저장소 전체에 없거나 구현되지 않았다고 단정하지 않는다.

| 작업 | 필수 문서 확인 뒤 먼저 탐색할 경로 |
| --- | --- |
| 새 웹 앱 | `implementation/src/investment_system/product/web_app/` |
| 게시된 옛 화면·전환 의존성 | `implementation/src/investment_system/product/web_assets/` |
| 계산·공통 엔진 | `implementation/src/investment_system/`의 관련 모듈 |
| 연구 명세·인계 | `implementation/docs/lab/`, `implementation/docs/backtest/`, `implementation/docs/forward_validation/` |
| 검증 | 관련 `implementation/tests/`, `implementation/tools/` |
| Worker·배포 | `implementation/worker/`, `.github/workflows/` |

## 필요한 경우에만 펼치는 자료

- `implementation/data/raw/`: 입력·출처·재현성 조사 때 필요한 파일만 읽는다.
- `implementation/experiments/`, `implementation/reports/`, 문서 아래 evidence:
  해당 실험·결함·결과를 확인할 때 읽는다. 실험 폴더에는 코드도 있으므로
  오래됐다는 이유만으로 미사용 또는 삭제 가능하다고 판단하지 않는다.
- 루트의 과거 문서와 SUPERSEDED 문서: 현재 지시로 사용하지 않는다.
  결정 이력 추적이나 명시적 참조가 필요한 경우에 읽는다.
- 기존 문서·증거 경로와 원본은 보존한다. 이 안내는 파일 삭제·이동 지시가 아니다.

## 변경 전에는 검색을 넓힌다

파일 삭제·이동·이름 변경이나 미사용 코드 제거 전에는 전체 추적 파일을
대상으로 참조를 확인한다. `git grep -n -F -- '경로 또는 식별자'` 등을
사용하고 basename·import·동적 경로·CI·배포·테스트·문서 링크도 확인한다.
문자열 검색 결과가 없다는 것만으로 삭제 가능하다고 판정하지 않는다.
원자료·동결 결과·승인 기록, 전환 기간에 필요한 옛 코드는 특히 보존한다.

변경 기록과 확인 근거는 우선 PR 본문에 간결하게 남긴다.
작은 정리마다 별도 보고서·receipt·중복 상태 문서를 만들지 않는다.
