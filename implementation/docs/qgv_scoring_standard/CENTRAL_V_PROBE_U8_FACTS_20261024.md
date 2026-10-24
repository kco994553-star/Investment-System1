# 중앙 V — IEX 실현 가능성 시험·U8 월말가 1회 수집 사실 기록 (2026-10-24)

> **상태: 기록 문서(사실만).** 코드·워크플로·가드는 바꾸지 않는다. 가격 값·가격 비율·수익률·종목별 가격 시각은 없다.
> 개수·크기·시간·실행 번호·상태 문자·코드 이름만 옮겼다.

- 작성: 2026-10-24 UTC, PR-A(`claude/central-v-core`). 계획 [CENTRAL_V_DC02_PLAN_20261024](CENTRAL_V_DC02_PLAN_20261024.md) 1절 "프로브·백필 사실을 문서에 옮긴다"의 이행.
- 근거: GitHub Actions 실행 기록(`gh run view <id> --json …`, `--log`)을 2026-10-24에 다시 읽었다. 세 브랜치는 **병합되지 않았다**: `claude/iex-hist-probe`(e3d9e7a2), `claude/iex-v4-backfill`(22dfcec0, 실행 커밋 311a3252).
- 세 실행의 출력은 원래 "개수만" 형식이다. split-check 줄에는 무차원 비율도 찍혀 있으나 여기에는 옮기지 않았다(판정 개수만).
- 실행기: 두 워크플로 모두 `runs-on: ubuntu-latest`였고 그날은 이미지 `ubuntu-24.04`(20261012.334.1, Ubuntu 24.04.5)로 풀렸다. 다시 돌리면 24.04로 고정해야 한다(#395와 같은 이유, 계획 1절).

## 1. Actions 실현 가능성 시험(probe) — 판정 PASS

| 실행 | 커밋 | 시각(UTC) | 내용 | 결과(개수만) |
| --- | --- | --- | --- | --- |
| 39935426233 | eb5e07c2 | 2026-10-23 09:55:51~09:59:17 | TOPS 1.6 하루치 1회(파일 날짜 20261021) | 11,836,588,093 B(11.84 GB) 내려받기 194.4초(약 61 MB/s), 전체 3.2분. 패킷 310,404,130, 메시지 347,516,700, 체결 7,019,479, 깨진 것 0. 요청 기호 507(Universe 504 + SPY·HYG·IEF): ROUND 505, 단주만 0, 체결 없음 2. **Universe 정규장 마지막 체결 502/504**(없음: `NASDAQ:PSKY`, `NASDAQ:WBD`). 최대 디스크 0.0 MB, 자식 최대 RSS 33.3 MB, gzip 오류 줄 0, 종료 코드 0/0/0. 한도(45분·디스크 10 GB·결측 5%) 안 → **PASS** |
| 39940040651 | 02c603ea | 10:34:15~10:40:03 | 같은 시험 + 상장 진단(파일 날짜 20261022) | 14,099,700,391 B(14.10 GB) 336.2초(약 42 MB/s), 전체 5.6분. 체결 8,311,899, 깨진 것 0. 기호 511: ROUND 508, 체결 없음 3. Universe 502/504(PSKY·WBD: 증권 목록·거래 상태·체결 모두 없음). SKYD 거래 상태 `T`·체결 있음. 최대 디스크 0.1 MB, RSS 33.2 MB |
| 39944426209 | e3d9e7a2 | 11:12:10~11:34:17 | PSKY→SKYD 전환일(파일 날짜 1002·1005·1006·1007·1009) | PSKY: 1002·1005 거래 상태 `T`·체결 있음, 1006부터 없음. SKYD: 1005까지 없음, 1006부터 `T`·체결 있음. WBD: 1006부터 Universe 체결 없음 목록에 있음. 하루 3.9~5.6분 |

- 이 결과가 `providers/iex_hist.py` `SYMBOL_ALIASES`의 두 항목(PSKY→SKYD 2026-10-06, WBD None 2026-10-06)의 근거다. WBD는 채우지 않는다(`NO_IEX_TRADE`, Universe504 고정 목록이라 행은 그대로).
- 1008은 조사하지 않았다(전환일 판정에는 1005·1006으로 충분).
- 처리 방식: `curl | gzip -dc | C 파서`(원본 `tools/iex_hist/iex_last_trade.c`, 이 PR의 `tools/iex_tops/iex_last_trade.c`와 sha256 `23a99339…8b34` 바이트 동일). 가격은 실행기 RAM에만 있었다.

## 2. U8 V4 월말가 1회 수집 — run 39945012772

- 브랜치 `claude/iex-v4-backfill`, 커밋 311a3252(push 1회 실행, 소유자 승인 2026-10-23). 뒤 커밋 22dfcec0이 push 트리거를 지웠다. 이 브랜치는 canonical에 병합하지 않는다(소유자 조건).
- 전체 2026-10-23 11:17:13~11:47:18 UTC(약 30분), 성공.

| 잡 | 시각(UTC) | 내용 |
| --- | --- | --- |
| plan | 11:17:16~11:17:27 | 계획(개수만): 코드 422, 월 62(2021-06~2026-09), 파일 62(MD5 확인 62), 파일 없는 달 0, 기호 요청 2,052, 달마다 기호 1~310, 압축 합계 **386.5 GB**(한도 400 GB), 샤드별 64.5·64.7·63.4·65.1·65.4·63.4 GB. 입력 `sec-qgv2.json` as_of 2026-10-23T00:48:22Z |
| backfill(0~5) | 시작 11:17:30~11:17:46, 끝 11:37:28(샤드 1)~11:46:57(샤드 2) | 샤드 6개 병렬. 달 수 10·10·10·11·11·10 = 62 |
| split-check | 11:47:00~11:47:17 | 비공개 샤드를 다시 읽어 커버리지·분할 일관성(무차원 출력) |

**저장소(비공개 `kco994553-star/investment-system1-raw` 릴리스):** 태그 `iex-v4-monthend-20261023-shard0..5`, 자산 `<태그>.json.gz` + `.json.gz.sha256`, 스키마 `iex-monthend/1`.

| 샤드 | 0 | 1 | 2 | 3 | 4 | 5 | 합계 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 달 수 | 10 | 10 | 10 | 11 | 11 | 10 | 62 |
| 올린 `json.gz` 바이트 | 15,595 | 9,785 | 4,222 | 3,901 | 15,939 | 2,354 | **51,796 B** |

- 계획 1절의 "저장소 크기는 기록 없음"은 이 표로 채운다(실행 로그 `RAW_UPLOADED bytes=`, `.sha256` 자산 제외).
- 커버리지: 기호 요청 2,052 = ROUND 2,002 + 단주만 0 + 체결 없음 50. 달별 스트림 시간 합 151.5분(샤드 병렬), 달별 GB 합 386.6.
- 체결 없음 50건의 코드 21개: `NASDAQ:ECHO`, `NASDAQ:EXE`, `NASDAQ:FISV`, `NASDAQ:GEHC`, `NASDAQ:GEN`, `NASDAQ:SNDK`, `NASDAQ:WTW`, `NYSE:BALL`, `NYSE:COR`, `NYSE:CPAY`, `NYSE:ELV`, `NYSE:FDXF`, `NYSE:GEV`, `NYSE:KVUE`, `NYSE:MRSH`, `NYSE:RVTY`, `NYSE:SOLV`, `NYSE:SW`, `NYSE:VLTO`, `NYSE:VMRK`, `NYSE:XYZ`. 게시기는 그 달을 `MONTH_END_PRICE_NOT_AVAILABLE`로 뺀다(`providers/iex_monthend.py` `month_closes`). 원인은 조사하지 않았다.
- split-check 커버리지: 완료 62/62(계획 62, 샤드 62, 빠진 달 0, 남는 달 0).
- split-check 분할 판정(U8 자체 표 `VERIFIED_SPLIT_ROWS` 50개 창, SEC 분할 비율 사실 + 표지 주식수 점프로 확인한 것): 시험 가능 25종목·25건 — `RAW_MISMATCH_FIXED_BY_F` 22, `RAW_CONSISTENT` 1(`NYSE:WSM`), `UNEXPECTED` 2(`NASDAQ:DXCM`, `NASDAQ:FTNT`), 나머지 25건 `NOT_TESTABLE`. 전체 판정 `MIXED`.
  - 이 F는 U8 도구의 분할 날짜 곱이다. #393의 F_k(각 연도 자기 보고 기준)와 다르다. #393 문서(`QGV_V2_QG_METHOD.md` V-PRICE-BASIS)는 WSM의 `RAW_CONSISTENT`를 "분할 구간의 배수 변화이지 기준 오류가 아니다"로, FTNT는 F_k 5/1/1/1/1, DXCM FY2021은 `SHARE_BASIS_UNCONFIRMED`(F_k `null`, 그 달 제외)로 설명한다.
  - 첫 게시 뒤 계획 5절 재대조에서 이 세 종목의 V4 산출 여부를 개수로만 확인한다(가격·비율은 남기지 않는다).

## 3. 이 PR(PR-A)에서 바뀐 것과 위 사실의 관계

- C 파서는 `tools/iex_tops/iex_last_trade.c` **한 벌**만 저장소에 있다. U8·probe 브랜치의 `tools/iex_hist/iex_last_trade.c`는 같은 바이트다. PR-E(U8 후속)가 그 도구를 들여오면 이 파일을 써야 한다. 시험 `test_one_parser_copy_and_one_symbol_alias_table`이 두 번째 `.c`나 두 번째 `SYMBOL_ALIASES` 정의를 막는다.
- 기호 별칭 표는 `providers/iex_hist.SYMBOL_ALIASES` 하나다. U8 `monthend_plan.py`의 자체 표(PSKY 항목 같음)는 PR-E에서 이것을 import하게 바꾼다(`CENTRAL_V_U4_U5_NEEDS_20261023.md` §1-4).
- 월말가 저장소 날짜 `--monthend-stamp 20261023`, 샤드 수 6은 위 실행과 같다(PR-C 워크플로 변수).
- 기준일(D3): 시험 39935426233은 10-23 09:55 UTC에 실행해 최신 파일이 20261021이었다. TOPS 파일은 T+1(04:24~10:22 UTC 생성)이므로 매일 00:37 UTC 무렵 시작하는 정기 실행은 보통 전 거래일을 쓴다. 휴장일·주말·T+1·반일 장 동작은 이제 시험이 있다(`tests/test_iex_hist.py` basis day 절). 반일 장은 실제 파일로 아직 확인하지 않았다. 첫 반일 장은 2026-11-27이다.
- 첫 게시 실행(PR-C 뒤 `all_shards`)의 시간 예상: probe 3.2~5.6분 + 게시기 계산. collect 잡 한도 안이다(정기 40분, `all_shards` 120분).
