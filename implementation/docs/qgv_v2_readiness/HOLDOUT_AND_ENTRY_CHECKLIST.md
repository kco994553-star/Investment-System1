# QGV v2 진입과 Holdout 보호 확인 체크리스트

확인일: **2026-10-10 UTC**. 기준 canonical: `ee039041ae7f5cb94e6a127930c7e43effb811ec`. 상태: **PREPARATION_ONLY / HOLDOUT_PROTECTION_UNCONFIRMED / V2_NOT_STARTED**. 마지막 표시는 이번 준비 작업에서 v2를 실행하지 않았다는 뜻이며 외부 개인 작업 전체의 실행 이력을 확정하지 않는다.

**현재 canonical의 계약은 Holdout 격리와 1회 사용을 요구하지만, 계약만으로 실제 보호 상태를 확인할 수 없다.** v2 실데이터 calibration 전에 보호 상태를 명시적으로 확인하고 PIT/OOS/Calibration 근거와 별도 사용자 결정을 확보해야 한다. 이 문서는 기간·시작/종료일·종목·표본을 선택하거나 추천하지 않으며 Holdout 입력·label·결과를 열람·사용하지 않는다.

## 1. 현재 확인 범위

| 근거 | 확인한 의미 | 의미하지 않는 것 |
| --- | --- | --- |
| [QGV Standard v1](../qgv_scoring_standard/QGV_SCORING_STANDARD_v1.md) 마지막 절 | v1은 STANDARD v1 / UNCALIBRATED. v2 전에 Holdout 보호를 명시 확인하고 PIT/OOS/Calibration 근거와 별도 결정을 요구함 | v2 착수·calibration 완료·Holdout 미소비 증명 |
| [EVL 계약](../../../Investment-System1%20%C2%B7%20Experiment%20%26%20Validation%20Layer%20Specification%20v0.1.md) §2·3·5·10·11·13 | Development / Calibration / Final Holdout / Live Forward 분리, append-only Trial Ledger, Final Holdout 1회 사용, 실패 후 재튜닝 재사용 금지, Freeze Manifest의 소비 상태 결속 요구 | 격리 저장소·ACL·optimizer 차단·atomic 1회 gate의 실제 구현 |
| [Track A 상태](../../../Investment-System1%20%C2%B7%20TRACK_A_REAL_DATA_STATUS.md), PR #3 동결 기록 | 역사적 REAL-DATA 기준선의 FROZEN_VERIFIED 범위를 보존 | strict zero-lookahead·새 split·OOS/Calibration 또는 Final Holdout 사용 승인 |
| [repository guard config](../coordination/governance/AUTONOMY_GUARD_CONFIG.v1.json) | Frozen/evidence·append-only 보호 정책 존재 | Holdout 전용 접근통제·읽기 차단·1회 소비 gate 및 GitHub 실제 enforcement 확인 |
| [historical 검증 코드](../../src/investment_system/validation/historical.py), [OOS partition 테스트](../../tests/test_oos_partition.py) | candidate 평가와 OOS label-only 경계, OOS/calibrated/official 미승격 | 검증된 OOS·실제 calibration·Final Holdout 보호 |

이번 확인은 위 HEAD의 **tracked** `implementation/src`, `implementation/tests`, `.github/workflows`, `implementation/docs/coordination/governance`의 파일 목록·문서/소스 검색이다. `final[ _-]?holdout`, `holdout_consumed`, `dataset.?split`, `trial.?ledger`에 해당하는 실제 런타임/테스트/워크플로 구현 파일은 이 범위에서 발견하지 못했다. 일반 `calibration` 문자열이나 가격 출처 대조 테스트는 모델 calibration/Final Holdout 보호 구현의 증거로 세지 않는다.

확장 소스 검색에서는 [current_behavior_probe.py](../qgv_common_contract_vnext/missing_data_gate/current_behavior_probe.py)의 반환값에 `holdout_consumed: False`라는 literal이 있다. 이 코드의 고정 선언은 봉인 dataset별 소비 registry·접근 로그·1회 gate의 증거가 아니며 실제 미소비 판정에 사용하지 않는다. probe는 실행하지 않았다.

