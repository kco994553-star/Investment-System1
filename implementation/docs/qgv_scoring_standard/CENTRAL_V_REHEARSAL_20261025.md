# 중앙 V 리허설 — 첫 게시 전 하루치 측정 (게시 없음)

> **상태: 준비 문서.** 워크플로 `.github/workflows/central-v-rehearsal.yml`와 판정 도구 `implementation/tools/central_v_rehearsal_report.py`를 설명한다. 아직 한 번도 돌리지 않았다. 값(토큰·키·가격)은 이 문서에 없고, 어디에도 적지 않는다.
> 근거: GSQ-024 "검증 먼저"(운영 전에 Actions에서 최근 거래일 하루치로 처리 시간·디스크·누락을 측정한다. 일일 collect/ledger와 분리), 소유자 지시 2026-10-24 3-b, [첫 게시 점검표](CENTRAL_V_GO_LIVE_CHECKLIST_20261024.md), [프로브·U8 사실](CENTRAL_V_PROBE_U8_FACTS_20261024.md) 1절, [계획](CENTRAL_V_DC02_PLAN_20261024.md).

- 작성: 2026-10-24 UTC, 브랜치 `claude/central-v-rehearsal`(중앙 V 사슬 맨 위 `claude/central-v-reader` = #393 → #400 → #403 → #404 → #405의 최종 코드 위).
- 이 브랜치는 canonical에 병합하지 않는다. 운영 워크플로(`sec-daily-public-inputs.yml`)는 바꾸지 않는다.

## 1. 무엇을 돌리나

**브랜치 `claude/central-v-rehearsal`을 push하면 그것이 곧 시작이다.** 다른 시작 방법은 없다(정기 실행·PR·수동 실행 없음). 기본 브랜치에서는 돌지 않는다. 다른 워크플로는 이 브랜치 push로 시작되지 않는다.

| 순서 | 잡 / 단계 | 내용 |
| --- | --- | --- |
| 1 | `presence` | Secret 3개의 **이름과 있음/없음만** 찍는다: `SECRET_PRESENT name=QGV_OFFICIAL_HMAC_KEY present=yes` 등(`RAW_REPO_READ_TOKEN`, `SEC_USER_AGENT`). 값은 실행기에 오지도 않는다(GitHub가 `secrets.X != ''` 비교 결과 true/false만 넘긴다). 시작 시각도 본다(`REHEARSAL_WINDOW`, 3절). 하나라도 없거나 시각이 밖이면 여기서 끝(아무것도 수집·내려받기 안 함) |
| 2 | `rehearsal` 앞부분 | 운영 collect 잡을 `all_shards` 방식으로 V 단계 직전까지 재현: 실행 맥락 줄, Node 고정, 오프라인 경계 회귀 시험, 가격 없는 cockpit 빌드, SEC 공개 입력(TARGET 행을 `sec-qgv2.json`에 준비), **Universe504 7개 샤드 전체 수집(`--all-shards`)**. 그래서 `sec-qgv2.json`이 지금 코드(calc_version `qgv2-calc/2026-10-23.1`)로 다시 쓰인다(게시기는 그 전 버전을 거부) |
| 3 | V 단계 앞 측정 | `df -B1`·`du -sb`로 디스크, 2초마다 디스크 사용량·남은 메모리를 적는 표본기(숫자만)를 V 단계 **전에** 띄운다(그래서 표본기는 Secret을 갖지 않는다) |
| 4 | **V 단계** | 운영 V 단계와 **바이트 단위로 같은** 단계(같은 명령·같은 env·Secret 2개는 이 단계 env에만·`cc`와 가드는 `env -u`로 Secret 없이·게시기는 시작하자마자 Secret을 env에서 지움). 결과는 `$RUNNER_TEMP/public-cockpit`에만 남는다. 로그에 `QGV_OFFICIAL attempt=… reason=… published=… basis=… rows=… ranked=… supplied=n/m` 한 줄 |
| 5 | V 단계 뒤 측정 | 끝난 시각, 단계 결과, 표본기 정지, `df -B1`·`du -sb` |
| 6 | 검사 | 같은 폴더에 아티팩트 가드(`pages_artifact_guard.py`)와 verify 잡의 가격 없는 검사(`qgv_official_check.py`)를 Secret 없이 다시 돌린다 |
| 7 | 뒷부분 | 운영 collect 잡의 V 뒤 단계(SIC·10-K·N-PORT, 도메인·로고, 13F, 8-K, 뉴스, 커버리지 줄). 잡 전체 시간을 재기 위해서다 |
| 8 | 판정 | `Rehearsal verdict (fixed codes and counts only)` 단계가 단계별 한 줄과 기준별 PASS/FAIL, 전체 판정을 찍는다(5절) |

모든 단계는 시작·끝 시각(`date +%s`)과 종료 코드를 `$RUNNER_TEMP/rehearsal-metrics`(아티팩트 폴더 밖)에 적는다. 필수 단계가 실패하면 운영처럼 잡이 멈추지만, 측정·검사·판정 단계는 실패 뒤에도 돈다(취소 때는 안 돈다).

## 2. 절대 하지 않는 것

- **비공개 원자료 저장소에 쓰지 않는다.** 원자료 쓰기 토큰은 파일 어디에도 없다. 샤드 도구는 그 토큰이 없으면 원 SEC 바이트를 올리지도 저장하지도 않고 샤드마다 `RAW_UPLOAD_NOT_CONFIGURED shard=<i>`를 찍는다. 수집 자체는 같다. 원자료 저장소는 V 단계의 읽기 전용 토큰으로 **월말가 저장소를 읽기만** 한다.
- 원장(forward validation ledger) 추가, 비공개 점수 이력(D9) 복사, Pages 아티팩트·워크플로 아티팩트 업로드, 배포, 캐시, push, 작업 요약(job summary) — 모두 없다. 만든 파일은 실행기와 함께 사라진다.
- 라이브 사이트에서는 **읽기만** 한다(이전 공개본을 이어 붙이는 운영과 같은 GET). 게시는 없다.
- 일부러 뺀 것(Secret을 더 쓰지 않으려고): SEC 공개 입력 단계의 `--macro-v0 --macro-evidence`(BEA·Census 키), OpenDART 두 단계(DART 키). 모두 `sec-qgv2.json`과 V 단계에 들어가지 않는다. 시간은 판정의 여유분(10분)으로 더한다.
- 출력: 고정 코드와 개수·바이트·초만. 가격·비율·수익률·종목별 값이나 날짜·종목 목록·URL·Secret 값은 찍지 않는다.
- 정기 실행과 섞이지 않게: 동시 실행 그룹이 따로다(`central-v-rehearsal`, 운영 그룹과 공유하면 대기 중인 정기 실행을 취소할 수 있어서 피함). 시작 시각 03:00~19:30 UTC만 허용한다(10월 정기 실행은 22:26~00:40 UTC 시작, collect 약 15분, 그 뒤 수동 대체 실행 가능성까지 피함).

## 3. 실패 기준과 판정

판정 줄 형식: `REHEARSAL_CRITERION name=<기준> value=<측정값> limit=<한도> verdict=PASS|FAIL [reason=…]`. 값이 없으면(그 단계가 못 돌았으면) `verdict=FAIL reason=NOT_MEASURED`다. 전체는 `REHEARSAL_VERDICT overall=PASS|FAIL passed=k/11 failed=…`이고, FAIL이면 판정 단계(와 잡)가 빨간색이다.

| 기준 | 한도 | 근거 |
| --- | --- | --- |
| `v_step_time` | V 단계 전체 ≤ 12분(720초) | 게시기 자체 한도 `timeout -k 30s 12m`(단계 한도 15분). 단계 전체가 12분을 넘으면 여유가 없다 |
| `job_time` | 잡 측정 시간 + 10분 ≤ 120분 | `all_shards` 실행의 collect 잡 한도 120분. 10분 = 빠진 운영 단계 여유(OpenDART 4분 47초·DART 투영 3초·원장 8초, 2026-10-24 정기 실행 40045938631; D9 이력은 단계 한도 5분) |
| `required_steps` | 필수 단계 모두 종료 코드 0 | 운영에서 필수 단계 실패는 그날 Pages 아티팩트를 막는다 |
| `inputs_calc_version` | `sec-qgv2.json` calc_version이 `qgv2-calc/2026-10-23.1` 이상 | 게시기가 그 전 버전을 `NOT_RUN`으로 거부 |
| `stream_disk_peak` | V 단계 중 디스크 사용 증가 최대 ≤ 10 GB(10,000,000,000 B) | GSQ-024 프로브 한도. 스트리밍(내려받기 → gzip → C 파서)이라 거의 0이어야 한다(프로브 0.0~0.1 MB) |
| `universe_last_trade` | Universe 행 중 IEX 정규장 마지막 체결이 **없는** 행 ≤ 5% → 504행이면 **≥ 479/504** | 프로브 한도(결측 5%). 없음 = `NO_IEX_TRADE`·`ODD_LOT_ONLY`·`PRICE_SYMBOL_UNMAPPED`. ADR·분할·식별 규칙으로 가격을 쓰지 않은 행(`rule_excluded`)은 체결 여부가 기록되지 않아 없음으로 세지 않고 따로 센다. 프로브 실측 502/504 |
| `supply` | 공급 ≥ ceil(95% × 적격) | 결정 D4(`supplied=n/m`, 게시기의 `supply.met`과 같은 계산) |
| `validator` | 게시본·상태 파일이 엄격 판독기 VALID이고 서로 맞음 | `qgv_official_check.py` 종료 코드 0, `publication=VALID status=VALID consistent=YES` |
| `js_twin` | Python과 JS 결과 일치 | 게시기는 JS 쌍둥이가 일치해야만 `published=NEW`를 쓴다. `JS_TWIN_…` 사유면 FAIL |
| `guard` | V 단계 성공(그 안의 가드 2회) + 검사 단계 가드 통과 | `QGV_OFFICIAL_GUARD_REFUSED`면 V 단계가 실패로 끝난다 |
| `attempt_ok` | 상태 파일 `attempt_state=OK` | 점검표 4절의 `attempt=OK` |

## 4. 예상 시간

| 구간 | 추정 | 근거(실측) |
| --- | --- | --- |
| `presence` | 약 10초 | — |
| 준비·오프라인 회귀 시험 | 약 3분 | 2026-10-24 정기 실행 2분 42초 |
| cockpit 빌드·SEC 공개 입력 | 약 1분 | 같은 실행 2초 + 59초(매크로 포함) |
| 7개 샤드 전체 | 약 21~27분 | 2026-10-17 `all_shards` 실행 38996553263: 21분 00초. 2026-10-24 샤드 1개 3분 52초 × 7 |
| V 단계 | 약 4~8분 | 프로브: 11.8~14.1 GB 내려받기·해석 3.2~5.6분. 여기에 C 파서 빌드, 월말가 저장소 읽기, 점수 계산, JS 쌍둥이, 가드 2회 |
| 검사·뒷부분·판정 | 약 3분 | 2026-10-24 정기 실행 V 뒤 단계 합 약 2분 36초 |
| **합계** | **약 32~42분** (판정 기준으로는 +10분 = 42~52분, 한도 120분) | 잡 한도는 140분(넘는 경우도 판정까지 가도록) |

첫 게시 날의 운영 `all_shards` collect는 여기에 OpenDART·원장·이력이 더해져 약 37~47분으로 본다.

## 5. 시작 전 조건과 결과 읽는 법

**시작 전(소유자 / Main):**
1. Secret 3개 등록 확인: `QGV_OFFICIAL_HMAC_KEY`(16바이트 이상), `RAW_REPO_READ_TOKEN`(원자료 저장소 하나, Contents 읽기만), `SEC_USER_AGENT`(기존). 점검표 1절. HMAC 키 길이는 `presence`가 볼 수 없다(값을 받지 않으므로). 짧으면 V 단계에서 `NOT_RUN HMAC_KEY_MISSING`으로 나온다.
2. 측정할 코드가 최종인지: CV-SPLIT (ii) 등 사슬에 바뀐 것이 있으면 Main이 최신 `claude/central-v-reader`를 이 브랜치에 병합한 뒤 push한다.
3. Actions에 진행 중이거나 대기 중인 `SEC daily public reported inputs` 실행이 없는지 본다. 시각은 03:00~19:30 UTC(한국 시각 12:00~다음 날 04:30). 전 거래일 IEX 파일은 다음 날 10:22 UTC까지 만들어지므로, 가장 최근 거래일을 재려면 11:00~19:30 UTC(20:00~04:30 KST)가 좋다. 그 전에 시작하면 하루 더 앞선 거래일 파일을 쓴다(그래도 "최근 거래일 하루치").
4. 소유자 승인 뒤 Main이 브랜치를 push한다. 다시 돌리려면 실행 화면의 **Re-run jobs**나 새 커밋 push.

**결과(휴대폰):** 저장소 → **Actions** → 왼쪽 **Central V rehearsal (measure only, no publication)** → 해당 실행.
- `presence` 잡: `SECRET_PRESENT …` 3줄, `REHEARSAL_WINDOW … verdict=OK`.
- `rehearsal` 잡 → 맨 아래 단계 **Rehearsal verdict (fixed codes and counts only)**:

```
REHEARSAL_SCOPE publication=NONE raw_repo_write=NONE ledger=NONE history=NONE pages_upload=NONE artifact_upload=NONE cache=NONE job_summary=NONE
REHEARSAL_STAGE stage=<단계> seconds=<초> rc=<종료 코드> kind=required|optional   (단계마다 한 줄, V 단계는 outcome=…)
REHEARSAL_JOB seconds=<초> allowance_excluded_steps=600 limit=7200
REHEARSAL_INPUTS file=sec-qgv2.json state=VALID calc_version=qgv2-calc/2026-10-23.1 records=504 records_current_calc=<n> records_no_data=<n> records_other_calc=<n> target=<n> same_bytes_as_attempt=YES
REHEARSAL_DISK fs_used_before=<B> fs_used_after=<B> fs_used_peak=<B> stream_peak_bytes=<B> … samples=<n> … mem_available_min=<B>
REHEARSAL_V attempt=OK reason=- published=NEW basis=<IEX 기준일> requested_basis=<요청 기준일> rows=<n> ranked=<n> supplied=<n>/<m> supply_met=YES
REHEARSAL_PRICE universe_rows=504 … supplied=<n> last_trade_missing=<n> rule_excluded=<n> NO_IEX_TRADE=<n> … consistent=YES
REHEARSAL_CRITERION name=… verdict=PASS   (11줄)
REHEARSAL_VERDICT overall=PASS passed=11/11 failed=-
```

- Main에 보낼 것: 실행 번호(run ID)와 위 `REHEARSAL_…` 줄 전부, V 단계의 `QGV_OFFICIAL …` 한 줄. 모두 개수·코드뿐이라 그대로 옮겨도 된다. Main이 첫 게시 점검표(`CENTRAL_V_GO_LIVE_CHECKLIST`)의 측정 칸을 채운다.
- `records_other_calc`가 0이 아니면 그만큼 수집에 실패한 행이 옛 calc_version으로 남아 V·순위에서 빠졌다는 뜻이다(`CALC_VERSION_MISMATCH`).

## 6. 한계

- 가격 확보에 실패한 시도(`SUPPLY_FAILED` 등)는 게시본을 쓰지 않으므로 `universe_last_trade`·`supply` 개수가 없다(`NOT_MEASURED`). 이유는 `attempt_ok`의 `reason`(예: `SUPPLY_BELOW_THRESHOLD`, `IEX_…`)에 나온다. 게시기는 실패한 시도에서 사유 코드 외의 개수를 내지 않는다(설계 그대로의 한 줄 출력).
- `rule_excluded` 행은 체결 여부가 기록되지 않는다. 그래서 `universe_last_trade`는 IEX에서 확인된 결측만 센다.
- 디스크 최대치는 2초 간격 표본이다. 스트리밍 방식이라 순간 최대도 작지만, 2초보다 짧은 순간은 놓칠 수 있다.
- 첫 게시 뒤에 다시 돌리면 라이브 게시본이 있어 V 단계가 그것을 먼저 싣는다(`KEPT_LAST_GOOD`). 그래도 새 입력이라 보통 `published=NEW`다.
- 이 리허설은 하루 SEC 수집을 한 번 더 하는 셈이다(같은 속도 제한 클라이언트). 정기 실행과 겹치지 않게 시작 시각을 막는다.
