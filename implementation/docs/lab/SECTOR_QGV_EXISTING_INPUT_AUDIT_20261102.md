# #467 후속 — 기존 실자료 원본을 열어 확인한 결과

후속: [지정 접수 건의 백업 탐색·C2 생성 기록·단계별 실제 수](SECTOR_QGV_TARGET_ACCESSION_C2_20261102.md).
완전 C2의 현재 판정은 **기존 생성 미확인**이며, 아래 '미복구'를 생성 확인으로 해석하지 않는다.

평가일 **2018-02-16**. 판정은 **입력 복구·재무 연결 부분 완료 / 첫 QGV 비교 차단**이다.
실제 QGV 점수 계산 **0회사**, 순위 비교 **0회사**. PIT 재무 행 계산 3건을 QGV 점수 계산으로 세지 않는다.

## 기준과 이번 변경

- 시작: #467 `research/sector-liquidity-diagnostics-20261102`, `21a3cbe42a43253b66afc14cc107ffecab4af282`.
- #432 파일럿: `research/bt-data-pilot-alpaca-probe-20261031`, `26396d1f9f71706ae6deaa1ee51797bebb4d9ffc`.
- 기존 #464/#465 계산·CPI·정규화 코드와 #467 사전등록을 유지한다. 책과 합성 시험은 다시 확인하지 않았다.
- 새 [오프라인 원본 점검 도구](../../experiments/sector-qgv-first-20261102/audit_existing_archives.py)는
  보관 ZIP의 원래 SHA sidecar 및 개별 원본 manifest를 검증하고 분류 증거·입력 상태를 비공개로 만든다.
  수집 기능과 점수 계산은 없다. 실제 재무 행만 기존 `exp_deciles.pit.compute_row`로 구성한다.

이전 보고는 알려진 release 이름·인계 위치 중심 점검이었다. 이번에는 실제 archive 내부까지 열었다.
따라서 **모든 SEC 원본이 없다는 뜻이 아니다.** 아래 복구 원본은 실제로 읽었고,
원래 파일럿의 로컬 전용 SEC 묶음과 구분한다.

## 원본·manifest 접근 결과

| 확인 위치 | 직접 확인한 내용 | 상태 |
| --- | --- | --- |
| #432 `REPLAY_PERIOD_V_LEDGER.sh`, `connect_pit_v.py` | 이전 계산은 v03의 `2016q1.zip`·회사별 companyfacts, v05의 submissions·history를 사용 | 코드 직접 열람. 해당 이전 로컬 루트는 이번 환경에 없음; 원격 백업 위치 미확인 |
| 비공개 raw release `bt-data-pilot-v06-alpaca-41152748825-1/private-inputs.zip` | 원본·정규화·요청·manifest, SEC 분류 파일 없음 | 다운로드·원래 ZIP hash 검증 성공 |
| `bt-data-pilot-v06-long-41168930483-1/summary.zip` | 달력 원본·manifest·집계·재사용 목록, SEC 분류 파일 없음 | 다운로드·원래 ZIP hash 검증 성공 |
| 같은 release의 `AMD.zip` | 보관된 2018년 SIP 응답에서 S일 봉 1개 확인 | ZIP와 응답 manifest hash 일치. 가격값은 비공개. 신원·분할 기준 적격으로 자동 승격하지 않음 |
| `raw-c21-store-36305927245/c21-raw-store-36305927245.zip` | 14,281개 ZIP member, 6,808개 manifest. 2018년까지 accession이 있는 SEC 공시 본문 80개·헤더 26개 원본 hash 대사 | 원본 복구 성공. FSDS 파일 없음. 분류·합병 원문 직접 확인 |
| `sec-universe-raw-2026-10-29-all-shard0` | 249개 member: companyfacts·submissions·당시 운영용 cover 등. 2018년 분류 헤더/FSDS 없음 | 다운로드·원래 archive hash 검증 성공. 나머지 shard까지 전수 확인한 것으로 세지 않음 |
| 저장소 `implementation/data/raw/manifests` | 원본을 가리키는 manifest는 있으나 checkout의 blobs에는 원본 없음 | manifest와 원본 부재를 구분; 위 C21 archive에서 복구 |

위 다운로드에서 권한 오류는 없었다. **접근 불가가 아니라, 특정 원본의 보관 묶음 부재 또는
이전 로컬 백업 위치 미확인**이다. SEC/Alpaca/KIS API 신규 수집은 하지 않았다.

