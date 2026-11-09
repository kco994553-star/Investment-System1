# 섹터 QGV 요소 선택·재계산 — 화면(2.2)과 Codex 공통 엔진 연결

작성 2026-11-06 Main, 개정 2026-11-07(오너 「섹터 QGV 실제 연결과 통합 마무리」, 「#505 실자료 부분 비교 계약 추가 인수」, 2.2.7 「섹터 QGV 설정(요소·가중치)」 지시).

**근거**
- 오너 지시 「섹터별 QGV 요소 선택·재계산 화면 구현」과 첨부 설계서
- Codex #505 `dc11144b`: `implementation/docs/research/sector_qgv/CONTRACT.md`, `catalog.json`, `presets.json`, `synthetic-input.json`, `synthetic-preview.json`, `synthetic-states.json`
- Codex #505 갱신 `aa9c4484`: `MAIN_INTEGRATION.md`, Main 전달 함수 `research/sector_qgv_main.run_preview_request`(`sector-qgv-main-request/1`). 연결기의 미리보기는 이 함수를 그대로 부른다
- Codex #505 갱신 `802752549def4bba34d8743a3b983e0bcfda8966`(`3a555f7b` V 재개 + `80275254` EV 단위·회계 범위): `V_RESUME.md`, `research/sector_qgv_v.py`, `v-synthetic-{pack,market,job,expected}.json`, `tests/test_sector_qgv_v.py`
- Codex #505 갱신 `7c2225a382aedf275749eb5c2f9f2385db7cdcf3`: `PARTIAL_COMPARISON.md`, `research/sector_qgv_partial.compare_axes`(`sector-qgv-axis-comparison/1`), `partial-synthetic-{snapshot,config,comparison}.json`
- Codex #514 `8a483471d02f7a9cfc0294117722cc01a32abbab`(기반 #505 `e3df0c1e`): `SAVED_SETTINGS_COMPATIBILITY.md`, `research/sector_qgv_restore.replay_saved_config`. 이 가지에 그대로 병합했다(Codex 파일 바이트 동일)

**범위**
- 병합·배포·신규 수집 승인이 아니다.
- 공식 게시본·순위·TARGET은 바뀌지 않는다.

## 1. 위치

| 기능 | 화면 |
| --- | --- |
| 2.2.1 축 가중치 · 2.2.2 내부 요인 가중치 · 2.2.3 프리셋 · 2.2.4 변경 영향 · 2.2.5 결측과 적용 비중 · 2.2.6 설정 관리 | 새 앱 `#/qgv` → 1.2 "가중치 · QGV 구성" |
| 2.2.7 **섹터 QGV 설정(요소·가중치)** (추가, 명세 원칙대로 2.2 아래. 요소 사전·검색·교체·추천과 섹터별 비중 설정을 포함) | 같은 칸. 칸 본문 첫 줄 제목이 "2.2.7 섹터 QGV 설정(요소·가중치)"이다 |

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
| `replay` | Codex #514 `replay_saved_config`(저장 기록 + 보관한 원래 미리보기 + 그 미리보기의 원래 스냅숏) | 새 요청 ID의 미리보기. 엔진이 요청 ID 외 모든 버전·해시·결과가 같다고 확인했을 때만 성공. 아니면 엔진 거부 코드. 연결기가 원래 미리보기를 갖고 있지 않으면 `RETAINED_INPUT_NOT_FOUND` |

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

- **기본 흐름(오너 2026-11-07): ① 10섹터 기본값 → ② 내 설정.**
  - ① 10섹터 기본값: 고른 섹터·회계모형의 엔진 기준 프리셋이다. 화면에 ID·버전을 보인다(예: `sector-qgv-default/0.1.0 v0.1.0`). 값은 엔진 `view`의 `default_preset`이다.
  - ② 내 설정: 이 범위를 바꾸거나 저장한 설정이다. 저장 기록은 기준(`base_preset_id`)을 그대로 적는다. 새 프리셋 ID를 만들지 않는다.
  - 공격형·균형형·수비형은 이 흐름의 단계가 아니다. 이 기기에 옛 리더보드 가중치 트리(`investment.web.v1.profile-drafts-v2`, `device-profile-drafts/2`)가 있으면 "이전 설정 호환"으로 목록만 보인다. 읽기만 하고 고치지 않는다.
  - 1.1.6 "이전 설정 결과(미리보기 · 호환)"도 같은 트리를 읽는다. 지금 자료로 계산한 값이다. 과거 결과 재현이 아니다(트리에 출발 프리셋·계산 버전이 없다, Codex #514).
  - 옛 화면(`web_assets`)의 공격형·균형형·수비형 편집기와 `user-preset/*@0.1` 숫자는 그대로다.
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
| VALUE_EXCLUDED | 관문: V 총점 반영 제외 · 남은 축 비례 재배분 · 기업 탈락·자료 미수집 아님 · 적용 Q x% · G y% (엔진 `post_gate_axis_weights`) |
| UNKNOWN | 관문 판정 불가 · 최종 점수·순위 없음 |

- **저장 위치:**
  - 이 기기(브라우저)뿐이다. 키는 `investment.web.v2.sector-qgv-user-config`이고 엔진 저장 기록 모양이다.
  - 동기화가 없고 백업 파일에 들어가지 않는다.
  - 저장 기록의 기준(`base_preset_id`)이 지금 엔진 기본값과 다르면 알리고 덮어쓰지 않는다.
  - 기본값 복원은 이 범위의 덮어쓰기만 지운다. 다시 받은 프리셋이 엔진 `default_preset`과 ID·버전·숫자까지 같은지 확인한다. 다르면 "기본값 복원 확인 실패"로 보인다. 다른 범위의 내 설정은 그대로다.
  - 읽을 수 없는 값은 사용자가 지울 때까지 그대로 둔다.

## 5.4 2.2.7 섹터 QGV 설정(요소·가중치) — 식별자·두 실행·작은 표본 (오너 2026-11-07)

**원본 참조와 내 설정**

| 표시 | 값 | 출처 |
| --- | --- | --- |
| 원본 참조 | `sector-qgv-default/0.1.0 v0.1.0` · 섹터·회계모형 · "기본값 · 바꾸지 않음" | 엔진 `view.default_preset`의 `preset_id`·`version`(`IS2.sectorQgv.base`). 저장 기록의 `config.base_preset_id`와 각 `scoped_overrides[...]`의 `preset_id`·`version`도 같은 값이다(편집은 비중만 바꾼다) |
| 내 설정 | 설정 ID `device` · `sector-qgv-config/1` · 설정 해시 12자 · "(설정 버전 필드 없음 · 해시로 식별)" · 적용 범위 n곳(예: 정보기술·일반, 금융·은행) | 저장 기록(#514와 같은 6키)의 `config.config_id`, `config.schema_version`, `canonical_config_hash`, `config.scoped_overrides`의 키 |

- 저장 전에는 "내 설정 · 저장 전"으로만 보인다.
- `config_id`는 해시에 들어가지 않는다(엔진 `config_hash`가 `config_id`·`owner_scope`·`display_preferences`를 뺀다). 설정이 같은지는 해시로 본다.
- **Codex 요청(공백):** `sector-qgv-config/1`에는 사용자 설정의 버전 필드가 없다. Main은 지어내지 않고 해시를 식별자로 쓴다. 기록에 `config_version`이 생기면 그대로 보인다. 섹터 최소 표본(20)도 응답에 필드가 없고 `normalization_version` 이름(`strict20`)에만 있다.

**두 실행 (저장된 내 설정)**

| 버튼 | 하는 일 | 화면 상태 |
| --- | --- | --- |
| 최신 입력에 설정 적용 | 저장된 `config`로 지금 고른 입력에 `preview`(기본값 → 내 설정) | `APPLIED_LATEST`: "최신 입력에 설정 적용 · 새 결과 · … 과거 결과 재현 아님 · 저장 기록은 그대로". 이 응답의 새 저장 기록은 쓰지 않는다 |
| 과거 입력으로 결과 재현 | 저장 기록 그대로 `replay`(Codex #514) | `REPRODUCED`: 엔진이 같음을 확인했을 때만. 원래 미리보기 → 재실행 ID, 설정·스냅숏·기준일·입력 해시·엔진·모델과 행 |
| | 엔진 거부 | `REFUSED`: "재현 거부 · 글자 · 엔진 코드 CODE"(예: `SAVED_PREVIEW_MISMATCH`, `REFERENCE_PREVIEW_IDENTITY_MISMATCH`, `SAVED_REPLAY_CONTEXT_OR_RESULT_MISMATCH`) |
| | 원래 미리보기·스냅숏이 이 경로에 없음 | `INPUT_MISSING`: "재현 입력(원래 preview·snapshot) 연결 전 … (RETAINED_INPUT_NOT_FOUND)" |
| | 재현 경로 없음(`OP_UNKNOWN`·연결 실패) | `NOT_CONNECTED`: "재현 입력(원래 preview·snapshot) 연결 전 · 재현 실행 경로 없음" |

- 어떤 실패에서도 최신 입력으로 바꿔 계산해 재현이라고 보이지 않는다.
- 개발 연결기는 미리보기마다 그 미리보기와 계산에 쓴 스냅숏을 프로세스 메모리에 최근 32개 보관한다. 디스크에 쓰지 않는다. 새로고침 뒤에도 연결기 프로세스가 같으면 재현된다. 연결기를 다시 시작하면 `INPUT_MISSING`이다.
- 실서비스의 원래 미리보기·스냅숏 보관(비공개 저장, 인증 서버)은 Main 미구현이다(§6 ③과 같은 조건).

**자동 덮어쓰기 없음**
- 읽을 때 저장 기록을 바꾸지 않는다(`IS2.sectorQgv.readSaved`). 마이그레이션이 없다.
- 새 엔진 기본값이면 `BASE_DIFFERS`로 알리고 그대로 둔다.
- 기본값 복원은 편집 중 설정의 그 범위만 바꾼다. 저장 기록 바이트는 `저장`을 누를 때까지 그대로다(node·브라우저 시험이 바이트를 비교한다).
- 쓰는 곳은 `저장` 클릭 하나뿐이다. 기존 6키 기록은 계속 통과한다.

**작은 표본 (유효 비교 기업 N<20, 엔진 `sector-midrank-strict20/1`)**
- 엔진은 요소 점수를 만들지 않는다(`score: null`, `score_status: PEER_SAMPLE_SMALL`, `valid_n`).
- 화면 글자는 "요소 점수 미산출 · 유효 비교 기업 N<20 (N=19)"이다(`IS2.sectorQgv.rowState`·`factorText`).
- 행 상태가 엔진의 `STRICT_INCOMPLETE`여도, 빠진 요소가 모두 `PEER_SAMPLE_SMALL`이면 "필수 요소 결측"이라고 쓰지 않는다. 섞이면 둘 다 쓴다.
- 관문 판정 불가·결측(자료 없음)·분류 미확정과 다른 글자다. 0점·순위로 보이지 않는다(총점 "최종 점수 없음", 순위 "없음").

## 5.5 Q/G 부분 비교 (`sector-qgv-axis-comparison/1`)

**실제 호출 연결**
- 미리보기 응답에 Codex `compare_axes(전 미리보기, 후 미리보기, 전 설정, 후 설정, request_id)`를 붙인다(`axis`). 연결기는 다시 조합하지 않고, 화면은 `comparison_id = request_id`와 양쪽 `config_hash`가 그 미리보기와 같은지 확인한다.
- `comparisons`·`comparison`(둘 다 클릭 때만): 비교 파일 목록과 이름으로 한 개.
  - 목록은 Codex 합성 D1(`partial-synthetic-comparison.json`, SHA-256 `18f3d0ef…`)과 Main 합성 I1이다.
  - Main 합성 I1은 Codex `compare_axes(input_treatment=True)` 출력이고 `tools/sector_qgv_axis_main_variants.py`로 만든다. pytest가 바이트 일치를 확인한다.
  - 비공개 실파일은 **개발 프로세스를 `SECTOR_QGV_PRIVATE_COMPARISONS`로 시작했을 때만** 목록에 들어간다. 조건은 절대 경로, Git 밖, mode 600, 8 MiB 이하, 같은 규격이다. 요청은 경로를 쓸 수 없고 목록의 이름만 쓴다.

**화면 표시** (`sector-qgv-axis.js` 판독기, `screen-sector-qgv-axis-live.js`)
- Q와 G를 따로 보인다.
  - 행마다: 전 → 후(차이), 전환(전후 모두 산출 / 새로 산출 / 빠짐 / 전후 모두 미산출), 미산출 사유, 변경 원인
  - 축마다: 전 산출 · 후 산출 · 공통 · 새로 · 빠짐 · 둘 다 없음 · 공통 중 바뀜 / 전체
- 총점 공통 산출이 0건이어도 Q/G 행을 숨기지 않는다. V·총점은 "산출 없음"으로만 보이고 0점으로 쓰지 않는다.
- 원인 구분:
  - D1(`SAME_INPUT_CONFIGURATION`) = "요소·비중 변경(같은 입력·분류)"
  - I1(`INPUT_CLASSIFICATION`) = "분류 보완·비교집단 확대(설정은 같음)". "상대점수 변화는 … 기업 실적이 좋아지거나 나빠졌다는 뜻이 아님"을 함께 보인다. 원인 `PEER_RESCORING`은 "비교집단 변화로 상대점수 재계산(실적 변화 아님)"으로 쓴다.
- 양쪽의 설정·입력·스냅숏·입력 버전·엔진·모델·정규화·분류 버전을 표로 보이고 다른 칸을 표시한다.
- 판독기는 D1과 I1이 섞이면 거부한다(`TREATMENT_MIXED`).
  - D1인데 입력·스냅숏·분류가 다르거나 원인이 재평가인 경우
  - I1인데 설정이 다르거나 원인이 요소 비중인 경우
- 행은 엔진 순서(회사 ID) 그대로 보인다.
  - 화면은 축별 순위·총점·시장 순위·성과를 만들지 않는다(정렬 없음).
  - 필터는 보이는 행만 고르고 개수와 비교집단을 바꾸지 않는다.
  - 50행씩 보이고, 요소 상세는 행을 열 때 그린다.

**실자료 (비공개, 개발 환경)**
- 보관: 비공개 저장소 `handoffs/sector-qgv-followup-20261107`, commit `0a628d52`. manifest·묶음 SHA-256은 #437 Codex 댓글과 같다.
- `settings-comparison/axis-comparison.json`(D1)과 `classification-result/axis-comparison.json`(I1)을 `tools/web_app_sector_qgv_private.js check`로 1440·390에서 확인했다(6개 통과).
  - D1: Q 공통 206 중 49 변경, G 280 불변
  - I1: Q 206→213(새로 7, 공통 중 바뀜 125), G 280→293(새로 13, 공통 중 바뀜 173), 분류 바뀐 행 14
  - 두 비교 모두 총점·V 산출 0건이지만 Q/G 행은 504행 모두 보인다.
- 출력은 PASS와 개수뿐이다. 저장소·Pages·로그에 넣지 않았다.

## 6. 지금 연결 상태 (세 상태를 따로 적는다, 2026-11-07 3차)

| 상태 | 지금 | 근거 |
| --- | --- | --- |
| ① 합성 입력의 실제 엔진 재계산 | **연결됨** (개발 환경) | 화면 → 공통 엔진 `run_preview_request` → 판독 → 전후 → Q/G 부분 비교 → 저장·복원. 입력 10종(상태 변형 9 + `V_RESUMED`) 모두 합성 |
| ② 비공개 실자료 비교 파일의 개발 화면 표시 | **확인됨** (개발 환경, CI 밖) | 비공개 D1·I1 `axis-comparison.json`을 `SECTOR_QGV_PRIVATE_COMPARISONS`로 시작한 개발 서버에서만 표시. 재계산이 아니라 Codex가 만든 결과 파일을 그대로 읽음 |
| ③ 인증된 경로에서의 비공개 실자료 재계산 | **미연결** | 인증 서버·비공개 전달(Main)이 없음. 연결기는 합성 입력 이름만 받고 경로·묶음 필드가 없음 |

- **③에 필요한 승인·입력:**
  - 인증 서버 배포와 Secret(로그인·세션 키)
  - 비공개 저장소에서 서버로 전달하는 경로
  - Codex의 실 V 재개 입력: 가격 전달 묶음과 근거 파일(`V_RESUME.md`의 `market_inputs`·`market_evidence`)
  - 날짜 있는 분류 근거
- **이미 구현·검증한 준비:**
  - 연결기의 요청 규격·응답 검사·늦은 응답 버림
  - 비공개 파일 수용 조건(절대 경로·Git 밖·mode 600·크기·규격)
  - 합성 V 재개 입력으로 같은 미리보기 경로 확인

| 항목 | 상태 |
| --- | --- |
| 배포 | 안 함. 공개 사이트에는 엔진 경로가 없음 |
| 공식 QGV·TARGET | 바뀌지 않음 |

### 6.1 V 재개 (#505 `3a555f7b`·`80275254`, `sector-qgv-v-resume/1`)

- Codex CLI의 `v-prepare`·`v-resume`은 오프라인 생산 쪽이다. 화면 계약(`sector-qgv-preview/1`·저장)은 바뀌지 않는다.
- 연결기는 합성 입력 `V_RESUMED` 하나를 더했다.
  - 고정 SHA-256의 `v-synthetic-pack.json`·`v-synthetic-market.json`을 Codex `research.sector_qgv_v.resume`에 넣어 만든 스냅숏이다. 연결기는 값을 채우지 않는다.
  - 같은 미리보기 호출로 V가 20/20 산출된다(시험 확인).
- 실 V는 0건이다(Codex 보고: 비가격 결손 1,053행·365사, 가격만으로 준비된 행 0).
  - 이것은 0점이 아니라 미산출이다.
  - 화면에 실 V 결과는 없다.
- **금융과 섹터 V는 따로 관리한다.**
  - 11/02 금융 11코드 가격 취득(#502·#504 쪽)과 11/04 섹터 504 V(이 쪽)는 별도 전달이다.
  - 금융 가격 취득이 섹터 V의 비가격 결손(CFO·capex·D&A·EPS 구성·자본 구성 근거 등)을 해소한다고 표시하지 않는다.
  - 기준일이 다르면 Codex 검증에서 거부된다.
  - 금융 의존성 #508 → #504는 이 섹터 통합과 별도 순서다.

## 7. 시험

| 시험 | 범위 |
| --- | --- |
| `tests/test_sector_qgv_bridge.py` | 응답 = 엔진 함수 결과(context·view·preview·compare·save); 70개 프리셋 = `presets.json`; Codex `synthetic-preview.json` 재현; 상태 변형이 `synthetic-states.json` 기대값과 같음(6 + FAILED); 관문 세 결과·판정 불가 null; 저장은 같은 설정의 보관 미리보기만; 합성 전용·고정 코드; stdio 순서·stderr 없음; `replay` = Codex `replay_saved_config`(보관 미리보기·원래 스냅숏, 결과 행 동일, 바뀐 기록 거부, 없는 미리보기·새 프로세스 `RETAINED_INPUT_NOT_FOUND`) |
| `tools/web_app_sector_qgv_node_test.js` (20) | 실제 연결기 프로세스로: 기본값은 엔진 것뿐(화면 파일에 상수·순위 계산 없음); 배지 근거; 편집(역할 예산 분할·빼기·교체·준비 중·부적합 거부); 엔진 검증 코드; 은행 변경이 번지지 않음·전체 적용 명시 복사; 재계산 = 엔진 호출(점수·순위 변화); 관문 세 결과; 상태; 다른 요청 응답 거부; 저장 기록; 표시 설정은 숫자를 바꾸지 않음; 기본 흐름 10섹터 기본값 → 내 설정(70개 범위의 기준 ID·버전); 복원 = 기준 프리셋 ID/버전; 프리셋 ID 재사용 없음(저장 뒤 70개 기준 = `presets.json`, `user-preset/*@0.1` 숫자 그대로); 옛 트리 = 이전 설정 호환; 2.2.7 이름(화면·문서); 원본 참조 vs 내 설정 식별자(설정 버전 없음); 최신 입력 적용 vs 과거 입력 재현(#514 재실행 = 원래 결과 행, 거부 코드·재현 입력 연결 전); 저장 바이트 불변; N<20 미산출 글자 |
| `tests/test_sector_qgv_v.py` (Codex) | V 재개. build `pytest tests`에 수집됨 |
| `tests/test_sector_qgv_partial.py` (Codex, 4) | 부분 비교 생성 쪽. build `pytest tests`에 수집됨(4개 확인) |
| `tools/web_app_sector_qgv_axis_node_test.js` (5) | Codex 합성 D1 고정; Main 합성 I1; 실제 엔진 미리보기에 붙은 비교; D1/I1 섞임·개수·null 사유·순위/성과 없음 거부; 판독기·화면에 정렬·순위·저장 없음 |
| `tools/web_app_sector_qgv_axis_browser_test.js` (1440·390·320, 12) | 미리보기 한 번 = 엔진 호출 한 번에 비교 포함; 파일 목록(클릭, 비공개 없음); D1 총점 공통 0인데 Q/G 20행; I1 원인 글자·버전 차이·분류 바뀐 행·요소 상세; 필터는 행만; 넘침 없음·44 px·키보드; 경계 |
| `tools/web_app_sector_qgv_private.js check` (CI 밖) | 비공개 D1·I1이 파일 그대로 보이는지 |
| `tools/web_app_sector_qgv_browser_test.js` (1440·390, 21) | 열 때 요청 없음; 연결(context·view); 배지 글자·검색·교체; 미리보기 한 번 = 엔진 호출 한 번(PBR은 합성 자료에 없어 V 0/20 엄격 결측, EV/EBITDA는 20/20); 화면 순위 = 엔진 직접 호출 순위; 저장·새로고침 유지; 바뀐 설정은 이전 미리보기 숨김·저장 막음; 취소·복원; 은행만 저장; 관문 세 결과; 거부 입력은 이전 결과 유지; 늦은 응답 버림; 휴대폰 넘침 없음·44 px; 경계(외부 요청 없음, 엔진 경로는 POST만, 저장 키 하나, 콘솔 오류 0, CSP 0); 엔진 경로 없는 사이트 = 연결 전; 흐름 ① 10섹터 기본값 → ② 내 설정, 공격형·균형형·수비형 안 보임, 복원 문구에 기준 ID·버전; 옛 트리가 있는 기기 = 이전 설정 호환 목록·1.1.6 미리보기 그대로·저장값 불변; 2.2.7 제목, 원본 참조·내 설정 글자, N<20 행(순위 없음·0 없음), 재현 = `replay` 한 번(재현됨), 최신 입력 적용 = `preview` 한 번(새 결과 글자), 연결기에 없는 기록 = 재현 입력 연결 전, 불러오기·복원 뒤 저장 바이트 불변 |

## 8. 금융 의존성과 통합 순서 (2026-11-07)

- #504(Codex 금융 변환기) `41075615cca715e94396bcde56594f8159f333ee`는 Main #508 `df1a9abb`의 순수 도우미 `providers/iex_values`를 import한다. #508의 정확한 patch를 그대로 포함한다.
- 그래서 **#508 → #504** 순서로 병합해야 한다. 가드 문제는 #508로 이미 해결했고 다시 조사하지 않는다.
- 섹터 QGV 통합 #510(#506+#507+#505)과 #504·#508은 서로 선행 조건이 아니다.
- 실금융 11 가격(11/02)은 11/04 섹터 자료와 합치지 않는다(Codex 문서 그대로).
