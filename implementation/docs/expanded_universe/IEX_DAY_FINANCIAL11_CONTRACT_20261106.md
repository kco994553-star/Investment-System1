# IEX 2026-11-02 금융 11코드 파생 파일·manifest 계약 (Codex 인계용)

작성 2026-11-06 Main. 오너 11/06 3차 지시 2항("실제 가격 수집 완료를 기다리지 말고 계약부터 인계").

**목적:** Codex가 #499 입력(`financial-v-price-input/1`) 변환을 실제 취득 전에 구현할 수 있게, #502 도구가 쓰는 두 파일의 필드·단위·상태 의미와 합성 예시를 넘긴다.

**범위:**
- 이 문서는 취득·병합·배포 승인이 아니다. 금융 11코드는 조건부 계산 대상이며 채택 수가 아니다.
- 변환(CIK, 분자별 `share_basis`, 기준 증거 연결)은 Codex 담당이다. 이 도구는 원천 형태만 만든다.

## 1. 기준과 예시 위치

| 항목 | 값 |
| --- | --- |
| 기준 코드 | #502 가지 `claude/iex-20261102-preserve-prep`. 이 문서를 더한 커밋의 전체 SHA는 #437 인계 댓글과 PR 본문에 적는다 |
| 도구 | `implementation/tools/iex_day_preserve_once.py` (`SCHEMA = iex-day-preserve-once/2`, `DERIVED_SCHEMA = iex-day-financial11-last-trade/1`) |
| 합성 예시 | `implementation/tests/fixtures/iex_day_financial11_examples_v1.json` — `derived_complete` · `manifest_complete` · `manifest_failed_md5` |
| 예시가 도구와 같다는 시험 | `tests/test_iex_day_preserve_once.py::test_synthetic_examples_match_the_tool` |

**합성 예시가 만들어진 방법**
- 도구의 `run()`을 합성 TOPS 파일·가짜 저장소·고정 시계(2026-11-07T01:00:00Z부터 1초씩)로 돌린 출력 그대로다.
- 다른 예시를 손으로 쓰지 않았다. 시험이 예시를 다시 만들어 비교하므로, 도구와 예시가 어긋나면 시험이 실패한다.
  - gzip 바이트의 해시·크기는 zlib 판에 따라 달라질 수 있어 느슨하게 비교한다.
  - 실패 예시의 업로드 수는 배경 업로더 시간에 따라 다르다. 그래서 "모두 이번 실행 것이고 삭제됨, 원천 GET 3"만 비교한다.
- **합성 표시:** 코드는 모두 지어낸 `NYSE:QZP*`(실제 티커 없음), 가격도 지어낸 값이다.
- `VARIES:*`는 기계·커밋마다 달라지는 값이다: 컴파일 결과 해시, git commit, 측정 초, 종료 코드 목록, 여유 바이트.
- `input.commit`(`fc88bf41…`)은 실제 비공개 입력 커밋 상수다. `input.file_sha256`은 합성 입력의 해시라 실제와 다르다.

## 2. 파생 파일 `iex-day-financial11-last-trade/1`

비공개 release `current-iex-20261102`에 `iex-20261102-financial11-last-trade-r<run>a<attempt>.json`으로 올린다. 공개 위치에는 두지 않는다.

### 2.1 머리 필드

| 필드 | 형식·단위 | 뜻 |
| --- | --- | --- |
| `schema_version` | `iex-day-financial11-last-trade/1` | |
| `basis_date` | `2026-11-02` | 거래일. 다른 날짜로 채우지 않음 |
| `source` | `IEX_HIST TOPS 1.6 last regular-session trade` | |
| `basis_kind` | `IEX_LAST_REGULAR_SESSION_TRADE` | 종가가 아니라 정규장 마지막 체결 |
| `currency` / `unit` | `USD` / `USD/share` | |
| `adjustment_basis` | `AS_TRADED` | 원 체결가. 분할·배당 조정 없음 |
| `attribution` | IEX 문구 | |
| `acquired_at_utc` | UTC 초 `…Z` | **실제 취득 완료 시각** = 본체를 끝까지 받고 크기·md5·gzip·파서 확인이 모두 끝난 순간. manifest `received.completed_at_utc`와 같다. 작업 종료 시각이 아니다 |
| `generated_at_utc` | UTC 초 | 이 파생 파일을 만든 시각(결과 생성) |
| `manifest` · `release_tag` | 이름 | 짝 manifest |
| `original` | `{sha256, md5, bytes}` | 원본 전체(조각을 이은 것)의 해시·크기 |
| `input` | `{commit, path, file_sha256, row_indexes}` | 11코드를 읽은 비공개 입력 |
| `session_window_ns` | `[t0, t1)` ns | 2026-11-02 14:30:00Z ~ 21:00:00Z(반열림) |
| `parser_source_sha256` · `parser_git_commit` | | 파서 C 원본 해시와 실행 커밋 |
| `states` | 상태별 수 | 합은 11 |
| `rows` | 11행 | 입력의 `row_indexes` 순서 |

