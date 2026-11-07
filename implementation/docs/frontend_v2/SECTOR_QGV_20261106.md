# 섹터 QGV 요소 선택·재계산 — 화면(2.2)과 Codex 공통 엔진 연결

작성 2026-11-06 Main, 개정 2026-11-07(오너 「섹터 QGV 실제 연결과 통합 마무리」).

**근거**
- 오너 지시 「섹터별 QGV 요소 선택·재계산 화면 구현」과 첨부 설계서
- Codex #505 `dc11144b`: `implementation/docs/research/sector_qgv/CONTRACT.md`, `catalog.json`, `presets.json`, `synthetic-input.json`, `synthetic-preview.json`, `synthetic-states.json`
- Codex #505 갱신 `aa9c4484`: `MAIN_INTEGRATION.md`, Main 전달 함수 `research/sector_qgv_main.run_preview_request`(`sector-qgv-main-request/1`). 연결기의 미리보기는 이 함수를 그대로 부른다

**범위**
- 병합·배포·신규 수집 승인이 아니다.
- 공식 게시본·순위·TARGET은 바뀌지 않는다.

## 1. 위치

| 기능 | 화면 |
| --- | --- |
| 2.2.1 축 가중치 · 2.2.2 내부 요인 가중치 · 2.2.3 프리셋 · 2.2.4 변경 영향 · 2.2.5 결측과 적용 비중 · 2.2.6 설정 관리 | 새 앱 `#/qgv` → 1.2 "가중치 · QGV 구성" |
| 2.2.7 요소 사전·검색·교체·추천 (추가, 명세 원칙대로 2.2 아래) | 같은 칸 |

- 새 메뉴·새 앱·새 기업 상세는 없다.
- 기업 상세(2.4)에서 들어오는 "QGV 구성 바꾸기" 링크는 아직 없다(후속).

## 2. 이번 개정에서 Codex 계약에 맞춘 것