## 직접 구성한 당시 분류 증거

보관 헤더의 `SUBJECT COMPANY` 블록에서 CIK·SIC를 읽었다. 소유 공시의 보고자(FILED BY) SIC를
대상 기업 SIC로 잘못 쓰지 않았다. 26개 관측은 4개 발행사이고, 두 후보 섹터 대응은 2개 발행사다.
해당 2회사 각각의 마지막 사용 가능 관측을 비공개 증거표에 기록했다.

- 고정 발행사 ID는 `SEC-CIK:<10자리 CIK>`다. 검증되지 않은 대표증권 ID는 null로 유지했다.
- 원천 SIC·설명, accession, 원문 URL·hash, 공시일, 원문 접수시각,
  `schedule.usable_from`의 가용일을 기록했다. S의 공시 cutoff는 2018-02-08이다.
- 원천에 분류 적용 시작일은 없어 **미상(null)**이다. 공시일을 적용 시작일로 쓰지 않았다.
- SIC 7372(포장 소프트웨어)→정보기술, SIC 4841(케이블/유료방송)→경기소비재의 미디어는
  확인된 책의 업종 설명에 따른 **연구용 대응**이다. 공식 GICS 대응이라고 주장하지 않는다.
  버전 `book10-sic-observed-evidence-v1-20261102`와 대응 근거를 행마다 적었다.
- 원문에 각 회사의 2015년·2016년 합병/기존 주식 소멸 또는 전액 현금 전환이 기록돼 있었다.
  당시 분류 관측을 복원할 수 있어도 해당 옛 증권을 S의 적격 표본으로 넣을 수 없다.
  같은 이름의 이후 기업이나 현재 티커로 이어 붙이지 않았다.

회사별 원문·이벤트 상세와 날짜는 비공개 `candidate-classification-evidence.json`에 있다.
이 2개는 #432 고정 10회사 밖의 보조 조사 표본이며, 원래 파일럿 10개와 합쳐 12개 적격으로 세지 않는다.

## 재무 연결과 3열 비교의 실제 상태

기존 #432 고정 10회사 중 C21에 있는 companyfacts 원본은 3개였다. 각 원본 hash를 검증하고,
기존 calc 23.1 PIT 경로로 S까지 사용 가능한 재무 행을 **3개 실제 구성**했다.
나머지 7개는 확인한 C21 archive 안에 해당 companyfacts가 없다. 이것은 SEC 전체에 자료가 없다는 뜻이 아니다.
3개 행은 `LIVE`이나 `SIC_AS_FILED_NOT_AVAILABLE`을 유지하며, 점수화·투자 적격을 뜻하지 않는다.
후일 접수된 재무를 섞지 않았고 최신 사용 공시·가용일·누락 필드를 행에 보존했다.
보관 companyfacts는 후일 수집본에서 공시일로 재구성한 입력이다. 2018년 당시에 수신한
벤더 전송본·수정 빈티지를 복원했다는 의미는 아니다.

| 평가일 | 조사 범위 | 실제 산출 |
| --- | --- | --- |
| 2018-02-16 | #432 고정 10회사 | 원본 재무 3회사 복구·PIT 행 3개. 해당 10회사의 당시 SIC 원본 0개 |
| 동일 | 보관 공시의 두 후보 섹터 보조 2회사 | 당시 분류 관측·연구용 대응 2개, S에 사용할 옛 증권 0개 |
| 동일 | 승인된 전체 C2 모집단 | 입력 manifest 미복구. 고정 10회사나 현재 Universe504로 대체하지 않음 |

| 요청한 비교 열 | 이번 상태 |
| --- | --- |
| ① 기존 점수·기존 순위 | 미산출 |
| ② 같은 점수·섹터 순위 | 미산출 |
| ③ 후보 점수·섹터 순위 | 미산출 |

두 후보 중 분류·재무·S의 적격 신원이 함께 충족된 회사가 없어 실행 섹터를 확정하지 않았다.
기존 사전등록의 가중치도 활성화하지 않았다. 순위 이동 사유는 **순위 미산출로 해당 없음**이다.