### 2.2 행 필드

| 필드 | 형식 | 뜻 |
| --- | --- | --- |
| `row_index` | 정수 | 비공개 입력 행 번호 |
| `code` | `NYSE:…` | Universe504 코드 |
| `iex_symbol` | 문자열 \| null | 기준일 별칭표로 바꾼 IEX 기호. null = 별칭표상 기준일에 기호 없음 |
| `parser_status` | `ROUND` \| `ODD_ONLY` \| `NO_TRADE` \| null | 파서 원 상태(null = 기호가 없어 파서에 넣지 않음) |
| `state` | 4종(2.3) | |
| `reason` | 코드(2.3) | 늘 있음 |
| `price` | 십진 문자열 `"123.4500"` \| null | **USD/share, 소수 넷째 자리까지 TOPS 정수 그대로.** 반올림·float 없음. PRICE일 때만 |
| `last_trade_ns` | 정수 ns \| null | 체결 시각(가격 체결 시각) |
| `last_trade_utc` | `…T14:32:00.000000000Z` \| null | 같은 시각, 아홉 자리 그대로 |
| `basis_date` · `source` · `parser_source_sha256` | | 머리와 같은 값 |

### 2.3 상태와 사유

| state | reason | 뜻 | 가격·시각 |
| --- | --- | --- | --- |
| `PRICE` | `REGULAR_SESSION_ROUND_LOT_LAST_TRADE` | 정규장 창 안의 마지막 라운드랏 체결(장외·단주 제외, 체결 취소 반영) | 있음 |
| `NO_TRADE` | `ODD_LOT_ONLY` | 단주 체결만 있음 | null |
| `NO_TRADE` | `NO_REGULAR_SESSION_ROUND_LOT_TRADE` | 기호는 있으나 정규장 라운드랏 체결 없음 | null |
| `NOT_IN_FILE` | `SYMBOL_NOT_IN_FILE` | 그날 파일에 기호 자체가 없음 | null |
| `NOT_IN_FILE` | `IEX_SYMBOL_NONE_FROM_ALIAS_DATE` | 별칭표상 기준일에 IEX 기호 없음 | null |
| `PRICE_INVALID` | `PRICE_OUT_OF_RANGE` | 0 이하 또는 상한 이상 | null |
| `PRICE_INVALID` | `TIMESTAMP_OUTSIDE_SESSION` | 체결 시각이 창 밖(방어) | null |
| `PRICE_INVALID` | `IEX_SYMBOL_INVALID` | 기호 형식 오류 | null |

- 합성 예시에는 위 상태 4종이 모두 있다(PRICE 3 · NO_TRADE 3 · NOT_IN_FILE 3 · PRICE_INVALID 2).
- `IEX_SYMBOL_NONE_FROM_ALIAS_DATE`는 실제 별칭 행(13·30)에서만 생겨 예시에는 없다. 도구 시험(`test_derived_rows_and_times`)이 다룬다.

## 3. manifest `iex-day-preserve-once/2`

이름은 `manifest-r<run>a<attempt>.json`이다. 실행마다 하나이고, 성공하면 맨 마지막에 올린다.

### 3.1 시각 (서로 다른 필드)

| 시각 | 필드 | 언제 채움 |
| --- | --- | --- |
| 가격 체결 시각 | 파생 `rows[].last_trade_ns`/`_utc` | 파서 결과 |
| 본체 수신 시작 | `received.started_at_utc` | 본체 GET 직전 |
| **실제 취득 완료** | `received.completed_at_utc` = 파생 `acquired_at_utc` | 스트림이 크기·md5·gzip·파서 확인을 통과한 직후 |
| 조각 보존 완료 | `chunks_preserved_at_utc` | 모든 조각 업로드·되받기 검증 뒤 |
| 재결합 검증 완료 | `reassembly.verified_at_utc` | 스트리밍 재결합 검증 뒤 |
| 결과 생성 | 파생 `generated_at_utc` | 파생 파일을 만들 때 |
| manifest 작성 | `written_at_utc` | 마지막 |