| 구분 | 이전(#507 `cd2fd62e`, Main 임시) | 지금 |
| --- | --- | --- |
| 기본값 | Main이 설계서 §5를 옮긴 프리셋 15개(`tests/fixtures/sector_qgv_default_v0_1_0.json`) | **삭제.** 엔진 `preset()` 70개(10섹터 × 7회계모형)를 그대로 받는다. 시험이 70개 모두 `presets.json`과 같은지 본다 |
| 요소 ID | 설계서 ID 9개 + Main 임시 이름 | 엔진 `list_factors()`의 `factor_id`(설계 ID)·`variant_id` 51개 |
| 설정 규격 | `sector-qgv-user-config/1`(Main 제안) | `sector-qgv-config/1` 그대로. 바꾼 프리셋은 `scoped_overrides["SECTOR\|TEMPLATE"]`에 엔진 모양(`axis_weights`, `axes[axis][role]={weight, factors}`)으로 넣는다 |
| 결과 규격 | `sector-qgv-bundle/1`(Main 제안) + 화면 합산 | `sector-qgv-preview/1`과 `compare_previews` 결과를 그대로 읽는다. **화면 합산 삭제** |
| 저장 기록 | 화면이 만든 설정 | 엔진 `save_user_config()` 결과 `{config, canonical_config_hash, preview_id, snapshot_id, universe_id, universe_version}` |
| 관문 | `gate_policy=NONE`만 받음 | `official-q-percentile-required/1`. 엔진의 `gate_status`(PASS / VALUE_EXCLUDED / UNKNOWN)를 글자로 구분한다. 판정 불가는 최종 점수·순위가 없다 |
| 역할 이름 | Main 임시 | 엔진 역할 키(V는 `earnings`·`cash`·`other_value`)에 한국어 이름만 붙인다 |
| 합성 자료 | Main이 지은 기업 281개·점수 | **삭제.** Codex `synthetic-input.json`(SHA-256 고정)과 `synthetic-states.json`의 상태 변형만 쓴다 |

## 3. 실행 경로 (개발 환경)

```
화면 클릭 → IS2.data.engine(요청)  ─POST sector-qgv-engine (같은 출처)→  개발 사이트
   → tools/web_app_sector_qgv_engine.js (자식 프로세스 1개)
   → tools/sector_qgv_engine_bridge.py → investment_system.research.sector_qgv (Codex #505, 수정 없음)
```

- **요청·응답:** `sector-qgv-engine-request/1` / `sector-qgv-engine-response/1`. 한 줄 JSON이다.

| op | 엔진 호출 | 응답 |
| --- | --- | --- |
| `context` | `default_config`, 레지스트리 | 버전 4개, 기본 설정, 섹터·회계모형, 관문 정책·기준값(`GATE_PERCENTILE`), 합성 입력 목록 |
| `view` | `validate_config`, `preset`, `list_factors` | 이 범위의 프리셋·기본 프리셋·요소 51개(배지 근거: `is_default`, `recommendation`, `calculator_status`, `accounting_applicability`), 검증 결과 |
| `preview` | Codex `sector_qgv_main.run_preview_request` = `preview_qgv`(편집 설정·저장 또는 기본 설정 둘) + `compare_previews` + `save_user_config` | before·after 미리보기, 비교, 이 미리보기의 저장 기록 |
| `save` | `save_user_config` | 보관한 미리보기로 다시 확인한 저장 기록 |

- **화면이 하는 것:** 설정 편집뿐이다. 축·역할·요소 bp, 추가(같은 역할이면 그 역할 예산을 나눔)·빼기·교체, 적용 범위, 합계 표시를 한다. 합계의 최종 판단은 엔진 검증이다.
- **화면이 하지 않는 것:** 요소 점수, 비교집단 정규화, 엄격 결측, 관문, 총점, 순위, 커버리지, 비교, 저장 확인. 이 값은 모두 엔진 응답 그대로 보인다.
  - 시험이 화면 파일에 엔진 상수(변형 ID·모델 버전·`GATE_PERCENTILE`)와 순위·백분위 계산이 없음을 확인한다.
- **요청 순서:** 응답의 `request_id`(두 미리보기 모두)·`op`·버전 4개·저장 기록의 `preview_id`가 요청과 다르면 버린다. 설정·입력이 그 사이 바뀌었어도 버린다(`data-sq-dropped`).
- **거부된 미리보기:** 예를 들어 회사 ID가 중복되면 이전 성공 결과를 바꾸지 않는다.
- **저장:** 미리보기 응답에 함께 온 엔진 저장 기록을, 보이는 미리보기가 지금 설정·입력과 같을 때만 `저장` 클릭 안에서 이 기기에 쓴다. 클릭 안에서 다시 왕복하지 않는다.
- **열 때 요청 없음:** 페이지를 열 때 엔진 요청은 없다. `계산 엔진 연결`·범위 변경·`결과 미리보기`·`변경 취소`·`기본값 복원` 클릭 때만 나간다.
- **공개 사이트:** 엔진 경로가 없다. 404·405·501은 `ENGINE_NOT_CONNECTED`("계산 실행 경로 연결 전")로 보이고, 결과를 지어내지 않는다.
- **개발 실행:** `node implementation/tools/web_app_sector_qgv_dev.js` → 출력된 주소의 `#/qgv` → 1.2 `계산 엔진 연결`.

## 4. 공개·비공개 경계

- **입력은 합성뿐이다.** 연결기의 입력 이름은 고정 목록이다: `NORMAL`·`GATE_UNKNOWN`·`GATE_EXCLUDED`·`PARTIAL`·`STALE`·`MAPPING_UNKNOWN`·`PEER_SAMPLE_SMALL`·`EMPTY`·`FAILED`.
  - 모두 Codex `synthetic-input.json`(job의 SHA-256 확인, 모든 근거 `synthetic`)에서 Codex 상태표의 변경을 적용해 만든다.
  - 요청에는 경로·묶음·스냅숏 필드가 없다. 다른 이름은 `INPUT_UNKNOWN`이다.
- **비공개 실행은 만들지 않았다.** 비공개 입력(#505가 보존한 `investment-system1-raw` handoff)으로 돌리려면 다음이 필요하다. 이번 범위가 아니다.
  - 인증된 서버 실행 위치
  - 비공개 저장·응답 전달
  - 요청자 권한 확인
- 이 연결기는 권한 경계가 아니다. 개발 사이트와 시험에서만 돈다. 배포하지 않는다.
- 요청에는 가격·보유·기기 저장값이 없다. 응답은 `data_kind: SYNTHETIC`이다.
- `CSP connect-src 'self'`로 충분하다. 보안 정책은 바꾸지 않았다.

## 5. 화면 동작

- **흐름:**
  1. 섹터(책 10섹터)·회계모형(7)을 고른다.
  2. Q/G/V 비중을 정한다.
  3. 역할별 요소를 교체·추가·빼기 한다(PER·PBR·별칭 검색).
  4. 고급 모드에서 역할·요소 비중을 바꾼다.
  5. 결과 미리보기(엔진 재계산) → 내 설정으로 저장 / 변경 취소 / 기본값 복원
- **배지(글자):**
  - 기본값 · 초기 설정
  - 추천(이유·근거 수준·출처·검토일)
  - 선택됨(지금 편집)
  - 계산 기능 준비 중(선택 불가)
  - 산식 적용 부적합(선택 불가)
  - 자료 일부 부족 n/N: 마지막 미리보기 커버리지 기준, 선택 가능
- **미리보기에 보이는 것(엔진 값):**
  - 엔진 버전, 설정 해시, 기준일, 스냅숏, 입력
  - 총점 산출 전 → 후(원래 모집단), 축별·세 축 산출, 전후 공통·새로·잃은 수, 미산출 사유
  - 실효비중
  - 행마다 상태, 관문, Q·G·V·총점 전 → 후, 순위 전 → 후, 공통 순위 전 → 후
  - "이 섹터·회계모형만 보기" 필터는 순위를 다시 매기지 않는다.
- **결측:** 미산출은 0이 아니다. "미산출 · 요소 이름 + 엔진 상태"(예: "PBR / 보통주 B/P 자료 없음") 또는 "최종 점수 없음 · 상태"로 보인다.
- **관문:**

| 엔진 `gate_status` | 화면 |
| --- | --- |
| PASS | 관문 통과 |
| VALUE_EXCLUDED | 관문: 가치(V) 제외 · 남은 축 비례 재배분 · 적용 Q x% · G y% (엔진 `post_gate_axis_weights`) |
| UNKNOWN | 관문 판정 불가 · 최종 점수·순위 없음 |

- **저장 위치:**
  - 이 기기(브라우저)뿐이다. 키는 `investment.web.v2.sector-qgv-user-config`이고 엔진 저장 기록 모양이다.
  - 동기화가 없고 백업 파일에 들어가지 않는다.
  - 저장 기록의 기준(`base_preset_id`)이 지금 엔진 기본값과 다르면 알리고 덮어쓰지 않는다.
  - 읽을 수 없는 값은 사용자가 지울 때까지 그대로 둔다.

## 6. 지금 연결 상태

| 항목 | 상태 |
| --- | --- |
| 화면 → 엔진 재계산 → 판독 → 전후 → 저장·복원 | 개발 환경에서 끝까지 연결. 합성 입력으로 검증 |
| 실자료(비공개) 실행 | 연결 안 함. 인증 서버·비공개 전달이 필요(Main), 날짜가 있는 책 섹터·회계모형 분류 근거와 관문 원천 연결이 필요(Codex 판정, Main은 보유 자료 위치 인계) |
| 배포 | 안 함. 공개 사이트에는 엔진 경로가 없음 |
| 공식 QGV·TARGET | 바뀌지 않음 |

## 7. 시험

| 시험 | 범위 |
| --- | --- |
| `tests/test_sector_qgv_bridge.py` | 응답 = 엔진 함수 결과(context·view·preview·compare·save); 70개 프리셋 = `presets.json`; Codex `synthetic-preview.json` 재현; 상태 변형이 `synthetic-states.json` 기대값과 같음(6 + FAILED); 관문 세 결과·판정 불가 null; 저장은 같은 설정의 보관 미리보기만; 합성 전용·고정 코드; stdio 순서·stderr 없음 |
| `tools/web_app_sector_qgv_node_test.js` (11) | 실제 연결기 프로세스로: 기본값은 엔진 것뿐(화면 파일에 상수·순위 계산 없음); 배지 근거; 편집(역할 예산 분할·빼기·교체·준비 중·부적합 거부); 엔진 검증 코드; 은행 변경이 번지지 않음·전체 적용 명시 복사; 재계산 = 엔진 호출(점수·순위 변화); 관문 세 결과; 상태; 다른 요청 응답 거부; 저장 기록; 표시 설정은 숫자를 바꾸지 않음 |
| `tools/web_app_sector_qgv_browser_test.js` (1440·390, 18) | 열 때 요청 없음; 연결(context·view); 배지 글자·검색·교체; 미리보기 한 번 = 엔진 호출 한 번(PBR은 합성 자료에 없어 V 0/20 엄격 결측, EV/EBITDA는 20/20); 화면 순위 = 엔진 직접 호출 순위; 저장·새로고침 유지; 바뀐 설정은 이전 미리보기 숨김·저장 막음; 취소·복원; 은행만 저장; 관문 세 결과; 거부 입력은 이전 결과 유지; 늦은 응답 버림; 휴대폰 넘침 없음·44 px; 경계(외부 요청 없음, 엔진 경로는 POST만, 저장 키 하나, 콘솔 오류 0, CSP 0); 엔진 경로 없는 사이트 = 연결 전 |
