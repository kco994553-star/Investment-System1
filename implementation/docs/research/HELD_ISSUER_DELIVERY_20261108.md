# 보유 발행사 전달 자료 구현 계획·계약

오너 2026-11-08 긴 작업 대기열 4절 및 공통 분류·95% 목표 보완을 구현한다.
기존 #523의 입력/원결과/분류 정체성 검사를 재사용하며 계산은 실행하지 않는다.
파일 소유: research/held_issuer_delivery.py, tools/held_issuer_delivery.py, 관련 연구 시험/합성 fixture만 Codex.
화면·Worker·공용 가드·워크플로는 Main 담당이다.

## 구현 계획

- [x] 수작업 합성 결과의 코드/발행사·분모·선정된 기본 요소·결손을 고정하고 실패 시험을 작성한다.
- [x] `project_delivery(job)`가 보유 재무 발행사 집합을 기존 held 자료에서 가져와 검색 색인, 발행사별 상세, coverage, manifest를 생성한다.
- [x] 원시 계산/점수화 없이 기존 결과의 상태·값을 대사한다. 원래 비교집단을 보존한다.
- [x] `verify_delivery(files)` 및 네트워크 없는 CLI로 해시·누락·중복·다른 평가일·범위 혼합·2MiB 상한을 검사한다.
- [x] 기존 비공개 입력에서 새 투영만 실행하고 원격 보존·재열기 확인 후 Draft PR/계약을 Main에 인계한다.

검토 초점: 같은 발행사의 여러 코드 행, 색인에는 있으나 상세 없는 발행사, 분류 미확인 기업 누락,
비교집단8004를 보유1057로 오인하는 표시, 정상 점수0과 결손null 혼동.
각각 변경 시험에서 독립적으로 확인한다.

## 계약

검색/상세/manifest는 `held-issuer-index/1`, `held-issuer-detail/1`, `held-issuer-delivery/1`이다.
원래 issuer_id와 분석 행 company_id를 보존하며 티커는 카탈로그 관측 문자열이다.
외부 고정 증권 ID를 새로 만들지 않는다. 운영504의 관련 코드 행은 별도 목록이다.
원결과 참조·SHA와 평가일·입력 스냅샷·모델/분류 버전은 manifest의 context에 묶는다.
분류 근거는 회사 소개 원문 전체나 증권 유효기간 증명과 다르다.
발행사 Q/G와 공식 Q 관문 입력, 실제 gate_status/총점, 증권 가격/기술은 별도 필드다.
가격·기술 미연결은 null/사유이며 발행사 Q/G 조회를 막지 않는다.

한 색인이 2MiB를 넘을 때만 결정적으로 나눈다. 각 상세와 manifest도 같은 상한을 따른다.
Main은 먼저 manifest와 색인만 읽고 선택한 발행사의 상세를 요청한다.
상세 SHA/크기/issuer_id/context_hash를 확인하고, 실패하면 해당 상세를 연결 오류로 표시한다.
새 묶음은 전체 무결성 검사 후 교체한다. 검증 실패를 빈 정상 목록으로 바꾸지 않는다.

coverage는 코드 행과 고유 발행사를 따로 센다. 고유 발행사의 축/동시/총점 유효는
원래 한 코드 행에서 그 단계가 완료된 경우이며 서로 다른 행의 축을 조합하지 않는다.
기본 선택 요소의 필수 구성요소 확보/원지표/요소점수와 Q/G/V/동시/총점은 별도다.
선택 요소 목록이 미확정이면 원래 분모에 남고 DEFAULT_SELECTION_UNRESOLVED로 센다.
필수 구성요소 존재는 유효성 통과와 다르다. per-factor coverage는 기본 모형 목표와 별도다.
95% 목표는 원래 모집단의 Q/G/V 동시 산출 및 최종 총점이 모두 있는 기업이며,
전체시장 분모와 커버리지는 미확정이면 null이다. 현재 기본 요소·관문·최소20·strict는 바꾸지 않는다.

## 검증과 실제 투영 범위

변경 시험: `PYTHONPATH=implementation/src python -m pytest -q implementation/tests/research/test_held_issuer_delivery.py` — 13통과.
CLI: `PYTHONPATH=implementation/src python implementation/tools/held_issuer_delivery.py --job <private-job.json> --output <new-private-dir>`.
합성만 `--synthetic` 사용. 동일 출력 경로 덮어쓰기를 거부하며 임시 디렉터리의 바이트를 다시 검증한 후 교체한다.
공개 fixture: `implementation/tests/fixtures/held_issuer_delivery/manifest.json`.
A의 Q=0은 유효값, B의 미분류는 원래 분모 유지, A의 두 관측 티커는 증권 신원 증명이 아니다.
A의 공식 Q 관문 입력 CONNECTED와 실제 gate UNKNOWN은 다른 상태다. 모든 총점은 null이다.