검색 범위 밖인 개인 저장소·기기·원격 서비스·다른 branch·삭제된 기록·외부 접근로그는 확인하지 않았다. 따라서 보호 상태는 **UNCONFIRMED**, 소비 상태는 **UNCONFIRMED**다. 레코드 부재·runner 부재·`HOLDOUT_CONSUMED` 문자열 부재를 `false` 또는 격리 성공으로 바꾸지 않는다. 기존 EVL 문서의 등록 당시 Track A 미동결 설명은 후속 PR #3의 역사 기준선 동결과 구분하며, 그 동결로 이후 모든 EVL/v2 단계가 자동 승인되는 것은 아니다.

## 2. 기간과 데이터를 열지 않는 보호 확인 절차

1. **책임 owner와 보호 대상 등록 여부 확인**: owner가 개인 환경의 기존 봉인 manifest/registry에서 등록 여부·불변 ID·보호 정책 버전·보관 위치 종류·생성/변경 receipt를 확인한다. 미등록이면 `UNREGISTERED`라는 사실만 기록하고 이 작업에서 새 기간/데이터를 선정하지 않는다. 본문·날짜·표본·회사 목록·수익률·label·평가지표는 읽거나 공개하지 않는다.
2. **무결성·접근 경계 확인**: 봉인 manifest와 저장소 ACL/version-lock, 접근 가능한 역할 및 optimizer·일반 연구 계정의 권한을 메타데이터로 비교한다. manifest hash가 실제 권한/불변성의 증거를 대신하지 않는다. 실제 봉인 파일을 열어 검증하는 대신 이미 생성된 검증 receipt와 저장 서비스의 metadata를 사용한다. 그 증거가 없으면 미확인이다.
3. **실행 진입점 확인**: loader/optimizer/Calibration/runner가 어떤 dataset ID·grant를 허용하고 거부하는지 소스·정책·기존 합성 검증 receipt로 확인한다. 명명 규칙이나 UI 숨김만으로 격리했다고 판정하지 않는다. 실제 데이터로 거부 실험·로드·dry run을 하지 않는다.
4. **소비·접근 기록 확인**: append-only ledger의 봉인/접근/평가/소비 event ID·state·검증 결과와 감사 범위를 확인한다. identity·token·URL query·기간/표본/결과 값은 개인 환경에 남긴다. 권한 변경·읽기·수출·optimizer 접근을 놓친 로그 기간이 있으면 `UNCONFIRMED`다. 실패·중단된 실행도 결과가 노출됐는지 판정할 근거가 필요하다.
5. **1회 gate 확인**: 동시 실행·재실행·실패 후 재사용을 막는 atomic 소비 정책과 기존 합성 검증 receipt를 확인한다. `HOLDOUT_CONSUMED=false`라는 값 하나만으로 gate 구현과 과거 미접근을 확정하지 않는다. 이 확인 작업에서 값을 생성·변경·초기화하지 않는다.
6. **보호 판정 receipt 작성**: owner·감사자·확인 HEAD/정책 버전·scope·판정·미확인 사유·비밀 없는 evidence 참조만 결속한다. 이미 존재하는 개인 evidence를 공개 Git으로 복사하지 않는다. 현재 작업의 공개 문서는 확인 방법과 미확인 상태만 남긴다.

| 판정 | 필요한 근거 | 다음 동작 |
| --- | --- | --- |
| UNREGISTERED | owner가 기존 등록이 없음을 확인한 metadata receipt | 기존 조건 유지. 새 Holdout 선정은 별도 사용자 결정 |
| UNCONFIRMED | owner/manifest/ACL/log/one-use gate 중 하나라도 미확인 | v2 실데이터 calibration 및 Holdout 사용 진입 차단 |
| PROTECTION_VERIFIED | owner·봉인 무결성·격리 ACL·전 진입점·충분한 감사로그·1회 gate의 일치 receipt | 보호 조건 확인만 완료. v2 승인이나 사용 승인은 별도 |
| CONSUMED | 기존 소비 event/receipt | 기존 소비 상태를 보존. 실패 후 재튜닝·재사용 금지 |
| 노출 의심 / UNCONFIRMED | 접근 범위의 문제·감사로그 공백 | 소비/미소비를 확정하지 않고 owner와 사용자에게 판단 요청 |

이 표의 판정명은 문서상 확인 상태이며 기존 runtime enum이나 소비 정책을 새로 구현한 것이 아니다. `PROTECTION_VERIFIED`와 소비 상태의 확인은 각각 기록해야 한다.

