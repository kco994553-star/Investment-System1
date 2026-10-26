# 중앙 V 비게시 리허설 검증 리뷰 — 2026-10-25

기능 **2·6**, Codex 검증·리뷰. 운영 근거는 [run 40156760950, attempt 1](https://github.com/kco994553-star/Investment-System1/actions/runs/40156760950), rehearsal HEAD **`c2e4b5c2ab50620a8cae99d2c9f56fb2bb70a99f`**, 03:03:01~03:32:46 UTC다. GitHub 플러그인으로 job 121059696985 로그를 읽었다. gh 로그 경로의 Forbidden은 전체 로그 조회 불가를 뜻하지 않는다. 원시 가격·Secret 값은 조회·출력하지 않았고 코드·워크플로 수정·운영 재실행·게시도 하지 않았다.

## 1. 실제 verdict: FAIL — PASS 6 / FAIL 2 / NOT_MEASURED 4

| 기준 | 판정 | 실제 관측·분모·한계 |
| --- | --- | --- |
| V 시간 | PASS | 105초 ≤ 720초. 실패까지의 시간이며 정상 전체 처리 시간은 아님 |
| 잡 시간 | PASS | 1,770+660=2,430초 ≤ 7,200초 |
| 필수 단계 | PASS | 7/7. 개별 step success가 공식 V 성공을 뜻하지 않음 |
| 최상위 calc_version | PASS | 기대·실제 `qgv2-calc/2026-10-23.1` |
| 행별 calc_version | **FAIL** | current=500, no_data=2, **other=2** → `ROWS_OF_ANOTHER_CALC_VERSION(other_calc=2)` |
| 디스크 증가 | PASS | 122,880B ≤ 10,000,000,000B, 표본 53개, 작업 폴더 잔여 0B |
| Universe 마지막 체결 | **NOT_MEASURED** | 기준 ≥479/504. 게시본 없음, 실제 분자 미측정 |
| D4 공급률 | **NOT_MEASURED** | `supplied=-/-`. **분모 0으로 쓰지 않음**. D4 분모는 동일 버전·GENERAL 교차단면의 비ADR·비분할 중 가격 없이 V 입력 단계까지 도달 가능한 행으로, Universe 504와 다름 |
| 엄격 검증 | **NOT_MEASURED** | publication=ABSENT / status=VALID. status 파일 유효와 공개 V 게시본의 엄격 검증 통과는 별개 |
| JS 쌍둥이 | **NOT_MEASURED** | 계산·비교 미도달, MATCH 주장 불가 |
| 가드 | PASS | V step success / guard rc=0. 게시본·JS·공급률 검증을 대신하지 않음 |
| attempt_ok | **FAIL** | `NO_OFFICIAL_YET / IEX_GZIP_FAILED` |

Secret의 등록·preflight 검사는 통과했으나 **월말 저장소 읽기 권한·HMAC 서명 기능은 gzip 실패 뒤 경로라 미검증**이다. 이름 `QGV_OFFICIAL_HMAC_KEY`·`RAW_REPO_READ_TOKEN`만 기록한다. 비게시 리허설에 배포 단계는 없다.

## 2. 서로 독립된 오류·재현

### A. 행 버전 혼합

실제 로그는 샤드 **7/7**, 발행사 **499/499 수집 성공·실패 0**과 함께 `unresolved_codes=2`, `preserved_previous_qgv2=2`, `preserved_unconfirmed=2`를 기록했다. unresolved 코드는 샤드 분할 밖에 있고 전체 504 merge에서 이전 검증 행이 보존되므로 두 결과가 동시에 가능하다. 최상위 버전이 최신이어도 보존 행의 구버전이 남는다. **실제 두 코드의 이름은 count-only 로그만으로 확정할 수 없다.**

같은 merge·inputs_facts 경로에 합성 unresolved 2행을 넣어 **current=25 / no_data=477 / other=2**, inputs_current_rows FAIL을 재현했다(합성 수치이며 위 운영 관측 500/2/2와 구별). 정상 NA는 버전 혼합으로 보지 않는다. Main은 #409·#410 반영 후 새 수집으로 `other_calc=0`을 확인한다. 기존 행의 버전 표기만 강제로 바꾸거나 가드를 우회하지 않는다.

### B. IEX 스트림·재시도 상태와 종료 판정

실제 `stream_day`와 C 파서에 합성 gzip/pcap을 넣고 localhost 부분 응답·timeout을 주입했다. 공급자 파일이나 운영 네트워크 성공을 시험한 것이 아니다. process exit 순서는 **download / gzip / parser**다.

| 합성 경로 | exit code | 현재 결과 |
| --- | --- | --- |
| 정상 gzip·pcap | 0 / 0 / 0 | OK |
| gzip은 정상, 파서 입력 조기 오류 | 0 / -13 / 5 | GZIP_FAILED: 파서 오류가 유발한 SIGPIPE를 gzip 원인처럼 표시 |
| 실제 잘린 gzip | 0 / 1 / 0 | GZIP_FAILED |
| curl 내부 retry: 부분 응답+재응답을 같은 stdout에 연결 | 0 / 1 / 0 | GZIP_FAILED: 원본 정상 gzip이어도 재시도 스트림 오염 |
| 내부 retry 없이 첫 전송 timeout | 28 / 1 / 0 | GZIP_FAILED: 전송 원인 가림 |
| 다음 시도를 전체 새 상태로 시작 | 0 / 0 / 0 | OK |

**구조적 결함은 재현했다. 실제 run 최초 trigger가 전송 실패인지 파서 조기 오류인지는 개별 stderr·exit code가 없어 미확정이다.** 이 검증만으로 실제 IEX 원본의 정상·손상을 단정하지 않는다.

#400 최소 수정 권고(Main 구현): curl 내부 retry의 부분 stdout 재사용을 제거하고 시도마다 digest·byte count·gzip·parser·출력 상태를 새로 만든다. 독립 전송 실패와 파서 조기 종료가 유발한 SIGPIPE를 실제 gzip 손상과 exit 조합으로 구별한다. 단순히 모든 오류를 parser 우선으로 바꾸면 잘린 gzip의 EOF를 잘못 분류할 수 있다. 실패 무시·검사 생략·경계 완화는 하지 않는다.

## 3. 실제 시험 범위

| 검증 | 수행·결과 |
| --- | --- |
| 스트림 관련 기존 단위 테스트 | `test_iex_hist.py`의 real parser·broken gzip·size/MD5, **4 passed / 15 deselected** |
| 버전·정상 NA 기존 테스트 | `test_sec_qgv2.py`의 다른 버전 percentile 차단·정상 NA 사유 보존, **2 passed** |
| 리허설 판정 기존 테스트 | `test_central_v_rehearsal_workflow.py`의 행 버전·마지막 체결/상태·공급 실패·미측정, **고유 4개 최종 통과** |
| 추출 환경 실패 | 초기 판정 테스트 2개는 임시 추출물의 `.github` 누락으로 FileNotFoundError. `.github` 추출 후 해당 2개만 재실행해 통과; 제품 수정으로 계산하지 않음 |
| 합성 재현 | 스트림 6경로와 행 혼합 FAIL 재현. 검증용 임시 파일만 사용, tracked 코드 변경 없음 |

전체 테스트는 실행하지 않았다. 소스는 위 rehearsal SHA의 `providers/iex_hist.py:269,294,312,322`, `tools/sec_universe_shares.py:592,684`, `universe/sec_universe_shares.py:355`, `universe/sec_qgv2.py:300,359`, `qgv/qgv_official.py:368`, `tools/central_v_rehearsal_report.py:314,326,338`을 대조했다.

## 4. Main 이행 조건·다음 창

- #409·#410이 반영된 canonical을 #393→수정 #400→#403→#404→#405→#411로 전파한다. 허용 소스·가격 경계 가드와 운영/리허설 V 단계 동일성을 유지한다.
- **수정된 새 rehearsal SHA**로 기존 승인 범위의 비게시 리허설을 한다. 구 run의 Re-run은 구 SHA 검증이므로 수정 검증이 아니다. 정기·긴급 ALLSHARDS-1026과 분리하며 중복 실행을 만들지 않는다.
- 재리허설은 03:00~19:30 UTC 범위, 최근 거래일 측정은 11:00 UTC 이후를 우선한다. 실행 직전 다른 수집·배포와의 비중첩을 확인한다.
- 최종 후보에서 `other_calc=0`, 정상 NA 구분, `status=OK / publication=NEW`, Universe·D4 각각의 실제 분자/분모, strict VALID/VALID·consistent YES, JS MATCH·가드·시간·디스크·**최종 PASS 12/12**를 확인한다. NOT_MEASURED가 남으면 미검증으로 보고한다.
- 첫 게시 날짜는 리허설·점검표 후 **11/04 전 목표**로 제안하고 오너 승인 뒤 실행한다. #393→#400→#403→#404→**전환용 별도 all_shards·새 calc_version 숫자 재대조**→#405→#411 순서를 계획한다. 긴급 ALLSHARDS-1026의 목적·run을 재사용하지 않는다.
- #411은 #405 뒤 동기화하고 `freshFor`·`official`·숨김 상태·TARGET 핸들러 충돌을 검증한다. 수정·재리허설·첫 게시의 실제 성공은 **아직 없다**.