2026-11-04 보유 원결과 1,057발행사/1,512티커 관측을 1개 색인과 1,057개 상세로 투영했다.
운영504와 겹치는 고유 발행사 494. 전체 1,060파일/15,704,755bytes:
색인 1,029,205bytes, 상세 10,924~21,023bytes, manifest 136,292bytes, coverage 44,363bytes.
원결과의 모든 상세 축·순위·총점·관문·표시 요소 상태/점수와 전수 대사했다. 점수 재계산 0회.
보유1057 상세의 상대점수 비교집단은 기존 카탈로그8004의 유효 집합이다. 1057로 재점수화하지 않는다.

95% 목표 측정은 원결과 재집계다. 운영504 코드행 Q232/G320, 고유501발행사 Q232/G320;
보유1057 Q494/G670, 카탈로그8004 Q495/G671. 모두 V/동시/최종총점 0건이다.
기업 기준 QGV+최종총점 목표 최소 수는 각각 476/501, 1005/1057, 7604/8004이며 현재 모두 미달이다.
원래 분모는 유지하며 전체시장 목표 실측은 분모 미확정으로 null이다.
필수 입력 존재·모든 기본 원지표·모든 기본 요소점수도 각각 별도 필드다. 한 요소의 성공을 전체 완료로 세지 않는다.

Main 요청: 기존 인증 경로의 별도 허용 prefix에 manifest→index→선택 issuer 상세 조회를 연결한다.
manifest와 개별 바이트 SHA/size/context를 검사하고, URI의 issuer_id는 이미 있는 발행사 ID 그대로 사용한다.
기존 Worker 경로 허용·판독기·화면은 Main 변경 사항이며 이 PR은 수정하지 않는다.
브라우저 통합/인증/배포/외부 API/성과 검증은 수행하지 않았다.

## Main 고정 경로 협의 반영 — SHARDS

#437 6721372088의 제한된 Worker 경로에 맞춰 `layout=SHARDS`를 추가했다.
기존 개별 issuer 출력은 재현 가능하게 남기며 새 `held-issuer-sharded/1`은 표시 투영만 바꾼다.
`expanded-index.json` → `expanded-detail/{sha256(issuer_id UTF8)[:2]}.json`.
저장 조각 키는 신원 ID가 아니다. 실제 issuer_id/analysis_row_id는 기존 값 그대로다.
각 파일에 요약 ref/SHA, 평가일, 원래 모집단·점수 비교집단·입력/분류/모델 버전 및 해시,
생산자 전체 SHA를 같은 identity/hash로 묶는다. 지정 shard가 상한을 넘으면 실패하며 임의 재분할 규칙을 만들지 않는다.
Worker의 `part=expanded_index|expanded_detail`, `shard=^[0-9a-f]{2}$` 외 경로 허용은 요청하지 않는다.
Main은 인증된 manifest SHA와 각 파일·현재 요약의 identity를 확인해야 한다. 자체 해시만으로 진위를 입증하지 않는다.

`delivery_summary`는 기존 #523 요약의 path/ref/SHA, `producer_sha`는 이 투영 코드를 실행한40자리 SHA다.
source snapshot·분류/모델/모집단·원결과 identity가 요약과 다르면 생성하지 않는다.
`verify_shards`는 전체 파일·중복·누락·조각 소속·색인/상세 상태와 identity·크기·해시를 검사한다.
합성 1색인/2조각: `implementation/tests/fixtures/held_issuer_shards/` (정상·미확인·다중 티커 및 거부 기대 설명 포함).
이전 ISSUER_FILES 검증13건에 새 조각/미측정/원래 snapshot에 묶인 readiness 검사3건을 더해16통과했다.

## 95% 원인 분해

coverage는 원래 모집단별 context와 source refs를 붙이고, any_raw/any_factor_scores 및
모든 기본 선택 원지표/요소점수를 분리한다. `any_*`는95% 달성 기준이 아니다.
원인 분류: 분류/회계/기간/주식 기준/가격/산식 적용/관문/표본/증권/EV.
`count`는 정확 집계 가능할 때만 수치다. `known_affected`, `known_not_affected`, `unassessed`는 분모와 대사하며
미측정이 남으면 count:null이다. 여러 원인은 겹치므로 합쳐 전체 미산출 수로 쓰지 않는다.
MISSING_INPUT만으로 기간 불일치나 산식 부적합을 확정하지 않는다. 관문 UNKNOWN과 VALUE_EXCLUDED는 별도 원래 counts도 보존한다.
`operating_v_readiness`와 `operating_v_resume`를 지정하면 보존 snapshot의 완전 일치·평가일·선택 요소·구성원 검사를 거쳐
기존 비가격/가격 대기 진단을 재집계한다. 원시 비율이나 점수 계산을 다시 하지 않는다.
확장은 기존 input-gaps를 재사용하며 unknown/범위 미확인을 가격 결손 확정으로 바꾸지 않는다.
예상 최종총점 증가 수는 추가 증거 전 null이다. 가격만 확보하면 해결된다는 의미가 아니다.
