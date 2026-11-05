# IEX 전체 기호 파서 모드 (`--all-symbols`) — 2026-11-05, Main

> **상태:** 코드와 합성 시험만 추가했다. 워크플로·가드·Codex 소유 Python·공개 파일·Universe504는 바꾸지 않았다.
> 실제 IEX 파일은 내려받지 않았고, 새 자료 수집도 하지 않았다.
> **실제 IEX 하루 파일에 이 모드를 돌리는 것은 별도 오너 승인이 필요하다.** 이 문서는 그 승인을 대신하지 않는다.

## 1. 무엇을 하나

- 파일: `implementation/tools/iex_tops/iex_last_trade.c` (C 파서는 계속 이 파일 하나다).
- 기존 Universe504 모드(`iex_last_trade <기호파일> <시작ns> <끝ns>`)는 인자·동작·출력 바이트가 그대로다.
  - 기호 상한 1,024(`MAXSYM`)도 그대로다.
  - 동일성 증명: 변경 전 파서 출력의 SHA-256 고정값 시험과, 변경 전 소스(git)를 따로 컴파일해 여러 입력에서 바이트 비교하는 시험(아래 6절).
- 새 모드는 `--all-symbols`를 줄 때만 켜진다.
  - 기호 파일로 미리 거르지 않는다. 기호가 있는 TOPS 1.6 메시지에 나온 기호는 모두 한 행이 된다.
    - 해당 메시지: 증권 디렉터리(D), 거래 상태(H), 호가 갱신(Q), 체결(T), 체결 취소(B), 운영 정지(O), 공매도 가격 시험(P), 증권 이벤트(E), 경매 정보(A), 공식 가격(X).
  - 표는 늘어나는 해시 표다. 고정 1,024 상한이 없다.
  - 안전 상한: 기본 50,000개 서로 다른 기호(`--max-symbols`로 1~1,000,000).
    - 넘으면 표준출력에 **아무것도 쓰지 않고** 종료 코드 6, 표준오류 `#ERROR SYMBOL_CEILING_EXCEEDED ceiling=N`. 잘라서 내보내지 않는다.

## 2. 무엇을 판정하지 않나

- 거래 가능·상장·적격(tradable / listed / eligible) 필드는 **없다**. 이 모드는 관측만 적는다.
  - 디렉터리만 있는 기호도 관측 행으로 남는다. 상태 메시지가 없으면 그것을 근거로 무엇도 참으로 두지 않는다.
  - 체결 없음·정지·연결 안 된 기호도 버리지 않는다.
- 유효기간(valid_from / valid_to)을 추론하지 않는다. 메시지 타임스탬프만 그대로 둔다.
- 기호 원문을 그대로 둔다(뒤쪽 공백 채움만 뺌, 인쇄 불가 바이트는 `\u00XX`로 이스케이프). 기호를 다른 코드로 바꾸지 않는다.
- 운영 정지(O)·공매도(P)·증권 이벤트(E)는 기호별 `other_messages` 개수로만 센다. 값은 기록하지 않는다.

## 3. 사용법

```
gzip -dc tops.pcap.gz | iex_last_trade --all-symbols <세션시작ns> <세션끝ns> \
    [--max-symbols N] [--source-bytes N] [--source-sha256 HEX64] [--no-stdin-sha256] > parsed.jsonl
```

- 세션 창은 `[시작, 끝)`이다(끝 미포함). 기존 모드와 같은 `iex_hist.session_ns(day)` 값을 쓰면 된다.
- `--source-bytes` / `--source-sha256`: 호출자가 받은 원본(.gz) 바이트 수와 SHA-256. 그대로 요약 행에 옮겨 적는다(검증은 호출자 몫).
- 파서는 표준입력(압축 푼 스트림)의 바이트 수와 SHA-256을 직접 센다.
  - `--no-stdin-sha256`이면 SHA-256 계산을 건너뛰고 `stdin_sha256: null`. 호출자가 원본 바이트 펌프에서 해시를 내면 이것이 빠르다(7절).
- 표준오류에는 이름 붙은 오류만 나간다. 가격 등 값은 표준출력 스트림에만 있다. 어디에 둘지는 호출자가 정한다.

## 4. 출력

JSON Lines. 기호 행을 원시 8바이트 기호 순으로 쓰고, 마지막에 요약 행 하나를 쓴다. 요약 행이 없으면 출력이 잘린 것이다.

### 기호 행 (`"record":"symbol"`)