calc 23.1의 `qgv_v2._cross`는 유효 비교 값이 8개 미만이면 `CROSS_SECTION_TOO_SMALL`을 돌려준다.
하지만 임의의 8회사를 채우는 것도 허용된 C2 복원이 아니다. 이번에는 승인된 C2 입력이 없어
점수 함수를 호출하지 않았고, 소표본 점수·현재 점수·다른 평가일 점수로 빈칸을 채우지 않았다.
한 회사만 비교하더라도 그 회사의 백분위가 의존하는 원래 C2가 필요하다.

## 최초 차단, 필요한 원본과 최소 다음 행동

첫 차단은 **고정 파일럿 중 S에 쓸 회사의 당시 분류 원본**이다. 복구한 정보기술 조사 후보는
재무와 S 가격을 이미 보유하지만 해당 공시 헤더·증권 종류 근거가 없다.

최소 구체 대상은 **CIK 0000002488, 10-Q accession `0000002488-17-000227`**이다.
보관 companyfacts에서 확인한 공시일은 **2017-11-02**, 기존 규칙의 가용일은 **2017-11-10**이다.
필요 원본은 해당 SEC 공시 헤더/접수 색인과 표지다. 필요한 필드는 대상 CIK, 당시 SIC,
공시/접수일, 증권 종류·당시 표지 신원이며 분류 시작일은 없으면 미상으로 둔다.
`filed <= 2018-02-08`인 원본을 사용하고, 그 뒤에 발표된 연차보고서로 대신하지 않는다.

**최소 다음 행동 하나:** 위 한 접수 건의 헤더·표지가 있는 기존 비공개 백업을 찾아 원본과
manifest를 복구한다. 기존 보관본이 없다면 그 한 접수 건을 확보하는 별도 최소 수집이 필요하지만
이번 작업에서 실행하거나 실행 승인을 받은 것으로 처리하지 않는다.

이 한 건을 복구해도 **C2 모집단 manifest 미복구**는 별도 점수화 차단으로 남는다.
그 입력에는 S의 구성원·발행사/대표증권·시총 적격, #465 CPI 근거와 동일 S의 PIT Q/G/V 입력이 필요하다.
전체시장 신규 수집을 이번에 제안·실행한 것으로 확대하지 않는다.

## 비공개 산출물·재현·검증 범위

승인된 기존 임시 연구 루트 아래:
`/workspace/private-bt-data-pilot-v06/continuation/sector-qgv-input-audit-20261102/`.
새 회사별 산출물은 `result-v2/`에 0700 디렉터리·0600 파일로 보존한다.
이는 **로컬 비공개 보존**이다. 결과를 원격 비공개 release에 업로드했다고 주장하지 않는다.
대신 원격의 기존 두 archive와 일반 연구 가지의 도구로 다시 만들 수 있게 했다.

- `classification-observations.json`: 당시 원천 분류 26관측.
- `candidate-classification-evidence.json`: 두 후보 섹터 2회사 대응·원문·가용일·합병 차단.
- `pilot-input-status.json`: 고정 10회사별 원본 존재·미확인 상태.
- `pit-financial-rows.json`: 원본 계보와 실제 PIT 재무 3행, 값 포함(비공개).
- `stored-signal-price.json`: 기존 응답의 S 봉과 계보(비공개).
- `historical-source-inventory.json`, `summary.json`, `manifest.json`: 복구·차단·입출력 hash.

재현(이미 보관된 archive를 내려받은 뒤; 명령 자체에 외부 수집 없음):

```sh
PYTHONPATH=implementation/src python implementation/experiments/sector-qgv-first-20261102/audit_existing_archives.py \
  --raw-zip <private>/c21-raw-store-36305927245.zip \
  --amd-zip <private>/AMD.zip \
  --out <new-private-output>
```

입력 옆에 원래 `.sha256` 파일이 필요하다. 기존 출력 경로와 git checkout 안 출력은 거부한다.
검증은 **보관 실자료의 자체 입력 검증·PIT 행 구성**이며 전체시장 점수 검증이나 독립 감사가 아니다.
최종 도구 실행 exit 0, 결과 8파일의 앞선 실제 입력 실행과 바이트 일치,
출력 manifest hash·0700/0600 권한·재무 공시 cutoff·분류 시작일 미상·합병일의 S 이전 여부를 확인했다.
방향 가드 0건, `git diff --check` 통과. 원격 CI 결과는 PR의 조회 시각과 함께 별도 보고한다.
책 원문·합성 계산 시험은 반복하지 않았다. 화면·공용 가드·워크플로·운영 계산은 변경하지 않았다.