## 3. QGV v2 진입 체크리스트

아래 체크는 **제출할 근거 목록**이다. 기간 선택·실행·신규 임계값·새 방법론/가중치 설계가 아니다. 확인되지 않은 항목을 PASS로 채우지 않는다.

보호 확인 후의 사전 연구 실행 범위 결정과, PIT/OOS/Calibration 근거를 제출한 뒤의 v2 채택/승격 결정은 다른 단계다. 근거를 준비하라는 지시만으로 calibration 실행이나 Holdout 사용을 허가받았다고 해석하지 않는다.

### 보호·권한·버전

- [ ] 위 절의 Holdout 보호·소비 판정 receipt가 있으며 보호가 명시 확인됐다.
- [ ] v1 정의·adoption receipt·기존 결과를 보존하고 v2를 별도 버전/namespace/artifact로 유지한다.
- [ ] v2 착수 목적·정확한 범위·owner·실행 권한이 별도 사용자 결정으로 기록됐다. v2 준비나 보호 확인은 Holdout 사용 권한이 아니다.
- [ ] 기존 core score·Official/Custom·Pre-Tax·invalidation·Promotion 경계를 유지한다. 코드/데이터/정책에 바뀔 범위를 사전 명시한다.

### PIT 입력과 lineage

- [ ] 각 dataset·Universe·식별/주식 종류·기업행위·재무·가격·Macro 입력의 권리, 원본 hash/vintage, 당시 `available_at <= decision_time` 근거가 결속됐다.
- [ ] current revised history·나중 편집된 membership·사후 조정 series·누락값·후기 filing·source fallback의 lookahead/불확실성을 분리했다. Track A retrospective PIT 한계를 strict PIT로 승격하지 않았다.
- [ ] `Dataset → Experiment → WalkForward → Robustness → ProfileCandidate → OfficialProfile` lineage와 source invalidation 전파가 확인됐다.
- [ ] 실제 prediction 시각/버전과 사후 outcome을 분리한다. prediction-realized join을 OOS/calibration으로 재명명하지 않는다.

### OOS 근거

- [ ] 기존 EVL이 요구하는 split·rolling/expanding 비교·label/rebalance에 따른 purge/embargo가 **사전 등록된** 연구 계약과 일치한다. 이 문서에서 구체 기간을 정하지 않는다.
- [ ] 후보 선택/튜닝에 노출되지 않은 OOS의 근거, 코드/data hash·seed·search budget와 실패/중단/배제 trial을 포함한 ledger가 있다.
- [ ] 기존 robustness·negative control·cost/delay·multiple-testing 기준의 결과가 있고 `NO_EVIDENCE_OF_SKILL`/`PROFILE_NOT_DISTINCT`를 임의 승격하지 않는다.
- [ ] 단일 historical run·사후 benchmark·모의 fixture PASS·높은 수익률만으로 OOS/PIT를 주장하지 않는다. 승인되지 않은 숫자 임계값을 추가하지 않는다.

### Calibration 근거와 v2 결정

- [ ] Development에서 모델/parameter 선택을 마감한 receipt가 있으며 Calibration은 기존 EVL의 threshold-only 범위와 일치한다.
- [ ] 보정 대상·입력·출력·사용 dataset 상태·실행 전후 버전·선택/실패 trial·민감도/안정성의 근거가 있다. 새로운 산식·가중치·threshold 범위는 이번 준비 문서에 없다.
- [ ] Calibration/OOS의 평가와 Holdout의 봉인 상태를 분리하고, Holdout을 튜닝/feature 선정/반복 평가에 쓰지 않았다.
- [ ] PIT/OOS/Calibration의 실제 근거와 남은 미확인을 사용자에게 제시해 v2에 대한 별도 결정을 받는다. v1의 `UNCALIBRATED`를 재라벨하지 않는다.

## 4. 이 준비의 종료 조건

확인 방법과 진입 체크리스트가 준비돼도 **Holdout 보호·미소비, PIT/OOS/Calibration 실증, v2 실행 승인은 미확인/미결정**으로 남는다. 후속 사용자 결정은 책임 owner의 보호 metadata receipt 제출, v2의 실제 착수 범위 및 필요한 경우 Holdout 선정/사용에 대한 별도 결정이다. 이번 작업에서는 해당 기간·데이터·결과를 선택하거나 열지 않는다.