| 필드 | 뜻 |
| --- | --- |
| `symbol` | 기호 원문 |
| `directory_seen`, `directory_messages` | 증권 디렉터리 메시지 유무·개수 |
| `directory_ts`, `directory_flags`, `round_lot_size` | 마지막 디렉터리 메시지의 타임스탬프·플래그 원값(시험 증권 0x80, WI 0x40, ETP 0x20)·단위주 크기. 없으면 null |
| `trading_status_seen`, `status_messages` | 거래 상태 메시지 유무·개수 |
| `trading_status`, `trading_status_ts`, `trading_status_reason` | 스트림 순서상 마지막 상태 코드(T/H/P/O)와 **그 메시지의** 타임스탬프·사유 원문. 없으면 null |
| `last_round_trade` | 세션 창 안, 연장시간(0x40)·단주(0x20) 플래그가 없는 마지막 체결 `{price_e4, size, ts, broken}`. 없으면 null |
| `trade_reports`, `trades_regular_round`, `trades_regular_odd`, `trades_excluded` | 체결 메시지 수: 전체 / 창 안 단위주 / 창 안 단주 / 연장시간·창 밖 |
| `trade_breaks` | 체결 취소 메시지 수. 마지막 단위주 체결의 체결 ID가 취소되면 `broken: true`(이전 체결로 되돌리지 않음) |
| `quote_updates`, `other_messages`, `messages` | 호가 갱신 수(호가 값은 기록 안 함) / 그 밖의 기호 메시지 수 / 합계 |

- 단주는 마지막 단위주 체결이 될 수 없다. 기존 모드의 `ODD_ONLY` 가격 같은 단주 가격은 이 모드에서 내보내지 않는다(개수만).
- 같은 타임스탬프면 나중 메시지가 이긴다(기존 모드와 같은 `>=` 규칙).

### 요약 행 (`"record":"summary"`)

- 정체: `parser`(`iex_last_trade`), `parser_version`(`2026-11-05.1`), `mode`(`all_symbols`), `symbol_ceiling`.
- 입력: `session_start_ns`, `session_end_ns`, `capture_format`(pcap / pcapng), `stdin_bytes`, `stdin_sha256`, `source_bytes`, `source_sha256`.
- 개수: `symbols`, `symbols_with_directory`, `symbols_with_trading_status`, `symbols_directory_without_status`, `symbols_with_round_trade`, `packets`, `packets_caplen_short`, `segments`, `bad_segments`, `messages`, `symbol_messages`, `short_symbol_messages`, `directory_messages`, `status_messages`, `quote_updates`, `trade_reports`, `trade_breaks`.
- 연속성: IEX-TP 헤더의 채널·세션·첫 메시지 순번으로 `first_sequence`(캡처 첫 세그먼트의 첫 순번), `sequence_gaps`, `sequence_gap_messages`, `sequence_regressions`(중복·역순), `stream_changes`.
- 완결성 플래그:
  - `truncated`: 캡처가 레코드 중간에서 끊김.
  - `symbol_ceiling_exceeded`: 성공 출력에서는 항상 false(넘으면 출력 자체가 없음).
  - `gaps_detected`: 순번 빈틈 또는 역순.
  - `complete`: 끊김·잘못된 세그먼트·빈틈/역순·잘린 캡처 길이가 모두 없고, IEX 세그먼트가 하나 이상일 때만 true.
- 끊긴 입력이어도 그때까지의 행과 요약을 쓰고 종료 코드 0이다. **호출자는 `complete: true`가 아니면 그날을 쓰지 말아야 한다.**

### 종료 코드

| 코드 | 이름(표준오류) |
| --- | --- |
| 2 | `BAD_ARGUMENT` |
| 3 | `NO_CAPTURE_HEADER` |
| 4 | `BAD_PCAPNG_BLOCK` |
| 5 | `unknown capture format` (기존 모드와 같은 문구) |
| 6 | `SYMBOL_CEILING_EXCEEDED ceiling=N` |
| 8 | `OUT_OF_MEMORY` |
| 9 | `WRITE_FAILED` |

## 5. 한계 — IEX 하루 파일로 정할 수 없는 것

- **대표 증권:** 한 발행사의 어느 종류주가 대표인지 정할 수 없다. 기호와 디렉터리 플래그만 있다.
- **전 종류 시가총액:** 종류별 발행주식수가 없다. IEX 가격 하나로 전 종류 시총을 만들 수 없다.
- **ADR 연결:** ADR과 원주, ADR 비율을 잇는 정보가 없다.
- **기업행위:** 분할·합병·기호 변경·상장폐지는 하루 파일로 알 수 없다. 기호가 같아도 같은 회사라는 보장이 없다(재사용 기호).
- **식별 유효성:** 그 기호가 언제부터 언제까지 그 증권이었는지 정할 수 없다. 이 모드는 그 날짜의 관측만 적는다.
- 그 밖:
  - IEX 체결은 전체 시장 거래량의 일부(약 3.8%, 2026-10-30 측정)다. IEX 마지막 체결은 통합 종가가 아니다.
  - 체결 취소가 마지막 체결을 가리키면 `broken`만 표시하고 이전 체결로 되돌리지 않는다(이력을 두지 않음).
  - 디렉터리·상태 메시지는 보통 개장 전에 오므로, 캡처 앞부분이 없으면 `*_seen`이 거짓이 될 수 있다. 앞부분 누락은 순번 빈틈으로 잡히지 않는다(첫 세그먼트가 기준이 됨). 호출자는 `first_sequence`가 1인지 따로 확인해야 한다. 실제 IEX 파일이 1에서 시작하는지는 아직 실제 자료로 확인하지 않았으므로 `complete` 조건에는 넣지 않았다.
  - DEEP 전용 메시지 종류(가격 단계 갱신 등)는 기호 행을 만들지 않고 전체 `messages`에만 센다.

