# GSQ-011 Holdout 보호 상태 확인 실행 기록

**판정: `UNCONFIRMED`**. 보호와 소비 상태 모두 미확인이다. **`CONFIRMED_PROTECTED` 또는 미소비라고 확정할 근거가 없고, 실제 `CONSUMED` event를 확인한 것도 아니다.** QGV v2 착수 보류를 유지한다.

실행일: **2026-10-10 UTC**. source audit 시각: `2026-10-10T01:59:11Z` 및 같은 세션의 보완 검색. 읽기 기준 GitHub canonical: `8d7fcb55728920a4d9d8f39023c1b4d566cd3e13`(#94 병합). 권한: [GSQ-011](../pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md)의 **보호 확인만 실행, 기간 선택·사용 금지**. 검사 대상은 tracked filename·문서/소스·정책 metadata다. Holdout 파일·가격/수익률·label·결과·표본·기간·봉인 원문은 열지 않았다.

## 1. 실제 실행한 확인과 결과

| 확인 항목 | 실행 범위/방법 | 관측 결과 | 판정에 사용하는 의미 |
| --- | --- | --- | --- |
| canonical/current source 결속 | GitHub canonical fetch, `git rev-parse HEAD`, tracked filename 목록 | 위 SHA이며 이 작업의 코드/테스트/워크플로 변경 없음 | 이 기록의 저장소 검사 범위 고정 |
| 보호/소비 runtime registry | `git ls-files`로 `implementation/src`, `implementation/tests`, `implementation/tools`, `implementation/worker`, `.github/workflows`, `implementation/docs/coordination/governance`의 **331개 tracked 파일** 목록을 고정; text source/policy에 `final[ _-]?holdout`, `holdout[ _-]?consum`, `dataset.?split`, `trial.?ledger` 검색 | 해당 특정 패턴의 구현 match **0개** | 검사 범위에서 보호 registry·소비 event·DatasetSplit/TrialLedger 구현 증거 미확보. 다른 이름/개인 환경의 존재·부재를 확정하지 않음 |
| 넓은 Holdout reference 검색 | 같은 범위에서 case-insensitive `holdout` 추가 검색 | Web fixture 도구의 ‘Holdout을 호출하지 않음’ 설명만 확인 | fixture 설명은 대상 봉인/접근 로그/미소비 증명이 아님 |
| 봉인/ledger 이름 확인 | 전체 tracked **filename만** `holdout`, `freeze.manifest`, `trial.ledger`, `dataset.split` 검색 | 기존 `HOLDOUT_AND_ENTRY_CHECKLIST.md`만 match | 명명 기반 확인에 해당. 문서 존재가 봉인 manifest/ledger가 아님. 이름이 다른 artifact·외부 저장소의 내용은 조사하지 않음 |
| EVL 계약 | [EVL](../../../Investment-System1%20%C2%B7%20Experiment%20%26%20Validation%20Layer%20Specification%20v0.1.md) §3·5·10·11·13 | Final Holdout 격리, 1회 사용과 `HOLDOUT_CONSUMED=true`, 실패 후 재튜닝 재사용 금지, Freeze Manifest의 상태 결속을 **요구** | 사양이며 실제 gate/봉인/소비 ledger 구현 receipt가 아님 |
| v1/v2 승인 상태 | [QGV Standard v1](../qgv_scoring_standard/QGV_SCORING_STANDARD_v1.md) L174–179 및 GSQ-011 | v2 전 보호 확인 필요; 사용자 v2 착수 보류 | 이번 확인으로 v2/calibration/사용 승인 또는 v1 calibration 완료가 되지 않음 |
| 고정 false 선언 | [current_behavior_probe.py](../qgv_common_contract_vnext/missing_data_gate/current_behavior_probe.py) L192 | `real_pit_oos_run=False, holdout_consumed=False`는 characterization 반환 literal | 봉인 dataset별 registry/접근 로그·atomic gate와 연결되지 않은 고정 선언. 미소비 근거로 불채택; probe 미실행 |
| OOS label-only | [test_oos_partition.py](../../tests/test_oos_partition.py) | 기존 OOS partition 표지·calibrated/official 미승격 검사 | 실제 OOS/Calibration 실행·Final Holdout 보호/미소비 증거가 아님; test 미실행 |
| 저장소 보호 정책 | [AUTONOMY_GUARD_CONFIG.v1.json](../coordination/governance/AUTONOMY_GUARD_CONFIG.v1.json) | Frozen 변경 금지·append-only·운영 guard 정책 | write 보호 정책이며 Holdout 읽기 격리·optimizer ACL·single-use gate/과거 소비를 증명하지 않음. mode/ruleset 변경 없음 |

위 검색은 Python 표준 파일 읽기와 git/rg metadata 검사로 실행했다. application runner/provider/optimizer/probe를 import하거나 실행하지 않았다. 실제 봉인 데이터에 loader/거부 실험/dry run을 수행하지 않았다. 개인 저장소·기기·원격 저장 서비스·접근로그·소비 ledger를 연결/열람하지 않았으며 인증/Secret도 조회하지 않았다.

## 2. 세 판정의 적용

| 요청된 판정 | 필요한 증거 | 이번 결과 |
| --- | --- | --- |
| `CONFIRMED_PROTECTED` | 기존 등록/봉인 ID, owner의 무결성·격리 ACL·모든 loader/optimizer 경계·감사로그 coverage·atomic 1회 gate 및 기존 합성 gate 검증 receipt, 소비 상태 결속 | **미충족**. 계약 외의 대상별 구현/서비스 metadata receipt를 확보하지 못함 |
| `CONSUMED` | 대상 봉인 ID와 연결된 기존 접근/평가/소비 event 및 검증 receipt | **미확인**. 특정 event를 발견하지 못했지만 미소비라고 해석하지 않음 |
| `UNCONFIRMED` | 보호 또는 소비를 결론낼 근거 부족·owner/로그/대상 등록 상태 미확인 | **적용**. 현재 저장소 근거로 가능한 판정 |

논리적으로 **‘소비 event를 못 찾음’ ≠ ‘소비되지 않음’**, **‘사용을 금지한 계약 있음’ ≠ ‘보호돼 있음’**이다. Track A Frozen 및 CI/guard 성공도 Holdout 접근 격리·미소비 증명을 대신하지 않는다. 현재 판정은 namespace/기간·데이터를 새로 등록한 결과가 아니며 기존 runtime enum이나 소비 상태를 바꾸지 않는다.

## 3. 다음 확인에 필요한 owner metadata

사용자가 더 확인하려면 [기존 절차](HOLDOUT_AND_ENTRY_CHECKLIST.md#2-기간과-데이터를-열지-않는-보호-확인-절차)에 따라 **이미 존재하는 보호 대상의** owner metadata receipt가 필요하다. 이 요청은 새 기간 선택/등록이나 Holdout 사용 요청이 아니다.

- 등록 유무·opaque 봉인 ID·정책 버전·보관 위치 **종류**와 기존 무결성 검증 receipt.
- optimizer/일반 연구 계정의 읽기·수출 제한과 loader grant, 권한 변경 감사 coverage.
- 기존 접근/평가/소비 event 상태와 누락/중단/실패 실행의 노출 판단 근거. 원 로그/identity/토큰/기간/표본/label/결과를 공개하지 않음.
- atomic 1회 gate 정책 및 **기존 합성 검증 receipt**, 상태를 초기화·고치지 않았다는 owner 결속.

owner가 기존 등록이 없다고 확인하면 그 사실을 남기고 판정은 `UNCONFIRMED` 안에서 등록 미확인/미등록을 구분한다. 이 작업에서 대체 Holdout을 선정하지 않는다. owner receipt가 확보되기 전에는 상태를 보호/미소비로 승격하지 않으며 **v2 착수 보류·Holdout 사용 금지**를 유지한다.