- **취득 전에는 완료 시각이 없다.**
  - 코드에 미리 채운 값이 없다. 시각은 해당 단계가 실제로 끝났을 때만 `now()`로 넣는다.
  - 수신을 끝내지 못한 실패 manifest에는 `received.completed_at_utc`도 `acquired_at_utc`도 없다. 예시 `manifest_failed_md5`가 그렇다(시험이 확인).
- 합성 예시의 순서: 체결 11-02 14:32Z < 수신 시작 < 취득 완료 < 조각 보존 < 재결합 검증 < 결과 생성 < manifest 작성.

### 3.2 COMPLETE 주요 필드

| 필드 | 뜻 |
| --- | --- |
| `state` = `COMPLETE`, `failed_stage` = null | |
| `run_id` · `manifest_name` · `release_tag` · `day` | |
| `parser` | `{source_path, source_sha256, binary_sha256, git_commit, mode: SYMBOLS_FILE}` |
| `input` | 비공개 입력 커밋·경로·해시·행 번호 |
| `symbols_filter` | 파서에 준 기호 목록의 해시·수 |
| `release` | `{created_by_this_run, existing_assets, existing_failed_manifests}` |
| `source` | 목록·메타데이터 URL, `metadata_size`, `metadata_md5`, `expected_chunks` |
| `received` | `{bytes, md5, sha256, exit_codes, flow_s, started_at_utc, completed_at_utc}` |
| `chunks[]` | `{name, size, sha256}`. 이 순서로 이으면 원본 |
| `reassembly` | `{mode: STREAMING_NO_FILE, bytes, chunks, sha256_match, md5_match, gzip_test_ok, verified_at_utc}` |
| `derived` | `{name, schema_version, sha256, bytes, rows, states, generated_at_utc}` |
| `disk` | 시작·메타데이터 뒤 여유, 필요량, 계산 최대(`budget_peak_bytes`), 실제 최대(`peak_bytes`) |
| `limits` | 원천 GET 3, 목록 8 MiB, 메타데이터 1 MiB, 본체 20e9, 조각 1e9, 조각 수 ≤20, 사전 여유 22e9 |
| `completeness` | 크기·md5·gzip·파서·curl·조각·재결합 확인 여부, 파생 행 11/11 |
| `requests` | 원천 GET·비공개 읽기·release·업로드·되받기·삭제 수 |
| `timings` | 단계별 초 |
| `written_at_utc` | |

### 3.3 FAILED

- 실패 manifest는 `state = FAILED`, `failed_stage`(코드), `stage`(어느 단계였나), `http_status`, `exit_code`, `error_class`를 가진다.
- 이번 실행이 올린 자산마다 `uploaded_assets[]`에 `{name, size, deleted, known_from}`를 남긴다. `known_from`은 업로드 응답 또는 이름 목록이다.
- 그 밖에 `all_partial_assets_deleted`, `failed_manifest_uploaded`가 있다.
- 지운 것은 이번 실행 이름의 자산뿐이다. release와 다른 자산은 건드리지 않는다.

## 4. `financial-v-price-input/1` 변환에 쓸 대응 (Codex 판단·구현)

| #499 입력 필드 | 이 파일에서 | 비고 |
| --- | --- | --- |
| `code` | `rows[].code` | |
| `value` | `rows[].price` (문자열 → 십진) | PRICE 행만. 나머지는 사유를 그대로 두고 값 없음 |
| `date` | `basis_date` | |
| `currency` · `unit` | `currency` · `unit` | |
| `traded_at` | `rows[].last_trade_utc` | |
| `acquired_at` | `acquired_at_utc` | |
| `price_type` (`IEX_LAST_REGULAR_TRADE`) | `basis_kind` + `reason = REGULAR_SESSION_ROUND_LOT_LAST_TRADE` | |
| `price_basis` (`RAW`) | `adjustment_basis = AS_TRADED` | |
| `trade_validation` | `state = PRICE`일 때만 적격 후보 | |
| `cik` · `share_basis` · `valid_from/valid_to` · `action_status` | **이 파일에 없음** | Codex의 기준 증거로 붙임 |

## 5. 실제 파일이 생기면

- 승인과 실행 뒤, 비공개 release의 실제 manifest·파생 파일·조각 목록의 이름·SHA-256·크기, 취득 완료 UTC, 실행 ID·코드 SHA를 #437로 인계한다.
- 실패하면 FAILED manifest 위치와 실패 단계를 인계한다.
- 형식은 이 문서와 같다. 다르면 이 문서와 예시를 먼저 고친다.