## 6. 시험 (합성 자료만)

`implementation/tests/test_iex_full_symbol_parser.py` (기존 `tests/test_iex_hist.py`의 체결·상태·pcap 생성기를 재사용):

- 1,024 초과(3,000) 기호 전부·정렬·요약 필드·입력 SHA-256 일치
- 디렉터리만 / 상태만 / 정지(H, 마지막 상태와 그 타임스탬프) / 체결 없음 / 호가만 있는 기호가 모두 행으로 남음, 판정 필드 없음
- 단주·연장시간·창 밖 체결은 마지막 단위주 체결이 아님(창 끝 미포함)
- 체결 취소가 마지막 체결만 `broken` 표시
- 기호 원문 보존·이스케이프
- 상한 초과 → 이름 붙은 실패, 출력 없음 (작은 상한, 기본 50,000 둘 다)
- 순번 빈틈·끊긴 입력·pcap-ng 동등성, 잘못된 인자, 입력 없음·알 수 없는 형식
- `--no-stdin-sha256`
- **Universe504 모드 바이트 동일:** 1,100기호 고정 입력(1,024 상한·DEEP·비IEX 세그먼트·짧은 메시지·끊긴 꼬리 포함)에서 변경 전 파서 출력 SHA-256 고정값과 일치, 그리고 git에 변경 전 소스(`cef0748e`)가 있으면 컴파일해 여러 입력·잘못된 인자에서 종료 코드·표준출력·표준오류를 바이트 비교(얕은 복제면 건너뜀)

## 7. 제안: 비공개 보관 (승인 전 제안일 뿐)

하루 실행마다 비공개 저장소에 두 파일:

1. `parsed.jsonl.gz` — 위 출력 그대로(가격 포함, 비공개).
2. `manifest.json`
   - 원본 URL(승인된 IEX HIST 버킷 링크), 받은 바이트 수, 원본 .gz SHA-256(받는 펌프에서 계산)과 GCS md5 확인 결과
   - 파서 `parser_version`·`mode`·`symbol_ceiling`·파서 소스 SHA-256
   - 요약 행의 패킷·세그먼트·메시지 수와 완결성 플래그(`truncated`, `gaps_detected`, `complete`)
   - `parsed.jsonl.gz`의 SHA-256

- **원본 pcap은 보관하지 않는다.** 따라서 나중에 다시 파싱할 수 없다.
  - 파서 오류가 발견되거나 새 필드가 필요하면 원본을 다시 내려받아야 한다. IEX가 그 날짜 파일을 계속 제공한다는 보장은 없다.
  - 그래서 manifest에 파서 버전·소스 해시를 남겨, 어떤 파서로 만든 행인지 항상 알 수 있게 한다.

### 예상 크기·속도 (합성 측정, 실제 값 아님)

- 기호 행 하나 약 450~500 바이트. 12,000기호 합성 출력 5.8 MB(비압축).
  - 실제 하루 약 13,000기호면 약 6~7 MB, gzip 후 약 1 MB 안팎(추정; 합성 자료는 반복이 많아 91 KB로 압축됨).
  - manifest는 수 KB.
  - 하루 1벌이면 연 약 250거래일 × 약 1 MB ≈ 250 MB(gzip, 추정).
- 처리 속도(이 세션 컨테이너, `cc -O2`, 1 GB 합성 pcap, 12,000기호, 메시지 2,080만 개):
  - 파싱만(`--no-stdin-sha256`): 약 0.9초/GB.
  - 표준입력 SHA-256 포함: 약 7.8초/GB(이 파서의 이식형 SHA-256이 병목).
  - 실제 하루 파일(압축 8~15 GB)에서는 압축 풀기·다운로드가 더 큰 병목일 것이다(기존 측정 파이프라인 약 62 MB/s). 원본 해시는 받는 펌프에서 내고 `--no-stdin-sha256`을 쓰는 것을 권한다.
- 메모리: 기호당 약 170 바이트 + 해시 색인. 50,000기호에서도 수십 MB 이내. 입력 버퍼는 기존 모드와 같다.
